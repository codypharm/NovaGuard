"""Database models for patient lab results."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Float, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_guard.database import Base

if False: # TYPE_CHECKING
    from nova_guard.models.patient import Patient

class LabResult(Base):
    """Patient laboratory test results."""

    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    
    test_name: Mapped[str] = mapped_column(String(255)) # e.g., "Serum Creatinine"
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50)) # e.g., "mg/dL"
    reference_range: Mapped[Optional[str]] = mapped_column(String(100)) # e.g., "0.74-1.35"
    is_abnormal: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(50), default="manual") # "manual" or "vision"
    
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    patient: Mapped["Patient"] = relationship(back_populates="lab_results")
