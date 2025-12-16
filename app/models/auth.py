from sqlalchemy import Column, String, Boolean, TIMESTAMP, Enum, Integer, ForeignKey
from uuid import uuid4
from sqlalchemy.orm import relationship
from app.core.database import Base
from sqlalchemy import func

# ----------------------
# Sessions table
# ----------------------
class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)

    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)

    device_info = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(TIMESTAMP, server_default=func.now())
    expires_at = Column(TIMESTAMP, nullable=False)

    user = relationship("User", backref="sessions")


# ----------------------
# OTP / Tokens table
# ----------------------
class OTP(Base):
    __tablename__ = "otps"

    otp_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)

    code = Column(String, nullable=False)
    purpose = Column(
        Enum("email_verification", "password_reset", "other", name="otp_purposes"),
        nullable=False
    )
    is_used = Column(Boolean, default=False)
    expires_at = Column(TIMESTAMP, nullable=False)

    created_at = Column(TIMESTAMP, server_default=func.now())

    user = relationship("User", backref="otps")


# ----------------------
# OAuth / Social login table
# ----------------------
class OAuthAccount(Base):
    __tablename__ = "oauth_accounts"

    oauth_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)

    provider = Column(Enum("google", "apple", "facebook", "other", name="oauth_providers"), nullable=False)
    provider_user_id = Column(String, nullable=False, unique=True)
    access_token = Column(String, nullable=True)
    refresh_token = Column(String, nullable=True)
    profile_email = Column(String, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", backref="oauth_accounts")


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    token_id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String, unique=True, nullable=False)
    expires_at = Column(TIMESTAMP, nullable=False)
    used_at = Column(TIMESTAMP, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now(), nullable=False)