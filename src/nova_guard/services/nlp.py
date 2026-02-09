"""Natural language query processing for patient safety checks."""

import re
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from nova_guard.api.patients import get_patient


async def parse_allergy_query(query: str, db: AsyncSession) -> dict:
    """
    Parse natural language allergy queries.
    
    Examples:
    - "is john doe allergic to paracetamol"
    - "check if patient 123 has penicillin allergy"
    - "does jane smith have aspirin allergy"
    
    Returns:
    {
        "patient_found": bool,
        "patient_name": str,
        "drug_name": str,
        "is_allergic": bool,
        "allergy_details": dict or None,
        "answer": str  # Natural language response
    }
    """
    
    query_lower = query.lower()
    
    # Extract patient ID if present (e.g., "id 123", "patient 123", "wi98")
    patient_id = None
    id_patterns = [
        r"id\s+(\d+)",
        r"patient\s+(\d+)",
        r"#(\d+)",
        r"\b(\d+)\b"  # Any standalone number
    ]
    
    for pattern in id_patterns:
        match = re.search(pattern, query_lower)
        if match:
            patient_id = int(match.group(1))
            break
    
    # Extract drug name (words after "allergic to", "allergy to", etc.)
    drug_name = None
    drug_patterns = [
        r"allergic to\s+(\w+)",
        r"allergy to\s+(\w+)",
        r"has\s+(\w+)\s+allergy",
    ]
    
    for pattern in drug_patterns:
        match = re.search(pattern, query_lower)
        if match:
            drug_name = match.group(1)
            break
    
    if not patient_id or not drug_name:
        return {
            "patient_found": False,
            "patient_name": None,
            "drug_name": drug_name,
            "is_allergic": False,
            "allergy_details": None,
            "answer": "❌ Could not parse query. Please include patient ID and drug name."
        }
    
    # Fetch patient
    patient = await get_patient(db, patient_id)
    
    if not patient:
        return {
            "patient_found": False,
            "patient_name": None,
            "drug_name": drug_name,
            "is_allergic": False,
            "allergy_details": None,
            "answer": f"❌ Patient ID {patient_id} not found in database."
        }
    
    # Check allergies
    is_allergic = False
    allergy_details = None
    
    for allergy in patient.allergies:
        if drug_name in allergy.allergen.lower():
            is_allergic = True
            allergy_details = {
                "allergen": allergy.allergen,
                "type": allergy.allergy_type,
                "severity": allergy.severity,
                "symptoms": allergy.symptoms,
            }
            break
    
    # Generate natural language answer
    if is_allergic:
        answer = (
            f"⚠️ YES - {patient.name} (ID: {patient_id}) is allergic to {allergy_details['allergen']}. "
            f"Severity: {allergy_details['severity']}. "
            f"Symptoms: {allergy_details['symptoms'] or 'Not specified'}."
        )
    else:
        answer = (
            f"✅ NO - {patient.name} (ID: {patient_id}) has no recorded allergy to {drug_name}. "
            f"Total allergies on file: {len(patient.allergies)}."
        )
    
    return {
        "patient_found": True,
        "patient_name": patient.name,
        "drug_name": drug_name,
        "is_allergic": is_allergic,
        "allergy_details": allergy_details,
        "answer": answer
    }
