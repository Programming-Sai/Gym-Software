from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.gyms import Gym
from app.models.users import User
from app.models.verifications import VerificationApplication
from app.schemas.admin_gyms import AdminGymOut, AdminGymStatusChangeRequest
from app.services.audit_log_service import write_audit_log


router = APIRouter(tags=["Admin | Gyms"])


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/", response_model=list[AdminGymOut])
def list_gyms(
    q: Optional[str] = Query(None, description="Search by gym name (contains)"),
    status: Optional[str] = Query(None, description="draft|active|suspended|closed"),
    owner_id: Optional[str] = Query(None),
    created_from: Optional[datetime] = Query(None),
    created_to: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    query = db.query(Gym).options(joinedload(Gym.owner))

    if q:
        s = f"%{q.strip().lower()}%"
        query = query.filter(Gym.name.ilike(s))
    if status:
        query = query.filter(Gym.status == status)
    if owner_id:
        query = query.filter(Gym.owner_id == owner_id)
    if created_from is not None:
        query = query.filter(Gym.created_at >= created_from)
    if created_to is not None:
        query = query.filter(Gym.created_at <= created_to)

    return query.order_by(Gym.created_at.desc()).limit(limit).offset(offset).all()


@router.get("/{gym_id}", response_model=AdminGymOut)
def get_gym(
    gym_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    gym = (
        db.query(Gym)
        .options(joinedload(Gym.owner))
        .filter(Gym.gym_id == gym_id)
        .first()
    )
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    return gym


def _set_gym_status(
    *,
    db: Session,
    request: Request,
    actor: User,
    gym: Gym,
    new_status: str,
    reason: str | None,
) -> Gym:
    old_status = gym.status
    if old_status == new_status:
        return gym

    gym.status = new_status
    db.add(gym)
    write_audit_log(
        db,
        category="crud",
        action="gym.status_changed",
        entity_type="gym",
        entity_id=gym.gym_id,
        actor=actor,
        request=request,
        success=True,
        payee_gym_id=gym.gym_id,
        metadata={"from": old_status, "to": new_status, "reason": reason, "owner_id": gym.owner_id},
    )
    db.commit()
    db.refresh(gym)
    return gym


def _ensure_gym_owner_verified(db: Session, gym: Gym) -> None:
    if not gym.owner_id:
        raise HTTPException(status_code=400, detail="Gym has no owner configured")

    approved = (
        db.query(VerificationApplication.application_id)
        .filter(
            VerificationApplication.applicant_type == "gym_owner",
            VerificationApplication.applicant_id == gym.owner_id,
            VerificationApplication.status == "approved",
        )
        .order_by(VerificationApplication.submitted_at.desc())
        .first()
    )
    if not approved:
        raise HTTPException(status_code=403, detail="Gym owner is not verified; gym cannot be activated")


@router.post("/{gym_id}/suspend", response_model=AdminGymOut)
def suspend_gym(
    gym_id: str,
    payload: AdminGymStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    gym = (
        db.query(Gym)
        .filter(Gym.gym_id == gym_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    return _set_gym_status(db=db, request=request, actor=admin, gym=gym, new_status="suspended", reason=payload.reason)


@router.post("/{gym_id}/activate", response_model=AdminGymOut)
def activate_gym(
    gym_id: str,
    payload: AdminGymStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    gym = (
        db.query(Gym)
        .filter(Gym.gym_id == gym_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    _ensure_gym_owner_verified(db, gym)
    return _set_gym_status(db=db, request=request, actor=admin, gym=gym, new_status="active", reason=payload.reason)


@router.post("/{gym_id}/close", response_model=AdminGymOut)
def close_gym(
    gym_id: str,
    payload: AdminGymStatusChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    gym = (
        db.query(Gym)
        .filter(Gym.gym_id == gym_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    return _set_gym_status(db=db, request=request, actor=admin, gym=gym, new_status="closed", reason=payload.reason)
