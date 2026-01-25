# app/schemas/checkins.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CheckinRequest(BaseModel):
    qr_nonce: str
    face_image_base64: str
    client_lat: Optional[float] = None
    client_lng: Optional[float] = None


class CheckinResponse(BaseModel):
    checkin_id: str
    status: str
    face_score: Optional[float]
    rejected_reason: Optional[str] = None
    created_at: datetime
    confirmed_at: Optional[datetime]
