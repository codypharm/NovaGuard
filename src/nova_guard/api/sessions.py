from datetime import datetime
from typing import Optional, List

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from nova_guard.models.session import Session
from nova_guard.models.patient import Patient


async def get_session(db: AsyncSession, session_id: str) -> Optional[Session]:
    """Retrieve a session by ID."""
    result = await db.execute(
        select(Session).where(Session.id == session_id).options(selectinload(Session.patient))
    )
    return result.scalar_one_or_none()


async def create_session(db: AsyncSession, session_id: str, title: str = "New Session") -> Session:
    """Create a new session."""
    session = Session(id=session_id, title=title)
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def update_session_patient(
    db: AsyncSession, 
    session_id: str, 
    patient_id: Optional[int], 
    preview_text: Optional[str] = None
) -> Optional[Session]:
    """Link a session to a patient and/or update title based on content."""
    session = await get_session(db, session_id)
    if not session:
        # If session doesn't exist (e.g. started chat without patient), create it now
        session = await create_session(db, session_id)
    
    # 1. If patient provided, link and set formal title
    if patient_id:
        patient_result = await db.execute(select(Patient).where(Patient.id == patient_id))
        patient = patient_result.scalar_one_or_none()
        
        if patient:
            session.patient_id = patient_id
            session.title = f"Patient #{patient.medical_record_number or patient.id} - {patient.name}"
            session.updated_at = datetime.utcnow()
            await db.flush()
            await db.refresh(session)
            return session

    # 2. If no patient linked yet, try to set a descriptive title from content
    # Only update if title is still the default "New Session" to avoid overwriting custom renames (future proof)
    if preview_text and session.title == "New Session":
        # Truncate to reasonable length
        clean_preview = preview_text.strip().split('\n')[0][:40]
        if len(preview_text) > 40:
            clean_preview += "..."
            
        session.title = clean_preview
        session.updated_at = datetime.utcnow()
        await db.flush()
        await db.refresh(session)
        
    return session


async def list_recent_sessions(db: AsyncSession, limit: int = 20) -> List[Session]:
    """List recent sessions for sidebar."""
    result = await db.execute(
        select(Session)
        .order_by(desc(Session.updated_at))
        .limit(limit)
        .options(
            selectinload(Session.patient).selectinload(Patient.allergies),
            selectinload(Session.patient).selectinload(Patient.drug_history),
            selectinload(Session.patient).selectinload(Patient.adverse_reactions)
        )
    )
    return list(result.scalars().all())
