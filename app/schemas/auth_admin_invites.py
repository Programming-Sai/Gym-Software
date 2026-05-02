from typing import Optional

from pydantic import BaseModel, Field


class AcceptAdminInviteRequest(BaseModel):
    password: Optional[str] = Field(None, min_length=8, max_length=200)
    full_name: Optional[str] = Field(None, min_length=2, max_length=120)
    phone_number: Optional[str] = Field(None, max_length=32)
