# app/models/checkins.py

from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Enum,
    TIMESTAMP,
    Text,
    Float,
    func,
)
from uuid import uuid4
from app.core.database import Base


class Checkin(Base):
    __tablename__ = "checkins"

    checkin_id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    user_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    gym_id = Column(
        String,
        ForeignKey("gyms.gym_id", ondelete="SET NULL"),
        nullable=True,  # optional for home workouts
    )

    qr_nonce = Column(String, unique=True, nullable=False)
    qr_issued_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)

    status = Column(
        Enum("provisional", "confirmed", "rejected", "expired", name="checkin_statuses"),
        nullable=False,
        server_default="provisional",
    )

    confirmed_at = Column(TIMESTAMP, nullable=True)
    rejected_reason = Column(Text, nullable=True)
    face_score = Column(Float, nullable=True)

    client_lat = Column(Float, nullable=True)
    client_lng = Column(Float, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

