from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ReconciliationStatus = Literal["open", "flagged", "resolved", "ignored"]


class ReconciliationEventOut(BaseModel):
    reconciliation_event_id: str
    provider: str
    provider_event: str
    provider_event_id: str | None = None
    reference: str
    status: ReconciliationStatus
    payload: dict[str, Any]
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReconciliationEventUpdateRequest(BaseModel):
    status: ReconciliationStatus | None = None
    notes: str | None = Field(default=None, max_length=4000)


class ReconciliationEventVerifyResponse(BaseModel):
    reconciliation_event_id: str
    provider: str
    reference: str
    provider_event: str
    verified_at: datetime
    verification: dict[str, Any]

