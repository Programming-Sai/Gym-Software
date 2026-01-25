# app/schemas/user.py
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    GYM_USER = "gym_user"
    DIETICIAN = "dietician"
    GYM_OWNER = "gym_owner"
    ADMIN = "admin"

class UserStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    LIMITED = "limited"
    SUSPENDED = "suspended"

class UserMeResponse(BaseModel):
    user_id: str
    email: EmailStr
    full_name: str
    phone_number: Optional[str]
    role: UserRole
    status: UserStatus
    email_verified: bool
    phone_verified: bool
    profile_file_id: Optional[str]
    current_subscription_tier_id: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Important for SQLAlchemy models


class RegisterFaceResponse(BaseModel):
    message: str
    registered_at: datetime

class UserFaceStatusResponse(BaseModel):
    has_face: bool
    registered_at: Optional[datetime]
