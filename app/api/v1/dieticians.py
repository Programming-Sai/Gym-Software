from typing import List
from fastapi import APIRouter, Depends, UploadFile, Form, File as FastAPIFile, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_db, get_current_user
from app.crud import dietician as crud_dietician
from app.schemas.dietician import DieticianDocumentSchema, DieticianInfoSchema


router = APIRouter(tags=["Dieticians"])

@router.get("/{dietician_id}", response_model=DieticianInfoSchema)
def get_dietician_info(dietician_id: str, db: Session = Depends(get_db)):
    dietician = crud_dietician.get_dietician(db, dietician_id)

    if not dietician:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dietician profile not found"
        )

    if dietician.status == "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dietician not verified"
        )

    return DieticianInfoSchema(
        dietician_id=dietician.dietician_id,
        user_id=dietician.user_id,
        bio=dietician.bio,
        specializations=dietician.specializations,
        experience_years=dietician.experience_years,
        status=dietician.status,
        profile_file_url=(
            dietician.profile_file.storage_url
            if dietician.profile_file
            else None
        ),
        average_rating=float(dietician.average_rating or 0),
        total_ratings=dietician.total_ratings,
        documents=[
            DieticianDocumentSchema(
                document_id=doc.document_id,
                document_type=doc.document_type,
                document_url=doc.file.storage_url,
            )
            for doc in dietician.dietician_documents
        ]
    )



@router.post("/request-verification")
async def request_dietician_verification(
    bio: str = Form(...),
    experience_years: int = Form(...),
    specializations: str = Form(...),
    document_types: str = Form(...),  
    files: List[UploadFile] = FastAPIFile(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "dietician":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a dietician")

    if len(files) != len(document_types.split(",")):
        print("\n\nLENGTH OF FILES: ", len(files), "LENGTH OF DOCUMENT_TYPES: ", len(document_types), " ", document_types, "\n\n")
        raise HTTPException(status_code=400, detail="Each file must have a document type")

    uploaded_files = [{"file": f.file, "filename": f.filename, "document_type": dt} for f, dt in zip(files, document_types.split(","))]

    application = crud_dietician.create_verification_request(
        db=db,
        user_id=current_user.user_id,
        bio=bio,
        specializations=specializations.split(","),
        experience_years=experience_years,
        uploaded_files=uploaded_files,
        uploader_id=current_user.user_id
    )

    return {
        "application_id": application.application_id,
        "status": application.status,
        "submitted_at": application.submitted_at
    }
