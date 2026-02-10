"""Database models for patient records and medical history."""

from datetime import date, datetime
from enum import Enum
from typing import Optional

from sqlalchemy import ForeignKey, String, Text, Date, DateTime, Float, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from nova_guard.database import Base


class AllergyType(str, Enum):
    """Types of allergies."""

    DRUG = "drug"
    ENVIRONMENTAL = "environmental"
    CONTACT = "contact"


class Severity(str, Enum):
    """Severity levels for allergies and adverse reactions."""

    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    LIFE_THREATENING = "life_threatening"


class Patient(Base):
    """Patient demographic and identification information."""

    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    date_of_birth: Mapped[date] = mapped_column(Date)
    medical_record_number: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    
    # Optional patient metadata
    weight: Mapped[Optional[str]] = mapped_column(String(50)) # e.g. "70kg"
    height: Mapped[Optional[str]] = mapped_column(String(50)) # e.g. "175cm"
    age_years: Mapped[Optional[int]]  # Calculated or stored
    is_pregnant: Mapped[bool] = mapped_column(Boolean, default=False)
    is_nursing: Mapped[bool] = mapped_column(Boolean, default=False)
    egfr: Mapped[Optional[float]] = mapped_column(Float)  # Kidney function (mL/min/1.73m²)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    drug_history: Mapped[list["DrugHistory"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    allergies: Mapped[list["AllergyRegistry"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    adverse_reactions: Mapped[list["AdverseReaction"]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class DrugHistory(Base):
    """Patient's medication history."""

    __tablename__ = "drug_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    
    drug_name: Mapped[str] = mapped_column(String(255))
    dose: Mapped[str] = mapped_column(String(100))  # e.g., "5mg", "10ml"
    frequency: Mapped[str] = mapped_column(String(100))  # e.g., "twice daily", "BID"
    
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[Optional[date]] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    patient: Mapped["Patient"] = relationship(back_populates="drug_history")


class AllergyRegistry(Base):
    """Patient's allergy registry."""

    __tablename__ = "allergy_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    
    allergen: Mapped[str] = mapped_column(String(255))  # Drug name or substance
    allergy_type: Mapped[AllergyType] = mapped_column(String(50))
    severity: Mapped[Severity] = mapped_column(String(50))
    
    symptoms: Mapped[Optional[str]] = mapped_column(Text)  # e.g., "Rash, itching"
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    patient: Mapped["Patient"] = relationship(back_populates="allergies")


class AdverseReaction(Base):
    """Patient's adverse drug reaction history."""

    __tablename__ = "adverse_reactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"))
    
    drug_name: Mapped[str] = mapped_column(String(255))
    reaction_date: Mapped[date] = mapped_column(Date)
    severity: Mapped[Severity] = mapped_column(String(50))
    
    symptoms: Mapped[str] = mapped_column(Text)  # Description of reaction
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    patient: Mapped["Patient"] = relationship(back_populates="adverse_reactions")
