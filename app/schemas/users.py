# Start simple - you can expand later
from enum import Enum
from pydantic import BaseModel, EmailStr

class UserRole(str, Enum):
    GYM_USER = "gym_user"
    DIETICIAN = "dietician"
    GYM_OWNER = "gym_owner"
    ADMIN = "admin"  # Even though no signup, needed for model

class UserStatus(str, Enum):
    PENDING_VERIFICATION = "pending_verification"
    ACTIVE = "active"
    LIMITED = "limited"  # For dieticians/gym_owners waiting admin approval
    SUSPENDED = "suspended"



class UserCreate(BaseModel):
    email: EmailStr
    password: str  # Frontend validated, we'll hash it
    full_name: str
    phone_number: str  # Frontend validated format
    role: UserRole