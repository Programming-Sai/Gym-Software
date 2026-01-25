from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from app.models.gyms import GymQRCode
from app.models.files import File
from app.services import qr_service

def create_gym_qr_code(db: Session, gym_id: str):
    existing_qr = (
        db.query(GymQRCode)
        .filter(GymQRCode.gym_id == gym_id, GymQRCode.is_active == True)
        .first()
    )

    qr_file = None
    storage_key = None

    # If QR exists, reuse the file
    if existing_qr and existing_qr.file:
        qr_file = existing_qr.file
        storage_key = qr_file.storage_key

    # Generate QR (overwrite if storage_key exists)
    qr_nonce, public_id, url = qr_service.generate_gym_qr(gym_id, storage_key)

    if qr_file:
        # Update existing file record
        qr_file.storage_url = url
        qr_file.updated_at = datetime.utcnow()
        db.add(qr_file)
    else:
        # Create new file
        qr_file = File(
            owner_type="gym",
            owner_id=gym_id,
            file_type="image",
            purpose="gym_qr_code",
            original_filename=f"gym_{gym_id}_qr.png",
            extension="png",
            mime_type="image/png",
            storage_provider="cloudinary",
            storage_key=public_id,
            storage_url=url
        )
        db.add(qr_file)
        db.commit()
        db.refresh(qr_file)

    # Update or create QR record
    if existing_qr:
        existing_qr.qr_nonce = qr_nonce
        existing_qr.is_active = True
        existing_qr.rotated_at = datetime.utcnow()
        existing_qr.file_id = qr_file.file_id
        qr = existing_qr
    else:
        qr = GymQRCode(
            gym_id=gym_id,
            qr_nonce=qr_nonce,
            file_id=qr_file.file_id,
            is_active=True
        )
        db.add(qr)

    db.commit()
    db.refresh(qr)
    return qr

def get_active_qr_for_gym(db, gym_id: str, qr_nonce: str):
    return (
        db.query(GymQRCode)
        .filter(
            GymQRCode.gym_id == gym_id,
            GymQRCode.qr_nonce == qr_nonce,
            GymQRCode.is_active == True,
        )
        .first()
    )


