from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Header
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.financials import Payout
from app.models.gyms import Gym
from app.models.users import User
from app.schemas.gyms import GymReceivePaymentsOut
from app.schemas.payouts import (
    PayoutApproveRequest,
    PayoutCreateRequest,
    PayoutOut,
    PayoutProcessRequest,
)
from app.services.paystack_service import PaystackService


router = APIRouter(tags=["Admin | Payouts"])
paystack_service = PaystackService()
logger = logging.getLogger(__name__)


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


def _ensure_no_other_processing_payout_for_gym(db: Session, *, gym_id: str, payout_id: str) -> None:
    other = (
        db.query(Payout.payout_id)
        .filter(
            Payout.gym_id == gym_id,
            Payout.status == "processing",
            Payout.payout_id != payout_id,
        )
        .first()
    )
    if other:
        raise HTTPException(status_code=409, detail="Another payout is already processing for this gym")


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


@router.post("/", response_model=PayoutOut)
def create_payout(
    payload: PayoutCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    gym = db.query(Gym).filter(Gym.gym_id == payload.gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    if not gym.payouts_enabled or not gym.paystack_recipient_code:
        raise HTTPException(status_code=400, detail="Gym is not payout-ready (recipient not verified)")

    amount = payload.amount
    fee = Decimal("0.00")
    net_amount = amount - fee

    pm = {
        "note": payload.note,
        "created_by_admin": admin.user_id,
        "created_at": datetime.utcnow().isoformat(),
        "gym_snapshot": {
            "gym_id": gym.gym_id,
            "name": gym.name,
            "payout_method": gym.payout_method,
            "payout_currency": getattr(gym, "payout_currency", None),
        },
    }

    payout = Payout(
        gym_id=gym.gym_id,
        payment_id=None,
        amount=amount,
        fee=fee,
        net_amount=net_amount,
        status="pending",
        initiated_by=admin.user_id,
        approved_by=None,
        approved_at=None,
        provider="paystack",
        recipient_code=gym.paystack_recipient_code,
        transfer_reference=None,
        provider_transfer_id=None,
        processed_date=None,
        completed_date=None,
        failure_reason=None,
        payout_metadata=pm,
    )

    db.add(payout)
    db.commit()
    db.refresh(payout)
    return payout


@router.get("/", response_model=list[PayoutOut])
def list_payouts(
    status: Optional[str] = Query(None, description="Filter by payout status"),
    gym_id: Optional[str] = Query(None, description="Filter by gym_id"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    q = db.query(Payout)
    if status:
        q = q.filter(Payout.status == status)
    if gym_id:
        q = q.filter(Payout.gym_id == gym_id)
    return q.order_by(Payout.created_at.desc()).limit(limit).offset(offset).all()


@router.post("/{payout_id}/approve", response_model=PayoutOut)
def approve_payout(
    payout_id: str,
    payload: PayoutApproveRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    payout = db.query(Payout).filter(Payout.payout_id == payout_id).first()
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")

    if payout.status not in {"pending", "failed"}:
        raise HTTPException(status_code=400, detail=f"Cannot approve payout in status={payout.status}")

    payout.approved_by = admin.user_id
    payout.approved_at = datetime.utcnow()

    pm = payout.payout_metadata or {}
    if payload.note:
        pm.setdefault("approval_notes", []).append(
            {"note": payload.note, "by": admin.user_id, "at": datetime.utcnow().isoformat()}
        )
    payout.payout_metadata = pm

    db.add(payout)
    db.commit()
    db.refresh(payout)
    return payout


@router.post("/{payout_id}/process", response_model=PayoutOut)
def process_payout(
    payout_id: str,
    payload: PayoutProcessRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    # Phase 1: lock + mark processing (commit before external call)
    payout = (
        db.query(Payout)
        .filter(Payout.payout_id == payout_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")

    if payout.status == "completed":
        return payout
    if payout.status == "processing":
        raise HTTPException(status_code=409, detail="Payout is already processing")
    if payout.status == "failed" and not payload.retry:
        raise HTTPException(status_code=400, detail="Payout failed. Pass retry=true to retry processing")
    if payout.status != "pending" and not (payout.status == "failed" and payload.retry):
        raise HTTPException(status_code=400, detail=f"Cannot process payout in status={payout.status}")

    if not payout.approved_by or not payout.approved_at:
        raise HTTPException(status_code=400, detail="Payout must be approved before processing")

    gym = db.query(Gym).filter(Gym.gym_id == payout.gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    if not gym.payouts_enabled:
        raise HTTPException(status_code=400, detail="Gym payouts are disabled")

    if not payout.recipient_code:
        raise HTTPException(status_code=400, detail="Payout missing recipient_code")

    _ensure_no_other_processing_payout_for_gym(db, gym_id=payout.gym_id, payout_id=payout.payout_id)

    # Verify-first (double payment prevention):
    # If this payout has ever been initiated before (processed_date set, or any prior attempts),
    # confirm provider state before trying to create another transfer.
    pm_pre = payout.payout_metadata or {}
    has_attempts = bool(pm_pre.get("process_attempts"))
    if payload.retry or payout.processed_date is not None or has_attempts:
        try:
            verification = paystack_service.verify_transfer(payout.payout_id)
            pm_pre.setdefault("paystack_verifications", []).append(
                {"raw": verification, "at": datetime.utcnow().isoformat()}
            )
            payout.payout_metadata = pm_pre

            provider_status = str(verification.get("status") or "").lower()
            transfer_code = verification.get("transfer_code")
            provider_id = verification.get("id")

            if transfer_code and not payout.transfer_reference:
                payout.transfer_reference = str(transfer_code)
            if provider_id and not payout.provider_transfer_id:
                payout.provider_transfer_id = str(provider_id)

            if provider_status == "success":
                payout.status = "completed"
                payout.completed_date = datetime.utcnow()
                payout.failure_reason = None
                db.add(payout)
                db.commit()
                db.refresh(payout)
                return payout

            if provider_status in {"failed", "reversed"}:
                # allow retry path to continue (we'll create a new transfer)
                pass
            else:
                # pending/processing/otp/etc -> keep processing and do not create a second transfer
                payout.status = "processing"
                if payout.processed_date is None:
                    payout.processed_date = datetime.utcnow()
                db.add(payout)
                db.commit()
                db.refresh(payout)
                return payout

        except HTTPException as e:
            # If verification fails, don't blindly initiate a second transfer unless explicitly retrying.
            pm_pre.setdefault("verification_errors", []).append(
                {"detail": str(e.detail), "at": datetime.utcnow().isoformat()}
            )
            payout.payout_metadata = pm_pre
            db.add(payout)
            db.commit()
            if not payload.retry:
                raise HTTPException(status_code=409, detail="Unable to verify previous transfer; retry required to proceed")

    payout.status = "processing"
    payout.processed_date = datetime.utcnow()
    payout.failure_reason = None

    pm = payout.payout_metadata or {}
    pm.setdefault("process_attempts", []).append(
        {"by": admin.user_id, "at": datetime.utcnow().isoformat(), "retry": bool(payload.retry)}
    )
    payout.payout_metadata = pm

    db.add(payout)
    db.commit()

    # Phase 2: external call (no DB locks held)
    try:
        transfer = paystack_service.create_transfer(
            amount=Decimal(payout.net_amount),
            recipient_code=payout.recipient_code,
            reference=payout.payout_id,
        )
    except HTTPException as e:
        # mark failed
        payout2 = (
            db.query(Payout)
            .filter(Payout.payout_id == payout_id)
            .with_for_update(nowait=False)
            .first()
        )
        if payout2:
            payout2.status = "failed"
            payout2.failure_reason = str(e.detail)
            pm2 = payout2.payout_metadata or {}
            pm2.setdefault("paystack_errors", []).append(
                {"detail": str(e.detail), "at": datetime.utcnow().isoformat()}
            )
            payout2.payout_metadata = pm2
            db.add(payout2)
            db.commit()
            db.refresh(payout2)
            return payout2
        raise

    # Phase 3: persist provider response (do NOT mark completed here; webhook/verify will finalize)
    payout3 = (
        db.query(Payout)
        .filter(Payout.payout_id == payout_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not payout3:
        raise HTTPException(status_code=500, detail="Payout disappeared during processing")

    # Store provider refs
    transfer_code = transfer.get("transfer_code") or transfer.get("reference")
    provider_id = transfer.get("id")

    payout3.transfer_reference = str(transfer_code) if transfer_code is not None else payout3.transfer_reference
    payout3.provider_transfer_id = str(provider_id) if provider_id is not None else payout3.provider_transfer_id

    pm3 = payout3.payout_metadata or {}
    pm3["paystack_transfer"] = {
        "raw": transfer,
        "stored_at": datetime.utcnow().isoformat(),
    }
    payout3.payout_metadata = pm3

    # Leave status as "processing" until transfer.success webhook (or explicit refresh) finalizes it.
    payout3.status = "processing"

    db.add(payout3)
    db.commit()
    db.refresh(payout3)
    return payout3


@router.post("/webhook")
async def paystack_transfers_webhook(
    request: Request,
    x_paystack_signature: str = Header(...),
    db: Session = Depends(get_db),
):
    """
    Paystack webhook for transfer events.

    Expected events (Paystack):
    - transfer.success
    - transfer.failed
    - transfer.reversed

    We locate the payout by `data.reference` (we set reference=payout_id when creating the transfer).
    """
    raw_body = await request.body()

    if not paystack_service.verify_webhook_signature(raw_body, x_paystack_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = await request.json()
    return handle_paystack_transfer_webhook(event=event, db=db)


def handle_paystack_transfer_webhook(*, event: dict, db: Session) -> dict:
    """
    Shared handler for Paystack transfer webhooks (used by the admin router webhook and the unified Paystack webhook).

    Expects `event` to already be parsed JSON, and signature verification to be handled by the caller.
    """
    event_name = event.get("event")
    data = event.get("data") or {}

    reference = data.get("reference")
    if not reference:
        return {"status": "ignored", "reason": "no reference"}

    if event_name not in {"transfer.success", "transfer.failed", "transfer.reversed"}:
        return {"status": "ignored", "reason": "unsupported event", "event": event_name}

    try:
        with db.begin():
            payout = (
                db.query(Payout)
                .filter(Payout.payout_id == str(reference))
                .with_for_update(nowait=False)
                .first()
            )

            if not payout:
                logger.error("Transfer webhook reference %s did not match payout", reference)
                return {"status": "ok", "note": "unknown_reference"}

            # Idempotent terminal states (do not downgrade completed)
            if payout.status == "completed":
                pm = payout.payout_metadata or {}
                pm.setdefault("webhook_duplicates", []).append(
                    {"event": event_name, "at": datetime.utcnow().isoformat()}
                )
                payout.payout_metadata = pm
                db.add(payout)
                return {"status": "ok", "note": "already_terminal"}

            if payout.status == "failed" and event_name != "transfer.success":
                pm = payout.payout_metadata or {}
                pm.setdefault("webhook_duplicates", []).append(
                    {"event": event_name, "at": datetime.utcnow().isoformat()}
                )
                payout.payout_metadata = pm
                db.add(payout)
                return {"status": "ok", "note": "already_terminal"}

            # Store provider fields if present
            transfer_code = data.get("transfer_code")
            provider_id = data.get("id")

            if transfer_code and not payout.transfer_reference:
                payout.transfer_reference = str(transfer_code)
            if provider_id and not payout.provider_transfer_id:
                payout.provider_transfer_id = str(provider_id)

            pm = payout.payout_metadata or {}
            pm.setdefault("paystack_webhooks", []).append(
                {"event": event_name, "data": data, "received_at": datetime.utcnow().isoformat()}
            )
            payout.payout_metadata = pm

            now = datetime.utcnow()

            if event_name == "transfer.success":
                payout.status = "completed"
                payout.completed_date = now
                payout.failure_reason = None
            else:
                payout.status = "failed"
                payout.completed_date = now
                payout.failure_reason = data.get("reason") or event_name

            db.add(payout)

        return {"status": "ok"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error processing transfer webhook for reference %s: %s", reference, str(e))
        raise HTTPException(status_code=500, detail="Internal error processing transfer webhook")


@router.post("/{payout_id}/refresh", response_model=PayoutOut)
def refresh_payout_status(
    payout_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    """
    Provider sync safety net: verifies transfer state by reference and updates payout status accordingly.
    Uses the payout_id as the transfer reference (same value used in create_transfer).
    """
    payout = (
        db.query(Payout)
        .filter(Payout.payout_id == payout_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not payout:
        raise HTTPException(status_code=404, detail="Payout not found")

    verification = paystack_service.verify_transfer(payout_id)

    provider_status = str(verification.get("status") or "").lower()
    transfer_code = verification.get("transfer_code")
    provider_id = verification.get("id")

    if transfer_code and not payout.transfer_reference:
        payout.transfer_reference = str(transfer_code)
    if provider_id and not payout.provider_transfer_id:
        payout.provider_transfer_id = str(provider_id)

    pm = payout.payout_metadata or {}
    pm.setdefault("paystack_verifications", []).append(
        {"raw": verification, "at": datetime.utcnow().isoformat()}
    )
    payout.payout_metadata = pm

    now = datetime.utcnow()
    if provider_status == "success":
        payout.status = "completed"
        payout.completed_date = now
        payout.failure_reason = None
    elif provider_status in {"failed", "reversed"}:
        payout.status = "failed"
        payout.completed_date = now
        payout.failure_reason = payout.failure_reason or provider_status
    else:
        payout.status = "processing" if payout.status != "completed" else payout.status
        if payout.processed_date is None:
            payout.processed_date = now

    db.add(payout)
    db.commit()
    db.refresh(payout)
    return payout
