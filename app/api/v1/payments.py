# app/api/v1/payments.py
from typing import Optional
from fastapi import APIRouter, Depends, Request, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from decimal import Decimal
import logging
import traceback

from app.core.database import get_db
from app.models.users import User
from app.services.paystack_service import PaystackService
from app.models import Subscription, SubscriptionTier, Payment, PaymentReconciliationEvent
from app.core.dependencies import get_current_user
from app.core.security import validate_callback

router = APIRouter(tags=["Payments"])
paystack_service = PaystackService()
logger = logging.getLogger(__name__)


# -----------------------
# Helper: find user's active or pending subscription
# -----------------------
def _get_user_active_or_pending(db: Session, user_id: str):
    return (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user_id,
            Subscription.status.in_(["active", "pending"])
        )
        .order_by(Subscription.created_at.desc())
        .first()
    )


# -------------------------------------------------
# INITIALIZE SUBSCRIPTION PAYMENT (idempotent-ish)
# -------------------------------------------------
@router.post("/initialize")
def initialize_subscription_payment(
    tier_id: str,
    callback_url: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != "gym_user":
        raise HTTPException(status_code=403, detail="Only gym users can have subscriptions")

    tier = db.query(SubscriptionTier).filter(
        SubscriptionTier.tier_id == tier_id,
        SubscriptionTier.is_active == True
    ).first()

    if not tier:
        raise HTTPException(status_code=404, detail="Subscription tier not found")

    # Only allow user tier subscriptions for gym users (business rule)
    if tier.tier_type != "user":
        raise HTTPException(status_code=403, detail="Tier not available for user subscriptions")

    validate_callback(callback_url)

    # Check for existing active / pending subscription (idempotency)
    existing = _get_user_active_or_pending(db, current_user.user_id)
    if existing:
        # If already active
        if existing.status == "active":
            # If already on same tier, return existing state
            if str(existing.tier_id) == str(tier.tier_id):
                return {
                    "status": "already_active",
                    "subscription_id": existing.subscription_id,
                    "tier_id": existing.tier_id,
                }
            # Different tier while active: require explicit upgrade endpoint
            raise HTTPException(
                status_code=400,
                detail="Active subscription exists. Use upgrade endpoint to change tiers."
            )
        # If pending: return reference or attempt to re-init if necessary
        if existing.status == "pending":
            pending_payment = None
            # try to find the most recent pending payment
            for p in (existing.payments or []):
                if p.status == "pending":
                    pending_payment = p
                    break

            if pending_payment:
                # Always (re)initialize with provider using same reference.
                try:
                    pm = pending_payment.payment_metadata or {}
                    metadata = {
                        "user_id": current_user.user_id,
                        "subscription_id": existing.subscription_id,
                        "expected_amount": pm.get("expected_amount") or int(Decimal(pending_payment.amount) * 100),
                        "currency": pm.get("currency", "GHS"),
                    }
                    paystack_data = paystack_service.initialize_transaction(
                        email=current_user.email,
                        amount=Decimal(pending_payment.amount),
                        reference=pending_payment.payment_id,
                        callback_url=callback_url,
                        metadata=metadata,
                        channels=["card", "mobile_money"],
                    )
                    # persist init payload
                    pm = pending_payment.payment_metadata or {}
                    pm["init"] = {
                        "returned_at": datetime.utcnow().isoformat(),
                        "authorization_url": paystack_data.get("authorization_url"),
                        "raw": paystack_data,
                    }
                    pending_payment.payment_metadata = pm
                    db.add(pending_payment)
                    db.commit()
                    return {
                        "status": "pending",
                        "reference": pending_payment.payment_id,
                        "authorization_url": paystack_data.get("authorization_url"),
                    }
                except HTTPException as he:
                    logger.info("Re-init failed; ask user to call verify for reference %s", pending_payment.payment_id)
                    return {
                        "status": "pending",
                        "reference": pending_payment.payment_id,
                        "note": "provider init failed; please call verify endpoint"
                    }
            # No pending payment (unexpected)
            raise HTTPException(status_code=500, detail="Pending subscription found but no pending payment")

    # No existing active/pending: create new pending subscription + payment
    try:
        subscription = Subscription(
            user_id=current_user.user_id,
            tier_id=tier.tier_id,
            plan_name=tier.tier_name,
            status="pending",
        )
        db.add(subscription)
        db.flush()
        expected = int(Decimal(tier.price_monthly) * 100)

        payment = Payment(
            user_id=current_user.user_id,
            subscription_id=subscription.subscription_id,
            amount=tier.price_monthly,
            net_amount=Decimal("0.00"),
            status="pending",
            payment_type="subscription",
            provider="paystack",
            payment_metadata={
                "expected_amount": expected,
                "currency": "GHS",
                "created_at": datetime.utcnow().isoformat(),
                "init": None
            },
        )
        db.add(payment)
        db.flush()

        # commit local rows to guarantee reconciliation record exists
        db.commit()

        reference = payment.payment_id

        metadata = {
            "user_id": current_user.user_id,
            "subscription_id": subscription.subscription_id,
            "expected_amount": expected,
            "currency": "GHS",
        }

        # Try provider initialize. If it fails, keep local pending rows but record init error.
        try:
            paystack_data = paystack_service.initialize_transaction(
                email=current_user.email,
                amount=Decimal(tier.price_monthly),
                reference=reference,
                callback_url=callback_url,
                metadata=metadata,
                channels=["card", "mobile_money"],
            )
            # persist init response back to payment
            try:
                with db.begin():
                    p = db.query(Payment).filter(Payment.payment_id == reference).with_for_update().first()
                    pm = p.payment_metadata or {}
                    pm["init"] = {
                        "returned_at": datetime.utcnow().isoformat(),
                        "authorization_url": paystack_data.get("authorization_url"),
                        "raw": paystack_data,
                    }
                    p.payment_metadata = pm
                    db.add(p)
            except Exception:
                logger.exception("Failed to persist init metadata for payment %s", reference)

            return {
                "authorization_url": paystack_data["authorization_url"],
                "reference": reference,
            }

        except HTTPException as he:
            # provider initialization failure - keep pending rows but record the failure so support can reconcile
            try:
                with db.begin():
                    p = db.query(Payment).filter(Payment.payment_id == reference).with_for_update().first()
                    pm = p.payment_metadata or {}
                    pm["init_error"] = {
                        "error": str(he.detail if hasattr(he, "detail") else he),
                        "at": datetime.utcnow().isoformat(),
                    }
                    p.payment_metadata = pm
                    db.add(p)
            except Exception:
                logger.exception("Failed to persist init error metadata for payment %s", reference)

            # Return error, but client has the reference to retry/verify later
            raise HTTPException(status_code=502, detail=f"Payment provider initialization failed; reference={reference}")

    except IntegrityError:
        db.rollback()
        # Race: another request created the pending/active row. Fetch it and return an idempotent response.
        existing = _get_user_active_or_pending(db, current_user.user_id)
        if not existing:
            raise HTTPException(status_code=500, detail="Integrity error during initialization")

        if existing.status == "active":
            if str(existing.tier_id) == str(tier.tier_id):
                return {"status": "already_active", "subscription_id": existing.subscription_id, "tier_id": existing.tier_id}
            raise HTTPException(status_code=400, detail="Active subscription exists. Use upgrade endpoint.")

        # pending
        pending_payment = next((p for p in (existing.payments or []) if p.status == "pending"), None)
        if pending_payment:
            pm = pending_payment.payment_metadata or {}
            init_info = pm.get("init") or {}
            return {
                "status": "pending",
                "reference": pending_payment.payment_id,
                "authorization_url": init_info.get("authorization_url"),
                "note": "race: returning existing pending"
            }
        raise HTTPException(status_code=500, detail="Race: pending subscription exists but no pending payment")
    except HTTPException:
        # re-raise known fastapi HTTP exceptions
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to initialize subscription payment")
        raise HTTPException(status_code=500, detail="Failed to initialize payment")







# -------------------------------------------------
# VERIFY PAYMENT (MANUAL / POLLING)
# -------------------------------------------------
@router.post("/verify/{reference}")
def verify_payment(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    client_error: Optional[HTTPException] = None

    try:
        # Lock the payment row (this will use the session transaction implicitly)
        payment = (
            db.query(Payment)
            .filter(Payment.payment_id == reference)
            .with_for_update(nowait=False)
            .first()
        )

        if not payment:
            raise HTTPException(status_code=404, detail="Payment not found")

        if payment.user_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="Not allowed")

        # Idempotent fast path
        if payment.status == "succeeded":
            return {"status": "succeeded"}

        # Ask provider for authoritative status
        verification = paystack_service.verify_transaction(reference)
        provider_status = str(verification.get("status") or "").lower()

        # provider returns amount in smallest unit
        provider_amount = int(verification.get("amount", 0))
        provider_currency = (verification.get("currency") or "").upper()
        metadata = verification.get("metadata") or {}

        pm = payment.payment_metadata or {}
        expected_local_amount = int(Decimal(payment.amount) * 100)

        # Advisory: compare provided expected_amount to local expected; record warnings, don't fail on mismatch
        raw_expected_amount = pm.get("expected_amount", metadata.get("expected_amount"))
        if raw_expected_amount is not None:
            try:
                if int(raw_expected_amount) != expected_local_amount:
                    pm.setdefault("verification_warnings", []).append({
                        "reason": "expected_amount_local_mismatch",
                        "metadata_expected_amount": raw_expected_amount,
                        "local_expected_amount": expected_local_amount,
                        "at": datetime.utcnow().isoformat()
                    })
            except (TypeError, ValueError):
                pm.setdefault("verification_warnings", []).append({
                    "reason": "invalid_expected_amount",
                    "metadata_expected_amount": raw_expected_amount,
                    "at": datetime.utcnow().isoformat()
                })

        # Handle provider not-success states
        if provider_status != "success":
            payment.raw_provider_payload = verification

            if provider_status in {"failed", "abandoned", "reversed", "cancelled"}:
                payment.status = "failed"
                payment.failed_at = datetime.utcnow()
                payment.failure_code = "provider_not_success"
                pm.setdefault("verification_issues", []).append({
                    "reason": "provider_not_success",
                    "provider_status": provider_status,
                    "at": datetime.utcnow().isoformat()
                })
                client_error = HTTPException(status_code=400, detail="Provider transaction is not successful")
            else:
                pm.setdefault("verification_warnings", []).append({
                    "reason": "provider_not_success_yet",
                    "provider_status": provider_status or None,
                    "at": datetime.utcnow().isoformat()
                })

            payment.payment_metadata = pm
            db.add(payment)

            # Persist failure/warning state before returning
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=400, detail="Subscription activation conflict")
            if client_error:
                raise client_error
            return {"status": payment.status}

        # Verify currency & amount (local amount is authoritative)
        if provider_currency != "GHS" or provider_amount != expected_local_amount:
            payment.status = "failed"
            payment.failed_at = datetime.utcnow()
            payment.failure_code = "amount_currency_mismatch"
            pm.setdefault("verification_issues", []).append({
                "reason": "amount_currency_mismatch",
                "provider_amount": provider_amount,
                "expected_amount": expected_local_amount,
                "at": datetime.utcnow().isoformat()
            })
            payment.payment_metadata = pm
            db.add(payment)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=400, detail="Subscription activation conflict")
            raise HTTPException(status_code=400, detail="Payment amount or currency does not match expected value")

        # Guard metadata subscription/user match
        if str(metadata.get("user_id")) != str(payment.user_id) or str(metadata.get("subscription_id")) != str(payment.subscription_id):
            payment.status = "failed"
            payment.failed_at = datetime.utcnow()
            payment.failure_code = "metadata_mismatch"
            pm.setdefault("verification_issues", []).append({
                "reason": "metadata_mismatch",
                "metadata": metadata,
                "at": datetime.utcnow().isoformat()
            })
            payment.payment_metadata = pm
            db.add(payment)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=400, detail="Subscription activation conflict")
            raise HTTPException(status_code=400, detail="Payment metadata mismatch")

        # Passed validation; apply success
        subscription = payment.subscription
        if not subscription:
            payment.status = "failed"
            payment.failed_at = datetime.utcnow()
            payment.failure_code = "missing_subscription"
            payment.payment_metadata = pm
            db.add(payment)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                raise HTTPException(status_code=400, detail="Subscription activation conflict")
            raise HTTPException(status_code=500, detail="Subscription missing for payment")

        # Write success fields
        payment.status = "succeeded"
        payment.provider_payment_id = str(verification.get("id"))
        provider_fees = verification.get("fees", 0) or 0
        payment.fee = Decimal(provider_fees) / 100
        payment.net_amount = Decimal(payment.amount) - payment.fee
        payment.succeeded_at = datetime.utcnow()
        payment.raw_provider_payload = verification

        # Start billing period using tier.duration_days (fallback to 30)
        now = datetime.utcnow()
        days = getattr(subscription.tier, "duration_days", 30) or 30
        subscription.current_period_start = now
        subscription.current_period_end = now + timedelta(days=int(days))
        subscription.status = "active"
        subscription.provider = "paystack"

        # Sync entitlement
        user = subscription.user
        user.current_subscription_tier_id = subscription.tier_id

        # store verification in metadata too
        pm["provider_verification"] = {
            "id": verification.get("id"),
            "raw": verification,
            "verified_at": datetime.utcnow().isoformat()
        }
        payment.payment_metadata = pm

        db.add(payment)
        db.add(subscription)
        db.add(user)

        # Persist success atomically
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(status_code=400, detail="Subscription activation conflict")

        return {"status": payment.status}

    except HTTPException:
        # re-raise known HTTP exceptions
        raise
    except Exception:
        # Unexpected error: log and return 500
        logger.exception("Unhandled exception during verify for reference %s: %s", reference, traceback.format_exc())
        try:
            db.rollback()
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Internal server error while verifying payment")






# -------------------------------------------------
# WEBHOOK
# -------------------------------------------------
@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(...),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()

    if not paystack_service.verify_webhook_signature(
        raw_body, x_paystack_signature
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = await request.json()

    # Only process charge.success for now (idempotent)
    if event.get("event") == "charge.success":
        data = event.get("data", {})
        reference = data.get("reference")
        if not reference:
            return {"status": "ignored", "reason": "no reference"}

        try:
            with db.begin():
                payment = db.query(Payment).filter(
                    Payment.payment_id == reference
                ).with_for_update(nowait=False).first()

                # If local payment row does not exist, persist a reconciliation event for follow-up.
                if not payment:
                    now_iso = datetime.utcnow().isoformat()
                    provider_event = event.get("event") or "unknown"
                    provider_event_id = str(data.get("id")) if data.get("id") is not None else None

                    existing_recon = db.query(PaymentReconciliationEvent).filter(
                        PaymentReconciliationEvent.provider == "paystack",
                        PaymentReconciliationEvent.provider_event == provider_event,
                        PaymentReconciliationEvent.reference == reference,
                    ).with_for_update(nowait=False).first()

                    if existing_recon:
                        payload = existing_recon.payload or {}
                        payload["seen_count"] = int(payload.get("seen_count", 1)) + 1
                        payload["last_seen_at"] = now_iso
                        payload["last_event"] = event
                        existing_recon.provider_event_id = provider_event_id or existing_recon.provider_event_id
                        existing_recon.payload = payload
                        db.add(existing_recon)
                        reconciliation_event_id = existing_recon.reconciliation_event_id
                    else:
                        recon = PaymentReconciliationEvent(
                            provider="paystack",
                            provider_event=provider_event,
                            provider_event_id=provider_event_id,
                            reference=reference,
                            status="open",
                            payload={
                                "seen_count": 1,
                                "first_seen_at": now_iso,
                                "last_seen_at": now_iso,
                                "last_event": event,
                            },
                            notes="Webhook received for unknown payment reference",
                        )
                        db.add(recon)
                        db.flush()
                        reconciliation_event_id = recon.reconciliation_event_id

                    logger.error(
                        "Webhook unknown payment reference %s; reconciliation event %s recorded",
                        reference,
                        reconciliation_event_id,
                    )
                    return {
                        "status": "ok",
                        "note": "reconciliation_recorded",
                        "reconciliation_event_id": reconciliation_event_id,
                    }

                # Idempotent: already processed
                if payment.status == "succeeded":
                    return {"status": "ok", "note": "already processed"}

                # Validate provider payload vs local expected values (amount/currency/metadata)
                provider_amount = int(data.get("amount", 0))
                provider_currency = (data.get("currency") or "").upper()
                metadata = data.get("metadata") or {}

                if provider_currency != "GHS" or provider_amount != int(Decimal(payment.amount) * 100):
                    # mismatch: mark failed and persist reason
                    payment.status = "failed"
                    payment.failed_at = datetime.utcnow()
                    payment.failure_code = "amount_currency_mismatch"
                    pm = payment.payment_metadata or {}
                    pm.setdefault("webhook_issues", []).append({
                        "reason": "amount_currency_mismatch",
                        "provider_amount": provider_amount,
                        "expected_amount": int(Decimal(payment.amount) * 100),
                        "metadata":metadata,
                        "at": datetime.utcnow().isoformat()
                    })
                    payment.payment_metadata = pm
                    db.add(payment)
                    logger.error("Webhook mismatch for %s: provider_amount=%s expected=%s",
                                 reference, provider_amount, int(Decimal(payment.amount) * 100))
                    return {"status": "ok", "note": "mismatch"}

                # Guard metadata subscription/user match (same enforcement as verify endpoint)
                if str(metadata.get("user_id")) != str(payment.user_id) or str(metadata.get("subscription_id")) != str(payment.subscription_id):
                    payment.status = "failed"
                    payment.failed_at = datetime.utcnow()
                    payment.failure_code = "metadata_mismatch"
                    pm = payment.payment_metadata or {}
                    pm.setdefault("webhook_issues", []).append({
                        "reason": "metadata_mismatch",
                        "metadata": metadata,
                        "at": datetime.utcnow().isoformat()
                    })
                    payment.payment_metadata = pm
                    db.add(payment)
                    logger.error("Webhook metadata mismatch for %s: metadata=%s", reference, metadata)
                    return {"status": "ok", "note": "metadata_mismatch"}

                # All good: mark succeeded
                subscription = payment.subscription
                if not subscription:
                    payment.status = "failed"
                    payment.failed_at = datetime.utcnow()
                    payment.failure_code = "missing_subscription"
                    db.add(payment)
                    logger.error("Webhook: subscription missing for payment %s", reference)
                    return {"status": "ok", "note": "missing subscription"}

                payment.status = "succeeded"
                payment.provider_payment_id = str(data.get("id"))
                payment.fee = Decimal(data.get("fees", 0)) / 100
                payment.net_amount = Decimal(payment.amount) - payment.fee
                payment.succeeded_at = datetime.utcnow()
                payment.raw_provider_payload = data

                now = datetime.utcnow()
                days = getattr(subscription.tier, "duration_days", 30) or 30
                subscription.current_period_start = now
                subscription.current_period_end = now + timedelta(days=int(days))
                subscription.status = "active"

                user = subscription.user
                user.current_subscription_tier_id = subscription.tier_id

                # persist raw webhook for audit in metadata as well
                pm = payment.payment_metadata or {}
                pm["raw_webhook"] = data
                payment.payment_metadata = pm

                db.add(payment)
                db.add(subscription)
                db.add(user)

        except IntegrityError:
            db.rollback()
            logger.exception("Webhook integrity error for reference %s", reference)
            # Return non-2xx so provider retries and we do not lose recoverable events.
            raise HTTPException(status_code=500, detail="Integrity error processing webhook")

        except Exception as exc:
            db.rollback()
            logger.exception("Unhandled exception processing webhook for reference %s: %s", reference, traceback.format_exc())
            # Let the provider retry for transient errors
            raise HTTPException(status_code=500, detail="Internal error processing webhook")
    return {"status": "ok"}

