from datetime import datetime
from decimal import Decimal
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


PaymentStatus = Literal["pending", "succeeded", "failed", "refunded"]
PaymentType = Literal["subscription", "checkin", "product", "other"]
SubscriptionStatus = Literal["pending", "active", "past_due", "cancelled"]


class AdminPaymentOut(BaseModel):
    payment_id: str
    user_id: str
    subscription_id: str | None = None
    gym_id: str | None = None

    amount: Decimal
    fee: Decimal
    net_amount: Decimal

    status: PaymentStatus
    payment_type: PaymentType

    provider: str
    provider_payment_id: str | None = None
    receipt_url: str | None = None

    payment_metadata: dict[str, Any] = {}

    created_at: datetime
    updated_at: datetime

    succeeded_at: datetime | None = None
    failed_at: datetime | None = None
    failure_code: str | None = None

    model_config = {"from_attributes": True}


class AdminPaymentDetailOut(AdminPaymentOut):
    raw_provider_payload: dict[str, Any] | None = None


class AdminSubscriptionOut(BaseModel):
    subscription_id: str
    user_id: str
    tier_id: str | None = None
    plan_name: str
    status: SubscriptionStatus
    provider: str

    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminSubscriptionDetailOut(AdminSubscriptionOut):
    payment_ids: list[str] = []


class AdminCancelSubscriptionRequest(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)

