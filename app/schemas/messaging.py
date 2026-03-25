from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.enums import UserRole

class MessageSend(BaseModel):
    receiver_id: UUID
    content: str
    file_id: Optional[UUID] = None

    @field_validator("content")
    @classmethod
    def normalize_content(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("content cannot be empty")
        return value


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message_id: UUID
    sender_id: UUID
    sender_type: UserRole
    receiver_id: UUID
    receiver_type: UserRole
    content: str
    file_id: Optional[UUID] = None
    created_at: datetime


class ConversationPreview(BaseModel):
    user_id: UUID
    user_type: UserRole
    user_name: str
    last_message: Optional[MessageResponse] = None


class ConversationResponse(BaseModel):
    messages: list[MessageResponse]
    total: int
    limit: int
    offset: int
