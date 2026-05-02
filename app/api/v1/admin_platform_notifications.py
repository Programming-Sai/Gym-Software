from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import cast, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.notifications import Notification, NotificationRecipient
from app.models.users import User
from app.schemas.admin_platform_notifications import (
    AdminPlatformNotificationBroadcastRequest,
    AdminPlatformNotificationOut,
    AdminPlatformNotificationSendRequest,
    AdminPlatformNotificationSendResponse,
)
from app.services.audit_log_service import write_audit_log
from app.services.fcm_service import fcm_service


router = APIRouter(tags=["Admin | Platform Notifications"])


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def _admin_marker(*, admin: User, extra: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "sent_via": "admin_platform",
        "sent_by_admin_id": admin.user_id,
        "sent_by_admin_role": admin.role,
    }
    if extra:
        base.update(extra)
    return base


@router.post("/broadcast", response_model=AdminPlatformNotificationSendResponse)
def broadcast_platform_notification(
    payload: AdminPlatformNotificationBroadcastRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    user_query = db.query(User.user_id).filter(User.status == "active")

    segment: dict[str, Any] = {"audience": payload.audience}
    if payload.audience == "role":
        if not payload.role:
            raise HTTPException(status_code=400, detail="role is required when audience=role")
        user_query = user_query.filter(User.role == payload.role)
        segment["role"] = payload.role

    user_ids = [r[0] for r in user_query.all()]
    if not user_ids:
        raise HTTPException(status_code=400, detail="No recipients match this broadcast")

    data = _admin_marker(admin=admin, extra={"segment": segment})
    if payload.data:
        data.update(payload.data)

    notification_ids = fcm_service.send(
        db=db,
        user_ids=user_ids,
        title=payload.title,
        body=payload.message,
        notification_type=payload.notification_type,
        scope="all" if payload.audience == "all" else "group",
        data=data,
        image_url=payload.image_url,
        send_push=bool(payload.send_push),
        sent_by_user_id=admin.user_id,
        sent_by_role=admin.role,
    )
    if not notification_ids:
        raise HTTPException(status_code=500, detail="Failed to create notification")

    notification_id = notification_ids[0]
    write_audit_log(
        db,
        category="crud",
        action="platform_notification.broadcast",
        entity_type="notification",
        entity_id=notification_id,
        actor=admin,
        request=request,
        success=True,
        metadata={"segment": segment, "send_push": bool(payload.send_push)},
    )
    db.commit()

    return AdminPlatformNotificationSendResponse(notification_id=notification_id, recipients_count=len(user_ids))


@router.post("/users/{user_id}", response_model=AdminPlatformNotificationSendResponse)
def send_platform_notification_to_user(
    user_id: str,
    payload: AdminPlatformNotificationSendRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.status != "active":
        raise HTTPException(status_code=400, detail="Target user is not active")

    data = _admin_marker(admin=admin, extra={"segment": {"audience": "user", "user_id": user_id}})
    if payload.data:
        data.update(payload.data)

    notification_id = fcm_service.send_to_user(
        db=db,
        user_id=user_id,
        title=payload.title,
        body=payload.message,
        notification_type=payload.notification_type,
        data=data,
        image_url=payload.image_url,
        send_push=bool(payload.send_push),
        sent_by_user_id=admin.user_id,
        sent_by_role=admin.role,
    )
    if not notification_id:
        raise HTTPException(status_code=500, detail="Failed to create notification")

    write_audit_log(
        db,
        category="crud",
        action="platform_notification.sent",
        entity_type="notification",
        entity_id=notification_id,
        actor=admin,
        request=request,
        success=True,
        metadata={"user_id": user_id, "send_push": bool(payload.send_push)},
    )
    db.commit()
    return AdminPlatformNotificationSendResponse(notification_id=notification_id, recipients_count=1)


@router.get("/", response_model=list[AdminPlatformNotificationOut])
def list_platform_notifications(
    from_ts: Optional[datetime] = Query(None),
    to_ts: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    # Prefer `Notification.sent_by_role` for new rows. Fall back to the historical marker in recipient.data.
    q = (
        db.query(Notification, func.count(NotificationRecipient.recipient_id).label("recipients_count"))
        .join(NotificationRecipient, NotificationRecipient.notification_id == Notification.notification_id)
        .filter(
            (Notification.sent_by_role.in_(["admin", "superadmin"]))
            | (
                NotificationRecipient.data.is_not(None)
                & cast(NotificationRecipient.data, JSONB).contains({"sent_via": "admin_platform"})
            )
        )
        .group_by(Notification.notification_id)
    )
    if from_ts:
        q = q.filter(Notification.created_at >= from_ts)
    if to_ts:
        q = q.filter(Notification.created_at <= to_ts)

    rows = q.order_by(Notification.created_at.desc()).limit(limit).offset(offset).all()

    out: list[AdminPlatformNotificationOut] = []
    for n, recipients_count in rows:
        out.append(
            AdminPlatformNotificationOut(
            notification_id=n.notification_id,
            type=n.type,
            scope=n.scope,
            title=n.title,
            message=n.message,
            image_url=n.image_url,
            created_at=n.created_at,
            sent_at=n.sent_at,
            recipients_count=int(recipients_count or 0),
            )
        )
    return out
