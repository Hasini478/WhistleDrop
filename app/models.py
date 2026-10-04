"""SQLAlchemy ORM models for WhistleDrop.

Notice: This schema strictly contains no user or reporter tables, and stores no
identifying request metadata (e.g. IP addresses, headers, or browser signatures).
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


def utc_now():
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)


class Report(Base):
    """Report model representing an anonymously submitted concern or incident."""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    # Storing only a cryptographic HMAC-SHA256 hash of the case code.
    case_code_hash = Column(String(64), unique=True, index=True, nullable=False)
    category = Column(String(50), index=True, nullable=False)
    description = Column(Text, nullable=False)
    evidence_url = Column(String(2048), nullable=True)
    status = Column(String(50), index=True, nullable=False, default="SUBMITTED")
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    status_updates = relationship(
        "StatusUpdate",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="StatusUpdate.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_reports_category_status", "category", "status"),
    )

    def __repr__(self) -> str:
        return f"<Report(id={self.id}, category='{self.category}', status='{self.status}')>"


class StatusUpdate(Base):
    """StatusUpdate model representing status transitions and public progression updates."""

    __tablename__ = "status_updates"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), index=True, nullable=False)
    status = Column(String(50), nullable=False)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, server_default=func.now(), nullable=False)

    # Relationships
    report = relationship("Report", back_populates="status_updates")

    def __repr__(self) -> str:
        return f"<StatusUpdate(id={self.id}, report_id={self.report_id}, status='{self.status}')>"
