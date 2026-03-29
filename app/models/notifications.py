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
    image_url = Column(String, nullable=True)
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



class DeviceToken(Base):
    __tablename__ = "device_tokens"

    token_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String, ForeignKey("sessions.session_id", ondelete="SET NULL"), nullable=True)
    fcm_token = Column(String, nullable=False, unique=True)
    device_info = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)
    last_used_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="device_tokens")
    session = relationship("Session", back_populates="device_tokens")