from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.financials import Payment
from app.models.users import User
from app.schemas.admin_money import AdminPaymentDetailOut, AdminPaymentOut
from app.services.audit_log_service import sanitize_metadata


router = APIRouter(tags=["Admin | Payments"])


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/", response_model=list[AdminPaymentOut])
def list_payments(
    status: Optional[str] = Query(None, description="pending|succeeded|failed|refunded"),
    user_id: Optional[str] = Query(None),
    subscription_id: Optional[str] = Query(None),
    gym_id: Optional[str] = Query(None),
    provider: Optional[str] = Query(None),
    payment_type: Optional[str] = Query(None, description="subscription|checkin|product|other"),
    from_ts: Optional[datetime] = Query(None),
    to_ts: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    q = db.query(Payment)

    if status:
        q = q.filter(Payment.status == status)
    if user_id:
        q = q.filter(Payment.user_id == user_id)
    if subscription_id:
        q = q.filter(Payment.subscription_id == subscription_id)
    if gym_id:
        q = q.filter(Payment.gym_id == gym_id)
    if provider:
        q = q.filter(Payment.provider == provider)
    if payment_type:
        q = q.filter(Payment.payment_type == payment_type)
    if from_ts:
        q = q.filter(Payment.created_at >= from_ts)
    if to_ts:
        q = q.filter(Payment.created_at <= to_ts)

    rows = q.order_by(Payment.created_at.desc()).limit(limit).offset(offset).all()
    # Sanitize metadata for admin-safe output.
    for p in rows:
        p.payment_metadata = sanitize_metadata(getattr(p, "payment_metadata", None))  # type: ignore[attr-defined]
    return rows


@router.get("/{payment_id}", response_model=AdminPaymentDetailOut)
def get_payment(
    payment_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    payment = db.query(Payment).filter(Payment.payment_id == payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    payment.payment_metadata = sanitize_metadata(getattr(payment, "payment_metadata", None))  # type: ignore[attr-defined]
    raw = getattr(payment, "raw_provider_payload", None)
    payment.raw_provider_payload = sanitize_metadata(raw) if isinstance(raw, dict) else None  # type: ignore[attr-defined]
    return payment

