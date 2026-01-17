from datetime import datetime, timedelta
from uuid import uuid4
from sqlalchemy.orm import Session
from app.models.auth import OTP

OTP_EXPIRY_MINUTES = 10  # MVP expiry

def create_email_verification_otp(db: Session, user_id: str) -> OTP:
    otp = OTP(
        otp_id=str(uuid4()),
        user_id=user_id,
        code=str(uuid4().int)[:6],  # simple 6-digit OTP
        purpose="email_verification",
        is_used=False,
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return otp

def get_valid_otp(db: Session, user_id: str, code: str, purpose: str) -> OTP | None:
    return (
        db.query(OTP)
        .filter(
            OTP.user_id == user_id,
            OTP.code == code,
            OTP.purpose == purpose,
            OTP.is_used == False,
            OTP.expires_at > datetime.utcnow()
        )
        .first()
    )

def mark_otp_used(db: Session, otp: OTP):
    otp.is_used = True
    db.commit()
    db.refresh(otp)
