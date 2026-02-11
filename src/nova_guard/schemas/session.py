from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from nova_guard.schemas.patient import PatientResponse

class SessionBase(BaseModel):
    id: str
    title: Optional[str] = "New Session"
    created_at: datetime
    updated_at: datetime

class SessionResponse(SessionBase):
    patient_id: Optional[int]
    patient: Optional[PatientResponse] = None

    class Config:
        from_attributes = True
