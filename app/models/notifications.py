# app/models/notifications.py

from sqlalchemy import (
    Column,
    String,
    Enum,
    Boolean,
    TIMESTAMP,
    func,
    ForeignKey,
    JSON,
)
from uuid import uuid4
from sqlalchemy.orm import relationship
from app.core.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    notification_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    
    type = Column(
        Enum(
            "info",          # general info
            "alert",         # important warnings
            "reminder",      # session or payment reminders
            "achievement",   # badges, goals completed
            name="notification_types"
        ),
        nullable=False,
        server_default="info"
    )

    scope = Column(
        Enum(
            "individual",   # specific users
            "group",        # e.g., all gym_owners, dieticians, etc.
            "all",          # everyone
            name="notification_scopes"
        ),
        nullable=False,
        server_default="individual"
    )

    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    sent_at = Column(TIMESTAMP, nullable=True)  # when notification was actually delivered

    # relationship to recipients
    recipients = relationship("NotificationRecipient", back_populates="notification")


class NotificationRecipient(Base):
    __tablename__ = "notification_recipients"

    recipient_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    notification_id = Column(String, ForeignKey("notifications.notification_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)

    is_read = Column(Boolean, default=False, nullable=False)
    # dynamic per-user data, e.g., daily workout score
    data = Column(JSON, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    delivered_at = Column(TIMESTAMP, nullable=True)  # when FCM successfully sent it

    notification = relationship("Notification", back_populates="recipients")
