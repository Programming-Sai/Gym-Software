from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class AdminDieticianUserOut(BaseModel):
    user_id: str
    full_name: str
    email: EmailStr
    phone_number: str | None = None
    role: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AdminDieticianOut(BaseModel):
    dietician_id: str
    user_id: str
    bio: str | None = None
    specializations: list[str] = []
    experience_years: int
    status: str
    profile_file_id: str | None = None
    average_rating: float | None = None
    total_ratings: int
    created_at: datetime
    updated_at: datetime

    user: AdminDieticianUserOut | None = None

    model_config = {"from_attributes": True}


class AdminDieticianStatusChangeRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)
