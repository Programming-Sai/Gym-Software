from sqlalchemy import Column, String, Enum, TIMESTAMP, Text, JSON, Integer, DECIMAL, func, ForeignKey
from uuid import uuid4
from app.core.database import Base
from sqlalchemy.orm import relationship, foreign

from app.models.enums import DocumentTypeEnum

class Dietician(Base):
    __tablename__ = "dieticians"

    dietician_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    bio = Column(Text, nullable=True)
    specializations = Column(JSON, default=[])   # array of strings
    experience_years = Column(Integer, default=0)
    
    
    status = Column(
        Enum("active", "suspended", "inactive", name="dietician_statuses"),
        nullable=False,
        server_default="active",
    )

    # REMOVED: documents JSON array - Now handled by relationship
    profile_file_id = Column(
        String, 
        ForeignKey("files.file_id", ondelete="SET NULL"), 
        nullable=True
    )

    average_rating = Column(DECIMAL(3,2), default=0)
    total_ratings = Column(Integer, default=0)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    
    profile_file = relationship("File", foreign_keys=[profile_file_id])
    
    # File relationships
    dietician_documents = relationship("DieticianDocument", back_populates="dietician", cascade="all, delete-orphan")
    
    # Client relationships
    clients = relationship("ClientAssignment", 
                          foreign_keys="ClientAssignment.dietician_id",
                          back_populates="dietician")
    
    
    
    ratings = relationship(
        "Rating",
        primaryjoin="and_(Rating.target_type=='dietician', foreign(Rating.target_id)==Dietician.dietician_id)",
        cascade="all, delete-orphan"
    )



class DieticianDocument(Base):
    """Proper relationship table for dietician documents"""
    __tablename__ = "dietician_documents"
    
    document_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    dietician_id = Column(String, ForeignKey("dieticians.dietician_id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String, ForeignKey("files.file_id", ondelete="CASCADE"), nullable=False)
    document_type = Column(DocumentTypeEnum, nullable=False)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    # Relationships
    dietician = relationship("Dietician", back_populates="dietician_documents")
    file = relationship("File")