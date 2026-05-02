from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class AuditLogOut(BaseModel):
    audit_log_id: str
    created_at: datetime

    category: str
    action: str

    entity_type: str
    entity_id: Optional[str] = None

    actor_user_id: Optional[str] = None
    actor_role: Optional[str] = None
    actor_ip: Optional[str] = None
    user_agent: Optional[str] = None
    request_id: Optional[str] = None

    amount: Optional[Decimal] = None
    currency: Optional[str] = None
    provider: Optional[str] = None
    provider_reference: Optional[str] = None

    payer_user_id: Optional[str] = None
    payee_user_id: Optional[str] = None
    payee_gym_id: Optional[str] = None
    initiated_by_user_id: Optional[str] = None
    approved_by_user_id: Optional[str] = None

    success: bool
    error_message: Optional[str] = None

    audit_metadata: dict[str, Any] = Field(default_factory=dict, serialization_alias="metadata")

    model_config = {"from_attributes": True, "populate_by_name": True}


class AuditLogPurgeResponse(BaseModel):
    deleted: int
