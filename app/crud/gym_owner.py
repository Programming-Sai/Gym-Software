from __future__ import annotations

import mimetypes
import os

from sqlalchemy.orm import Session

from app.crud.files import MEDIA_PROJECT_FOLDER
from app.models import File, VerificationApplication, VerificationDocument
from app.models.enums import DocumentTypeEnum
from app.services import cloudinary_service


def create_verification_request(
    db: Session,
    *,
    user_id: str,
    uploaded_files: list[dict],  # [{'file': file, 'filename': str, 'document_type': str}]
    uploader_id: str,
) -> VerificationApplication:
    allowed_doc_types = set(DocumentTypeEnum.enums)

    file_records: list[tuple[File, str]] = []
    for file_data in uploaded_files:
        file_obj = file_data["file"]
        filename = file_data["filename"]
        doc_type = str(file_data["document_type"] or "").strip()

        if doc_type not in allowed_doc_types:
            raise ValueError(f"Invalid document_type: {doc_type}")

        ext = os.path.splitext(filename)[1].lower().replace(".", "")
        resource_type = "raw" if ext in ["pdf", "doc", "docx"] else "image"

        result = cloudinary_service.upload_file(
            file_obj,
            folder=f"{MEDIA_PROJECT_FOLDER}/gym_owner_documents",
            resource_type=resource_type,
        )
        public_id = result["public_id"]
        url = result["secure_url"]
        mime_type, _ = mimetypes.guess_type(filename)

        file_record = File(
            owner_type="user",
            owner_id=user_id,
            file_type="document" if resource_type == "raw" else "image",
            purpose="verification_document",
            original_filename=filename,
            extension=ext or "",
            mime_type=mime_type or "application/octet-stream",
            storage_provider="cloudinary",
            storage_key=public_id,
            storage_url=url,
            uploaded_by=uploader_id,
            associated_table="verification_documents",
            associated_record_id=None,  # populated after VerificationDocument is created
            is_public=False,
        )
        db.add(file_record)
        db.flush()
        file_records.append((file_record, doc_type))

    application = VerificationApplication(
        applicant_type="gym_owner",
        applicant_id=user_id,
        status="pending",
    )
    db.add(application)
    db.flush()

    for file_record, doc_type in file_records:
        verification_doc = VerificationDocument(
            application_id=application.application_id,
            file_id=file_record.file_id,
            document_type=doc_type,
        )
        db.add(verification_doc)
        db.flush()
        file_record.associated_record_id = verification_doc.verification_document_id

    db.commit()
    db.refresh(application)
    return application


def get_verification_requests(db: Session, *, user_id: str):
    return (
        db.query(VerificationApplication)
        .filter(
            VerificationApplication.applicant_type == "gym_owner",
            VerificationApplication.applicant_id == user_id,
        )
        .all()
    )

