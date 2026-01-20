from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from uuid import UUID

class GymBase(BaseModel):
    name: str
    address: str
    description: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    contact_email: Optional[EmailStr]
    contact_phone: Optional[str]
    equipment: Optional[List[str]] = []
    facilities: Optional[List[str]] = []
    capacity: Optional[int]
    opening_hours: Optional[Dict[str, str]] = {}

class GymCreate(GymBase):
    pass

class GymResponse(BaseModel):
    gym_id: str
    owner_id: str

    name: str
    description: Optional[str]
    address: str

    latitude: Optional[float]
    longitude: Optional[float]

    contact_email: Optional[EmailStr]
    contact_phone: Optional[str]

    equipment: List[str] = []
    facilities: List[str] = []
    opening_hours: Dict[str, str] = {}
    capacity: Optional[int]

    status: str
    subscription_tier: str

    average_rating: float
    total_ratings: int

    class Config:
        from_attributes = True



class GymListResponse(BaseModel):
    gyms: List[GymResponse]
    total: int

    class Config:
        from_attributes = True

class GymUpdate(BaseModel):
    name: Optional[str]
    address: Optional[str]
    description: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    contact_email: Optional[EmailStr]
    contact_phone: Optional[str]
    equipment: Optional[List[str]]
    facilities: Optional[List[str]]
    capacity: Optional[int]
    opening_hours: Optional[Dict[str, str]] 