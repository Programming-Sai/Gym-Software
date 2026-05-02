import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.auth import AdminInvite
from app.models.users import User
from app.schemas.admin_invites import (
    AdminInviteCreateRequest,
    AdminInviteCreatedResponse,
    AdminInviteOut,
    AdminInviteRevokeRequest,
)
from app.services.audit_log_service import write_audit_log


router = APIRouter(tags=["Admin | Invites"])


def superadmin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return current_user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/", response_model=AdminInviteCreatedResponse)
def create_admin_invite(
    payload: AdminInviteCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    superadmin: User = Depends(superadmin_required),
):
    email = payload.email.strip().lower()
    role_to_grant = payload.role_to_grant
    if role_to_grant not in {"admin", "superadmin"}:
        raise HTTPException(status_code=400, detail="Invalid role_to_grant")

    # Reduce attack surface:
    # - Revoke any existing pending invites for this email before issuing a new token.
    now = datetime.utcnow()
    existing_pending = (
        db.query(AdminInvite)
        .filter(
            AdminInvite.email == email,
            AdminInvite.accepted_at.is_(None),
            AdminInvite.revoked_at.is_(None),
            AdminInvite.expires_at > now,
        )
        .all()
    )
    for inv in existing_pending:
        inv.revoked_at = now
        inv.revoked_by = superadmin.user_id
        inv.revoke_reason = "superseded_by_new_invite"
        db.add(inv)

    token = secrets.token_urlsafe(32)
    invite = AdminInvite(
        email=email,
        role_to_grant=role_to_grant,
        token_hash=_hash_token(token),
        expires_at=now + timedelta(hours=int(payload.expires_in_hours)),
        created_by=superadmin.user_id,
        send_count=1,
        last_sent_at=now,
    )
    db.add(invite)
    write_audit_log(
        db,
        category="crud",
        action="admin_invite.created",
        entity_type="admin_invite",
        entity_id=invite.invite_id,
        actor=superadmin,
        request=request,
        success=True,
        metadata={"email": email, "role_to_grant": role_to_grant},
    )
    db.commit()
    db.refresh(invite)
    return {
        "invite_id": invite.invite_id,
        "email": invite.email,
        "role_to_grant": invite.role_to_grant,
        "expires_at": invite.expires_at,
        "created_by": invite.created_by,
        "created_at": invite.created_at,
        "accepted_by": invite.accepted_by,
        "accepted_at": invite.accepted_at,
        "revoked_by": invite.revoked_by,
        "revoked_at": invite.revoked_at,
        "revoke_reason": invite.revoke_reason,
        "send_count": invite.send_count,
        "last_sent_at": invite.last_sent_at,
        "token": token,
    }


@router.get("/", response_model=list[AdminInviteOut])
def list_admin_invites(
    status: Optional[str] = Query(None, description="pending|accepted|revoked|expired"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _superadmin: User = Depends(superadmin_required),
):
    q = db.query(AdminInvite)
    now = datetime.utcnow()
    if status == "pending":
        q = q.filter(AdminInvite.accepted_at.is_(None), AdminInvite.revoked_at.is_(None), AdminInvite.expires_at > now)
    elif status == "accepted":
        q = q.filter(AdminInvite.accepted_at.is_not(None))
    elif status == "revoked":
        q = q.filter(AdminInvite.revoked_at.is_not(None))
    elif status == "expired":
        q = q.filter(AdminInvite.accepted_at.is_(None), AdminInvite.revoked_at.is_(None), AdminInvite.expires_at <= now)
    elif status is not None:
        raise HTTPException(status_code=400, detail="Invalid status filter")
    return q.order_by(AdminInvite.created_at.desc()).limit(limit).offset(offset).all()


@router.post("/{invite_id}/revoke", response_model=AdminInviteOut)
def revoke_admin_invite(
    invite_id: str,
    payload: AdminInviteRevokeRequest,
    request: Request,
    db: Session = Depends(get_db),
    superadmin: User = Depends(superadmin_required),
):
    invite = (
        db.query(AdminInvite)
        .filter(AdminInvite.invite_id == invite_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invite already accepted")
    if invite.revoked_at is not None:
        return invite

    invite.revoked_at = datetime.utcnow()
    invite.revoked_by = superadmin.user_id
    invite.revoke_reason = payload.reason.strip()

    db.add(invite)
    write_audit_log(
        db,
        category="crud",
        action="admin_invite.revoked",
        entity_type="admin_invite",
        entity_id=invite.invite_id,
        actor=superadmin,
        request=request,
        success=True,
        metadata={"reason": payload.reason},
    )
    db.commit()
    db.refresh(invite)
    return invite


@router.post("/{invite_id}/resend", response_model=AdminInviteCreatedResponse)
def resend_admin_invite(
    invite_id: str,
    request: Request,
    db: Session = Depends(get_db),
    superadmin: User = Depends(superadmin_required),
):
    invite = (
        db.query(AdminInvite)
        .filter(AdminInvite.invite_id == invite_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invite already accepted")
    if invite.revoked_at is not None:
        raise HTTPException(status_code=400, detail="Invite is revoked")

    now = datetime.utcnow()
    if invite.expires_at <= now:
        raise HTTPException(status_code=400, detail="Invite is expired; create a new one")

    # Rotate token (so old link becomes unusable).
    token = secrets.token_urlsafe(32)
    invite.token_hash = _hash_token(token)
    invite.send_count = int(invite.send_count or 0) + 1
    invite.last_sent_at = now

    db.add(invite)
    write_audit_log(
        db,
        category="crud",
        action="admin_invite.resent",
        entity_type="admin_invite",
        entity_id=invite.invite_id,
        actor=superadmin,
        request=request,
        success=True,
        metadata={"email": invite.email, "send_count": invite.send_count},
    )
    db.commit()
    db.refresh(invite)
    return {
        "invite_id": invite.invite_id,
        "email": invite.email,
        "role_to_grant": invite.role_to_grant,
        "expires_at": invite.expires_at,
        "created_by": invite.created_by,
        "created_at": invite.created_at,
        "accepted_by": invite.accepted_by,
        "accepted_at": invite.accepted_at,
        "revoked_by": invite.revoked_by,
        "revoked_at": invite.revoked_at,
        "revoke_reason": invite.revoke_reason,
        "send_count": invite.send_count,
        "last_sent_at": invite.last_sent_at,
        "token": token,
    }
