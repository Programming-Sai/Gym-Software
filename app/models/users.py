from sqlalchemy import Column, String, Enum, Boolean, TIMESTAMP, ForeignKey, func
from uuid import uuid4
from app.core.database import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = "users"

    user_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone_number = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)

    # Profile image reference to files table
    profile_file_id = Column(
        String, 
        ForeignKey("files.file_id", ondelete="SET NULL"), 
        nullable=True
    )

    role = Column(
        Enum("gym_user", "dietician", "gym_owner", "admin", name="user_roles"),
        nullable=False,
        server_default="gym_user"
    )
    status = Column(
        Enum("active", "limited", "suspended", "inactive", name="user_statuses"),
        nullable=False,
        server_default="active"
    )
    
    email_verified = Column(Boolean, default=False)
    phone_verified = Column(Boolean, default=False)
    
    # Payment provider ID (e.g., Paystack customer ID)
    payment_provider_customer_id = Column(String, nullable=True)
    
    # Current subscription tier reference
    current_subscription_tier_id = Column(
        String,
        ForeignKey("subscription_tiers.tier_id", ondelete="SET NULL"),
        nullable=True
    )

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    profile_file = relationship("File", foreign_keys=[profile_file_id])
    subscription_tier = relationship("SubscriptionTier", foreign_keys=[current_subscription_tier_id])
    checkins = relationship(
        "Checkin",
        back_populates="user",
        cascade="all, delete-orphan"
    )

    
    # Only for gym_owner and dietician roles
    verification_applications = relationship("VerificationApplication", 
                                           foreign_keys="VerificationApplication.applicant_id",
                                           primaryjoin="and_(User.user_id==VerificationApplication.applicant_id, "
                                                      "VerificationApplication.applicant_type.in_(['gym_owner', 'dietician']))",
                                           back_populates="applicant_user")
    
    owned_gyms = relationship("Gym", foreign_keys="Gym.owner_id", back_populates="owner")
    favorite_gyms = relationship("UserFavoriteGym", back_populates="user", cascade="all, delete-orphan")
    assigned_dietician = relationship("ClientAssignment", 
                                     foreign_keys="ClientAssignment.user_id",
                                     back_populates="user",
                                     uselist=False)


    # Messages
    sent_messages = relationship(
        "Message",
        back_populates="sender",
        foreign_keys="Message.sender_id",
        cascade="all, delete-orphan"
    )
    received_messages = relationship(
        "Message",
        back_populates="receiver",
        foreign_keys="Message.receiver_id",
        cascade="all, delete-orphan"
    )
