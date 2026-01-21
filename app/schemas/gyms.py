from fastapi import UploadFile
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from uuid import UUID
from enum import Enum  
from datetime import datetime


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

class GymPhotoCreate(BaseModel):
    is_primary: bool = False  # we still accept this

class GymDocumentType(str, Enum):
    business_license = "business_license"
    tax_id = "tax_id"
    proof_of_ownership = "proof_of_ownership"
    other = "other"

class GymDocumentCreate(BaseModel):
    document_type: GymDocumentType

class FileResponse(BaseModel):
    file_id: str
    original_filename: str
    extension: str
    mime_type: str
    storage_url: str
    storage_key: str
    file_type: str
    purpose: str

    class Config:
        orm_mode = True

class GymPhotoResponse(BaseModel):
    gym_photo_id: str
    gym_id: str
    is_primary: bool
    display_order: int
    file: FileResponse

    class Config:
        orm_mode = True

class GymDocumentResponse(BaseModel):
    gym_document_id: str
    gym_id: str
    document_type: str
    file: FileResponse

    class Config:
        orm_mode = True



class GymStaffStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"


class GymStaffCreate(BaseModel):
    user_id: str
    role: str
    assigned_classes: Optional[str] = None


class GymStaffRead(BaseModel):
    staff_id: str
    gym_id: str
    user_id: str
    role: str
    assigned_classes: Optional[str]
    status: GymStaffStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class GymStaffListResponse(BaseModel):
    staff: List[GymStaffRead]