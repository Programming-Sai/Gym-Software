# app/services/checkin_service.py
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timedelta

from app.models.checkins import Checkin
from app.models.gyms import Gym
from app.models.users import User
from app.crud.gym_qr_code import get_active_qr_for_gym
from app.services.face_id_service import compare_faces
from datetime import date
from sqlalchemy import func


FACE_MATCH_THRESHOLD = 75.0


def perform_checkin(
    db: Session,
    *,
    user: User,
    gym_id: str,
    qr_nonce: str,
    face_image_base64: str,
    client_lat: float | None,
    client_lng: float | None,
):
    gym = db.query(Gym).filter(Gym.gym_id == gym_id).first()
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    qr = get_active_qr_for_gym(db, gym_id, qr_nonce)
    if not qr:
        raise HTTPException(status_code=400, detail="Invalid QR code")

    if not user.face_file or not user.face_file.storage_url:
        raise HTTPException(status_code=400, detail="User face not registered")
    
    already_checked_in = (
        db.query(Checkin)
        .filter(
            Checkin.user_id == user.user_id,
            Checkin.gym_id == gym_id,
            Checkin.status == "confirmed",
            func.date(Checkin.created_at) == date.today(),
        )
        .first()
    )

    if already_checked_in:
        raise HTTPException(
            status_code=400,
            detail="User already checked in today"
        )


    checkin = Checkin(
        user_id=user.user_id,
        gym_id=gym_id,
        qr_nonce=qr_nonce,
        client_lat=client_lat,
        client_lng=client_lng,
        status="provisional",
    )
    db.add(checkin)
    db.flush()

    try:
        score = compare_faces(user.face_file.storage_url, face_image_base64)
        checkin.face_score = score

        if score >= FACE_MATCH_THRESHOLD:
            checkin.status = "confirmed"
            checkin.confirmed_at = datetime.utcnow()
        else:
            checkin.status = "rejected"
            checkin.rejected_reason = "Face mismatch"

    except Exception as e:
        checkin.status = "rejected"
        checkin.rejected_reason = str(e)
        db.commit()
        raise

    finally:
        db.commit()
        db.refresh(checkin)

    return checkin
