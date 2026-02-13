"""LangGraph nodes for prescription processing workflow."""

import re
from typing import Optional

from nova_guard.graph.state import PatientState
from nova_guard.schemas.patient import PrescriptionData
from langchain_core.messages import AIMessage



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
        CLINICAL_QUERY - question about this specific patient based on mrn number or name 
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
        # "messages": [f"Intent classified as **{clean_intent}**"]
    }

async def image_intake_node(state: PatientState) -> dict:
    """
    Extract prescription data from handwritten image using Amazon Nova Lite.
    """
    from nova_guard.services.bedrock import bedrock_client
    
    print("📷 Image Intake: Processing prescription via Nova Lite...")
    image_bytes = state.get("prescription_image")
    
    if not image_bytes:
        print("❌ Error: No image provided")
        return {}
        
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
            # "messages": ["⚠️ Image analysis failed (Check AWS Creds), using Mock"]
        }
        
    return {
        "extracted_data": extracted,
        "input_type": "image",
        "confidence_score": 0.95, # Nova Lite doesn't give a score easily, assume high if success
        # "messages": ["✅ Image analysis complete (Nova Lite)"]
    }

async def text_intake_node(state: PatientState) -> dict:
    print("⌨️ Text intake node")

    text = state.get("prescription_text", "").strip()
    if not text:
        return {"extracted_data": None}

    text_lower = text.lower()

    # ─── Special commands first ────────────────────────────────────────
    if any(w in text_lower for w in ["open source", "show source", "source for"]):
        # naive last-drug heuristic → can be improved later with LLM
        words = text.split()
        drug_candidates = [w for w in words[-4:] if w.istitle() or w.isalpha()]
        if drug_candidates:
            drug = drug_candidates[-1].rstrip(".,!?")
            # url = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={drug}"
            return {
                # "external_url": url, (Let tools_node handle this)
                # "messages": [f"🔗 DailyMed link generated for **{drug}**"],
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
                # "messages": [f"🔍 Clinical query detected — drug: **{drug}**"]
            }

    # ─── Robust LLM Prescription Parsing ────────────────────────────────
    # Regex is too brittle for conversational input like "he got this prescription..."
    # We use LLM to extract structured data.
    from nova_guard.services.bedrock import bedrock_client
    import json
    from nova_guard.schemas.patient import PrescriptionData
    
    extraction_prompt = """\
    You are a pharmacy intake assistant. Extract ALL prescription details from the text.
    Handle multiple drugs if present (e.g. "Lisinopril 10mg and Valsartan 80mg").
    
    Return a valid JSON object with a "prescriptions" key containing a list of objects:
    {
        "prescriptions": [
            {
                "drug_name": "Generic Name",
                "dose": "10mg",
                "frequency": "daily",
                "notes": "indication or other details"
            },
            ...
        ]
    }
    
    Conversational text:
    "{text}"
    
    JSON:
    """
    
    try:
        extracted_json_str = await bedrock_client.extract_entity(
            text=text,
            prompt=extraction_prompt
        )
        # Attempt to clean code blocks if present (Bedrock sometimes adds ```json ... ```)
        cleaned_json = extracted_json_str.replace("```json", "").replace("```", "").strip()
        data = json.loads(cleaned_json)
        
        prescriptions_list = []
        if "prescriptions" in data and isinstance(data["prescriptions"], list):
            for item in data["prescriptions"]:
                if item.get("drug_name") and item["drug_name"].lower() != "none":
                    prescriptions_list.append(PrescriptionData(
                        drug_name=item["drug_name"],
                        dose=item.get("dose") or "Unknown",
                        frequency=item.get("frequency") or "Unknown",
                        notes=item.get("notes") or "LLM extracted"
                    ))
        
        # Fallback for single object return (if LLM ignores list instruction)
        elif data.get("drug_name"):
             prescriptions_list.append(PrescriptionData(
                drug_name=data["drug_name"],
                dose=data.get("dose") or "Unknown",
                frequency=data.get("frequency") or "Unknown",
                notes=data.get("notes") or "LLM extracted"
            ))

        if prescriptions_list:
            # Populate both new list and robust backward compatibility
            return {
                "prescriptions": prescriptions_list,
                "extracted_data": prescriptions_list[0], # Backward compat
                "confidence_score": 0.90,
                # "messages": [f"Prescription extracted: {len(prescriptions_list)} drugs found ({', '.join(p.drug_name for p in prescriptions_list)})"]
            }

    except Exception as e:
        print(f"LLM extraction failed: {e}")
    
    # Ultimate fallback if LLM fails
    return {
        "prescriptions": [],
        "extracted_data": None,
        "confidence_score": 0.40,
        # "messages": ["Could not extract prescription details. Please rephrase."]
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
        # "messages": [f"✅ Transcribed from voice: {extracted.drug_name} {extracted.dose}"]
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
        return "fetch_patient"
         

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
    
    # Fallback to assistant (e.g. for general chat or unknown intent)
    # instead of END, which would be silent.
    return "assistant_node"

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
                # "messages": [f"❌ Patient ID {state['patient_id']} not found"]
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
            # "messages": [f"✅ Loaded profile for {patient.name} (Age: {patient.age_years})"]
        }


async def fetch_medical_knowledge_node(state: PatientState) -> dict:
    from nova_guard.services.openfda import openfda_client
    from nova_guard.services.bedrock import bedrock_client

    prescriptions = state.get("prescriptions", [])

    # Direct search with valyu
    query = state.get("prescription_text") or ""
    bio_research = query and await bedrock_client.research(query) 
    print("Valyu Response", bio_research)
    
    # Fallback: if no prescriptions parsed yet (e.g. direct Clinical Query), extract them now
    if not prescriptions:
        txt = state.get("prescription_text") or ""
        if txt:
            # Re-use the multi-drug extraction logic or a simplified version
            
            import json
            try:
                extraction_prompt = "Extract ALL generic drug names from this text as a JSON list of strings: {\"drugs\": [\"...\", \"...\"]}. Text: " + txt
                extracted = await bedrock_client.extract_entity(text=txt, prompt=extraction_prompt)
                data = json.loads(extracted.replace("```json", "").replace("```", "").strip())
                for d in data.get("drugs", []):
                    prescriptions.append(PrescriptionData(drug_name=d, dose="", frequency=""))
            except Exception:
                pass

    if not prescriptions:
         # return {"messages": ["⚠️ No identifiable drugs for knowledge lookup"]}
         return {}

    print(f"📖 Fetching FDA labels for: {[p.drug_name for p in prescriptions]}")

    drug_info_map = {}
    
    for prescription in prescriptions:
        drug_name = prescription.drug_name
        label = await openfda_client.get_drug_label(drug_name)
       
        if not label:
            continue

        refined = {
            "drug_name": drug_name,
            "indications": openfda_client._extract_field(label, "indications_and_usage") or "—",
            "dosage": openfda_client._extract_field(label, "dosage_and_administration") or "—",
            "contraindications": openfda_client._extract_field(label, "contraindications") or "—",
            "boxed_warning": openfda_client._extract_field(label, "boxed_warning") or "None",
            "warnings": openfda_client._extract_field(label, "warnings") or "—",
            "interactions": openfda_client._extract_field(label, "drug_interactions") or "—",
            "source_url": openfda_client._get_citation(label) or "—",
        }
        refined["research_report"] = bio_research
        drug_info_map[drug_name] = refined

    # Backward compatibility for single-drug nodes (if any)
    first_drug_info = list(drug_info_map.values())[0] if drug_info_map else None

    return {
        "drug_info_map": drug_info_map,
        "drug_info": first_drug_info, # Backward compat
        "research_report": bio_research,
        # Ensure prescriptions is updated in state if we acted as fallback
        "prescriptions": prescriptions 
    }

def auditor_node(state: PatientState) -> dict:
    from nova_guard.schemas.patient import SafetyFlag

    flags = []
    prescriptions = state.get("prescriptions", [])
    profile = state.get("patient_profile", {})

    if not prescriptions or not profile:
        return {"safety_flags": flags}

    current_drugs = [d["drug_name"].lower() for d in profile.get("current_drugs", [])]
    
    # Check each new prescription
    for i, rx in enumerate(prescriptions):
        drug_name = rx.drug_name.lower()
        
        # 1. Prior Adverse Reaction Check
        for reaction in profile.get("adverse_reactions", []):
            if drug_name in reaction.get("drug_name", "").lower():
                flags.append(SafetyFlag(
                    severity="warning",
                    category="prior_adverse_reaction",
                    message=f"Prior {reaction['severity']} reaction to {reaction['drug_name']}: {reaction['symptoms']}",
                    source="Patient history"
                ))

        # 2. Duplicate Therapy (vs Current Meds)
        if drug_name in current_drugs:
            flags.append(SafetyFlag(
                severity="warning",
                category="therapeutic_duplication",
                message=f"Patient already taking **{rx.drug_name}**",
                source="Current medication list"
            ))
            
        # 3. Duplicate Therapy (vs Other New Prescriptions)
        for j, other_rx in enumerate(prescriptions):
            if i != j and drug_name == other_rx.drug_name.lower():
                # Avoid duplicate flags for the same pair (only flag once)
                if i < j: 
                    flags.append(SafetyFlag(
                        severity="warning",
                        category="duplicate_therapy",
                        message=f"Duplicate prescription in current request: **{rx.drug_name}** appears multiple times.",
                        source="Current Request"
                    ))

    return {
        "safety_flags": flags,
        # "messages": [f"Audit (history): {len(flags)} flag(s) found"]
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
            f"Answer strictly using provided FDA reference data and bio-research data: {state['research_report']}. "
            "If multiple drugs are involved, structure the answer clearly for EACH drug. "
            "Include: mechanism of action, approved indications, "
            "standard dosing & key adjustments (renal/hepatic/elderly), "
            "black box warnings (quote if present), major contraindications, "
            "serious warnings, clinically important interactions, "
            "pregnancy/lactation risks. Use precise, professional language."
        ),
        "CLINICAL_QUERY": (
            "Act as high-reliability patient-safety clinical decision support. "
            "Cross-reference ALL extracted drugs against allergies / ADRs / comorbidities / organ function / "
            "age / pregnancy status. "
            "Clearly highlight: allergy/cross-reactivity risk, serious DDIs (Drug-Drug Interactions), "
            "duplicate therapy, required dose adjustments, critical monitoring. "
            "Use cautious, factual, non-alarmist tone."
        ),
        "AUDIT": (
            "Explain automated prescription safety audit results to pharmacist. "
            "Structure answer:\n"
            "1. Overall verdict (Red/Yellow/Green)\n"
            "2. Triggered Rules/Flags (Grouped by Drug if applicable)\n"
            "3. Drug-Drug Interactions (if any)\n"
            "4. Clinical rationale & severity for each finding\n"
            "5. Primary patient safety implication\n"
            "6. Recommended pharmacist actions"
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
            return json.dumps(obj, indent=2, ensure_ascii=False, default=str)
        except:
            return str(obj)[:800] + "…" if len(str(obj)) > 800 else str(obj)

    patient_profile_str = safe_json(state.get("patient_profile"), "No patient profile selected")
    verdict_str = safe_json(state.get("verdict"), "No verdict available")
    
    # Use drug_info_map for multi-drug context
    drug_info_map = state.get("drug_info_map")
    # Fallback to single drug info if map is missing (backward compat)
    if not drug_info_map and state.get("drug_info"):
        drug_info_map = {"Primary Drug": state.get("drug_info")}
        
    fda_data_str = safe_json(drug_info_map, "No FDA data available")

    # Pass the structured prescriptions list
    prescriptions = state.get("prescriptions", [])
    # Fallback to single extracted data
    if not prescriptions and state.get("extracted_data"):
        prescriptions = [state.get("extracted_data")]
        
    prescriptions_str = safe_json(prescriptions, "No structured prescription data found")

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
        
        EXTRACTED PRESCRIPTIONS
        {prescriptions_str}

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
        • CHECK FOR DRUG-DRUG INTERACTIONS between all prescribed drugs (using generic names from FDA data)
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
        response_text = await bedrock_client.chat(
            system_prompt=system_prompt,
            user_query=current_input,
            history=history,
        )
        response = AIMessage(content=response_text)
    except Exception as exc:
        error_preview = str(exc)[:140].replace("\n", " ")
        response = AIMessage(content=(
             "**System Notice**\n\n"
             f"Temporary issue contacting clinical reasoning engine ({error_preview}).\n"
             "Please try again in a moment or rephrase."
        ))

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
        return {"messages": messages + [AIMessage(content="⚠️ Tools Node called without a specific action.")]}

    action = action_request.get("action")
    drug = action_request.get("drug")

    # 1. Action: Generate External Reference Link
    if action == "open_source":
        # We don't use webbrowser.open() here because it's a backend service.
        # Instead, we send the URL to the React frontend to handle window.open().
        source_url = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?query={drug}"
        return {
            "messages": messages + [AIMessage(content=f"🔗 Generated clinical reference link for {drug}.")],
            "external_url": source_url,
            "system_action": None  # Clear the action once handled
        }

    # 2. Action: Generate PDF Audit Report
    if action == "generate_report":
        # Logic to trigger your report generation service (e.g., using ReportLab or FPDF)
        report_status = "📄 Clinical Audit Report (PDF) is being generated for the pharmacist."
        return {
            "messages": messages + [AIMessage(content=report_status)],
            "system_action": None
        }

    # return {"messages": messages + [AIMessage(content="⚠️ Tool action failed to trigger a response.")]}

async def openfda_node(state: PatientState) -> dict:
    """
    Run comprehensive safety checks via OpenFDA for ALL prescriptions.
    """
    from nova_guard.services.openfda import openfda_client
    
    print("💊 Running OpenFDA safety checks...")
    
    prescriptions = state.get("prescriptions", [])
    profile = state.get("patient_profile")
    
    if not prescriptions or not profile:
        return {
            "safety_flags": [],
            # "messages": ["⚠️ Skipping OpenFDA checks: Missing data"]
        }
    
    all_new_flags = []
    
    # Run checks for EACH drug
    for rx in prescriptions:
        flags = await openfda_client.run_all_checks(
            drug_name=rx.drug_name,
            patient_profile=profile
        )
        all_new_flags.extend(flags)
    
    # Combine with existing flags (from auditor node)
    existing_flags = state.get("safety_flags", [])
    combined_flags = existing_flags + all_new_flags
    
    return {
        "safety_flags": combined_flags,
        # "messages": [f"✅ OpenFDA checks complete: Found {len(all_new_flags)} new flag(s) across {len(prescriptions)} drugs"]
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
        # "messages": [f"Verdict: **{status.upper()}** — {msg}"]
    }