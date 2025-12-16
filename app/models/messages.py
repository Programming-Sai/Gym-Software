from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Boolean,
    Text,
    TIMESTAMP,
    func,
    Index,
)
from uuid import uuid4
from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"

    message_id = Column(String, primary_key=True, default=lambda: str(uuid4()))

    sender_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    receiver_id = Column(
        String,
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )

    content = Column(Text, nullable=False)

    is_read = Column(Boolean, default=False, nullable=False)

    created_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        nullable=False,
    )

    read_at = Column(TIMESTAMP, nullable=True)

    __table_args__ = (
        Index("ix_messages_sender", "sender_id"),
        Index("ix_messages_receiver", "receiver_id"),
        Index("ix_messages_sender_receiver", "sender_id", "receiver_id"),
    )
