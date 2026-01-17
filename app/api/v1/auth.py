# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.models.users import User
from app.schemas.auth import SignupRequest, SignupResponse
from app.core.database import get_db
from app.core.security import hash_password
from app.core.otp_service import generate_unique_otp
# from app.services.email_service import send_email  # implement this separately
from app.schemas.otp import VerifyEmailRequest, ResendOTPRequest
from app.services.auth_service import verify_email, resend_verification
from app.schemas.login import LoginRequest, LoginResponse
from app.services.auth_service import login_user
from app.core.dependencies import get_current_user, get_db
from fastapi import Depends, APIRouter

router = APIRouter()

@router.post("/signin", response_model=LoginResponse)
def login(
    data: LoginRequest,
    db = Depends(get_db)
):
    return login_user(db, data.email, data.password)


@router.post("/signup", response_model=SignupResponse)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    # 1. Check if user exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # 2. Create user
    new_user = User(
        full_name=data.full_name,
        email=data.email,
        phone_number=data.phone_number,
        password_hash=hash_password(data.password),
        role=data.role or "gym_user"
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 3. Generate OTP
    otp_code = generate_unique_otp(db, new_user.user_id)

    # # 4. Send OTP
    # send_email(
    #     to_email=new_user.email,
    #     subject="Verify your email",
    #     body=f"Your verification code is {otp_code}"
    # )

    # 5. Return response
    return SignupResponse(
        user_id=new_user.user_id,
        email=new_user.email,
        message="User created successfully. Check your email for verification code."
    )


@router.post("/verify-email")
def verify_email_endpoint(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    success, msg = verify_email(db, request.email, request.code)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/resend-verification")
def resend_verification_endpoint(request: ResendOTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    code = resend_verification(db, user)
    return {"otp": code}  # MVP returns OTP directly


@router.get("/me")
def me(user = Depends(get_current_user)):
    return user
