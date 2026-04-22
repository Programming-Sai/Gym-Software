from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.financials import Payout
from app.models.gyms import Gym
from app.models.users import User
from app.schemas.gyms import GymReceivePaymentsOut
from app.services.paystack_service import PaystackService


router = APIRouter(tags=["Admin | Payouts"])
paystack_service = PaystackService()


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def _ensure_no_processing_payouts(db: Session, gym_id: str) -> None:
    processing = (
        db.query(Payout.payout_id)
        .filter(Payout.gym_id == gym_id, Payout.status == "processing")
        .first()
    )
    if processing:
        raise HTTPException(
            status_code=409,
            detail="Cannot modify receive-payments while a payout is processing",
        )


@router.post("/gyms/{gym_id}/receive-payments/verify", response_model=GymReceivePaymentsOut)
def verify_receive_payments(
    gym_id: str,
    force: bool = Query(False, description="Recreate recipient even if already verified"),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    gym = db.query(Gym).filter(Gym.gym_id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    _ensure_no_processing_payouts(db, gym_id)

    if gym.payout_method is None:
        raise HTTPException(status_code=400, detail="Gym has no receive-payments configuration")

    if (
        not force
        and gym.paystack_recipient_code
        and gym.payouts_enabled
        and gym.payout_recipient_verified_at is not None
    ):
        return gym

    # If rotating recipient, deactivate the old one first.
    if force and gym.paystack_recipient_code:
        try:
            paystack_service.delete_transfer_recipient(gym.paystack_recipient_code)
        except HTTPException:
            # Keep going only if you want a "best effort" rotation.
            # For now, be strict: surface Paystack error to caller.
            raise

        gym.paystack_recipient_code = None
        gym.payouts_enabled = False
        gym.payout_recipient_verified_at = None
        db.add(gym)
        db.commit()
        db.refresh(gym)

    currency = (gym.payout_currency or "GHS").upper()

    # Map our method -> Paystack recipient type.
    # For Ghana: bank usually uses "ghipss"; momo uses "mobile_money".
    if gym.payout_method == "bank":
        if not (gym.payout_account_number and gym.payout_bank_code and gym.payout_account_name):
            raise HTTPException(status_code=400, detail="Missing bank receive-payments fields on gym")

        recipient_type = "ghipss" if currency == "GHS" else "nuban"
        name = gym.payout_account_name
        account_number = gym.payout_account_number
        bank_code = gym.payout_bank_code

    elif gym.payout_method == "momo":
        if not (gym.payout_momo_number and gym.payout_momo_provider):
            raise HTTPException(status_code=400, detail="Missing momo receive-payments fields on gym")

        recipient_type = "mobile_money"
        # If we don't store an explicit momo account name, fall back to gym name.
        name = gym.name
        account_number = gym.payout_momo_number
        bank_code = gym.payout_momo_provider

    else:
        raise HTTPException(status_code=400, detail="Invalid payout_method on gym")

    metadata: dict[str, Any] = {"gym_id": gym.gym_id, "gym_name": gym.name}

    recipient = paystack_service.create_transfer_recipient(
        recipient_type=recipient_type,
        name=name,
        account_number=account_number,
        bank_code=bank_code,
        currency=currency,
        metadata=metadata,
    )

    recipient_code = recipient.get("recipient_code")
    if not recipient_code:
        raise HTTPException(status_code=502, detail="Paystack recipient creation returned no recipient_code")

    gym.paystack_recipient_code = str(recipient_code)
    gym.payouts_enabled = True
    gym.payout_recipient_verified_at = datetime.utcnow()

    db.add(gym)
    db.commit()
    db.refresh(gym)
    return gym

