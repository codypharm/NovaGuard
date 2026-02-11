"""Pydantic schemas for API request/response validation."""

from datetime import date, datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field, ConfigDict

from nova_guard.models.patient import AllergyType, Severity


# ============================================================================
# Drug History Schemas
# ============================================================================

class DrugHistoryBase(BaseModel):
    """Base drug history schema."""

    drug_name: str = Field(..., min_length=1, max_length=255)
    dose: str = Field(..., max_length=100, description="e.g., '5mg', '10ml'")
    frequency: str = Field(..., max_length=100, description="e.g., 'twice daily', 'BID'")
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True
    notes: Optional[str] = None


class DrugHistoryCreate(DrugHistoryBase):
    """Schema for creating drug history entry."""

    patient_id: int


class DrugHistoryResponse(DrugHistoryBase):
    """Schema for drug history response."""

    id: int
    patient_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Allergy Registry Schemas
# ============================================================================

class AllergyCreate(BaseModel):
    """Schema for creating allergy entry."""

    patient_id: int
    allergen: str = Field(..., min_length=1, max_length=255)
    allergy_type: AllergyType
    severity: Severity
    symptoms: Optional[str] = None
    notes: Optional[str] = None


class AllergyResponse(BaseModel):
    """Schema for allergy response."""

    id: int
    patient_id: int
    allergen: str
    allergy_type: AllergyType
    severity: Severity
    symptoms: Optional[str]
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Adverse Reaction Schemas
# ============================================================================

class AdverseReactionCreate(BaseModel):
    """Schema for creating adverse reaction entry."""

    patient_id: int
    drug_name: str = Field(..., min_length=1, max_length=255)
    reaction_date: date
    severity: Severity
    symptoms: str = Field(..., min_length=1)
    notes: Optional[str] = None


class AdverseReactionResponse(BaseModel):
    """Schema for adverse reaction response."""

    id: int
    patient_id: int
    drug_name: str
    reaction_date: date
    severity: Severity
    symptoms: str
    notes: Optional[str]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Patient Schemas
# ============================================================================

class PatientBase(BaseModel):
    """Base patient schema."""

    name: str = Field(..., min_length=1, max_length=255)
    date_of_birth: date
    medical_record_number: Optional[str] = Field(None, max_length=100)
    weight: Optional[str] = Field(None, max_length=50)
    height: Optional[str] = Field(None, max_length=50)
    age_years: Optional[int] = Field(None, ge=0, le=150)
    is_pregnant: bool = False
    is_nursing: bool = False
    egfr: Optional[float] = Field(None, ge=0, description="Kidney function (mL/min/1.73m²)")


class PatientCreate(PatientBase):
    """Schema for creating a new patient."""

    allergies: Optional[list[AllergyCreate]] = None


class PatientResponse(PatientBase):
    """Schema for patient response."""

    id: int
    created_at: datetime
    updated_at: datetime
    
    allergies: list[AllergyResponse] = []
    drug_history: list[DrugHistoryResponse] = []
    adverse_reactions: list[AdverseReactionResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Prescription Processing Schemas (for LangGraph)
# ============================================================================

class PrescriptionData(BaseModel):
    """Extracted prescription data."""

    drug_name: str
    dose: str
    frequency: str
    prescriber: Optional[str] = None
    notes: Optional[str] = None


class PrescriptionInput(BaseModel):
    """Input for prescription processing."""

    input_type: Literal["image", "text", "voice"]
    patient_id: int
    
    # One of these will be populated based on input_type
    prescription_image: Optional[bytes] = None
    prescription_text: Optional[str] = None
    prescription_audio: Optional[bytes] = None


class SafetyFlag(BaseModel):
    """
    Represents a specific safety concern identified during processing.
    """
    severity: Literal["info", "warning", "critical"]
    category: str  # e.g., "allergy", "interaction", "contraindication"
    message: str
    source: str  # e.g., "OpenFDA", "Patient History"
    citation: Optional[str] = None  # URL to source (DailyMed, PubMed, etc.)


class SafetyVerdict(BaseModel):
    """Final safety assessment."""

    status: Literal["green", "yellow", "red"]
    flags: list[SafetyFlag]
    recommendation: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
