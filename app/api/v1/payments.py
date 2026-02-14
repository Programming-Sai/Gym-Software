from typing import Optional
from fastapi import APIRouter, Depends, Request, Header, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from decimal import Decimal
from app.core.database import get_db
from app.services.paystack_service import PaystackService
from app.models import Subscription, SubscriptionTier, Payment
from app.core.dependencies import get_current_user
import uuid
from app.core.security import validate_callback

router = APIRouter(tags=["Payments"])

paystack_service = PaystackService()


# -------------------------------------------------
# INITIALIZE SUBSCRIPTION PAYMENT
# -------------------------------------------------
@router.post("/initialize")
def initialize_subscription_payment(
    tier_id: str,
    callback_url: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):

    if current_user.role != "gym_user":
        raise HTTPException(status_code=403, detail="Only gym users can have subscriptions")

    tier = db.query(SubscriptionTier).filter(
        SubscriptionTier.tier_id == tier_id,
        SubscriptionTier.is_active == True
    ).first()

    if not tier:
        raise HTTPException(status_code=404, detail="Subscription tier not found")

    validate_callback(callback_url)

    try:
        # Create subscription (pending)
        subscription = Subscription(
            user_id=current_user.user_id,
            tier_id=tier.tier_id,
            plan_name=tier.tier_name,
            status="pending",
            current_period_start=datetime.utcnow(),
            current_period_end=datetime.utcnow() + timedelta(days=30),
        )
        db.add(subscription)
        db.flush()

        # Create payment
        payment = Payment(
            user_id=current_user.user_id,
            subscription_id=subscription.subscription_id,
            amount=tier.price_monthly,
            net_amount=tier.price_monthly,
            status="pending",
            payment_type="subscription",
            provider="paystack",
        )
        db.add(payment)
        db.commit()
        db.refresh(payment)

        reference = payment.payment_id

        metadata = {
            "user_id": current_user.user_id,
            "subscription_id": subscription.subscription_id,
        }

        paystack_response = paystack_service.initialize_transaction(
            email=current_user.email,
            amount=Decimal(tier.price_monthly),
            reference=reference,
            callback_url=callback_url,
            metadata=metadata,
            channels=["card", "mobile_money"],
        )

        return {
            "authorization_url": paystack_response["authorization_url"],
            "reference": reference,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# -------------------------------------------------
# VERIFY PAYMENT (MANUAL / POLLING)
# -------------------------------------------------
@router.get("/verify/{reference}")
def verify_payment(reference: str, db: Session = Depends(get_db)):
    payment = db.query(Payment).filter(
        Payment.payment_id == reference
    ).first()

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    verification = paystack_service.verify_transaction(reference)

    if verification["status"] == "success":
        payment.status = "succeeded"
        payment.provider_payment_id = verification["id"]
        payment.fee = Decimal(verification.get("fees", 0)) / 100
        payment.net_amount = payment.amount - payment.fee

        subscription = payment.subscription
        subscription.status = "active"

        db.commit()

    return {"status": payment.status}


# -------------------------------------------------
# WEBHOOK
# -------------------------------------------------
@router.post("/webhook")
async def paystack_webhook(
    request: Request,
    x_paystack_signature: str = Header(None),
    db: Session = Depends(get_db),
):
    raw_body = await request.body()

    if not paystack_service.verify_webhook_signature(
        raw_body, x_paystack_signature
    ):
        raise HTTPException(status_code=400, detail="Invalid signature")

    event = await request.json()

    if event["event"] == "charge.success":
        data = event["data"]
        reference = data["reference"]

        payment = db.query(Payment).filter(
            Payment.payment_id == reference
        ).first()

        if payment and payment.status != "succeeded":
            payment.status = "succeeded"
            payment.provider_payment_id = str(data["id"])
            payment.fee = Decimal(data.get("fees", 0)) / 100
            payment.net_amount = payment.amount - payment.fee

            subscription = payment.subscription
            subscription.status = "active"

            db.commit()

    return {"status": "ok"}
