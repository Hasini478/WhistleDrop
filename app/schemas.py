"""Pydantic validation schemas and enums for WhistleDrop."""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportCategory(str, Enum):
    """Allowed categories for anonymous reports."""

    SECURITY = "Security"
    HARASSMENT = "Harassment"
    CORRUPTION = "Corruption"
    TECHNICAL = "Technical"
    OTHER = "Other"


class ReportStatus(str, Enum):
    """Allowed workflow statuses for reports."""

    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


# Status Workflow Definition
TERMINAL_STATUSES = {ReportStatus.RESOLVED, ReportStatus.DISMISSED}

ALLOWED_TRANSITIONS = {
    ReportStatus.SUBMITTED: {ReportStatus.UNDER_REVIEW, ReportStatus.DISMISSED},
    ReportStatus.UNDER_REVIEW: {ReportStatus.RESOLVED, ReportStatus.DISMISSED, ReportStatus.UNDER_REVIEW},
    ReportStatus.RESOLVED: set(),
    ReportStatus.DISMISSED: set(),
}


def validate_status_transition(current_status: str, new_status: ReportStatus) -> tuple[bool, str]:
    """Validate if a status transition is permitted by the workflow rules.

    Returns:
        (is_valid, error_message)
    """
    try:
        curr_enum = ReportStatus(current_status)
    except ValueError:
        return False, f"Current status '{current_status}' is invalid."

    if curr_enum in TERMINAL_STATUSES:
        return False, f"Cannot update status: Report is in terminal status '{curr_enum.value}'."

    allowed = ALLOWED_TRANSITIONS.get(curr_enum, set())
    if new_status not in allowed:
        allowed_names = [s.value for s in allowed]
        return False, (
            f"Invalid status transition from '{curr_enum.value}' to '{new_status.value}'. "
            f"Allowed transitions: {allowed_names}"
        )

    return True, ""


# --- Request Schemas ---

class ReportCreate(BaseModel):
    """Payload for submitting a new anonymous report."""

    category: ReportCategory = Field(
        ...,
        description="Category of the report: Security, Harassment, Corruption, Technical, or Other",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=10000,
        description="Detailed description of the incident or misconduct",
    )
    evidence_url: Optional[str] = Field(
        None,
        max_length=2048,
        description="Optional URL pointing to external supporting evidence",
    )

    @field_validator("description", mode="before")
    @classmethod
    def validate_description(cls, v: object) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Description must be a non-empty string.")
        stripped = v.strip()
        if len(stripped) > 10000:
            raise ValueError("Description exceeds maximum length of 10,000 characters.")
        return stripped

    @field_validator("evidence_url", mode="before")
    @classmethod
    def validate_evidence_url(cls, v: object) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return None
            parsed = urlparse(stripped)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError("evidence_url must be a valid HTTP or HTTPS URL.")
            if len(stripped) > 2048:
                raise ValueError("evidence_url exceeds maximum length of 2048 characters.")
            return stripped
        raise ValueError("evidence_url must be a string or null.")

    model_config = ConfigDict(extra="forbid")


class StatusUpdateCreate(BaseModel):
    """Payload for moderator updating a report's status and appending a message."""

    status: ReportStatus = Field(..., description="New status for the report")
    message: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Public progress or explanation update message",
    )

    @field_validator("message", mode="before")
    @classmethod
    def validate_message(cls, v: object) -> str:
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Status update message must be a non-empty string.")
        stripped = v.strip()
        if len(stripped) > 1000:
            raise ValueError("Status update message exceeds maximum length of 1,000 characters.")
        return stripped

    model_config = ConfigDict(extra="forbid")


# --- Response Schemas ---

class ReportSubmitResponse(BaseModel):
    """Response returned upon successful anonymous submission."""

    message: str = "Report submitted successfully."
    case_code: str = Field(..., description="One-time secret case code to check status")

    model_config = ConfigDict(from_attributes=True)


class StatusUpdatePublic(BaseModel):
    """Publicly visible status update entry."""

    status: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReportTrackingResponse(BaseModel):
    """Response for public case tracking. Excludes internal IDs and secret hashes."""

    case_code: str
    category: str
    status: str
    created_at: datetime
    status_updates: List[StatusUpdatePublic] = []

    model_config = ConfigDict(from_attributes=True)


class StatusUpdateModerator(BaseModel):
    """Moderator view of a status update entry."""

    id: int
    status: str
    message: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModeratorReportSummary(BaseModel):
    """Summary item in moderator's paginated list of reports."""

    id: int
    category: str
    description: str
    evidence_url: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ModeratorReportDetail(BaseModel):
    """Full detail of a single report for authenticated moderators."""

    id: int
    category: str
    description: str
    evidence_url: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    status_history: List[StatusUpdateModerator] = []

    model_config = ConfigDict(from_attributes=True)


class ModeratorReportListResponse(BaseModel):
    """Paginated response for moderator report listing."""

    total: int
    limit: int
    offset: int
    reports: List[ModeratorReportSummary]
