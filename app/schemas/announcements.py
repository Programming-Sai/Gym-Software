from pydantic import BaseModel
from datetime import datetime
from typing import Literal, Optional


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    audience: str = "all"          # all | members | staff
    status: str = "draft"      # draft | published
    publish_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_important: bool = False


class AnnouncementResponse(BaseModel):
    announcement_id: str
    title: str
    content: str
    audience: str
    is_important: bool
    created_at: datetime
    is_read: bool

    class Config:
        from_attributes = True



class AnnouncementUpdateRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    audience: Optional[Literal["all", "members", "staff"]] = None
    publish_at: Optional[datetime] = None
    is_important: Optional[bool] = None
    