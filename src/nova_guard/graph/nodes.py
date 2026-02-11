"""LangGraph nodes for prescription processing workflow."""

import re
from typing import Optional

from nova_guard.graph.state import PatientState
from nova_guard.schemas.patient import PrescriptionData


# ============================================================================
# INTAKE NODES - Handle different input modalities
# ============================================================================

async def gateway_supervisor_node(state: PatientState) -> dict:
    from nova_guard.services.bedrock import bedrock_client

    print("🌉 Gateway Supervisor: classifying intent...")

    text = state.get("prescription_text", "")
    has_image = state.get("prescription_image") is not None
    has_voice = state.get("prescription_audio") is not None  # currently unused

    classification_prompt = """\
        You are a precise medical intent classifier for a pharmacist decision-support system.

        Classify the input into **exactly one** of these categories:

        AUDIT          - processing a new prescription (image, typed Rx, voice dictation)
        CLINICAL_QUERY - question about this specific patient (allergies, interactions, history…)
        MEDICAL_KNOWLEDGE - general pharmacology / drug information question
        SYSTEM_ACTION  - user requests an action (open source, generate report, etc.)
        GENERAL_CHAT   - greeting, thanks, meta conversation, off-topic

        Rules:
        - Return **only** the category name — nothing else
        - Prefer AUDIT when prescription-like content is present (dose, frequency, sig, etc.)
        - Prefer CLINICAL_QUERY when patient-specific context is mentioned
        """

    raw_intent = await bedrock_client.classify_intent(
        text=text,
        has_image=has_image,
        prompt=classification_prompt
    )

    intent = raw_intent.strip().upper()

    # More robust mapping (handles model hallucinations better)
    intent_map = {
        "AUDIT": "AUDIT",
        "PRESCRIPTION": "AUDIT",
        "NEW RX": "AUDIT",
        "CLINICAL_QUERY": "CLINICAL_QUERY",
        "QUERY": "CLINICAL_QUERY",
        "PATIENT QUESTION": "CLINICAL_QUERY",
        "MEDICAL_KNOWLEDGE": "MEDICAL_KNOWLEDGE",
        "DRUG INFO": "MEDICAL_KNOWLEDGE",
        "SYSTEM_ACTION": "SYSTEM_ACTION",
        "ACTION": "SYSTEM_ACTION",
        "GENERAL_CHAT": "GENERAL_CHAT",
        "CHAT": "GENERAL_CHAT",
    }

    clean_intent = intent_map.get(intent)
    if clean_intent is None:
        clean_intent = "GENERAL_CHAT"  # safest fallback
        print(f"⚠️  Intent fallback → GENERAL_CHAT (raw: {raw_intent})")

    print(f"→ Intent: {clean_intent}")

    return {
        "intent": clean_intent,
        "messages": [f"Intent classified as **{clean_intent}**"]
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

async def text_intake_node(state: PatientState) -> dict:
    print("⌨️ Text intake node")

    text = state.get("prescription_text", "").strip()
    if not text:
        return {"messages": ["No input text received"], "extracted_data": None}

    text_lower = text.lower()

    # ─── Special commands first ────────────────────────────────────────
    if any(w in text_lower for w in ["open source", "show source", "source for"]):
        # naive last-drug heuristic → can be improved later with LLM
        words = text.split()
        drug_candidates = [w for w in words[-4:] if w.istitle() or w.isalpha()]
        if drug_candidates:
            drug = drug_candidates[-1].rstrip(".,!?")
            url = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={drug}"
            return {
                "external_url": url,
                "messages": [f"🔗 DailyMed link generated for **{drug}**"],
                "system_action": {"action": "open_source", "drug": drug}
            }

    # ─── Query detection ────────────────────────────────────────────────
    query_indicators = [
        "allergic", "allergy", "allergies", "reaction", "interact", "safe", "contraindicat",
        "check", "does the patient", "is the patient", "can we give", "should we"
    ]

    is_likely_query = any(ind in text_lower for ind in query_indicators)

    if is_likely_query:
        # Very simple drug name extraction — improve later
        from nova_guard.services.bedrock import bedrock_client

        drug = await bedrock_client.extract_entity(
            text=text,
            prompt="Extract only the most likely generic drug name mentioned in this pharmacist question. Return only the name or 'NONE'."
        )
        drug = drug.strip().upper()
        if drug == "NONE":
            drug = None

        if drug:
            return {
                "extracted_data": PrescriptionData(
                    drug_name=drug,
                    dose="N/A",
                    frequency="N/A",
                    notes="Safety / clinical query"
                ),
                "confidence_score": 0.85,
                "messages": [f"🔍 Clinical query detected — drug: **{drug}**"]
            }

    # ─── Classic prescription parsing fallback ──────────────────────────
    # Keep your existing regex, but make it optional groups
    pattern = r"(?P<drug>[A-Za-z][\w\-/ ]{2,})\s+(?P<dose>[\d.]+(?:\s*(?:mg|mcg|mg/ml|g|IU|%))?)?.*?(?P<freq>(?:once|twice|three times)?\s*(?:daily|every\s*\w+|q\w+d?))?.*$"
    m = re.search(pattern, text, re.I)

    if m and m.group("drug"):
        drug = m.group("drug").strip()
        dose = (m.group("dose") or "unknown").strip()
        freq = (m.group("freq") or "unknown").strip()

        return {
            "extracted_data": PrescriptionData(
                drug_name=drug,
                dose=dose,
                frequency=freq,
                notes="Basic text parse"
            ),
            "confidence_score": 0.75 if dose != "unknown" else 0.55,
            "messages": [f"Prescription parse: **{drug}** {dose} {freq}"]
        }

    # ultimate fallback
    return {
        "extracted_data": None,
        "confidence_score": 0.40,
        "messages": ["Treating input as general clinical question"]
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
        print("No text provided, fetching tools")
        return "tools_node"
    
    # Path for Chat / Questions
    if intent == "CLINICAL_QUERY":
        # If we have text, parse it for drug names first (even if just a query)
        if state.get("prescription_text"):
            return "text_intake"
        print("No text provided, fetching patient")
        return "fetch_patient" # Always fetch patient context for history questions

    if intent == "MEDICAL_KNOWLEDGE":
        return "fetch_medical_knowledge"
        
    if intent == "GENERAL_CHAT":
        print("General chat detected, fetching assistant")
        return "assistant_node"
         
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
    from nova_guard.services.openfda import openfda_client

    drug_name = None

    if ed := state.get("extracted_data"):
        drug_name = ed.drug_name
    elif txt := state.get("prescription_text"):
        from nova_guard.services.bedrock import bedrock_client
        try:
            drug_name = await bedrock_client.extract_entity(
                text=txt,
                prompt="Return only the primary generic drug name mentioned. Return NONE if no drug is found."
            )
            drug_name = drug_name.strip()
            if drug_name.upper() == "NONE":
                drug_name = None
        except:
            pass

    if not drug_name:
        return {"messages": ["⚠️ No identifiable drug name for knowledge lookup"]}

    print(f"📖 Fetching FDA label: {drug_name}")

    label = await openfda_client.get_drug_label(drug_name)

    if not label:
        return {"messages": [f"⚠️ No FDA label data found for **{drug_name}**"]}

    refined = {
        "drug_name": drug_name,
        "indications": openfda_client._extract_field(label, "indications_and_usage") or "—",
        "dosage": openfda_client._extract_field(label, "dosage_and_administration") or "—",
        "contraindications": openfda_client._extract_field(label, "contraindications") or "—",
        "boxed_warning": openfda_client._extract_field(label, "boxed_warning") or "None",
        "source_url": openfda_client._get_citation(label) or "—"
    }

    return {
        "drug_info": refined,
        "messages": [f"FDA data retrieved for **{drug_name}**"]
    }

def auditor_node(state: PatientState) -> dict:
    from nova_guard.schemas.patient import SafetyFlag

    flags = []
    extracted = state.get("extracted_data")
    profile = state.get("patient_profile", {})

    if not extracted or not profile:
        return {"safety_flags": flags}

    drug = extracted.drug_name.lower()

    # Existing adverse reaction check
    for rx in profile.get("adverse_reactions", []):
        if drug in rx.get("drug_name", "").lower():
            flags.append(SafetyFlag(
                severity="warning",
                category="prior_adverse_reaction",
                message=f"Prior {rx['severity']} reaction to {rx['drug_name']}: {rx['symptoms']}",
                source="Patient history"
            ))

    # Simple duplicate therapy check (phase 1 version)
    current_drugs = [d["drug_name"].lower() for d in profile.get("current_drugs", [])]
    if drug in current_drugs:
        flags.append(SafetyFlag(
            severity="warning",
            category="therapeutic_duplication",
            message=f"Patient already taking **{drug.title()}**",
            source="Current medication list"
        ))

    return {
        "safety_flags": flags,
        "messages": [f"Audit (history): {len(flags)} flag(s) found"]
    }

async def assistant_node(state: PatientState) -> dict:
    """
    Clinical dialogue & decision-support engine.
    Adapts behavior strongly based on detected intent.
    """
    from nova_guard.services.bedrock import bedrock_client
    import json

    # ─── 1. Intent fallback & normalization ────────────────────────────────
    intent = (state.get("intent") or "GENERAL_CHAT").strip().upper()

    # ─── 2. Role instructions per intent (short & explicit) ────────────────
    role_map = {
        "MEDICAL_KNOWLEDGE": (
            "Act as evidence-based clinical pharmacist. "
            "Answer strictly using provided FDA reference data only. "
            "Include: mechanism of action, approved indications, "
            "standard dosing & key adjustments (renal/hepatic/elderly), "
            "black box warnings (quote if present), major contraindications, "
            "serious warnings, clinically important interactions, "
            "pregnancy/lactation risks. Use precise, professional language."
        ),
        "CLINICAL_QUERY": (
            "Act as high-reliability patient-safety clinical decision support. "
            "Cross-reference allergies / ADRs / comorbidities / organ function / "
            "age / pregnancy status against proposed medication(s). "
            "Clearly highlight: allergy/cross-reactivity risk, serious DDIs, "
            "duplicate therapy, required dose adjustments, critical monitoring. "
            "Use cautious, factual, non-alarmist tone."
        ),
        "AUDIT": (
            "Explain automated prescription safety audit results to pharmacist. "
            "Structure answer:\n"
            "1. Overall verdict (Red/Yellow/Green)\n"
            "2. Which rules/flags triggered\n"
            "3. Clinical rationale & severity for each\n"
            "4. Primary patient safety implication\n"
            "5. Recommended pharmacist actions"
        ),
        "GENERAL_CHAT": (
            "You are Nova Guard — friendly, professional hospital pharmacist colleague. "
            "Be helpful and concise. May engage in light context-appropriate small talk. "
            "Always remain clinically focused. Never give direct patient advice."
            "If you do not know the answer to a question, you must say so"
        )
    }

    role_description = role_map.get(intent, role_map["GENERAL_CHAT"])

    # ─── 3. Safe context string preparation ────────────────────────────────
    def safe_json(obj, fallback="—"):
        if obj is None:
            return fallback
        try:
            return json.dumps(obj, indent=2, ensure_ascii=False)
        except:
            return str(obj)[:800] + "…" if len(str(obj)) > 800 else str(obj)

    patient_profile_str = safe_json(state.get("patient_profile"), "No patient profile selected")
    verdict_str = (
        state["verdict"].status
        if state.get("verdict") and hasattr(state["verdict"], "status")
        else state["verdict"].get("status", "N/A")
        if isinstance(state.get("verdict"), dict)
        else "N/A"
    )
    fda_data_str = safe_json(state.get("drug_info"), "No FDA data available")

    current_input = (state.get("prescription_text") or "").strip()
    if not current_input:
        current_input = "(no new user message — continuing context)"

    # ─── 4. Modern, stricter system prompt ─────────────────────────────────
    system_prompt = f"""\
        You are **Nova Guard** — advanced clinical pharmacist decision support assistant.

        ROLE & TONE:
        {role_description}

        CURRENT CONTEXT:
        ──────────────────────────────
        PATIENT PROFILE
        {patient_profile_str}

        SAFETY AUDIT VERDICT
        {verdict_str}

        FDA REFERENCE DATA (pharmacology / dosing / mechanism / indications ONLY)
        {fda_data_str}

        CURRENT QUESTION / INPUT
        ──────────────────────────────
        {current_input}
        ──────────────────────────────

        MANDATORY RULES — YOU MUST FOLLOW ALL:
        • Pharmacology/dosing/indication/warning answers MUST come from FDA REFERENCE DATA only
        • ALWAYS cross-check PATIENT PROFILE for allergies, serious ADRs, relevant organ function
        • Be extremely cautious regarding: anaphylaxis risk, cross-reactivity, QT prolongation, serotonin syndrome, major CYP/DDI risks
        • Use professional, precise, pharmacist-to-pharmacist language
        • Format EVERY answer using clean Markdown: headings, bullets, **bold critical warnings**, tables when comparing
        • If Red/Yellow flags exist — mention them EARLY and clearly (never bury safety info)
        • When data is missing/insufficient → clearly state: "Information not available in current context"
        • NEVER give direct patient-facing advice — always frame as recommendation for the reviewing pharmacist
        • Answer only the current question — do not add unsolicited information
        • Think step-by-step before answering safety-sensitive questions

        Reply professionally, clearly and helpfully.
        """

    # ─── 5. History & LLM call ─────────────────────────────────────────────
    history = state.get("messages", []) or []

    try:
        response = await bedrock_client.chat(
            system_prompt=system_prompt,
            user_query=current_input,
            history=history,
        )
    except Exception as exc:
        error_preview = str(exc)[:140].replace("\n", " ")
        response = {
            "role": "assistant",
            "content": (
                "**System Notice**\n\n"
                f"Temporary issue contacting clinical reasoning engine ({error_preview}).\n"
                "Please try again in a moment or rephrase."
            )
        }

    return {
        "messages": [response],
        "prescription_text": None,          # clear current input
        # Optional debug helper (uncomment during development)
        # "last_assistant_prompt": system_prompt,
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
    from nova_guard.schemas.patient import SafetyVerdict

    flags = state.get("safety_flags", [])

    critical = any(f.severity == "critical" for f in flags)
    warning  = any(f.severity == "warning"  for f in flags)

    if critical:
        status = "red"
        msg = "DO NOT DISPENSE — critical safety issue(s)"
    elif warning:
        status = "yellow"
        msg = "Proceed with caution — review warning(s)"
    else:
        status = "green"
        msg = "No major safety concerns detected"

    verdict = SafetyVerdict(
        status=status,
        flags=flags,
        recommendation=msg,
        confidence_score=state.get("confidence_score", 0.0)
    )

    return {
        "verdict": verdict,
        "messages": [f"Verdict: **{status.upper()}** — {msg}"]
    }