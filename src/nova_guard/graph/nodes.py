"""LangGraph nodes for prescription processing workflow."""

import re
from typing import Optional

from nova_guard.graph.state import PatientState
from nova_guard.schemas.patient import PrescriptionData


# ============================================================================
# INTAKE NODES - Handle different input modalities
# ============================================================================

def image_intake_node(state: PatientState) -> dict:
    """
    Extract prescription data from handwritten image.
    
    Phase 1: Mock implementation (returns dummy data)
    Phase 2: Will use Amazon Nova 2 Lite via Bedrock
    
    In production, this would:
    1. Send image to Nova 2 Lite
    2. Use multimodal reasoning to extract drug, dose, frequency
    3. Return confidence score (0-1)
    """
    print("📷 Image Intake: Processing handwritten prescription...")
    
    # Mock extraction (Phase 1)
    extracted = PrescriptionData(
        drug_name="Lisinopril",
        dose="10mg",
        frequency="once daily",
        prescriber="Dr. Smith",
        notes="Mock extraction from image"
    )
    
    # Mock confidence (in production, Nova 2 Lite provides this)
    confidence = 0.95
    
    return {
        "extracted_data": extracted,
        "confidence_score": confidence,
        "messages": [f"✅ Extracted from image: {extracted.drug_name} {extracted.dose}"]
    }


def text_intake_node(state: PatientState) -> dict:
    """
    Parse typed prescription text OR natural language queries.
    
    Handles two types of input:
    1. Prescription format: "Lisinopril 10mg once daily"
    2. Natural language query: "is patient allergic to paracetamol"
    
    If it's a query (contains "allergic", "allergy", "check"), it will:
    - Extract the drug name
    - Mark it as a safety check query (not a new prescription)
    """
    print("⌨️ Text Intake: Parsing typed input...")
    
    text = state["prescription_text"]
    if not text:
        return {
            "extracted_data": None,
            "confidence_score": 0.0,
            "messages": ["❌ No text provided"]
        }
    
    text_lower = text.lower()
    
    # ========================================================================
    # Check if this is a QUERY (not a prescription)
    # ========================================================================
    query_keywords = ["allergic", "allergy", "check", "does", "is", "has"]
    is_query = any(keyword in text_lower for keyword in query_keywords)
    
    if is_query:
        # Extract drug name from query
        drug_patterns = [
            r"allergic to\s+(\w+)",
            r"allergy to\s+(\w+)",
            r"has\s+(\w+)\s+allergy",
            r"check\s+(\w+)",
        ]
        
        drug_name = None
        for pattern in drug_patterns:
            match = re.search(pattern, text_lower)
            if match:
                drug_name = match.group(1)
                break
        
        if drug_name:
            # This is a safety check query, not a new prescription
            extracted = PrescriptionData(
                drug_name=drug_name,
                dose="N/A",  # Not a prescription
                frequency="N/A",
                notes=f"Safety check query: {text}"
            )
            
            return {
                "extracted_data": extracted,
                "confidence_score": 1.0,
                "messages": [f"🔍 Query detected: Checking {drug_name} safety for patient"]
            }
        else:
            return {
                "extracted_data": None,
                "confidence_score": 0.0,
                "messages": ["❌ Could not extract drug name from query"]
            }
    
    # ========================================================================
    # Otherwise, parse as PRESCRIPTION
    # ========================================================================
    # Pattern: drug_name dose frequency
    pattern = r"(\w+)\s+(\d+(?:\.\d+)?(?:mg|ml|g))\s+(.+)"
    match = re.match(pattern, text, re.IGNORECASE)
    
    if match:
        extracted = PrescriptionData(
            drug_name=match.group(1),
            dose=match.group(2),
            frequency=match.group(3),
            notes="Parsed from text input"
        )
        confidence = 1.0  # Text parsing is deterministic
        
        return {
            "extracted_data": extracted,
            "confidence_score": confidence,
            "messages": [f"✅ Parsed prescription: {extracted.drug_name} {extracted.dose}"]
        }
    else:
        return {
            "extracted_data": None,
            "confidence_score": 0.0,
            "messages": ["❌ Could not parse text. Expected format: 'DrugName Dose Frequency' or a natural language query"]
        }


def voice_intake_node(state: PatientState) -> dict:
    """
    Convert voice to text and extract prescription.
    
    Phase 1: Mock implementation
    Phase 2: Will use Amazon Nova 2 Sonic via Bedrock
    
    In production, this would:
    1. Send audio to Nova 2 Sonic
    2. Get speech-to-text transcription
    3. Parse the transcription
    """
    print("🎤 Voice Intake: Processing voice prescription...")
    
    # Mock extraction (Phase 1)
    extracted = PrescriptionData(
        drug_name="Metformin",
        dose="500mg",
        frequency="twice daily",
        notes="Mock extraction from voice"
    )
    
    confidence = 0.92
    
    return {
        "extracted_data": extracted,
        "confidence_score": confidence,
        "messages": [f"✅ Transcribed from voice: {extracted.drug_name} {extracted.dose}"]
    }


# ============================================================================
# ROUTER NODE - Directs to correct intake node
# ============================================================================

def route_input(state: PatientState) -> str:
    """
    Route to the appropriate intake node based on input_type.
    
    Returns the name of the next node to execute.
    """
    input_type = state["input_type"]
    
    routing = {
        "image": "image_intake",
        "text": "text_intake",
        "voice": "voice_intake"
    }
    
    next_node = routing.get(input_type)
    print(f"🔀 Routing to {next_node} node...")
    
    return next_node


# ============================================================================
# PROCESSING NODES - Fetch patient data and run safety checks
# ============================================================================

async def fetch_patient_node(state: PatientState) -> dict:
    """
    Fetch patient profile from database.
    
    This retrieves:
    - Patient demographics
    - Current medications (drug_history)
    - Allergies
    - Adverse reactions
    """
    from nova_guard.database import AsyncSessionLocal
    from nova_guard.api.patients import get_patient
    
    print(f"🔍 Fetching patient profile for ID: {state['patient_id']}...")
    
    async with AsyncSessionLocal() as db:
        patient = await get_patient(db, state["patient_id"])
        
        if not patient:
            return {
                "patient_profile": None,
                "messages": [f"❌ Patient ID {state['patient_id']} not found"]
            }
        
        # Convert to dict for state
        profile = {
            "id": patient.id,
            "name": patient.name,
            "age_years": patient.age_years,
            "is_pregnant": patient.is_pregnant,
            "is_nursing": patient.is_nursing,
            "egfr": patient.egfr,
            "current_drugs": [
                {"drug_name": d.drug_name, "dose": d.dose, "frequency": d.frequency}
                for d in patient.drug_history if d.is_active
            ],
            "allergies": [
                {"allergen": a.allergen, "type": a.allergy_type, "severity": a.severity}
                for a in patient.allergies
            ],
            "adverse_reactions": [
                {"drug_name": r.drug_name, "symptoms": r.symptoms, "severity": r.severity}
                for r in patient.adverse_reactions
            ]
        }
        
        return {
            "patient_profile": profile,
            "messages": [f"✅ Loaded profile for {patient.name} (Age: {patient.age_years})"]
        }


def auditor_node(state: PatientState) -> dict:
    """
    Cross-reference new prescription against patient history.
    
    This is a preliminary check before OpenFDA:
    - Check if drug is in patient's allergy list
    - Check if patient had adverse reactions to this drug before
    - Check for duplicate medications
    """
    from nova_guard.schemas.patient import SafetyFlag
    
    print("🔬 Auditing prescription against patient history...")
    
    flags = []
    extracted = state["extracted_data"]
    profile = state["patient_profile"]
    
    if not extracted or not profile:
        return {"safety_flags": flags}
    
    drug_name = extracted.drug_name.lower()
    
    # Check allergies
    for allergy in profile.get("allergies", []):
        if drug_name in allergy["allergen"].lower():
            flags.append(SafetyFlag(
                severity="critical",
                category="allergy",
                message=f"Patient is allergic to {allergy['allergen']} ({allergy['severity']})",
                source="Patient History"
            ))
    
    # Check adverse reactions
    for reaction in profile.get("adverse_reactions", []):
        if drug_name in reaction["drug_name"].lower():
            flags.append(SafetyFlag(
                severity="warning",
                category="adverse_reaction",
                message=f"Patient had {reaction['severity']} reaction to {reaction['drug_name']}: {reaction['symptoms']}",
                source="Patient History"
            ))
    
    # Check for duplicates
    for current_drug in profile.get("current_drugs", []):
        if drug_name in current_drug["drug_name"].lower():
            flags.append(SafetyFlag(
                severity="warning",
                category="duplicate_medication",
                message=f"Patient is already taking {current_drug['drug_name']} {current_drug['dose']}",
                source="Patient History"
            ))
    
    return {
        "safety_flags": flags,
        "messages": [f"🔬 Auditor found {len(flags)} flag(s)"]
    }


async def openfda_node(state: PatientState) -> dict:
    """
    Run comprehensive safety checks via OpenFDA.
    
    16+ checks including:
    - Boxed Warnings
    - Contraindications
    - Drug Interactions
    - Pregnancy/Nursing Safety
    - Pediatric/Geriatric Use
    """
    from nova_guard.services.openfda import openfda_client
    
    print("💊 Running OpenFDA safety checks...")
    
    extracted = state.get("extracted_data")
    profile = state.get("patient_profile")
    
    if not extracted or not profile:
        return {
            "safety_flags": [],
            "messages": ["⚠️ Skipping OpenFDA checks: Missing data"]
        }
    
    # Run all checks
    flags = await openfda_client.run_all_checks(
        drug_name=extracted.drug_name,
        patient_profile=profile
    )
    
    # Combine with existing flags (from auditor node)
    existing_flags = state.get("safety_flags", [])
    all_flags = existing_flags + flags
    
    return {
        "safety_flags": all_flags,
        "messages": [f"✅ OpenFDA checks complete: Found {len(flags)} new flag(s)"]
    }


def verdict_node(state: PatientState) -> dict:
    """
    Generate final safety verdict based on all flags.
    
    Verdict levels:
    - GREEN: No safety concerns
    - YELLOW: Minor warnings, proceed with caution
    - RED: Critical issues, do NOT dispense
    """
    from nova_guard.schemas.patient import SafetyVerdict
    
    print("⚖️ Generating safety verdict...")
    
    flags = state.get("safety_flags", [])
    
    # Determine verdict status
    has_critical = any(f.severity == "critical" for f in flags)
    has_warning = any(f.severity == "warning" for f in flags)
    
    if has_critical:
        status = "red"
        recommendation = "DO NOT DISPENSE - Critical safety issues detected"
    elif has_warning:
        status = "yellow"
        recommendation = "PROCEED WITH CAUTION - Review warnings with patient"
    else:
        status = "green"
        recommendation = "SAFE TO DISPENSE - No safety concerns detected"
    
    verdict = SafetyVerdict(
        status=status,
        flags=flags,
        recommendation=recommendation,
        confidence_score=state.get("confidence_score", 0.0)
    )
    
    return {
        "verdict": verdict,
        "messages": [f"⚖️ Verdict: {status.upper()} - {recommendation}"]
    }
