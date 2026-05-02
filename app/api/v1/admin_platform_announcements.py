from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.announcements import Announcement
from app.models.users import User
from app.schemas.admin_platform_announcements import (
    PlatformAnnouncementCreateRequest,
    PlatformAnnouncementOut,
    PlatformAnnouncementUpdateRequest,
)
from app.services.audit_log_service import write_audit_log


router = APIRouter(tags=["Admin | Platform Announcements"])


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.post("/", response_model=PlatformAnnouncementOut)
def create_platform_announcement(
    payload: PlatformAnnouncementCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    # Draft-only creation: publishing (and publish_at stamping) is handled by the publish endpoint.
    status = "draft"

    announcement = Announcement(
        created_by=admin.user_id,
        target_type="platform",
        gym_id=None,
        title=payload.title.strip(),
        content=payload.content.strip(),
        audience=payload.audience,
        status=status,
        publish_at=None,
        expires_at=payload.expires_at,
        is_important=bool(payload.is_important),
    )
    db.add(announcement)
    db.flush()

    write_audit_log(
        db,
        category="crud",
        action="platform_announcement.created",
        entity_type="announcement",
        entity_id=announcement.announcement_id,
        actor=admin,
        request=request,
        success=True,
        metadata={
            "status": status,
            "audience": payload.audience,
            "is_important": bool(payload.is_important),
        },
    )

    db.commit()
    db.refresh(announcement)
    return announcement


@router.get("/", response_model=list[PlatformAnnouncementOut])
def list_platform_announcements(
    status: Optional[str] = Query(None, description="draft|published|archived"),
    audience: Optional[str] = Query(None, description="all|members|staff"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    q = db.query(Announcement).filter(Announcement.target_type == "platform")
    if status:
        q = q.filter(Announcement.status == status)
    if audience:
        q = q.filter(Announcement.audience == audience)
    return q.order_by(Announcement.created_at.desc()).limit(limit).offset(offset).all()


@router.patch("/{announcement_id}", response_model=PlatformAnnouncementOut)
def update_platform_announcement(
    announcement_id: str,
    payload: PlatformAnnouncementUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    announcement = (
        db.query(Announcement)
        .filter(Announcement.announcement_id == announcement_id, Announcement.target_type == "platform")
        .with_for_update(nowait=False)
        .first()
    )
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    if announcement.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft announcements can be updated")

    changed: dict[str, object] = {}
    if payload.title is not None:
        announcement.title = payload.title.strip()
        changed["title"] = True
    if payload.content is not None:
        announcement.content = payload.content.strip()
        changed["content"] = True
    if payload.audience is not None:
        announcement.audience = payload.audience
        changed["audience"] = payload.audience
    if "expires_at" in payload.model_fields_set:
        announcement.expires_at = payload.expires_at
        changed["expires_at"] = True
    if payload.is_important is not None:
        announcement.is_important = bool(payload.is_important)
        changed["is_important"] = bool(payload.is_important)

    if announcement.expires_at and announcement.publish_at and announcement.expires_at <= announcement.publish_at:
        raise HTTPException(status_code=400, detail="expires_at must be after publish_at")

    db.add(announcement)
    write_audit_log(
        db,
        category="crud",
        action="platform_announcement.updated",
        entity_type="announcement",
        entity_id=announcement.announcement_id,
        actor=admin,
        request=request,
        success=True,
        metadata={"changes": changed},
    )
    db.commit()
    db.refresh(announcement)
    return announcement


@router.post("/{announcement_id}/publish", response_model=PlatformAnnouncementOut)
def publish_platform_announcement(
    announcement_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    announcement = (
        db.query(Announcement)
        .filter(Announcement.announcement_id == announcement_id, Announcement.target_type == "platform")
        .with_for_update(nowait=False)
        .first()
    )
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    if announcement.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft announcements can be published")

    now = datetime.utcnow()
    if announcement.expires_at and announcement.expires_at <= now:
        raise HTTPException(status_code=400, detail="Cannot publish an announcement that is already expired")

    announcement.status = "published"
    # Publishing is a server-side action; always stamp publish_at at time of publish.
    # If an announcement was scheduled (publish_at in the future), publishing early overrides it.
    announcement.publish_at = now

    if announcement.expires_at and announcement.expires_at <= announcement.publish_at:
        raise HTTPException(status_code=400, detail="expires_at must be after publish_at")

    db.add(announcement)
    write_audit_log(
        db,
        category="crud",
        action="platform_announcement.published",
        entity_type="announcement",
        entity_id=announcement.announcement_id,
        actor=admin,
        request=request,
        success=True,
        metadata={"audience": announcement.audience, "is_important": bool(announcement.is_important)},
    )
    db.commit()
    db.refresh(announcement)
    return announcement


@router.post("/{announcement_id}/archive", response_model=PlatformAnnouncementOut)
def archive_platform_announcement(
    announcement_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    announcement = (
        db.query(Announcement)
        .filter(Announcement.announcement_id == announcement_id, Announcement.target_type == "platform")
        .with_for_update(nowait=False)
        .first()
    )
    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    if announcement.status == "archived":
        return announcement

    previous_status = announcement.status
    announcement.status = "archived"
    db.add(announcement)
    write_audit_log(
        db,
        category="crud",
        action="platform_announcement.archived",
        entity_type="announcement",
        entity_id=announcement.announcement_id,
        actor=admin,
        request=request,
        success=True,
        metadata={"previous_status": previous_status},
    )
    db.commit()
    db.refresh(announcement)
    return announcement
