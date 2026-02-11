from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_guard.database import Base

class Session(Base):
    """
    Represents a conversational session.
    The actual chat history is stored in LangGraph's checkpointer,
    but this table tracks metadata and patient linkage.
    """
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID string
    title: Mapped[Optional[str]] = mapped_column(String(255), default="New Session")
    
    patient_id: Mapped[Optional[int]] = mapped_column(ForeignKey("patients.id"), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    patient: Mapped[Optional["Patient"]] = relationship(back_populates="sessions")
