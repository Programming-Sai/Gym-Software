from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, EmailStr, Field


class AdminInviteCreateRequest(BaseModel):
    email: EmailStr
    role_to_grant: Literal["admin", "superadmin"] = "admin"
    expires_in_hours: int = Field(48, ge=1, le=168)


class AdminInviteRevokeRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class AdminInviteOut(BaseModel):
    invite_id: str
    email: EmailStr
    role_to_grant: str
    expires_at: datetime

    created_by: Optional[str] = None
    created_at: datetime

    accepted_by: Optional[str] = None
    accepted_at: Optional[datetime] = None

    revoked_by: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revoke_reason: Optional[str] = None

    send_count: int
    last_sent_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AdminInviteCreatedResponse(AdminInviteOut):
    token: str

