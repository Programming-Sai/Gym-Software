from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


UserRole = Literal["gym_user", "dietician", "gym_owner", "admin", "superadmin"]
UserStatus = Literal["active", "limited", "suspended", "inactive"]


class AdminUserOut(BaseModel):
    user_id: str
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    role: UserRole
    status: UserStatus
    email_verified: bool
    phone_verified: bool
    profile_file_id: str | None = None
    current_subscription_tier_id: str | None = None
    face_file_id: str | None = None
    face_registered_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminUserStatusChangeRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class AdminUserRoleChangeRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class AdminUserPromoteRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class AdminUserDemoteRequest(BaseModel):
    note: str | None = Field(default=None, max_length=500)
    # Used only for demotion, since "previous role" is not stored in DB.
    demote_to_role: Literal["gym_user", "dietician", "gym_owner"] | None = None


class AdminSessionOut(BaseModel):
    session_id: str
    user_id: str
    device_info: str | None = None
    ip_address: str | None = None
    is_active: bool
    created_at: datetime
    expires_at: datetime

    model_config = {"from_attributes": True}


class AdminRevokeSessionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
