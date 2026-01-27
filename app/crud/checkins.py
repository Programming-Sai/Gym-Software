from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from uuid import uuid4

from app.models.checkins import Checkin
from app.models.gyms import Gym, GymQRCode


PROVISIONAL_EXPIRY_MINUTES = 5


def create_provisional_checkin(
    db: Session,
    *,
    user_id,
    gym_id,
    qr_nonce: str,
    client_lat=None,
    client_lng=None
):
    # 1. Validate QR
    qr = (
        db.query(GymQRCode)
        .filter(
            GymQRCode.qr_nonce == qr_nonce,
            GymQRCode.gym_id == gym_id,
            GymQRCode.is_active == True
        )
        .first()
    )

    if not qr:
        raise ValueError("Invalid or expired QR code")

    # 2. Prevent duplicate provisional check-ins
    expiry_cutoff = datetime.utcnow() - timedelta(minutes=PROVISIONAL_EXPIRY_MINUTES)

    existing = (
        db.query(Checkin)
        .filter(
            Checkin.user_id == user_id,
            Checkin.gym_id == gym_id,
            Checkin.status == "provisional",
            Checkin.created_at >= expiry_cutoff
        )
        .first()
    )

    if existing:
        raise ValueError("Active provisional check-in already exists")

    # 3. Create check-in
    checkin = Checkin(
        checkin_id=uuid4(),
        user_id=user_id,
        gym_id=gym_id,
        qr_nonce=qr_nonce,
        status="provisional",
        client_lat=client_lat,
        client_lng=client_lng
    )

    db.add(checkin)
    db.commit()
    db.refresh(checkin)

    return checkin


def get_user_checkins(
    db: Session,
    target_user_id: str,
    *,
    viewer,
):
    q = db.query(Checkin).filter(Checkin.user_id == target_user_id)

    if viewer.role == "gym_owner":
        owned_gym_ids = (
            db.query(Gym.gym_id)
            .filter(Gym.owner_id == viewer.user_id)
            .subquery()
        )
        q = q.filter(Checkin.gym_id.in_(owned_gym_ids))

    return q.order_by(Checkin.created_at.desc()).all()


def get_gym_checkins(db: Session, gym_id: str):
    return (
        db.query(Checkin)
        .filter(Checkin.gym_id == gym_id)
        .order_by(Checkin.created_at.desc())
        .all()
    )
