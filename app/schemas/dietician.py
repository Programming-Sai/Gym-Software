from pydantic import BaseModel
from typing import List, Optional

class DieticianDocumentSchema(BaseModel):
    document_id: str
    document_type: str
    document_url: str

    class Config:
        orm_mode = True

class DieticianInfoSchema(BaseModel):
    dietician_id: str
    user_id: str
    bio: Optional[str]
    specializations: List[str]
    experience_years: int
    status: str

    profile_file_url: Optional[str]

    average_rating: float
    total_ratings: int

    documents: List[DieticianDocumentSchema]

    class Config:
        orm_mode = True


class VerificationDocumentInput(BaseModel):
    file_id: str
    document_type: str  # Should match VerificationDocument.document_type enum

class VerificationRequestInput(BaseModel):
    bio: str
    specializations: List[str]
    experience_years: int
    documents: List[VerificationDocumentInput]
