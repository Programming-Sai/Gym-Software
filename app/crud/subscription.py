# app/crud/subscription.py

from sqlalchemy.orm import Session
from app.models.financials import SubscriptionTier
from app.schemas.subscription import (
    SubscriptionTierCreate,
    SubscriptionTierUpdate,
)


# ---------- CREATE ----------

def create_tier(db: Session, tier_in: SubscriptionTierCreate):
    tier = SubscriptionTier(**tier_in.model_dump())
    db.add(tier)
    db.commit()
    db.refresh(tier)
    return tier


# ---------- READ ----------

def get_tier(db: Session, tier_id: str):
    return (
        db.query(SubscriptionTier)
        .filter(SubscriptionTier.tier_id == tier_id)
        .first()
    )


def get_all_tiers(db: Session, active_only: bool = False):
    query = db.query(SubscriptionTier)
    if active_only:
        query = query.filter(SubscriptionTier.is_active == True)
    return query.order_by(SubscriptionTier.display_order).all()


# ---------- UPDATE ----------

def update_tier(db: Session, tier: SubscriptionTier, tier_in: SubscriptionTierUpdate):
    update_data = tier_in.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(tier, field, value)

    db.commit()
    db.refresh(tier)
    return tier


# ---------- DELETE (Soft Delete Recommended) ----------

def delete_tier(db: Session, tier: SubscriptionTier):
    # Soft delete instead of hard delete
    tier.is_active = False
    db.commit()
    db.refresh(tier)
    return tier
