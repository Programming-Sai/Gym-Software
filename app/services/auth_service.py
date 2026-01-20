from sqlalchemy.orm import Session as DBSession
from app.crud.otp import create_email_verification_otp, get_valid_otp, mark_otp_used
from app.crud.user import mark_email_verified
from app.models.users import User
from app.crud.user import get_user_by_email
from app.core.security import verify_password, create_refresh_token
from app.core.jwt import create_access_token
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from app.models.auth import Session

def login_user(db: DBSession, email: str, password: str):
    user = get_user_by_email(db, email)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified"
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    access_token = create_access_token(subject=str(user.user_id))
    refresh_token = create_refresh_token()

    session = Session(
        user_id=user.user_id,
        access_token=access_token,      
        refresh_token=refresh_token,    # REQUIRED
        expires_at=datetime.utcnow() + timedelta(days=30),
        is_active=True
    )

    db.add(session)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


def verify_email(db: DBSession, email: str, code: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False, "User not found"

    otp = get_valid_otp(db, user.user_id, code, purpose="email_verification")
    if not otp:
        return False, "Invalid or expired OTP"

    mark_otp_used(db, otp)
    mark_email_verified(db, user.user_id)
    return True, "Email verified successfully"

def resend_verification(db: DBSession, user: User):
    # Optional: invalidate old OTPs
    # db.query(OTP).filter(OTP.user_id==user.user_id, OTP.purpose=="email_verification", OTP.is_used==False).update({"is_used": True})
    # db.commit()

    otp = create_email_verification_otp(db, user.user_id)
    # For MVP, we just return the code; email will be wired later
    return otp.code


def refresh_access_token(db: DBSession, refresh_token: str):
    session = db.query(Session).filter(
        Session.refresh_token == refresh_token,
        Session.is_active == True,
        Session.expires_at > datetime.utcnow()
    ).first()

    if not session:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access = create_access_token(subject=str(session.user_id))
    new_refresh = create_refresh_token()

    session.access_token = new_access
    session.refresh_token = new_refresh
    session.expires_at = datetime.utcnow() + timedelta(days=30)

    db.commit()

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer"
    }


def logout(db: DBSession, refresh_token: str):
    session = db.query(Session).filter(
        Session.refresh_token == refresh_token
    ).first()

    if session:
        session.is_active = False
        db.commit()
