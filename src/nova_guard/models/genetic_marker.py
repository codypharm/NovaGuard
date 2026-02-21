"""Database models for patient genetic markers (PGx)."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_guard.database import Base

if False: # TYPE_CHECKING
    from nova_guard.models.patient import Patient

class GeneticMarker(Base):
    """Patient pharmacogenomics genetic markers."""

    __tablename__ = "genetic_markers"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    
    gene: Mapped[str] = mapped_column(String(50)) # e.g., "CYP2D6"
    phenotype: Mapped[str] = mapped_column(String(100)) # e.g., "Poor Metabolizer"
    source: Mapped[str] = mapped_column(String(50), default="manual") 
    
    tested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    patient: Mapped["Patient"] = relationship(back_populates="genetic_markers")
