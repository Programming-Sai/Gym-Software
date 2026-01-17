from sqlalchemy.orm import Session
from app.crud.otp import create_email_verification_otp, get_valid_otp, mark_otp_used
from app.crud.user import mark_email_verified
from app.models.users import User
from app.crud.user import get_user_by_email
from app.core.security import verify_password
from app.core.jwt import create_access_token
from fastapi import HTTPException, status

def login_user(db, email: str, password: str):
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

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


def verify_email(db: Session, email: str, code: str):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False, "User not found"

    otp = get_valid_otp(db, user.user_id, code, purpose="email_verification")
    if not otp:
        return False, "Invalid or expired OTP"

    mark_otp_used(db, otp)
    mark_email_verified(db, user.user_id)
    return True, "Email verified successfully"

def resend_verification(db: Session, user: User):
    # Optional: invalidate old OTPs
    # db.query(OTP).filter(OTP.user_id==user.user_id, OTP.purpose=="email_verification", OTP.is_used==False).update({"is_used": True})
    # db.commit()

    otp = create_email_verification_otp(db, user.user_id)
    # For MVP, we just return the code; email will be wired later
    return otp.code
