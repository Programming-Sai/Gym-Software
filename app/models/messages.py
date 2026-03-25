
from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Enum,
    Text,
    TIMESTAMP,
    func,
    Index,
)
from uuid import uuid4
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.enums import UserRole, user_role_enum


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    sender_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    sender_type = Column(user_role_enum, nullable=False)

    receiver_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    receiver_type = Column(user_role_enum, nullable=False)

    content = Column(Text, nullable=False)

    file_id = Column(String, ForeignKey("files.file_id", ondelete="SET NULL"), nullable=True)

    created_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        nullable=False,
    )

    read_at = Column(TIMESTAMP, nullable=True)

    # ⚡ ADD RELATIONSHIPS
    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_messages")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_messages")
    file = relationship("File")

    __table_args__ = (
        Index("ix_messages_sender", "sender_id"),
        Index("ix_messages_receiver", "receiver_id"),
        Index("ix_messages_conversation", "sender_id", "receiver_id"),
    )
