from sqlalchemy.orm import Session
from sqlalchemy import String, or_, and_, func, cast
from app.models.gyms import Gym
from app.schemas.gyms import GymCreate
from typing import Optional, List, Tuple

def create_gym(db: Session, owner_id: str, gym_data: GymCreate) -> Gym:
    gym = Gym(owner_id=owner_id, **gym_data.dict())
    db.add(gym)
    db.commit()
    db.refresh(gym)
    return gym


def get_gym(db: Session, gym_id: str) -> Gym | None:
    return db.query(Gym).filter(Gym.gym_id == gym_id).first()


def update_gym(db: Session, gym_id: str, updates: dict) -> Gym | None:
    gym = db.query(Gym).filter(Gym.gym_id == gym_id).first()
    if not gym:
        return None
    for key, value in updates.items():
        setattr(gym, key, value)
    db.commit()
    db.refresh(gym)
    return gym


def delete_gym(db: Session, gym_id: str) -> Gym | None:
    gym = db.query(Gym).filter(Gym.gym_id == gym_id).first()
    if not gym:
        return None
    db.delete(gym)
    db.commit()
    return gym


def get_gyms(
    db: Session,
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = "active",
    subscription_tier: Optional[str] = None,
    equipment: Optional[str] = None,
    facility: Optional[str] = None,
    min_capacity: Optional[int] = None,
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    radius_km: Optional[float] = None
) -> Tuple[List[Gym], int]:

    query = db.query(Gym)

    # Filter by status
    if status:
        query = query.filter(Gym.status == status)

    # Filter by subscription tier
    if subscription_tier:
        query = query.filter(Gym.subscription_tier == subscription_tier)

    # Filter by equipment / facility
    if equipment:
        query = query.filter(Gym.equipment.contains([equipment]))
    if facility:
        query = query.filter(Gym.facilities.contains([facility]))

    # Filter by capacity
    if min_capacity:
        query = query.filter(Gym.capacity >= min_capacity)

    # Proximity filter (Haversine formula)
    if lat is not None and lng is not None and radius_km is not None:
        distance = (
            6371
            * func.acos(
                func.cos(func.radians(lat))
                * func.cos(func.radians(Gym.latitude))
                * func.cos(func.radians(Gym.longitude) - func.radians(lng))
                + func.sin(func.radians(lat)) * func.sin(func.radians(Gym.latitude))
            )
        )
        query = query.filter(distance <= radius_km)
        query = query.order_by(distance)

    total = query.count()
    gyms = query.offset(skip).limit(limit).all()
    return gyms, total


def search_gyms(db: Session, q: str, skip: int = 0, limit: int = 10) -> Tuple[List[Gym], int]:
    query = db.query(Gym).filter(
        or_(
            Gym.name.ilike(f"%{q}%"),
            Gym.address.ilike(f"%{q}%"),
            cast(Gym.facilities, String).ilike(f"%{q}%"),
            cast(Gym.equipment, String).ilike(f"%{q}%"),
        )
    )

    # Only active gyms by default
    query = query.filter(Gym.status == "active")

    total = query.count()
    gyms = query.offset(skip).limit(limit).all()
    return gyms, total
