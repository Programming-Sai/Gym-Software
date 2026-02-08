from typing import List, Optional
from fastapi import APIRouter, Depends, Query, UploadFile, Form, File as FastAPIFile, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.crud import dietician as crud_dietician
from app.models.dieticians import Dietician
from app.models.relationships import ClientAssignment
from app.schemas.dietician import (
    ClientAssignmentSchema,
    ClientAssignmentStatusUpdate,
    ClientDieticianAssignmentSchema,
    DieticianDocumentSchema,
    DieticianInfoSchema,
    DieticianListingSchema,
    DieticianVerificationStatusSchema,
)

router = APIRouter(tags=["Dieticians"])


def is_admin(user) -> bool:
    return user and user.role == "admin"


def is_self(user, dietician: Dietician) -> bool:
    return user and user.user_id == dietician.user_id


@router.get("/{dietician_id}", response_model=DieticianListingSchema | DieticianInfoSchema)
def get_dietician_info(
    dietician_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    dietician = crud_dietician.get_dietician(db, dietician_id)

    if not dietician or (dietician.status != "active" and not (
        is_self(current_user, dietician) or is_admin(current_user)
    )):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dietician profile not found",
        )



    base_payload = dict(
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
        verified_document_count = (
            len(dietician.dietician_documents)
            if dietician.status == "active"
            else 0
        ),
    )

    # PRIVATE VIEW
    if is_self(current_user, dietician) or is_admin(current_user):
        return DieticianInfoSchema(
            **base_payload,
            documents=[
                DieticianDocumentSchema(
                    document_id=doc.document_id,
                    document_type=doc.document_type,
                    document_url=doc.file.storage_url,
                )
                for doc in dietician.dietician_documents
            ],
        )

    # PUBLIC VIEW
    return DieticianListingSchema(**base_payload)


@router.get("/", response_model=List[DieticianListingSchema])
def list_dieticians(
    db: Session = Depends(get_db),
    specialization: Optional[str] = Query(None),
    min_experience: Optional[int] = Query(None),
    min_rating: Optional[float] = Query(None),
):
    query = db.query(Dietician).filter(Dietician.status == "active")

    if specialization:
        query = query.filter(Dietician.specializations.contains([specialization]))

    if min_experience:
        query = query.filter(Dietician.experience_years >= min_experience)

    if min_rating:
        query = query.filter(Dietician.average_rating >= min_rating)

    dieticians = query.all()

    results = []
    for d in dieticians:
        results.append(
            DieticianListingSchema(
                dietician_id=d.dietician_id,
                user_id=d.user_id,
                bio=d.bio,
                specializations=d.specializations,
                experience_years=d.experience_years,
                status=d.status,
                profile_file_url=d.profile_file.storage_url if d.profile_file else None,
                average_rating=float(d.average_rating or 0),
                total_ratings=d.total_ratings,
                verified_document_count=len(d.dietician_documents),

            )
        )

    return results


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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a dietician")

    if len(files) != len(document_types.split(",")):
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


@router.post(
    "/dieticians/{dietician_id}/assignments",
    response_model=ClientAssignmentSchema,
    status_code=status.HTTP_201_CREATED
)
def assign_dietician(
    dietician_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "gym_user":
        raise HTTPException(status_code=403, detail="Only clients can assign dieticians")

    dietician = db.query(Dietician).filter(
        Dietician.dietician_id == dietician_id,
        Dietician.status == "active"
    ).first()

    if not dietician:
        raise HTTPException(status_code=404, detail="Dietician not available")

    existing = db.query(ClientAssignment).filter(
        ClientAssignment.dietician_id == dietician_id,
        ClientAssignment.user_id == current_user.user_id,
        ClientAssignment.status != "ended",
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="You already have an active assignment with this dietician",
        )

    assignment = ClientAssignment(
        dietician_id=dietician_id,
        user_id=current_user.user_id,
        status="active",  # auto-accept
    )

    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    return assignment


@router.patch(
    "/client-assignments/{assignment_id}",
    response_model=ClientAssignmentSchema
)
def update_assignment_status(
    assignment_id: str,
    payload: ClientAssignmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    assignment = db.query(ClientAssignment).filter(
        ClientAssignment.assignment_id == assignment_id,
        ClientAssignment.user_id == current_user.user_id,
    ).first()

    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if assignment.status == "ended":
        raise HTTPException(status_code=400, detail="Assignment already ended")

    if payload.status not in {"paused", "ended"}:
        raise HTTPException(status_code=400, detail="Invalid status transition")

    assignment.status = payload.status

    if payload.status == "ended":
        assignment.ended_at = func.now()
        assignment.ended_reason = payload.ended_reason

    db.commit()
    db.refresh(assignment)

    return assignment


@router.get("/me/assignments", response_model=List[ClientAssignmentSchema])
def get_my_clients(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "dietician":
        raise HTTPException(status_code=403, detail="Only dieticians can access this")

    dietician = db.query(Dietician).filter(Dietician.user_id == current_user.user_id).first()
    if not dietician:
        raise HTTPException(status_code=404, detail="Dietician profile not found")

    query = db.query(ClientAssignment).filter(ClientAssignment.dietician_id == dietician.dietician_id)
    
    if status:
        query = query.filter(ClientAssignment.status == status)

    return query.all()


@router.get("/me/dieticians", response_model=List[ClientDieticianAssignmentSchema])
def get_my_dieticians(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "gym_user":
        raise HTTPException(status_code=403, detail="Only clients can access this")

    assignments = db.query(ClientAssignment).filter(ClientAssignment.user_id == current_user.user_id).all()

    results = []
    for a in assignments:
        results.append(
            ClientDieticianAssignmentSchema(
                assignment_id=a.assignment_id,
                status=a.status,
                assigned_at=a.assigned_at,
                ended_at=a.ended_at,
                ended_reason=a.ended_reason,
                dietician=DieticianListingSchema(
                    dietician_id=a.dietician.dietician_id,
                    user_id=a.dietician.user_id,
                    bio=a.dietician.bio,
                    specializations=a.dietician.specializations,
                    experience_years=a.dietician.experience_years,
                    status=a.dietician.status,
                    profile_file_url=a.dietician.profile_file.storage_url if a.dietician.profile_file else None,
                    average_rating=float(a.dietician.average_rating or 0),
                    total_ratings=a.dietician.total_ratings,
                    verified_document_count=len(a.dietician.dietician_documents)
                )
            )
        )
    return results


@router.get("/me/verification", response_model=List[DieticianVerificationStatusSchema])
def get_my_verification_status(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if current_user.role != "dietician":
        raise HTTPException(status_code=403, detail="Only dieticians can access this")

    applications = crud_dietician.get_verification_requests(db, current_user.user_id)
    return applications
