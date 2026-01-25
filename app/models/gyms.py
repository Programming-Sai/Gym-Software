from sqlalchemy import Column, String, Enum, Boolean, TIMESTAMP, DECIMAL, Text, JSON, Integer, func, ForeignKey
from uuid import uuid4
from app.core.database import Base
from sqlalchemy.orm import relationship, foreign
from sqlalchemy import and_
from app.models.ratings import Rating



class Gym(Base):
    __tablename__ = "gyms"

    gym_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    owner_id = Column(String, ForeignKey("users.user_id", ondelete="SET NULL"), nullable=False)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    address = Column(String, nullable=False)

    latitude = Column(DECIMAL(9, 6), nullable=True)
    longitude = Column(DECIMAL(9, 6), nullable=True)

    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)

    equipment = Column(JSON, default=[])
    facilities = Column(JSON, default=[])

    # NO verification_application_id here - verification is on user level for gym_owner
    # The gym status depends on owner's verification status

    status = Column(
        Enum("draft", "active", "suspended", "closed", name="gym_statuses"),
        nullable=False,
        server_default="draft",
    )

    subscription_tier = Column(
        Enum("basic", "standard", "premium", name="gym_subscription_tiers"),
        nullable=False,
        server_default="basic",
    )

    # REMOVED: photos JSON array - Now handled by relationship
    # REMOVED: documents JSON array - Now handled by relationship

    average_rating = Column(DECIMAL(3, 2), default=0)
    total_ratings = Column(Integer, default=0)

    opening_hours = Column(JSON, default={})
    capacity = Column(Integer, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_gyms")
    
    # File relationships
    gym_photos = relationship("GymPhoto", back_populates="gym", cascade="all, delete-orphan")
    # Add this relationship inside Gym class
    qr_code = relationship("GymQRCode", back_populates="gym", uselist=False)

    # Other relationships
    ratings = relationship(
        Rating,
        primaryjoin=and_(
            foreign(Rating.target_id) == gym_id,
            Rating.target_type == "gym"
        ),
        viewonly=True
    )
    staff = relationship("GymStaff", back_populates="gym", cascade="all, delete-orphan")
    checkins = relationship("Checkin", back_populates="gym", cascade="all, delete-orphan")
    favorite_users = relationship("UserFavoriteGym", back_populates="gym", cascade="all, delete-orphan")
    payouts = relationship("Payout", back_populates="gym", cascade="all, delete-orphan")
    workout_sessions = relationship("WorkoutSession", back_populates="gym", cascade="all, delete-orphan")
    gym_documents = relationship("GymDocument", back_populates="gym", cascade="all, delete-orphan")





class GymPhoto(Base):
    """Proper relationship table for gym photos"""
    __tablename__ = "gym_photos"
    
    gym_photo_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    gym_id = Column(String, ForeignKey("gyms.gym_id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String, ForeignKey("files.file_id", ondelete="CASCADE"), nullable=False)
    is_primary = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    # Relationships
    gym = relationship("Gym", back_populates="gym_photos")
    file = relationship("File")


class GymDocument(Base):
    """Proper relationship table for gym documents"""
    __tablename__ = "gym_documents"
    
    gym_document_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    gym_id = Column(String, ForeignKey("gyms.gym_id", ondelete="CASCADE"), nullable=False)
    file_id = Column(String, ForeignKey("files.file_id", ondelete="CASCADE"), nullable=False)
    document_type = Column(
        Enum("business_license", "tax_id", "proof_of_ownership", "other", name="gym_document_types"),
        nullable=False
    )
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    # Relationships
    gym = relationship("Gym", back_populates="gym_documents")
    file = relationship("File")



class GymQRCode(Base):
    __tablename__ = "gym_qr_codes"

    qr_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    gym_id = Column(String, ForeignKey("gyms.gym_id", ondelete="CASCADE"), nullable=False, unique=True)
    qr_nonce = Column(String, unique=True, nullable=False)
    file_id = Column(String, ForeignKey("files.file_id", ondelete="SET NULL"), nullable=True)  # optional
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    rotated_at = Column(TIMESTAMP, nullable=True)

    # Relationships
    gym = relationship("Gym")
    file = relationship("File")
