from datetime import datetime
from pydantic import BaseModel
from typing import List, Literal, Optional


class DieticianDocumentSchema(BaseModel):
    document_id: str
    document_type: str
    document_url: str

    class Config:
        orm_mode = True

class DieticianBaseSchema(BaseModel):
    dietician_id: str
    user_id: str
    bio: Optional[str]
    specializations: List[str]
    experience_years: int
    status: str

    profile_file_url: Optional[str]

    average_rating: float
    total_ratings: int
    verified_document_count: int

    class Config:
        orm_mode = True

class DieticianListingSchema(DieticianBaseSchema):
    """
    Public-safe view.
    Used for listing AND public single view.
    """
    pass

class DieticianInfoSchema(DieticianBaseSchema):
    """
    Private view.
    Documents only included for:
    - dietician (self)
    - main admin
    """
    documents: Optional[List[DieticianDocumentSchema]] = None

class VerificationDocumentInput(BaseModel):
    file_id: str
    document_type: str  # Should match VerificationDocument.document_type enum

class VerificationRequestInput(BaseModel):
    bio: str
    specializations: List[str]
    experience_years: int
    documents: List[VerificationDocumentInput]

class ClientAssignmentSchema(BaseModel):
    assignment_id: str
    dietician_id: str
    user_id: str
    status: str
    assigned_at: str

    class Config:
        orm_mode = True

class ClientAssignmentStatusUpdate(BaseModel):
    status: Literal["paused", "ended"]
    ended_reason: Optional[str] = None

class ClientDieticianAssignmentSchema(BaseModel):
    assignment_id: str
    status: str
    assigned_at: str
    ended_at: Optional[str]
    ended_reason: Optional[str]
    dietician: DieticianListingSchema  # embed public-safe dietician info

    class Config:
        orm_mode = True

class DieticianVerificationStatusSchema(BaseModel):
    application_id: str
    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime]
    rejection_reason: Optional[str]

    model_config = {
        "from_attributes": True  # <-- replaces orm_mode in Pydantic v2
    }