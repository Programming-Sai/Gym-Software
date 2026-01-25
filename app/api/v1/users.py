from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.users import (
    RegisterFaceResponse,
    UserFaceStatusResponse,
)
from app.crud.user import (
    register_or_replace_user_face,
    get_user_face_status,
)

router = APIRouter(tags=["Users"])


@router.post("/users/face", response_model=RegisterFaceResponse)
def register_face(
    face: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    if face.content_type not in ["image/jpeg", "image/jpg", "image/png"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Face must be an image (jpeg, jpg or png)",
        )

    user = register_or_replace_user_face(db, user, face)

    return RegisterFaceResponse(
        message="Face registered successfully",
        registered_at=user.face_registered_at,
    )


@router.get("/users/face", response_model=UserFaceStatusResponse)
def get_face_status(user=Depends(get_current_user)):
    return get_user_face_status(user)
