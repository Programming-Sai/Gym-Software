# app/crud/files.py
from sqlalchemy.orm import Session
from app.models.files import File
from uuid import uuid4

MEDIA_PROJECT_FOLDER="gym"


def create_file_record(
    db: Session,
    owner_type: str,
    owner_id: str,
    file_type: str,
    purpose: str,
    original_filename: str,
    extension: str,
    mime_type: str,
    file_size: int | None,
    storage_provider: str,
    storage_key: str,
    storage_url: str,
    uploaded_by: str | None = None,
    associated_table: str | None = None,
    associated_record_id: str | None = None,
) -> File:
    file = File(
        file_id=str(uuid4()),
        owner_type=owner_type,
        owner_id=owner_id,
        file_type=file_type,
        purpose=purpose,
        original_filename=original_filename,
        extension=extension,
        mime_type=mime_type,
        file_size=file_size,
        storage_provider=storage_provider,
        storage_key=storage_key,
        storage_url=storage_url,
        uploaded_by=uploaded_by,
        associated_table=associated_table,
        associated_record_id=associated_record_id
    )
    db.add(file)
    db.commit()
    db.refresh(file)
    return file
