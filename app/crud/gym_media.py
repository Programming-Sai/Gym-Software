# app/crud/gym_media.py
from sqlalchemy.orm import Session
from app.models.gyms import GymPhoto, GymDocument
from app.models.files import File
from app.services.cloudinary_service import upload_file, delete_file
from app.crud.files import create_file_record, MEDIA_PROJECT_FOLDER
from uuid import uuid4
from typing import Optional


# -------------------------
# GYM PHOTOS
# -------------------------

def add_or_replace_gym_photo(
    db: Session,
    gym_id: str,
    file,
    filename: str,
    uploaded_by: Optional[str] = None,
    gym_photo_id: Optional[str] = None,
    is_primary: bool = False
) -> GymPhoto:
    """
    Adds a new photo or replaces an existing one if gym_photo_id is provided.
    """
    # Determine Cloudinary public_id if replacing
    existing_photo = None
    public_id = None
    if gym_photo_id:
        existing_photo = db.query(GymPhoto).filter(GymPhoto.gym_photo_id == gym_photo_id).first()
        if existing_photo:
            public_id = existing_photo.file.storage_key

    # 1️⃣ Upload to Cloudinary
    result = upload_file(file=file, folder=f"{MEDIA_PROJECT_FOLDER}/{gym_id}/photos", resource_type="image", public_id=public_id)

    # 2️⃣ Create or update File record
    extension = filename.split(".")[-1]
    if existing_photo:
        file_record = existing_photo.file
        file_record.original_filename = filename
        file_record.extension = extension
        file_record.mime_type = getattr(file, "content_type", "application/octet-stream")
        file_record.storage_key = result["public_id"]
        file_record.storage_url = result["secure_url"]
        file_record.uploaded_by = uploaded_by
        db.commit()
        db.refresh(file_record)
    else:
        file_record = create_file_record(
            db=db,
            owner_type="gym",
            owner_id=gym_id,
            file_type="image",
            purpose="gym_photo",
            original_filename=filename,
            extension=extension,
            mime_type=getattr(file, "content_type", "application/octet-stream"),
            file_size=None,
            storage_provider="cloudinary",
            storage_key=result["public_id"],
            storage_url=result["secure_url"],
            uploaded_by=uploaded_by,
            associated_table="gym_photos"
        )

    # 3️⃣ Create or update GymPhoto
    if existing_photo:
        existing_photo.is_primary = is_primary
        db.commit()
        db.refresh(existing_photo)
        return existing_photo
    else:
        photo = GymPhoto(
            gym_id=gym_id,
            file_id=file_record.file_id,
            is_primary=is_primary
        )
        db.add(photo)
        db.commit()
        db.refresh(photo)
        return photo


def delete_gym_photo(db: Session, gym_photo_id: str) -> Optional[GymPhoto]:
    photo = db.query(GymPhoto).filter(GymPhoto.gym_photo_id == gym_photo_id).first()
    if not photo:
        return None

    # Delete Cloudinary file
    delete_file(photo.file.storage_key, resource_type="image")

    # Delete File record
    db.delete(photo.file)

    # Delete GymPhoto
    db.delete(photo)
    db.commit()
    return photo


def list_gym_photos(db: Session, gym_id: str):
    return db.query(GymPhoto).filter(GymPhoto.gym_id == gym_id).all()


# -------------------------
# GYM DOCUMENTS
# -------------------------

def add_or_replace_gym_document(
    db: Session,
    gym_id: str,
    file,
    filename: str,
    document_type: str,
    uploaded_by: Optional[str] = None,
    gym_document_id: Optional[str] = None
) -> GymDocument:
    """
    Adds a new document or replaces an existing one if gym_document_id is provided.
    """
    existing_doc = None
    public_id = None
    if gym_document_id:
        existing_doc = db.query(GymDocument).filter(GymDocument.gym_document_id == gym_document_id).first()
        if existing_doc:
            public_id = existing_doc.file.storage_key

    # 1️⃣ Upload to Cloudinary (raw type for documents)
    result = upload_file(file=file, folder=f"{MEDIA_PROJECT_FOLDER}/{gym_id}/documents", resource_type="raw", public_id=public_id)

    # 2️⃣ Create or update File record
    extension = filename.split(".")[-1]
    if existing_doc:
        file_record = existing_doc.file
        file_record.original_filename = filename
        file_record.extension = extension
        file_record.mime_type = getattr(file, "content_type", "application/octet-stream")
        file_record.storage_key = result["public_id"]
        file_record.storage_url = result["secure_url"]
        file_record.uploaded_by = uploaded_by
        db.commit()
        db.refresh(file_record)
    else:
        file_record = create_file_record(
            db=db,
            owner_type="gym",
            owner_id=gym_id,
            file_type="document",
            purpose="verification_document",
            original_filename=filename,
            extension=extension,
            mime_type=getattr(file, "content_type", "application/octet-stream"),
            file_size=None,
            storage_provider="cloudinary",
            storage_key=result["public_id"],
            storage_url=result["secure_url"],
            uploaded_by=uploaded_by,
            associated_table="gym_documents"
        )

    # 3️⃣ Create or update GymDocument
    if existing_doc:
        existing_doc.document_type = document_type
        db.commit()
        db.refresh(existing_doc)
        return existing_doc
    else:
        doc = GymDocument(
            gym_id=gym_id,
            file_id=file_record.file_id,
            document_type=document_type
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)
        return doc


def delete_gym_document(db: Session, gym_document_id: str) -> Optional[GymDocument]:
    doc = db.query(GymDocument).filter(GymDocument.gym_document_id == gym_document_id).first()
    if not doc:
        return None

    # Delete Cloudinary file
    delete_file(doc.file.storage_key, resource_type="raw")

    # Delete File record
    db.delete(doc.file)

    # Delete GymDocument
    db.delete(doc)
    db.commit()
    return doc


def list_gym_documents(db: Session, gym_id: str):
    return db.query(GymDocument).filter(GymDocument.gym_id == gym_id).all()
