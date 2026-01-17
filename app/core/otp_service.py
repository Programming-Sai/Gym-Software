# app/core/otp_service.py
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.auth import OTP
from app.core.config import settings  # from .env

def generate_unique_otp(db: Session, user_id: str) -> str:
    length = settings.OTP_LENGTH
    expires_minutes = settings.OTP_EXPIRE_MINUTES

    while True:
        code = "".join([str(random.randint(0, 9)) for _ in range(length)])
        existing = db.query(OTP).filter(OTP.code == code, OTP.is_used == False).first()
        if not existing:
            break

    otp = OTP(
        user_id=user_id,
        code=code,
        purpose="email_verification",
        expires_at=datetime.utcnow() + timedelta(minutes=expires_minutes),
        is_used=False
    )
    db.add(otp)
    db.commit()
    db.refresh(otp)
    return otp.code
