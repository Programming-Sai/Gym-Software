from sqlalchemy.orm import Session
from app.crud.files import MEDIA_PROJECT_FOLDER
from app.models import Dietician, VerificationApplication, VerificationDocument, DieticianDocument, File
from uuid import uuid4
from app.services import cloudinary_service
import os
import mimetypes


def get_dietician_by_user_id(db: Session, user_id: str) -> Dietician | None:
    return db.query(Dietician).filter(Dietician.user_id == user_id).first()


def get_dietician(db: Session, dietician_id: str) -> Dietician | None:
    return db.query(Dietician).filter(Dietician.dietician_id == dietician_id).first()


def create_verification_request(
    db: Session,
    user_id: str,
    bio: str,
    specializations: list[str],
    experience_years: int,
    uploaded_files: list[dict],  # [{'file': UploadFile, 'filename': str, 'document_type': str}]
    uploader_id: str
) -> VerificationApplication:

    # 1. Create or update dietician info
    dietician = get_dietician_by_user_id(db, user_id)
    if not dietician:
        dietician = Dietician(
            user_id=user_id,
            bio=bio,
            specializations=specializations,
            experience_years=experience_years,
            status="inactive"  # inactive until verification
        )
        db.add(dietician)
        db.flush()  # get dietician_id
    else:
        dietician.bio = bio
        dietician.specializations = specializations
        dietician.experience_years = experience_years
        dietician.status = "inactive"

    # 2. Upload files to Cloudinary and create File entries
    file_ids = []
    for file_data in uploaded_files:
        file_obj = file_data["file"]
        filename = file_data["filename"]
        doc_type = file_data["document_type"]

        # Determine extension & resource_type
        ext = os.path.splitext(filename)[1].lower().replace(".", "")
        resource_type = "raw" if ext in ["pdf", "doc", "docx"] else "image"

        # Upload file
        result = cloudinary_service.upload_file(
            file_obj,
            folder=f"{MEDIA_PROJECT_FOLDER}/dietician_documents",
            resource_type=resource_type
        )
        public_id = result["public_id"]
        url = result["secure_url"]
        mime_type, _ = mimetypes.guess_type(filename)

        # 3a. Create File record
        file_record = File(
            owner_type="dietician",
            owner_id=dietician.dietician_id,
            file_type="document" if resource_type == "raw" else resource_type,
            purpose="verification_document",
            original_filename=filename,
            extension=ext,
            mime_type=mime_type or "application/octet-stream",
            storage_provider="cloudinary",
            storage_key=public_id,
            storage_url=url,
            uploaded_by=uploader_id,
            associated_table="dietician_documents",
            associated_record_id=None,  # will populate after DieticianDocument is created
            is_public=False
        )
        db.add(file_record)
        db.flush()  # get file_id
        file_ids.append((file_record, doc_type))

        # 3b. Create DieticianDocument row
        dietician_doc = DieticianDocument(
            dietician_id=dietician.dietician_id,
            file_id=file_record.file_id,
            document_type=doc_type
        )
        db.add(dietician_doc)
        db.flush()
        # Update file's associated_record_id
        file_record.associated_record_id = dietician_doc.document_id

    # 4. Create verification application
    application = VerificationApplication(
        applicant_type="dietician",
        applicant_id=user_id,
        status="pending"
    )
    db.add(application)
    db.flush()

    # 5. Create VerificationDocument rows
    for file_record, doc_type in file_ids:
        verification_doc = VerificationDocument(
            application_id=application.application_id,
            file_id=file_record.file_id,
            document_type=doc_type
        )
        db.add(verification_doc)

    db.commit()
    db.refresh(application)
    return application
