from sqlalchemy import Column, String, Enum, TIMESTAMP, Text, ForeignKey, func
from uuid import uuid4
from app.core.database import Base
from sqlalchemy.orm import relationship

from app.models.enums import DocumentTypeEnum

class VerificationApplication(Base):
    """Central verification system for dieticians and gym owners ONLY"""
    __tablename__ = "verification_applications"
    
    application_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    
    applicant_type = Column(
        Enum("gym_owner", "dietician", name="verification_applicant_types"),
        nullable=False
    )
    applicant_id = Column(String, nullable=False)  # user_id (for gym_owner or dietician)
    
    status = Column(
        Enum("pending", "approved", "rejected", "more_info_required", name="verification_statuses"),
        nullable=False,
        server_default="pending"
    )
    
    submitted_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    reviewed_at = Column(TIMESTAMP, nullable=True)
    reviewed_by = Column(
        String, 
        ForeignKey("users.user_id", ondelete="SET NULL"), 
        nullable=True
    )
    
    rejection_reason = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    
    # For "more_info_required" status
    info_request = Column(Text, nullable=True)
    info_requested_at = Column(TIMESTAMP, nullable=True)
    info_provided_at = Column(TIMESTAMP, nullable=True)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    applicant_user = relationship("User", 
                                 foreign_keys=[applicant_id],
                                 primaryjoin="VerificationApplication.applicant_id==User.user_id")
    
    # Documents submitted for verification
    verification_documents = relationship("VerificationDocument", 
                                         back_populates="application",
                                         cascade="all, delete-orphan")


class VerificationDocument(Base):
    """Documents submitted for verification (references files table)"""
    __tablename__ = "verification_documents"
    
    verification_document_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    application_id = Column(
        String, 
        ForeignKey("verification_applications.application_id", ondelete="CASCADE"), 
        nullable=False
    )
    file_id = Column(
        String, 
        ForeignKey("files.file_id", ondelete="CASCADE"), 
        nullable=False
    )
    document_type = Column(DocumentTypeEnum, nullable=False)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    # Relationships
    application = relationship("VerificationApplication", back_populates="verification_documents")
    file = relationship("File")