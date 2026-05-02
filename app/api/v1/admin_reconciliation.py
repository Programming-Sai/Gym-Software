import json
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.financials import PaymentReconciliationEvent
from app.models.users import User
from app.schemas.reconciliation import (
    ReconciliationEventOut,
    ReconciliationEventUpdateRequest,
    ReconciliationEventVerifyResponse,
)
from app.services.audit_log_service import write_audit_log
from app.services.paystack_service import PaystackService


router = APIRouter(tags=["Admin | Reconciliation"])
paystack_service = PaystackService()


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def superadmin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return current_user


def _payload_size(payload: Any) -> int:
    try:
        return len(json.dumps(payload, default=str))
    except Exception:
        return 0


def _append_verification(event: PaymentReconciliationEvent, *, verification: dict[str, Any]) -> None:
    payload = event.payload or {}
    payload.setdefault("verifications", []).append(
        {"at": datetime.utcnow().isoformat(), "result": verification}
    )
    event.payload = payload


@router.get("/", response_model=list[ReconciliationEventOut])
def list_reconciliation_events(
    status: Optional[str] = Query(None, description="open|flagged|resolved|ignored"),
    provider: Optional[str] = Query(None, description="e.g. paystack"),
    provider_event: Optional[str] = Query(None),
    reference: Optional[str] = Query(None, description="Exact reference match"),
    from_ts: Optional[datetime] = Query(None),
    to_ts: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    q = db.query(PaymentReconciliationEvent)
    if status:
        q = q.filter(PaymentReconciliationEvent.status == status)
    if provider:
        q = q.filter(PaymentReconciliationEvent.provider == provider)
    if provider_event:
        q = q.filter(PaymentReconciliationEvent.provider_event == provider_event)
    if reference:
        q = q.filter(PaymentReconciliationEvent.reference == reference)
    if from_ts:
        q = q.filter(PaymentReconciliationEvent.created_at >= from_ts)
    if to_ts:
        q = q.filter(PaymentReconciliationEvent.created_at <= to_ts)
    return q.order_by(PaymentReconciliationEvent.updated_at.desc()).limit(limit).offset(offset).all()


@router.get("/{reconciliation_event_id}", response_model=ReconciliationEventOut)
def get_reconciliation_event(
    reconciliation_event_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    event = (
        db.query(PaymentReconciliationEvent)
        .filter(PaymentReconciliationEvent.reconciliation_event_id == reconciliation_event_id)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Reconciliation event not found")
    return event


@router.patch("/{reconciliation_event_id}", response_model=ReconciliationEventOut)
def update_reconciliation_event(
    reconciliation_event_id: str,
    payload: ReconciliationEventUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_required),
):
    event = (
        db.query(PaymentReconciliationEvent)
        .filter(PaymentReconciliationEvent.reconciliation_event_id == reconciliation_event_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Reconciliation event not found")

    old_status = event.status
    new_status = payload.status

    # Permission rules:
    # - admin: can only flag (open -> flagged) or update notes
    # - superadmin: can set any status
    if new_status is not None:
        if actor.role != "superadmin":
            if new_status != "flagged":
                raise HTTPException(status_code=403, detail="Only superadmin can change reconciliation status")
            if old_status not in {"open", "flagged"}:
                raise HTTPException(status_code=400, detail=f"Cannot flag status={old_status}")
        event.status = new_status

    if payload.notes is not None:
        event.notes = payload.notes.strip() if payload.notes.strip() else None

    db.add(event)
    write_audit_log(
        db,
        category="money",
        action="reconciliation.updated",
        entity_type="payment_reconciliation_event",
        entity_id=event.reconciliation_event_id,
        actor=actor,
        request=request,
        success=True,
        metadata={
            "from_status": old_status,
            "to_status": event.status,
            "notes_len": len(event.notes) if event.notes else 0,
        },
    )
    db.commit()
    db.refresh(event)
    return event


@router.post("/{reconciliation_event_id}/verify", response_model=ReconciliationEventVerifyResponse)
def verify_reconciliation_with_provider(
    reconciliation_event_id: str,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(admin_required),
):
    event = (
        db.query(PaymentReconciliationEvent)
        .filter(PaymentReconciliationEvent.reconciliation_event_id == reconciliation_event_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not event:
        raise HTTPException(status_code=404, detail="Reconciliation event not found")

    provider = (event.provider or "").lower()
    provider_event = str(event.provider_event or "")
    reference = str(event.reference or "")
    if not reference:
        raise HTTPException(status_code=400, detail="Reconciliation event has no reference")

    if provider != "paystack":
        raise HTTPException(status_code=400, detail=f"Unsupported provider={provider}")

    # Verification is read-only: fetch provider state and store it into payload.verifications[].
    if provider_event.startswith("transfer.") or provider_event.startswith("payout."):
        verification = paystack_service.verify_transfer(reference)
    elif provider_event.startswith("refund."):
        # Paystack refund fetch uses the original transaction reference.
        verification = paystack_service.fetch_refund(reference)
    else:
        # default: treat as transaction reference (payments)
        verification = paystack_service.verify_transaction(reference)

    _append_verification(event, verification=verification)

    # Keep payload bounded defensively (provider payloads can be large).
    if _payload_size(event.payload) > 200_000:
        event.payload = {
            "note": "payload_truncated",
            "verifications": (event.payload or {}).get("verifications", [])[-5:],
        }

    db.add(event)
    write_audit_log(
        db,
        category="money",
        action="reconciliation.verified",
        entity_type="payment_reconciliation_event",
        entity_id=event.reconciliation_event_id,
        actor=actor,
        request=request,
        success=True,
        provider="paystack",
        provider_reference=reference,
        metadata={"provider_event": provider_event},
    )
    db.commit()
    db.refresh(event)

    return ReconciliationEventVerifyResponse(
        reconciliation_event_id=event.reconciliation_event_id,
        provider=event.provider,
        reference=event.reference,
        provider_event=event.provider_event,
        verified_at=datetime.utcnow(),
        verification=verification,
    )

