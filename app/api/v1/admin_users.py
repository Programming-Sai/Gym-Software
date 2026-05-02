from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.crud.checkins import get_user_checkins
from app.models.auth import Session as DBSession
from app.models.users import User
from app.schemas.admin_users import (
    AdminRevokeSessionRequest,
    AdminSessionOut,
    AdminUserOut,
    AdminUserDemoteRequest,
    AdminUserPromoteRequest,
    AdminUserStatusChangeRequest,
)
from app.services.audit_log_service import write_audit_log


router = APIRouter(tags=["Admin | Users"])


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def superadmin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return current_user


def _ensure_can_manage_target(*, actor: User, target: User) -> None:
    # Admins should not be able to change a superadmin account.
    if target.role == "superadmin" and actor.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin privileges required for this action")


@router.get("/", response_model=list[AdminUserOut])
def list_users(
    q: Optional[str] = Query(None, description="Search by email/full_name (contains)"),
    role: Optional[str] = Query(None, description="gym_user|dietician|gym_owner|admin|superadmin"),
    status: Optional[str] = Query(None, description="active|limited|suspended|inactive"),
    email_verified: Optional[bool] = Query(None),
    phone_verified: Optional[bool] = Query(None),
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    query = db.query(User)

    if q:
        s = f"%{q.strip().lower()}%"
        query = query.filter((User.email.ilike(s)) | (User.full_name.ilike(s)))
    if role:
        query = query.filter(User.role == role)
    if status:
        query = query.filter(User.status == status)
    if email_verified is not None:
        query = query.filter(User.email_verified == email_verified)
    if phone_verified is not None:
        query = query.filter(User.phone_verified == phone_verified)
    if created_from is not None:
        query = query.filter(User.created_at >= created_from)
    if created_to is not None:
        query = query.filter(User.created_at <= created_to)

    return query.order_by(User.created_at.desc()).limit(limit).offset(offset).all()


@router.get("/{user_id}", response_model=AdminUserOut)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/{user_id}/checkins")
def admin_list_user_checkins(
    user_id: str,
    gym_id: str | None = Query(None, description="Optional filter by gym_id"),
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    # Use existing checkins query helper (it already limits gym_owner scope; admins get all).
    checkins = get_user_checkins(db, user_id, viewer=admin)
    if gym_id:
        checkins = [c for c in checkins if getattr(c, "gym_id", None) == gym_id]

    return checkins[offset : offset + limit]


def _set_user_status(
    *,
    db: Session,
    request: Request,
    actor: User,
    target: User,
    new_status: str,
    reason: str | None,
):
    _ensure_can_manage_target(actor=actor, target=target)
    if actor.user_id == target.user_id and new_status in {"suspended", "limited"}:
        raise HTTPException(status_code=400, detail="You cannot restrict your own account")

    old_status = target.status
    if old_status == new_status:
        return target

    target.status = new_status
    db.add(target)

    write_audit_log(
        db,
        category="crud",
        action="user.status_changed",
        entity_type="user",
        entity_id=target.user_id,
        actor=actor,
        request=request,
        success=True,
        metadata={
            "from": old_status,
            "to": new_status,
            "reason": reason,
            "target_role": target.role,
        },
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/{user_id}/suspend", response_model=AdminUserOut)
def suspend_user(
    user_id: str,
    payload: AdminUserStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return _set_user_status(
        db=db,
        request=request,
        actor=admin,
        target=target,
        new_status="suspended",
        reason=payload.reason,
    )


@router.post("/{user_id}/activate", response_model=AdminUserOut)
def activate_user(
    user_id: str,
    payload: AdminUserStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return _set_user_status(
        db=db,
        request=request,
        actor=admin,
        target=target,
        new_status="active",
        reason=payload.reason,
    )


@router.post("/{user_id}/limit", response_model=AdminUserOut)
def limit_user(
    user_id: str,
    payload: AdminUserStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return _set_user_status(
        db=db,
        request=request,
        actor=admin,
        target=target,
        new_status="limited",
        reason=payload.reason,
    )


@router.get("/{user_id}/sessions", response_model=list[AdminSessionOut])
def list_user_sessions(
    user_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _ensure_can_manage_target(actor=admin, target=target)

    return (
        db.query(DBSession)
        .filter(DBSession.user_id == user_id)
        .order_by(DBSession.created_at.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )


@router.post("/{user_id}/sessions/{session_id}/revoke", response_model=AdminSessionOut)
def revoke_user_session(
    user_id: str,
    session_id: str,
    payload: AdminRevokeSessionRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    if admin.user_id == user_id:
        raise HTTPException(status_code=400, detail="You cannot revoke your own sessions via admin endpoint")

    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    _ensure_can_manage_target(actor=admin, target=target)

    session = (
        db.query(DBSession)
        .filter(DBSession.session_id == session_id, DBSession.user_id == user_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.is_active:
        session.is_active = False
        db.add(session)
        write_audit_log(
            db,
            category="security",
            action="session.revoked",
            entity_type="session",
            entity_id=session.session_id,
            actor=admin,
            request=request,
            success=True,
            metadata={
                "user_id": user_id,
                "reason": payload.reason,
            },
        )
        db.commit()

    db.refresh(session)
    return session


def _set_user_role(
    *,
    db: Session,
    request: Request,
    actor: User,
    target: User,
    new_role: str,
    note: str | None,
):
    _ensure_can_manage_target(actor=actor, target=target)
    if actor.user_id == target.user_id and new_role == "superadmin":
        raise HTTPException(status_code=400, detail="Self-promotion is not allowed")

    old_role = target.role
    if old_role == new_role:
        return target

    # Avoid clobbering specialized roles unless explicitly intended.
    # The system stores a single role; promotion should start from a base role.
    if old_role not in {"gym_user", "admin", "superadmin"}:
        raise HTTPException(
            status_code=400,
            detail="Role change is restricted for non-basic roles; handle manually",
        )

    target.role = new_role
    db.add(target)
    write_audit_log(
        db,
        category="crud",
        action="user.role_changed",
        entity_type="user",
        entity_id=target.user_id,
        actor=actor,
        request=request,
        success=True,
        metadata={
            "from": old_role,
            "to": new_role,
            "note": note,
        },
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/{user_id}/promote-to-admin", response_model=AdminUserOut)
def promote_to_admin(
    user_id: str,
    payload: AdminUserPromoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    superadmin: User = Depends(superadmin_required),
):
    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return _set_user_role(db=db, request=request, actor=superadmin, target=target, new_role="admin", note=payload.note)


@router.post("/{user_id}/promote-to-superadmin", response_model=AdminUserOut)
def promote_to_superadmin(
    user_id: str,
    payload: AdminUserPromoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    superadmin: User = Depends(superadmin_required),
):
    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    return _set_user_role(
        db=db,
        request=request,
        actor=superadmin,
        target=target,
        new_role="superadmin",
        note=payload.note,
    )


@router.post("/{user_id}/demote-admin", response_model=AdminUserOut)
def demote_admin(
    user_id: str,
    payload: AdminUserDemoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    superadmin: User = Depends(superadmin_required),
):
    target = db.query(User).filter(User.user_id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    if target.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=400, detail="Target user is not an admin")

    demote_to = payload.demote_to_role or "gym_user"
    return _set_user_role(
        db=db,
        request=request,
        actor=superadmin,
        target=target,
        new_role=demote_to,
        note=payload.note,
    )
