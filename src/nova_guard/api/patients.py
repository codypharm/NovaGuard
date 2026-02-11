"""Patient CRUD operations."""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nova_guard.models.patient import Patient, DrugHistory, AllergyRegistry, AdverseReaction
from nova_guard.schemas.patient import (
    PatientCreate,
    DrugHistoryCreate,
    AllergyCreate,
    AdverseReactionCreate,
)


async def create_patient(db: AsyncSession, patient: PatientCreate) -> Patient:
    """Create a new patient."""
    db_patient = Patient(**patient.model_dump())
    db.add(db_patient)
    await db.flush()
    await db.refresh(db_patient)
    return db_patient


async def update_patient(
    db: AsyncSession, patient_id: int, patient_data: PatientCreate
) -> Optional[Patient]:
    """Update an existing patient."""
    db_patient = await get_patient(db, patient_id)
    if not db_patient:
        return None

    update_data = patient_data.model_dump(exclude_unset=True)
    
    # Handle allergies separately if provided
    if "allergies" in update_data:
        allergies_data = update_data.pop("allergies")
        if allergies_data is not None:
             # Clear existing allergies for this patient
             await db.execute(
                 select(AllergyRegistry).where(AllergyRegistry.patient_id == patient_id)
             )
             # Better approach: delete all and re-add to ensure sync (handles deletions)
             from sqlalchemy import delete
             await db.execute(delete(AllergyRegistry).where(AllergyRegistry.patient_id == patient_id))
             
             for allergy in allergies_data:
                 # Ensure patient_id is correct
                 allergy['patient_id'] = patient_id
                 db_allergy = AllergyRegistry(**allergy)
                 db.add(db_allergy)

    for key, value in update_data.items():
        setattr(db_patient, key, value)

    await db.flush()
    await db.refresh(db_patient)
    return db_patient


async def get_patient(db: AsyncSession, patient_id: int) -> Optional[Patient]:
    """Get patient by ID with all related data."""
    result = await db.execute(
        select(Patient)
        .where(Patient.id == patient_id)
        .options(
            selectinload(Patient.drug_history),
            selectinload(Patient.allergies),
            selectinload(Patient.adverse_reactions),
        )
    )
    return result.scalar_one_or_none()


async def get_patient_by_mrn(db: AsyncSession, mrn: str) -> Optional[Patient]:
    """Get patient by MRN with all related data."""
    result = await db.execute(
        select(Patient)
        .where(Patient.medical_record_number == mrn)
        .options(
            selectinload(Patient.drug_history),
            selectinload(Patient.allergies),
            selectinload(Patient.adverse_reactions),
        )
    )
    return result.scalar_one_or_none()


async def get_patients(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[Patient]:
    """Get list of patients."""
    result = await db.execute(select(Patient).offset(skip).limit(limit))
    return list(result.scalars().all())


async def add_drug_to_history(
    db: AsyncSession, drug: DrugHistoryCreate
) -> DrugHistory:
    """Add drug to patient's history."""
    db_drug = DrugHistory(**drug.model_dump())
    db.add(db_drug)
    await db.flush()
    await db.refresh(db_drug)
    return db_drug


async def add_allergy(db: AsyncSession, allergy: AllergyCreate) -> AllergyRegistry:
    """Add allergy to patient's registry."""
    # Check for existing allergy (case-insensitive)
    result = await db.execute(
        select(AllergyRegistry)
        .where(AllergyRegistry.patient_id == allergy.patient_id)
        .where(AllergyRegistry.allergen.ilike(allergy.allergen))
    )
    existing = result.scalar_one_or_none()
    
    if existing:
        return existing

    db_allergy = AllergyRegistry(**allergy.model_dump())
    db.add(db_allergy)
    await db.flush()
    await db.refresh(db_allergy)
    return db_allergy


async def add_adverse_reaction(
    db: AsyncSession, reaction: AdverseReactionCreate
) -> AdverseReaction:
    """Add adverse reaction to patient's history."""
    db_reaction = AdverseReaction(**reaction.model_dump())
    db.add(db_reaction)
    await db.flush()
    await db.refresh(db_reaction)
    return db_reaction
