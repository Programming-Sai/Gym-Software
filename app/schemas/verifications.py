from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VerificationWithdrawRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=2000)


class VerificationApproveRequest(BaseModel):
    admin_notes: Optional[str] = Field(None, max_length=4000)


class VerificationRejectRequest(BaseModel):
    rejection_reason: str = Field(..., min_length=3, max_length=4000)
    admin_notes: Optional[str] = Field(None, max_length=4000)


class VerificationMoreInfoRequest(BaseModel):
    info_request: str = Field(..., min_length=3, max_length=4000)


class VerificationAddNoteRequest(BaseModel):
    note: str = Field(..., min_length=1, max_length=4000)


class VerificationFileOut(BaseModel):
    file_id: str
    storage_url: str
    original_filename: str
    mime_type: str
    purpose: str

    model_config = {"from_attributes": True}


class VerificationDocumentOut(BaseModel):
    verification_document_id: str
    document_type: str
    file: VerificationFileOut

    model_config = {"from_attributes": True}


class VerificationUserOut(BaseModel):
    user_id: str
    full_name: str
    email: str
    phone_number: Optional[str] = None
    role: str
    status: str

    model_config = {"from_attributes": True}


class VerificationApplicationAdminOut(BaseModel):
    application_id: str

    applicant_type: str
    applicant_id: str
    applicant_user: Optional[VerificationUserOut] = None

    status: str
    submitted_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    reviewer: Optional[VerificationUserOut] = None

    rejection_reason: Optional[str] = None
    admin_notes: Optional[str] = None

    info_request: Optional[str] = None
    info_requested_at: Optional[datetime] = None
    info_provided_at: Optional[datetime] = None

    withdrawn_at: Optional[datetime] = None
    withdrawn_reason: Optional[str] = None
    withdrawn_by: Optional[str] = None
    withdrawer: Optional[VerificationUserOut] = None

    verification_documents: list[VerificationDocumentOut] = []

    model_config = {"from_attributes": True}
