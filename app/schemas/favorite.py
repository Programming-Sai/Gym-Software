from pydantic import BaseModel
from datetime import datetime

from app.schemas.gyms import GymResponse


class FavoriteResponse(BaseModel):
    favorite_id: str
    created_at: datetime

    gym: GymResponse  # name, address, image, rating, etc

    class Config:
        from_attributes = True
