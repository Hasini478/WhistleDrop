"""Anonymous reporter endpoints for submitting and tracking reports.

Guarantees reporter privacy:
- No accounts, sessions, or cookies.
- No storage of IP addresses, user agents, or request metadata.
- Internal database IDs and hashes are never exposed.
"""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.config import Settings, get_settings
from app.database import get_db
from app.models import Report, StatusUpdate
from app.schemas import (
    ReportCategory,
    ReportCreate,
    ReportStatus,
    ReportSubmitResponse,
    ReportTrackingResponse,
    StatusUpdatePublic,
)
from app.security import generate_case_code, hash_case_code

router = APIRouter(tags=["Reports (Anonymous)"])


@router.post(
    "",
    response_model=ReportSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an anonymous report",
    description=(
        "Submit a confidential report without creating an account or providing any identity details. "
        "Returns a unique, cryptographically generated case code used for tracking."
    ),
)
def submit_report(
    payload: ReportCreate,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportSubmitResponse:
    """Submit an anonymous report and receive an unguessable case code."""
    # 1. Generate unguessable case code and its one-way cryptographic HMAC hash
    case_code = generate_case_code()
    case_code_hash = hash_case_code(case_code, settings.SECRET_KEY)

    # 2. Create the report record with initial SUBMITTED status
    new_report = Report(
        category=payload.category.value,
        description=payload.description,
        evidence_url=payload.evidence_url,
        status=ReportStatus.SUBMITTED.value,
        case_code_hash=case_code_hash,
    )
    db.add(new_report)
    db.flush()  # Obtain new_report.id for initial status update

    # 3. Create initial status history entry
    initial_update = StatusUpdate(
        report_id=new_report.id,
        status=ReportStatus.SUBMITTED.value,
        message="Report submitted and pending review.",
    )
    db.add(initial_update)
    db.commit()

    return ReportSubmitResponse(
        message="Report submitted successfully.",
        case_code=case_code,
    )


@router.get(
    "/track/{case_code}",
    response_model=ReportTrackingResponse,
    status_code=status.HTTP_200_OK,
    summary="Track report status anonymously",
    description=(
        "Check status and public progress updates using only the secret case code. "
        "Excludes all internal IDs, database hashes, or moderator metadata."
    ),
)
def track_report(
    case_code: str,
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ReportTrackingResponse:
    """Lookup a report by hashing the submitted case code."""
    cleaned_code = case_code.strip()
    if not cleaned_code:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found with the provided case code.",
        )

    code_hash = hash_case_code(cleaned_code, settings.SECRET_KEY)

    report = db.query(Report).filter(Report.case_code_hash == code_hash).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found with the provided case code.",
        )

    # Convert status updates into public schema
    public_updates = [
        StatusUpdatePublic(
            status=update.status,
            message=update.message,
            created_at=update.created_at,
        )
        for update in report.status_updates
    ]

    return ReportTrackingResponse(
        case_code=cleaned_code,
        category=report.category,
        status=report.status,
        created_at=report.created_at,
        status_updates=public_updates,
    )
