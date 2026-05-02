from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.users import User
from app.models.verifications import VerificationApplication, VerificationDocument
from app.schemas.verifications import (
    VerificationAddNoteRequest,
    VerificationApplicationAdminOut,
    VerificationApproveRequest,
    VerificationMoreInfoRequest,
    VerificationRejectRequest,
)
from app.services.audit_log_service import write_audit_log


router = APIRouter(tags=["Admin | Verifications"])


def admin_required(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in {"admin", "superadmin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/", response_model=list[VerificationApplicationAdminOut])
def list_verification_applications(
    applicant_type: Optional[str] = Query(None, description="gym_owner | dietician"),
    status: Optional[str] = Query(None, description="Filter by verification status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    q = (
        db.query(VerificationApplication)
        .options(
            selectinload(VerificationApplication.applicant_user),
            selectinload(VerificationApplication.reviewer),
            selectinload(VerificationApplication.withdrawer),
            selectinload(VerificationApplication.verification_documents).selectinload(VerificationDocument.file),
        )
    )
    if applicant_type:
        q = q.filter(VerificationApplication.applicant_type == applicant_type)
    if status:
        q = q.filter(VerificationApplication.status == status)
    return q.order_by(VerificationApplication.submitted_at.desc()).limit(limit).offset(offset).all()


@router.get("/{application_id}", response_model=VerificationApplicationAdminOut)
def get_verification_application(
    application_id: str,
    db: Session = Depends(get_db),
    _admin: User = Depends(admin_required),
):
    application = (
        db.query(VerificationApplication)
        .options(
            selectinload(VerificationApplication.applicant_user),
            selectinload(VerificationApplication.reviewer),
            selectinload(VerificationApplication.withdrawer),
            selectinload(VerificationApplication.verification_documents).selectinload(VerificationDocument.file),
        )
        .filter(VerificationApplication.application_id == application_id)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Verification application not found")
    return application


def _append_admin_note(existing: Optional[str], *, note: str, admin_id: str) -> str:
    stamp = datetime.utcnow().isoformat()
    entry = f"[{stamp}] admin:{admin_id} — {note.strip()}"
    if existing and existing.strip():
        return existing.rstrip() + "\n" + entry
    return entry


@router.post("/{application_id}/approve", response_model=VerificationApplicationAdminOut)
def approve_verification_application(
    application_id: str,
    payload: VerificationApproveRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    application = (
        db.query(VerificationApplication)
        .options(
            selectinload(VerificationApplication.applicant_user),
            selectinload(VerificationApplication.reviewer),
            selectinload(VerificationApplication.withdrawer),
            selectinload(VerificationApplication.verification_documents).selectinload(VerificationDocument.file),
        )
        .filter(VerificationApplication.application_id == application_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Verification application not found")

    if application.status in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail=f"Application is already {application.status}")
    if application.status == "withdrawn":
        raise HTTPException(status_code=400, detail="Cannot approve a withdrawn application")

    application.status = "approved"
    application.reviewed_at = datetime.utcnow()
    application.reviewed_by = admin.user_id
    application.rejection_reason = None
    application.info_request = None
    application.info_requested_at = None

    if payload.admin_notes and payload.admin_notes.strip():
        application.admin_notes = _append_admin_note(
            application.admin_notes, note=payload.admin_notes, admin_id=admin.user_id
        )

    db.add(application)
    write_audit_log(
        db,
        category="crud",
        action="verification.approved",
        entity_type="verification_application",
        entity_id=application.application_id,
        actor=admin,
        request=request,
        success=True,
        metadata={
            "applicant_type": application.applicant_type,
            "applicant_id": application.applicant_id,
        },
    )
    db.commit()
    db.refresh(application)
    return application


@router.post("/{application_id}/reject", response_model=VerificationApplicationAdminOut)
def reject_verification_application(
    application_id: str,
    payload: VerificationRejectRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    application = (
        db.query(VerificationApplication)
        .options(
            selectinload(VerificationApplication.applicant_user),
            selectinload(VerificationApplication.reviewer),
            selectinload(VerificationApplication.withdrawer),
            selectinload(VerificationApplication.verification_documents).selectinload(VerificationDocument.file),
        )
        .filter(VerificationApplication.application_id == application_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Verification application not found")

    if application.status in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail=f"Application is already {application.status}")
    if application.status == "withdrawn":
        raise HTTPException(status_code=400, detail="Cannot reject a withdrawn application")

    application.status = "rejected"
    application.reviewed_at = datetime.utcnow()
    application.reviewed_by = admin.user_id
    application.rejection_reason = payload.rejection_reason.strip()

    if payload.admin_notes and payload.admin_notes.strip():
        application.admin_notes = _append_admin_note(
            application.admin_notes, note=payload.admin_notes, admin_id=admin.user_id
        )

    db.add(application)
    write_audit_log(
        db,
        category="crud",
        action="verification.rejected",
        entity_type="verification_application",
        entity_id=application.application_id,
        actor=admin,
        request=request,
        success=True,
        metadata={
            "applicant_type": application.applicant_type,
            "applicant_id": application.applicant_id,
            "rejection_reason": payload.rejection_reason,
        },
    )
    db.commit()
    db.refresh(application)
    return application


@router.post("/{application_id}/request-more-info", response_model=VerificationApplicationAdminOut)
def request_more_info_for_verification_application(
    application_id: str,
    payload: VerificationMoreInfoRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    application = (
        db.query(VerificationApplication)
        .options(
            selectinload(VerificationApplication.applicant_user),
            selectinload(VerificationApplication.reviewer),
            selectinload(VerificationApplication.withdrawer),
            selectinload(VerificationApplication.verification_documents).selectinload(VerificationDocument.file),
        )
        .filter(VerificationApplication.application_id == application_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Verification application not found")

    if application.status in {"approved", "rejected"}:
        raise HTTPException(status_code=400, detail=f"Cannot request more info for status={application.status}")
    if application.status == "withdrawn":
        raise HTTPException(status_code=400, detail="Cannot request more info for a withdrawn application")

    application.status = "more_info_required"
    application.info_request = payload.info_request.strip()
    application.info_requested_at = datetime.utcnow()
    application.reviewed_at = None
    application.reviewed_by = None

    db.add(application)
    write_audit_log(
        db,
        category="crud",
        action="verification.more_info_requested",
        entity_type="verification_application",
        entity_id=application.application_id,
        actor=admin,
        request=request,
        success=True,
        metadata={
            "applicant_type": application.applicant_type,
            "applicant_id": application.applicant_id,
            "info_request": payload.info_request,
        },
    )
    db.commit()
    db.refresh(application)
    return application


@router.post("/{application_id}/clear-more-info", response_model=VerificationApplicationAdminOut)
def clear_more_info_for_verification_application(
    application_id: str,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    application = (
        db.query(VerificationApplication)
        .options(
            selectinload(VerificationApplication.applicant_user),
            selectinload(VerificationApplication.reviewer),
            selectinload(VerificationApplication.withdrawer),
            selectinload(VerificationApplication.verification_documents).selectinload(VerificationDocument.file),
        )
        .filter(VerificationApplication.application_id == application_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Verification application not found")

    if application.status != "more_info_required":
        raise HTTPException(status_code=400, detail=f"Application is not in more_info_required (status={application.status})")

    application.status = "pending"
    application.info_request = None
    application.info_requested_at = None

    db.add(application)
    write_audit_log(
        db,
        category="crud",
        action="verification.more_info_cleared",
        entity_type="verification_application",
        entity_id=application.application_id,
        actor=admin,
        request=request,
        success=True,
        metadata={
            "applicant_type": application.applicant_type,
            "applicant_id": application.applicant_id,
        },
    )
    db.commit()
    db.refresh(application)
    return application


@router.post("/{application_id}/add-note", response_model=VerificationApplicationAdminOut)
def add_note_to_verification_application(
    application_id: str,
    payload: VerificationAddNoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_required),
):
    application = (
        db.query(VerificationApplication)
        .options(
            selectinload(VerificationApplication.applicant_user),
            selectinload(VerificationApplication.reviewer),
            selectinload(VerificationApplication.withdrawer),
            selectinload(VerificationApplication.verification_documents).selectinload(VerificationDocument.file),
        )
        .filter(VerificationApplication.application_id == application_id)
        .with_for_update(nowait=False)
        .first()
    )
    if not application:
        raise HTTPException(status_code=404, detail="Verification application not found")

    application.admin_notes = _append_admin_note(
        application.admin_notes, note=payload.note, admin_id=admin.user_id
    )

    db.add(application)
    write_audit_log(
        db,
        category="crud",
        action="verification.note_added",
        entity_type="verification_application",
        entity_id=application.application_id,
        actor=admin,
        request=request,
        success=True,
        metadata={
            "applicant_type": application.applicant_type,
            "applicant_id": application.applicant_id,
            "note": payload.note,
        },
    )
    db.commit()
    db.refresh(application)
    return application
