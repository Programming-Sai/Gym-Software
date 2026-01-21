from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from app.schemas.gyms import GymCreate, GymDocumentType, GymListResponse, GymResponse, GymUpdate, GymPhotoResponse, GymDocumentResponse, GymStaffCreate, GymStaffRead, GymStaffListResponse
from app.core.dependencies import get_db, get_current_user
from app.crud.gym import create_gym, get_gym, get_gym_by_id, update_gym, delete_gym, get_gyms, search_gyms, list_gym_staff, add_staff_to_gym, remove_staff_from_gym
from app.crud.gym_media import add_or_replace_gym_photo, list_gym_photos, delete_gym_photo, add_or_replace_gym_document, list_gym_documents, delete_gym_document




router = APIRouter(tags=["Gyms"])


@router.post("/", response_model=GymResponse)
def create_gym_endpoint(
    gym_data: GymCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # Only gym_owner can create a gym
    if current_user.role != "gym_owner":
        raise HTTPException(status_code=403, detail="Only gym owners can create gyms")
    
    return create_gym(db=db, owner_id=current_user.user_id, gym_data=gym_data)




@router.patch("/{gym_id}")
def patch_gym(gym_id: str, data: GymUpdate, db: Session = Depends(get_db)):
    updated_gym = update_gym(db, gym_id, data.dict(exclude_unset=True))
    if not updated_gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    return updated_gym

@router.delete("/{gym_id}")
def remove_gym(gym_id: str, db: Session = Depends(get_db)):
    gym = delete_gym(db, gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    return {"message": "Gym deleted successfully"}


@router.get("/search", response_model=GymListResponse)
def search_gyms_endpoint(
    q: str = Query(..., min_length=1),
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    gyms, total = search_gyms(db, q, skip=skip, limit=limit)
    return GymListResponse(gyms=gyms, total=total)

@router.get("/", response_model=GymListResponse)
def list_gyms(
    skip: int = 0,
    limit: int = 10,
    status: str = "active",
    subscription_tier: str = None,
    equipment: str = None,
    facility: str = None,
    min_capacity: int = None,
    lat: float = None,
    lng: float = None,
    radius_km: float = None,
    db: Session = Depends(get_db)
):
    gyms, total = get_gyms(
        db,
        skip=skip,
        limit=limit,
        status=status,
        subscription_tier=subscription_tier,
        equipment=equipment,
        facility=facility,
        min_capacity=min_capacity,
        lat=lat,
        lng=lng,
        radius_km=radius_km
    )
    return GymListResponse(gyms=gyms, total=total)


@router.get("/{gym_id}", response_model=GymResponse)
def get_gym_endpoint(gym_id: str, db: Session = Depends(get_db)):
    gym = get_gym(db=db, gym_id=gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")
    return gym



@router.post("/{gym_id}/photos", response_model=GymPhotoResponse)
def upload_or_replace_gym_photo(
    gym_id: str,
    file: UploadFile = File(...),
    gym_photo_id: Optional[str] = None,  # for replace
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Upload a new gym photo or replace an existing one.
    """
    # Only gym owners should upload
    if current_user.role != "gym_owner":
        raise HTTPException(status_code=403, detail="Only gym owners can upload photos")

    ALLOWED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"]
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid file type. Only JPEG, PNG, WebP allowed.")

    try:
        photo = add_or_replace_gym_photo(
            db=db,
            gym_id=gym_id,
            file=file.file,
            filename=file.filename,
            uploaded_by=current_user.user_id,
            gym_photo_id=gym_photo_id,
        )
        return photo
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload photo: {str(e)}")


@router.get("/{gym_id}/photos", response_model=List[GymPhotoResponse])
def get_gym_photos(
    gym_id: str,
    db: Session = Depends(get_db)
):
    return list_gym_photos(db, gym_id)


@router.delete("/photos/{gym_photo_id}", response_model=GymPhotoResponse)
def remove_gym_photo(
    gym_photo_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    photo = delete_gym_photo(db, gym_photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")
    return photo


# ---------------------------
# GYM DOCUMENTS
# ---------------------------

@router.post("/{gym_id}/documents", response_model=GymDocumentResponse)
def upload_or_replace_gym_document(
    gym_id: str,
    file: UploadFile = File(...),
    document_type: GymDocumentType = Query(...),
    gym_document_id: Optional[str] = None,  # for replace
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    """
    Upload a new gym document or replace an existing one.
    """
    if current_user.role != "gym_owner":
        raise HTTPException(status_code=403, detail="Only gym owners can upload documents")
    
    ALLOWED_DOC_TYPES = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in ALLOWED_DOC_TYPES:
        raise HTTPException(status_code=400, detail="Invalid document type. Only PDF/DOC/DOCX allowed.")
        


    try:
        document = add_or_replace_gym_document(
            db=db,
            gym_id=gym_id,
            file=file.file,
            filename=file.filename,
            document_type=document_type.value,
            uploaded_by=current_user.user_id,
            gym_document_id=gym_document_id
        )
        return document
    except Exception as e:
     raise HTTPException(status_code=500, detail=f"Failed to upload document: {str(e)}")



@router.get("/{gym_id}/documents", response_model=List[GymDocumentResponse])
def get_gym_documents(
    gym_id: str,
    db: Session = Depends(get_db)
):
    return list_gym_documents(db, gym_id)


@router.delete("/documents/{gym_document_id}", response_model=GymDocumentResponse)
def remove_gym_document(
    gym_document_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    doc = delete_gym_document(db, gym_document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{gym_id}/staff", response_model=GymStaffListResponse)
def get_gym_staff(
    gym_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    gym = get_gym_by_id(db, gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    if current_user.role != "gym_owner" or gym.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    staff = list_gym_staff(db, gym_id)
    return {"staff": staff}



@router.post("/{gym_id}/staff", response_model=GymStaffRead)
def add_gym_staff(
    gym_id: str,
    payload: GymStaffCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    gym = get_gym_by_id(db, gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    if current_user.role != "gym_owner" or gym.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        return add_staff_to_gym(
            db=db,
            gym_id=gym_id,
            user_id=payload.user_id,
            role=payload.role,
            assigned_classes=payload.assigned_classes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{gym_id}/staff/{staff_id}")
def delete_gym_staff(
    gym_id: str,
    staff_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    gym = get_gym_by_id(db, gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    if current_user.role != "gym_owner" or gym.owner_id != current_user.user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        remove_staff_from_gym(db, gym_id, staff_id)
        return {"detail": "Staff removed successfully"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
