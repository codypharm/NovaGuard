"""Audit log model for clinical interaction accountability."""

from datetime import datetime
from typing import Optional

from sqlalchemy import String, DateTime, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from nova_guard.database import Base


class AuditLog(Base):
    """Records every AI recommendation for compliance and accountability."""
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50))          # e.g. "clinical_interaction"
    intent: Mapped[Optional[str]] = mapped_column(String(50)) # e.g. "AUDIT", "MEDICAL_KNOWLEDGE"
    query: Mapped[Optional[str]] = mapped_column(Text)        # User's input (truncated)
    response_summary: Mapped[Optional[str]] = mapped_column(Text)  # First 500 chars of response
    verdict_status: Mapped[Optional[str]] = mapped_column(String(20))  # "green"/"yellow"/"red"
    flag_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
