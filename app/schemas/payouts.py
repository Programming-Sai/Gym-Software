from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


PayoutStatus = Literal["pending", "processing", "completed", "failed", "cancelled"]
PayoutEventType = Literal[
    "created",
    "approved",
    "process_attempt",
    "provider_verification",
    "provider_webhook",
    "provider_error",
    "cancelled",
    "refreshed",
]


class PayoutCreateRequest(BaseModel):
    gym_id: str = Field(..., min_length=1)
    amount: Decimal = Field(..., gt=0)
    note: str | None = None


class PayoutApproveRequest(BaseModel):
    note: str | None = None


class PayoutProcessRequest(BaseModel):
    retry: bool = False


class PayoutCancelRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class PayoutRetryRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class PayoutOut(BaseModel):
    payout_id: str
    gym_id: str
    payment_id: str | None

    amount: Decimal
    fee: Decimal
    net_amount: Decimal

    status: PayoutStatus

    initiated_by: str
    approved_by: str | None
    approved_at: datetime | None

    provider: str
    recipient_code: str
    transfer_reference: str | None
    provider_transfer_id: str | None

    processed_date: datetime | None
    completed_date: datetime | None
    failure_reason: str | None

    payout_metadata: dict[str, Any] = {}

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PayoutEventOut(BaseModel):
    type: PayoutEventType
    at: datetime
    data: dict[str, Any] = {}


class PayoutEventsOut(BaseModel):
    payout_id: str
    events: list[PayoutEventOut]
