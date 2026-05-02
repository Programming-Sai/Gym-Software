from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.audit_logs import AuditLog
from app.models.users import User
from app.schemas.audit_logs import AuditLogOut, AuditLogPurgeResponse


router = APIRouter(tags=["Admin | Audit Logs"])


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/", response_model=list[AuditLogOut])
def list_audit_logs(
    category: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    entity_id: Optional[str] = Query(None),
    actor_user_id: Optional[str] = Query(None),
    payer_user_id: Optional[str] = Query(None),
    payee_gym_id: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    request_id: Optional[str] = Query(None),
    from_ts: Optional[datetime] = Query(None),
    to_ts: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    q = db.query(AuditLog)

    if category:
        q = q.filter(AuditLog.category == category)
    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    if actor_user_id:
        q = q.filter(AuditLog.actor_user_id == actor_user_id)
    if payer_user_id:
        q = q.filter(AuditLog.payer_user_id == payer_user_id)
    if payee_gym_id:
        q = q.filter(AuditLog.payee_gym_id == payee_gym_id)
    if request_id:
        q = q.filter(AuditLog.request_id == request_id)
    if success is not None:
        q = q.filter(AuditLog.success == success)
    if from_ts:
        q = q.filter(AuditLog.created_at >= from_ts)
    if to_ts:
        q = q.filter(AuditLog.created_at <= to_ts)

    return q.order_by(AuditLog.created_at.desc()).limit(limit).offset(offset).all()


@router.get("/{audit_log_id}", response_model=AuditLogOut)
def get_audit_log(
    audit_log_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    record = db.query(AuditLog).filter(AuditLog.audit_log_id == audit_log_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return record


@router.delete("/purge", response_model=AuditLogPurgeResponse)
def purge_audit_logs(
    keep_days: int = Query(30, ge=1, le=3650, description="Keep only the most recent N days"),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    cutoff = datetime.utcnow() - timedelta(days=int(keep_days))
    deleted = (
        db.query(AuditLog)
        .filter(AuditLog.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()
    return AuditLogPurgeResponse(deleted=int(deleted or 0))
