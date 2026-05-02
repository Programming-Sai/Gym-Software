from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


NotificationType = Literal["info", "alert", "reminder", "achievement"]


class AdminPlatformNotificationSendRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    message: str = Field(..., min_length=1, max_length=2000)
    notification_type: NotificationType = "info"
    image_url: str | None = Field(default=None, max_length=2000)
    data: dict[str, Any] | None = None
    send_push: bool = True


class AdminPlatformNotificationBroadcastRequest(AdminPlatformNotificationSendRequest):
    audience: Literal["all", "role"] = "all"
    role: Literal["gym_user", "dietician", "gym_owner", "admin", "superadmin"] | None = None


class AdminPlatformNotificationSendResponse(BaseModel):
    notification_id: str
    recipients_count: int


class AdminPlatformNotificationOut(BaseModel):
    notification_id: str
    type: str
    scope: str
    title: str
    message: str
    image_url: str | None
    created_at: datetime
    sent_at: datetime | None
    recipients_count: int

