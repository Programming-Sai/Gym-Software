from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.crud.checkins import get_user_checkins
from app.crud.favorites import get_user_favorites
from app.schemas.checkins import CheckinListResponse
from app.schemas.favorite import FavoriteResponse
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

@router.get("/{user_id}/checkins", response_model=List[CheckinListResponse])
def list_user_checkins(
    user_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    if (
        user.user_id != user_id
        and user.role not in ("admin", "gym_owner")
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return get_user_checkins(db, user_id, viewer=user)




@router.get("/{user_id}/favorites", response_model=list[FavoriteResponse])
def list_user_favorites(
    user_id: str,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    if user.user_id != user_id and user.role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    return get_user_favorites(db, user_id)
