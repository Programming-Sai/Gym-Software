from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.financials import Subscription
from app.models.users import User
from app.schemas.admin_money import (
    AdminCancelSubscriptionRequest,
    AdminSubscriptionDetailOut,
    AdminSubscriptionOut,
)
from app.services.audit_log_service import write_audit_log


router = APIRouter(tags=["Admin | Subscriptions"])


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def superadmin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "superadmin":
        raise HTTPException(status_code=403, detail="Superadmin access required")
    return current_user


@router.get("/", response_model=list[AdminSubscriptionOut])
def list_subscriptions(
    status: Optional[str] = Query(None, description="pending|active|past_due|cancelled"),
    user_id: Optional[str] = Query(None),
    tier_id: Optional[str] = Query(None),
    from_ts: Optional[datetime] = Query(None),
    to_ts: Optional[datetime] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    q = db.query(Subscription)
    if status:
        q = q.filter(Subscription.status == status)
    if user_id:
        q = q.filter(Subscription.user_id == user_id)
    if tier_id:
        q = q.filter(Subscription.tier_id == tier_id)
    if from_ts:
        q = q.filter(Subscription.created_at >= from_ts)
    if to_ts:
        q = q.filter(Subscription.created_at <= to_ts)
    return q.order_by(Subscription.created_at.desc()).limit(limit).offset(offset).all()


@router.get("/{subscription_id}", response_model=AdminSubscriptionDetailOut)
def get_subscription(
    subscription_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    subscription = (
        db.query(Subscription)
        .options(joinedload(Subscription.payments))
        .filter(Subscription.subscription_id == subscription_id)
        .first()
    )
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    payment_ids = [p.payment_id for p in (subscription.payments or [])]
    out = AdminSubscriptionDetailOut.model_validate(subscription)
    out.payment_ids = payment_ids
    return out


@router.post("/{subscription_id}/cancel", response_model=AdminSubscriptionOut)
def cancel_subscription(
    subscription_id: str,
    payload: AdminCancelSubscriptionRequest,
    request: Request,
    db: Session = Depends(get_db),
    superadmin: User = Depends(superadmin_required),
):
    subscription = (
        db.query(Subscription)
        .options(joinedload(Subscription.user))
        .filter(Subscription.subscription_id == subscription_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    if subscription.status == "cancelled":
        return subscription

    old_status = subscription.status
    now = datetime.utcnow()
    subscription.status = "cancelled"
    subscription.cancel_at_period_end = False
    if subscription.current_period_end is None or subscription.current_period_end > now:
        subscription.current_period_end = now

    # Remove entitlement if it matches this subscription.
    user = subscription.user
    if user and user.current_subscription_tier_id == subscription.tier_id:
        user.current_subscription_tier_id = None
        db.add(user)

    db.add(subscription)
    write_audit_log(
        db,
        category="money",
        action="subscription.cancelled",
        entity_type="subscription",
        entity_id=subscription.subscription_id,
        actor=superadmin,
        request=request,
        success=True,
        payer_user_id=subscription.user_id,
        metadata={"from": old_status, "reason": payload.reason},
    )
    db.commit()
    db.refresh(subscription)
    return subscription

