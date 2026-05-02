from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AnnouncementAudience = Literal["all", "members", "staff"]
AnnouncementStatus = Literal["draft", "published", "archived"]


class PlatformAnnouncementCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=20000)
    audience: AnnouncementAudience = "all"
    # Announcements are created as drafts and then published via the publish endpoint.
    # publish_at: datetime | None = None  # Optional scheduling timestamp (server will stamp on publish)
    expires_at: datetime | None = None
    is_important: bool = False


class PlatformAnnouncementUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    audience: AnnouncementAudience | None = None
    expires_at: datetime | None = None
    is_important: bool | None = None


class PlatformAnnouncementOut(BaseModel):
    announcement_id: str
    created_by: str
    target_type: Literal["platform"]
    gym_id: None = None

    title: str
    content: str
    audience: AnnouncementAudience
    status: AnnouncementStatus

    publish_at: datetime | None
    expires_at: datetime | None
    is_important: bool

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
