from sqlalchemy import Column, String, Enum, TIMESTAMP, Integer, Boolean, func, Index, ForeignKey
from uuid import uuid4
from app.core.database import Base
from sqlalchemy.orm import relationship

class File(Base):
    __tablename__ = "files"

    file_id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    owner_type = Column(
        Enum("user", "gym", "dietician", name="file_owner_types"),
        nullable=False,
    )
    owner_id = Column(String, nullable=False)   # polymorphic owner id

    file_type = Column(
        Enum("image", "document", "video", "audio", name="file_types"),
        nullable=False,
    )
    purpose = Column(
        Enum(
            "profile_image",
            "gym_photo",
            "verification_document",
            "certificate",
            "chat_attachment",
            "face_id",
            "workout_media",
            "announcement_media",
            "other",
            name="file_purposes",
        ),
        nullable=False,
    )

    original_filename = Column(String, nullable=False)
    extension = Column(String, nullable=False)
    mime_type = Column(String, nullable=False)

    file_size = Column(Integer, nullable=True)

    storage_provider = Column(
        Enum("cloudinary", "s3", "local", name="storage_providers"),
        default="cloudinary",
        nullable=False,
    )
    storage_key = Column(String, nullable=False)  # cloudinary public_id or path
    storage_url = Column(String, nullable=False)  # Full URL to access file
    
    # New fields for better tracking
    associated_table = Column(String, nullable=True)  # e.g., "gym_photos", "dietician_documents"
    associated_record_id = Column(String, nullable=True)  # ID in the associated table
    
    is_temporary = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)
    
    # User who uploaded the file
    uploaded_by = Column(
        String, 
        ForeignKey("users.user_id", ondelete="SET NULL"), 
        nullable=True
    )

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)  # Soft delete

    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])

    # Indexes
    __table_args__ = (
        Index("ix_files_owner", "owner_type", "owner_id"),
        Index("ix_files_associated", "associated_table", "associated_record_id"),
        Index("ix_files_temporary", "is_temporary"),
    )