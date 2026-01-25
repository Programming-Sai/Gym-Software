

from app.models.users import User
from sqlalchemy.orm import Session
from sqlalchemy.orm import Session
from datetime import datetime
from app.models.files import File
from app.services.cloudinary_service import upload_file
from app.crud.files import MEDIA_PROJECT_FOLDER


def register_or_replace_user_face(db: Session, user: User, file):
    """
    Registers or replaces a user's face image.
    """

    upload_kwargs = {
        "file": file.file,
        "folder": f"{MEDIA_PROJECT_FOLDER}/users/{user.user_id}/face",
        "resource_type": "image",
    }

    # overwrite if face already exists
    if user.face_file:
        upload_kwargs["public_id"] = user.face_file.storage_key

    result = upload_file(**upload_kwargs)

    if user.face_file:
        # update existing file
        face_file = user.face_file
        face_file.original_filename=file.filename,
        face_file.storage_url = result["secure_url"]
        face_file.updated_at = datetime.utcnow()
        db.add(face_file)
    else:
        # create new file
        face_file = File(
            owner_type="user",
            owner_id=user.user_id,
            file_type="image",
            purpose="face_id",
            original_filename=file.filename,
            extension="png",
            mime_type=file.content_type,
            storage_provider="cloudinary",
            storage_key=result["public_id"],
            storage_url=result["secure_url"],
        )
        db.add(face_file)
        db.commit()
        db.refresh(face_file)

        user.face_file_id = face_file.file_id

    user.face_registered_at = datetime.utcnow()

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def get_user_face_status(user: User):
    return {
        "has_face": bool(user.face_file_id),
        "registered_at": user.face_registered_at,
    }



def mark_email_verified(db: Session, user_id: str):
    user = db.query(User).filter(User.user_id == user_id).first()
    if user:
        user.email_verified = True
        db.commit()
        db.refresh(user)
        return user
    return None

def get_user_by_email(db, email: str):
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db, user_id: str):
    return db.query(User).filter(User.user_id == user_id).first()
