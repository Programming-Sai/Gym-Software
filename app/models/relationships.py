from sqlalchemy import Column, String, ForeignKey, TIMESTAMP, Enum, UniqueConstraint, func
from uuid import uuid4
from app.core.database import Base
from sqlalchemy.orm import relationship

class UserFavoriteGym(Base):
    """User favorite/bookmarked gyms"""
    __tablename__ = "user_favorite_gyms"
    
    favorite_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    gym_id = Column(String, ForeignKey("gyms.gym_id", ondelete="CASCADE"), nullable=False)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    gym = relationship("Gym", back_populates="favorite_users")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('user_id', 'gym_id', name='uq_user_favorite_gym'),)


class ClientAssignment(Base):
    """Dietician-Client relationships"""
    __tablename__ = "client_assignments"
    
    assignment_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    dietician_id = Column(String, ForeignKey("dieticians.dietician_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    
    status = Column(
        Enum("active", "ended", "paused", name="client_assignment_statuses"),
        nullable=False,
        server_default="active"
    )
    
    assigned_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    ended_at = Column(TIMESTAMP, nullable=True)
    ended_reason = Column(String, nullable=True)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    dietician = relationship("Dietician", back_populates="clients")
    user = relationship("User")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('dietician_id', 'user_id', name='uq_client_assignment'),)


class GymStaff(Base):
    """Gym staff/instructors"""
    __tablename__ = "gym_staff"
    
    staff_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    gym_id = Column(String, ForeignKey("gyms.gym_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    
    role = Column(String, nullable=False)  # e.g., "Personal Trainer", "Yoga Instructor"
    assigned_classes = Column(String, nullable=True)  # Comma-separated class names
    
    status = Column(
        Enum("active", "inactive", "suspended", name="staff_statuses"),
        nullable=False,
        server_default="active"
    )
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    gym = relationship("Gym", back_populates="staff")
    user = relationship("User")