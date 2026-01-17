# app/schemas/auth.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional



class SignupRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone_number: Optional[str]
    role: Optional[str] = "gym_user"

class SignupResponse(BaseModel):
    user_id: str
    email: EmailStr
    message: str

