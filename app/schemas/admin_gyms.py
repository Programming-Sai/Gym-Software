from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


GymStatus = Literal["draft", "active", "suspended", "closed"]


class AdminGymOwnerOut(BaseModel):
    user_id: str
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminGymOut(BaseModel):
    gym_id: str
    owner_id: str
    name: str
    description: str | None = None
    address: str
    latitude: float | None = None
    longitude: float | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    status: GymStatus
    subscription_tier: str
    created_at: datetime
    updated_at: datetime

    payouts_enabled: bool
    paystack_recipient_code: str | None = None
    payout_method: str | None = None
    payout_currency: str
    payout_recipient_verified_at: datetime | None = None

    owner: AdminGymOwnerOut | None = None

    model_config = {"from_attributes": True}


class AdminGymStatusChangeRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
