"""Moderator management endpoints for WhistleDrop.

All endpoints require HTTP Basic authentication.
Provides report auditing, filtering, inspection, and workflow progression.
Guarantees moderators cannot see reporter identity information (none exists) or case code secrets.
"""

from datetime import datetime, timezone
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.auth import get_current_moderator
from app.database import get_db
from app.models import Report, StatusUpdate
from app.schemas import (
    ModeratorReportDetail,
    ModeratorReportListResponse,
    ModeratorReportSummary,
    ReportCategory,
    ReportStatus,
    StatusUpdateCreate,
    StatusUpdateModerator,
    validate_status_transition,
)

router = APIRouter(
    tags=["Moderator"],
    dependencies=[Depends(get_current_moderator)],
)


@router.get(
    "/reports",
    response_model=ModeratorReportListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all reports with filtering and pagination",
    description=(
        "Retrieve reports with optional category and status filters. "
        "Supports offset/limit pagination."
    ),
)
def list_reports(
    db: Annotated[Session, Depends(get_db)],
    category: Optional[ReportCategory] = Query(None, description="Filter by report category"),
    report_status: Optional[ReportStatus] = Query(
        None, alias="status", description="Filter by report status"
    ),
    limit: int = Query(20, ge=1, le=100, description="Page size (1-100)"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
) -> ModeratorReportListResponse:
    """List reports for authenticated moderators with filtering and pagination."""
    query = db.query(Report)

    if category is not None:
        query = query.filter(Report.category == category.value)
    if report_status is not None:
        query = query.filter(Report.status == report_status.value)

    total = query.count()
    reports = (
        query.order_by(Report.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    items = [
        ModeratorReportSummary(
            id=r.id,
            category=r.category,
            description=r.description,
            evidence_url=r.evidence_url,
            status=r.status,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in reports
    ]

    return ModeratorReportListResponse(
        total=total,
        limit=limit,
        offset=offset,
        reports=items,
    )


@router.get(
    "/reports/{report_id}",
    response_model=ModeratorReportDetail,
    status_code=status.HTTP_200_OK,
    summary="View details of a specific report",
    description="Retrieve full details and complete status transition history for a report.",
)
def get_report(
    report_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> ModeratorReportDetail:
    """Retrieve detailed report information including full status update audit trail."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found.",
        )

    history = [
        StatusUpdateModerator(
            id=u.id,
            status=u.status,
            message=u.message,
            created_at=u.created_at,
        )
        for u in report.status_updates
    ]

    return ModeratorReportDetail(
        id=report.id,
        category=report.category,
        description=report.description,
        evidence_url=report.evidence_url,
        status=report.status,
        created_at=report.created_at,
        updated_at=report.updated_at,
        status_history=history,
    )


@router.patch(
    "/reports/{report_id}/status",
    response_model=ModeratorReportDetail,
    status_code=status.HTTP_200_OK,
    summary="Update report status and append public progress update",
    description=(
        "Advance the workflow status of a report and append an explanation message. "
        "Enforces strict workflow transition rules; terminal statuses cannot be modified."
    ),
)
def update_report_status(
    report_id: int,
    payload: StatusUpdateCreate,
    db: Annotated[Session, Depends(get_db)],
) -> ModeratorReportDetail:
    """Update report status following strictly defined workflow state transitions."""
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report with ID {report_id} not found.",
        )

    # Validate state transition rules
    is_valid, error_msg = validate_status_transition(report.status, payload.status)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg,
        )

    now_utc = datetime.now(timezone.utc)

    # Update report status and timestamp
    report.status = payload.status.value
    report.updated_at = now_utc

    # Append new status update history record
    new_update = StatusUpdate(
        report_id=report.id,
        status=payload.status.value,
        message=payload.message,
        created_at=now_utc,
    )
    db.add(new_update)
    db.commit()
    db.refresh(report)

    history = [
        StatusUpdateModerator(
            id=u.id,
            status=u.status,
            message=u.message,
            created_at=u.created_at,
        )
        for u in report.status_updates
    ]

    return ModeratorReportDetail(
        id=report.id,
        category=report.category,
        description=report.description,
        evidence_url=report.evidence_url,
        status=report.status,
        created_at=report.created_at,
        updated_at=report.updated_at,
        status_history=history,
    )
