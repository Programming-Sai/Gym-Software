from sqlalchemy.orm import Session
from app.crud.otp import create_email_verification_otp, get_valid_otp, mark_otp_used
from app.crud.user import mark_email_verified
from app.models.users import User

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
