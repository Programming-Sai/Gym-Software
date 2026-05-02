from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.dieticians import Dietician
from app.models.users import User
from app.schemas.admin_dieticians import AdminDieticianOut, AdminDieticianStatusChangeRequest
from app.services.audit_log_service import write_audit_log


router = APIRouter(tags=["Admin | Dieticians"])


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/", response_model=list[AdminDieticianOut])
def list_dieticians_admin(
    status: Optional[str] = Query(None, description="active|suspended|inactive"),
    user_id: Optional[str] = Query(None),
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    query = db.query(Dietician).options(joinedload(Dietician.user))
    if status:
        query = query.filter(Dietician.status == status)
    if user_id:
        query = query.filter(Dietician.user_id == user_id)
    if created_from is not None:
        query = query.filter(Dietician.created_at >= created_from)
    if created_to is not None:
        query = query.filter(Dietician.created_at <= created_to)
    return query.order_by(Dietician.created_at.desc()).limit(limit).offset(offset).all()


@router.get("/{dietician_id}", response_model=AdminDieticianOut)
def get_dietician_admin(
    dietician_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    dietician = (
        db.query(Dietician)
        .options(joinedload(Dietician.user))
        .filter(Dietician.dietician_id == dietician_id)
        .first()
    )
    if not dietician:
        raise HTTPException(status_code=404, detail="Dietician not found")
    return dietician


def _set_dietician_status(
    *,
    db: Session,
    request: Request,
    actor: User,
    dietician: Dietician,
    new_status: str,
    reason: str | None,
) -> Dietician:
    old_status = dietician.status
    if old_status == new_status:
        return dietician

    dietician.status = new_status
    db.add(dietician)
    write_audit_log(
        db,
        category="crud",
        action="dietician.status_changed",
        entity_type="dietician",
        entity_id=dietician.dietician_id,
        actor=actor,
        request=request,
        success=True,
        metadata={"from": old_status, "to": new_status, "reason": reason, "user_id": dietician.user_id},
    )
    db.commit()
    db.refresh(dietician)
    return dietician


@router.post("/{dietician_id}/suspend", response_model=AdminDieticianOut)
def suspend_dietician_admin(
    dietician_id: str,
    payload: AdminDieticianStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    dietician = (
        db.query(Dietician)
        .filter(Dietician.dietician_id == dietician_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not dietician:
        raise HTTPException(status_code=404, detail="Dietician not found")
    return _set_dietician_status(
        db=db,
        request=request,
        actor=admin,
        dietician=dietician,
        new_status="suspended",
        reason=payload.reason,
    )


@router.post("/{dietician_id}/activate", response_model=AdminDieticianOut)
def activate_dietician_admin(
    dietician_id: str,
    payload: AdminDieticianStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    dietician = (
        db.query(Dietician)
        .filter(Dietician.dietician_id == dietician_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not dietician:
        raise HTTPException(status_code=404, detail="Dietician not found")
    return _set_dietician_status(
        db=db,
        request=request,
        actor=admin,
        dietician=dietician,
        new_status="active",
        reason=payload.reason,
    )

