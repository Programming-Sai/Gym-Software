# app/schemas/subscription.py

from pydantic import BaseModel 
from decimal import Decimal
from typing import List, Optional, Literal, Dict, Any


# ----------- Subscription Tier Schemas -----------

class SubscriptionTierBase(BaseModel):
    tier_name: str
    tier_type: Literal["user", "gym"]
    price_monthly: Decimal
    price_yearly: Optional[Decimal] = None
    features: List[str]
    is_active: bool = True
    display_order: int = 0


class SubscriptionTierCreate(SubscriptionTierBase):
    pass


class SubscriptionTierUpdate(BaseModel):
    tier_name: Optional[str] = None
    tier_type: Optional[Literal["user", "gym"]] = None
    price_monthly: Optional[Decimal] = None
    price_yearly: Optional[Decimal] = None
    features: Optional[List[str]] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class SubscriptionTierResponse(SubscriptionTierBase):
    tier_id: str

    class Config:
        from_attributes = True
