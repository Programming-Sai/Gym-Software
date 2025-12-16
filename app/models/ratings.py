from sqlalchemy import Column, Index, String, ForeignKey, Integer, Text, TIMESTAMP, Enum, func
from uuid import uuid4
from app.core.database import Base
from sqlalchemy.orm import relationship

class Rating(Base):
    """Unified rating system for gyms, dieticians, etc."""
    __tablename__ = "ratings"
    
    rating_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    
    # Who gave the rating
    user_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False
    )
    
    # What is being rated (polymorphic)
    target_type = Column(
        Enum("gym", "dietician", name="rating_target_types"),
        nullable=False
    )
    
    # ID of the target (gym_id or dietician_id)
    target_id = Column(String, nullable=False)
    
    # Rating values
    rating = Column(Integer, nullable=False)  # 1-5
    comment = Column(Text, nullable=True)
    
    # Additional metadata
    visit_date = Column(TIMESTAMP, nullable=True)  # When they visited/used service
    would_recommend = Column(Integer, nullable=True)  # 0-10 scale
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User")
    
    # Index for efficient queries
    __table_args__ = (
        Index('ix_ratings_target', 'target_type', 'target_id'),
        Index('ix_ratings_user_target', 'user_id', 'target_type', 'target_id'),
    )