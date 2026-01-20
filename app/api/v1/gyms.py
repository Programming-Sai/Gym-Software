from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.schemas.gyms import GymCreate, GymListResponse, GymResponse, GymUpdate
from app.core.dependencies import get_db, get_current_user
from app.crud.gym import create_gym, get_gym, update_gym, delete_gym, get_gyms, search_gyms


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

