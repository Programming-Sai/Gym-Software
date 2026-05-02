# app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.models.users import User
from app.models.auth import AdminInvite
from app.schemas.auth import SignupRequest, SignupResponse
from app.schemas.users import UserMeResponse
from app.core.database import get_db
from app.core.security import hash_password
from app.core.otp import generate_unique_otp
# from app.services.email_service import send_email  # implement this separately
from app.schemas.otp import VerifyEmailRequest, ResendOTPRequest
from app.services.auth_service import verify_email, resend_verification
from app.schemas.login import LoginRequest, LoginResponse
from app.services.auth_service import login_user, refresh_access_token, logout
from app.core.dependencies import get_current_user, get_db
from fastapi import Depends, APIRouter
from app.services.audit_log_service import write_audit_log
from app.schemas.auth_admin_invites import AcceptAdminInviteRequest
from datetime import datetime
import hashlib

router = APIRouter(tags=["Auth"])

@router.post("/signin",response_model=LoginResponse)
def signin(
    data: LoginRequest,
    db = Depends(get_db)
):
    return login_user(db, data.email, data.password)


@router.post("/signup", response_model=SignupResponse)
def signup(data: SignupRequest, request: Request, db: Session = Depends(get_db)):
    requested_role = (data.role or "gym_user").strip()
    if requested_role in {"admin", "superadmin"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role",
        )
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
        role=requested_role or "gym_user"
    )
    db.add(new_user)
    db.flush()
    write_audit_log(
        db,
        category="crud",
        action="user.created",
        entity_type="user",
        entity_id=new_user.user_id,
        actor=None,
        request=request,
        success=True,
        metadata={"role": new_user.role},
    )
    db.commit()
    db.refresh(new_user)

    # 3. Generate OTP
    _otp_code = generate_unique_otp(db, new_user.user_id)

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


@router.post("/verify-email", )
def verify_email_endpoint(request: VerifyEmailRequest, db: Session = Depends(get_db)):
    success, msg = verify_email(db, request.email, request.code)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
    return {"message": msg}

@router.post("/resend-verification",)
def resend_verification_endpoint(request: ResendOTPRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.email_verified:
        raise HTTPException(status_code=400, detail="Email already verified")
    
    resend_verification(db, user)
    # No OTP delivery is implemented yet; we only persist the OTP in the database.
    # Do not return OTPs in API responses.
    return {"message": "Verification code generated"}


@router.get("/me", response_model=UserMeResponse)
def me(user = Depends(get_current_user)):
    return user

@router.post("/refresh")
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    return refresh_access_token(db, refresh_token)

@router.post("/logout")
def logout_user(refresh_token: str, db: Session = Depends(get_db)):
    logout(db, refresh_token)
    return {"message": "Logged out successfully"}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/admin-invites/{token}/accept")
def accept_admin_invite(
    token: str,
    payload: AcceptAdminInviteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    # Token is stored hashed in DB; never store raw tokens.
    token = token.strip()
    if len(token) < 20:
        raise HTTPException(status_code=400, detail="Invalid token")

    now = datetime.utcnow()
    invite = (
        db.query(AdminInvite)
        .filter(AdminInvite.token_hash == _hash_token(token))
        .with_for_update(nowait=False)
        .first()
    )
    if not invite:
        raise HTTPException(status_code=404, detail="Invite not found")
    if invite.revoked_at is not None:
        raise HTTPException(status_code=400, detail="Invite revoked")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="Invite already accepted")
    if invite.expires_at <= now:
        raise HTTPException(status_code=400, detail="Invite expired")

    if invite.role_to_grant not in {"admin", "superadmin"}:
        raise HTTPException(status_code=400, detail="Invite role is invalid")

    email = (invite.email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Invite email is invalid")

    user = db.query(User).filter(User.email == email).first()
    created = False
    if not user:
        if not payload.full_name:
            raise HTTPException(status_code=400, detail="full_name is required for new users")
        if not payload.password:
            raise HTTPException(status_code=400, detail="password is required for new users")
        user = User(
            full_name=payload.full_name.strip(),
            email=email,
            phone_number=(payload.phone_number.strip() if payload.phone_number else None),
            password_hash=hash_password(payload.password),
            role=invite.role_to_grant,
            email_verified=True,  # proof via possession of invite token delivered to that email
            phone_verified=False,
            status="active",
        )
        db.add(user)
        db.flush()
        created = True
    else:
        # Reduce attack surface: avoid clobbering existing specialized roles.
        # Promotion should start from a normal base user role.
        if user.role not in {"gym_user", "admin", "superadmin"}:
            raise HTTPException(
                status_code=400,
                detail="This email belongs to a non-basic role; admin promotion requires manual handling",
            )

        user.role = invite.role_to_grant
        user.email_verified = True
        if user.status != "active":
            user.status = "active"
        db.add(user)

    invite.accepted_at = now
    invite.accepted_by = user.user_id
    db.add(invite)

    write_audit_log(
        db,
        category="crud",
        action="admin_invite.accepted",
        entity_type="admin_invite",
        entity_id=invite.invite_id,
        actor=user,
        request=request,
        success=True,
        metadata={
            "email": email,
            "role_granted": invite.role_to_grant,
            "user_created": created,
        },
    )
    db.commit()

    return {
        "status": "accepted",
        "user_id": user.user_id,
        "role": user.role,
        "user_created": created,
    }
