import asyncio
from nova_guard.database import async_session
from nova_guard.api.patients import create_patient, get_patient
from nova_guard.schemas.patient import PatientCreate

async def test():
    async with async_session() as db:
        patient_data = PatientCreate(
            name="Test Patient",
            date_of_birth="1990-01-01",
            medical_record_number="TEST-1234",
            allergies=[{"allergen": "Peanuts", "allergy_type": "food", "severity": "severe"}]
        )
        patient = await create_patient(db, patient_data)
        print("Created patient allergies:", patient.allergies)

if __name__ == "__main__":
    asyncio.run(test())
