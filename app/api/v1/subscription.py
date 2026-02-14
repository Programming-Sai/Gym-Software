# app/api/v1/subscription.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.subscription import (
    SubscriptionTierCreate,
    SubscriptionTierUpdate,
    SubscriptionTierResponse,
)
from app.crud import subscription as crud
from app.models.users import User


router = APIRouter(tags=["Subscription Plans"])


# -------- ADMIN GUARD --------

def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


# -------- CREATE --------

@router.post("/", response_model=SubscriptionTierResponse)
def create_subscription_tier(
    tier_in: SubscriptionTierCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    return crud.create_tier(db, tier_in)


# -------- READ ALL --------

@router.get("/", response_model=List[SubscriptionTierResponse])
def list_subscription_tiers(
    active_only: bool = False,
    db: Session = Depends(get_db),
):
    return crud.get_all_tiers(db, active_only=active_only)


# -------- READ ONE --------

@router.get("/{tier_id}", response_model=SubscriptionTierResponse)
def get_subscription_tier(
    tier_id: str,
    db: Session = Depends(get_db),
):
    tier = crud.get_tier(db, tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")
    return tier


# -------- UPDATE --------

@router.put("/{tier_id}", response_model=SubscriptionTierResponse)
def update_subscription_tier(
    tier_id: str,
    tier_in: SubscriptionTierUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    tier = crud.get_tier(db, tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    return crud.update_tier(db, tier, tier_in)


# -------- DELETE (SOFT) --------

@router.delete("/{tier_id}", response_model=SubscriptionTierResponse)
def delete_subscription_tier(
    tier_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_required),
):
    tier = crud.get_tier(db, tier_id)
    if not tier:
        raise HTTPException(status_code=404, detail="Tier not found")

    return crud.delete_tier(db, tier)
