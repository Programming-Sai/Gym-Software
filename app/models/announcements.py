from sqlalchemy import Column, String, Text, TIMESTAMP, ForeignKey, Enum, Boolean, UniqueConstraint, func
from uuid import uuid4
from app.core.database import Base
from sqlalchemy.orm import relationship

class Announcement(Base):
    __tablename__ = "announcements"
    
    announcement_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    
    # Who created the announcement
    created_by = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # Target: specific gym or platform-wide
    target_type = Column(
        Enum("gym", "platform", name="announcement_target_types"),
        nullable=False,
        server_default="gym"
    )
    
    # If gym-specific, which gym
    gym_id = Column(
        String,
        ForeignKey("gyms.gym_id", ondelete="CASCADE"),
        nullable=True
    )
    
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    
    # Who should see this
    audience = Column(
        Enum("all", "members", "staff", name="announcement_audience"),
        nullable=False,
        server_default="all"
    )
    
    # Status
    status = Column(
        Enum("draft", "published", "archived", name="announcement_statuses"),
        nullable=False,
        server_default="draft"
    )
    
    # Scheduling
    publish_at = Column(TIMESTAMP, nullable=True)  # For scheduled announcements
    expires_at = Column(TIMESTAMP, nullable=True)   # Auto-archive after this date
    
    is_important = Column(Boolean, default=False)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    gym = relationship("Gym", foreign_keys=[gym_id])
    
    # Track who has seen/read it
    reads = relationship("AnnouncementRead", back_populates="announcement", cascade="all, delete-orphan")


class AnnouncementRead(Base):
    """Track which users have read which announcements"""
    __tablename__ = "announcement_reads"
    
    read_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    announcement_id = Column(
        String,
        ForeignKey("announcements.announcement_id", ondelete="CASCADE"),
        nullable=False
    )
    user_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    read_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    
    # Relationships
    announcement = relationship("Announcement", back_populates="reads")
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint('announcement_id', 'user_id', name='uq_announcement_read_user'),
    )