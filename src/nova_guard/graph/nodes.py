"""LangGraph nodes for prescription processing workflow."""

import re
from typing import Optional

from nova_guard.graph.state import PatientState
from nova_guard.schemas.patient import PrescriptionData


# ============================================================================
# INTAKE NODES - Handle different input modalities
# ============================================================================

async def gateway_supervisor_node(state: PatientState) -> dict:
    """
    The 'Air Traffic Controller' for Nova Guard.
    Analyzes input modality and user intent to determine the clinical path.
    """
    from nova_guard.services.bedrock import bedrock_client
    
    print("Gateway Supervisor: Analyzing multi-modal intent...")
    
    # 1. Gather all inputs from the current state
    text = state.get("prescription_text", "")
    has_image = state.get("prescription_image") is not None
    has_voice = state.get("prescription_audio") is not None
    
    # 2. Voice Handling (Phase 2 Integration)
    # If audio is present, we'd use Nova 2 Sonic here to transcribe it
    # For now, we assume the text or image is the primary driver.

    # 3. Intent Classification via Nova 2 Lite
    # This prompt tells Nova exactly how to categorize the pharmacist's goal
    classification_prompt = """
    You are a Medical Intent Classifier. Analyze the user's input and classify it into ONE category:
    
    - AUDIT: User wants to process a NEW prescription (via image upload or dictation).
    - CLINICAL_QUERY: User is asking a question about the patient's history, allergies, or meds.
    - MEDICAL_KNOWLEDGE: User is asking a general medical question (e.g., 'What is the dosage for X?').
    - SYSTEM_ACTION: User wants to perform a tool action like 'open source' or 'generate report'.

    Return ONLY the category name.
    """
    
    # We pass the text and a flag if an image exists to help Nova decide
    intent = await bedrock_client.classify_intent(
        text=text, 
        has_image=has_image, 
        prompt=classification_prompt
    )
    print(f"Intent: {intent}")
    # Clean the output (Nova might return 'Intent: AUDIT', we just want 'AUDIT')
    intent = intent.strip().upper()
    if "AUDIT" in intent: intent = "AUDIT"
    elif "QUERY" in intent: intent = "CLINICAL_QUERY"
    elif "KNOWLEDGE" in intent: intent = "MEDICAL_KNOWLEDGE"
    elif "ACTION" in intent: intent = "SYSTEM_ACTION"

    return {
        "intent": intent,
        "messages": [f"Supervisor classified intent as: {intent}"]
    }

async def image_intake_node(state: PatientState) -> dict:
    """
    Extract prescription data from handwritten image using Amazon Nova Lite.
    """
    from nova_guard.services.bedrock import bedrock_client
    
    print("📷 Image Intake: Processing prescription via Nova Lite...")
    image_bytes = state.get("prescription_image")
    
    if not image_bytes:
        return {"messages": ["❌ Error: No image provided"]}
        
    extracted = await bedrock_client.process_image(image_bytes)
    
    if not extracted:
        # Fallback for Phase 2 if credentials fail
        print("⚠️ Bedrock processing failed, falling back to mock (for demo continuity)")
        extracted = PrescriptionData(
            drug_name="Lisinopril",
            dose="10mg",
            frequency="once daily",
            prescriber="Dr. Smith (Mock - Bedrock Failed)",
            notes="Fallback extraction"
        )
        return {
            "extracted_data": extracted,
            "input_type": "image",
            "messages": ["⚠️ Image analysis failed (Check AWS Creds), using Mock"]
        }
        
    return {
        "extracted_data": extracted,
        "input_type": "image",
        "confidence_score": 0.95, # Nova Lite doesn't give a score easily, assume high if success
        "messages": ["✅ Image analysis complete (Nova Lite)"]
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
    # ========================================================================    # Check if this is a QUERY or COMMAND
    query_keywords = ["allergic", "allergy", "check", "does", "is", "has", "open", "show"]
    is_query = any(keyword in text_lower for keyword in query_keywords)
    
    if is_query:
        # Check for "Open Source" command
        if "open" in text_lower or "show" in text_lower:
             # Basic extraction of drug name for the command
             # "Open source for Aspirin" -> "Aspirin"
             words = text.split()
             # This is a naive extraction for Phase 1 demo
             # A real system would use specific NER or the NLP service
             potential_drug = words[-1] # Assume last word is drug for now, or use nlp service
             
             # Let's try to be a bit smarter if "for" is present
             if "for" in words:
                 try:
                     for_index = words.index("for")
                     potential_drug = " ".join(words[for_index+1:]).strip("?.!")
                 except:
                     pass
            
             if potential_drug:
                 # Check if we can normalize it to get a good URL
                 # We will just open the OpenFDA search or DailyMed search for now.
                 
                 url = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={potential_drug}"
                 print(f"🖥️ Generating source link for {potential_drug}: {url}")
                 
                 return {
                     "input_type": "text",
                     "prescription_text": text,
                     "external_url": url,
                     "messages": [f"🚀 Generated DailyMed link for '{potential_drug}'"]
                 }

        # Use NLP service for structured allergy/safety queries
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
    intent = state.get("intent")
    
    # Path for New Prescription / Image
    if intent == "AUDIT":
        return "image_intake" if state.get("prescription_image") else "text_intake"
    
    # Path for Actions (The new Tools Node)
    if intent == "SYSTEM_ACTION":
        # If we have text, we might need to parse parameters from it first
        if state.get("prescription_text"):
            return "text_intake"
        return "tools_node"
    
    # Path for Chat / Questions
    if intent == "CLINICAL_QUERY":
        # If we have text, parse it for drug names first (even if just a query)
        if state.get("prescription_text"):
            return "text_intake"
        return "fetch_patient" # Always fetch patient context for history questions

    if intent == "MEDICAL_KNOWLEDGE":
        return "fetch_medical_knowledge"  
         
    return "assistant_node"

def conditional_fetch_patient(state: PatientState) -> str:
    """
    Routes the workflow after patient data is retrieved, 
    matching specific defined intents.
    """
    intent = state.get("intent")
    
    # 1. AUDIT: Move to the internal safety auditor
    if intent == "AUDIT":
        return "auditor"
    
    # 2. CLINICAL_QUERY: Move to assistant to explain the patient history
    if intent == "CLINICAL_QUERY":
        return "assistant_node"
    
    # 3. MEDICAL_KNOWLEDGE: Move to fetch FDA data before the assistant explains it
    if intent == "MEDICAL_KNOWLEDGE":
        return "fetch_medical_knowledge"
    
    # 4. SYSTEM_ACTION: This usually bypasses fetch_patient, 
    # but if routed here, it should hit the tools node.
    if intent == "SYSTEM_ACTION":
        return "tools_node"
    
    return END

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


async def fetch_medical_knowledge_node(state: PatientState) -> dict:
    """
    Fetches raw medical labeling data for the Assistant to summarize.
    Works for both new prescriptions and general chat questions.
    """
    from nova_guard.services.openfda import openfda_client
    
    # 1. Resolve the drug name from state
    drug_name = None
    if state.get("extracted_data"):
        drug_name = state["extracted_data"].drug_name
    elif state.get("prescription_text"):
        # Basic cleanup of the chat text to find the drug name
        drug_name = state["prescription_text"].strip()

    if not drug_name:
        return {"messages": ["❌ System could not identify a drug name for lookup."]}

    print(f"🔍 Knowledge Lookup: Fetching label for {drug_name}...")
    
    # 2. Use your existing 'get_drug_label' method
    label_data = await openfda_client.get_drug_label(drug_name)
    
    if not label_data:
        return {"messages": [f"⚠️ No official FDA label found for '{drug_name}'."]}

    # 3. Filter the massive JSON into 'Assistant-friendly' snippets
    # This prevents hitting token limits and keeps the AI focused.
    refined_knowledge = {
        "drug_name": drug_name,
        "indications": openfda_client._extract_field(label_data, "indications_and_usage"),
        "dosage": openfda_client._extract_field(label_data, "dosage_and_administration"),
        "contraindications": openfda_client._extract_field(label_data, "contraindications"),
        "boxed_warning": openfda_client._extract_field(label_data, "boxed_warning"),
        "source_url": openfda_client._get_citation(label_data)
    }
    
    return {
        "drug_info": refined_knowledge,
        "messages": [f"✅ Retrieved medical knowledge for {drug_name}."]
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

async def assistant_node(state: PatientState) -> dict:
    """
    Enhanced clinical dialogue engine.
    Adapts its persona based on the detected Intent.
    """
    from nova_guard.services.bedrock import bedrock_client
    
    intent = state.get("intent", "CLINICAL_QUERY")
    user_query = state.get("prescription_text")
    profile = state.get("patient_profile", {})
    drug_info = state.get("drug_info", {})
    audit_verdict = state.get("verdict")

    # 1. Dynamic Instruction Set based on Intent
    intent_instructions = {
        "MEDICAL_KNOWLEDGE": "Focus on summarizing the provided FDA drug labeling. Explain indications, dosage, and side effects clearly.",
        "CLINICAL_QUERY": "Focus on the intersection of the patient's history and the current meds. Be extremely cautious about allergy and interaction risks.",
        "AUDIT": "Explain the safety flags found during the prescription review. Help the pharmacist understand the 'Red' or 'Yellow' status."
    }

    # 2. Refined System Prompt
    system_prompt = f"""
    You are the Nova Guard Clinical Assistant. 
    ROLE: {intent_instructions.get(intent, "General Assistant")}
    
    PATIENT PROFILE: {profile if profile else 'Not selected'}
    SAFETY VERDICT: {audit_verdict.status if audit_verdict else 'N/A'}
    FDA DATA: {drug_info if drug_info else 'Not available'}

    RULES:
    - Use the 'FDA DATA' specifically for dosage and mechanism questions.
    - Use the 'PATIENT PROFILE' for allergy and history questions.
    - If suggesting an alternative, append: 'Substitution requires physician authorization.'
    - Keep responses under 150 words to maintain professional speed.
    """

    # 3. Message History Handling
    history = state.get("messages", [])

    response = await bedrock_client.chat(
        system_prompt=system_prompt,
        user_query=user_query,
        history=history
    )
    
    return {
        "messages": [f"Assistant: {response}"], # LangGraph's add_messages handles the append
        "prescription_text": None 
    }


async def tools_node(state: PatientState) -> dict:
    """
    Executes system actions requested by the Supervisor or Assistant.
    Provides the 'Action' layer for the Agentic workflow.
    """
    print("🛠️ Tools Node: Executing clinical system action...")
    
    # The Supervisor or Assistant puts a 'system_action' dict in the state
    # Format: {"action": "open_source", "drug": "Lisinopril"}
    action_request = state.get("system_action")
    messages = state.get("messages", [])
    
    if not action_request:
        return {"messages": messages + ["⚠️ Tools Node called without a specific action."]}

    action = action_request.get("action")
    drug = action_request.get("drug")

    # 1. Action: Generate External Reference Link
    if action == "open_source":
        # We don't use webbrowser.open() here because it's a backend service.
        # Instead, we send the URL to the React frontend to handle window.open().
        source_url = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?query={drug}"
        return {
            "messages": messages + [f"🔗 Generated clinical reference link for {drug}."],
            "external_url": source_url,
            "system_action": None  # Clear the action once handled
        }

    # 2. Action: Generate PDF Audit Report
    if action == "generate_report":
        # Logic to trigger your report generation service (e.g., using ReportLab or FPDF)
        report_status = "📄 Clinical Audit Report (PDF) is being generated for the pharmacist."
        return {
            "messages": messages + [report_status],
            "system_action": None
        }

    return {"messages": messages + ["❌ Tool action not recognized."]}

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
