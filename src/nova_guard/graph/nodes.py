"""LangGraph nodes for prescription processing workflow."""

import re
import logging
from typing import Optional

from nova_guard.graph.state import PatientState
from nova_guard.schemas.patient import PrescriptionData
from langchain_core.messages import AIMessage

logger = logging.getLogger(__name__)



# ============================================================================
# INTAKE NODES - Handle different input modalities
# ============================================================================

async def gateway_supervisor_node(state: PatientState) -> dict:
    from nova_guard.services.bedrock import bedrock_client

    logger.info("Gateway Supervisor: classifying intent")

    text = state.get("prescription_text", "")
    has_image = state.get("prescription_image") is not None
    has_voice = state.get("prescription_audio") is not None  # currently unused

    classification_prompt = """\
        You are a precise medical intent classifier for a pharmacist decision-support system.

        Classify the input into **exactly one** of these categories:

        AUDIT          - processing a new prescription (image, or text)
        CLINICAL_QUERY - question about a specific patient based on mrn number or name 
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
        logger.debug("Intent fallback -> GENERAL_CHAT (raw: %s)", raw_intent)

    logger.info("Intent: %s", clean_intent)

    return {
        "intent": clean_intent,
        # "messages": [f"Intent classified as **{clean_intent}**"]
    }

async def image_intake_node(state: PatientState) -> dict:
    """
    Extract prescription data from handwritten image using Amazon Nova Lite.
    """
    from nova_guard.services.bedrock import bedrock_client
    
    logger.info("Image intake: processing prescription via Nova Lite")
    image_bytes = state.get("prescription_image")
    
    if not image_bytes:
        logger.error("No image provided for image intake")
        return {}
        
    extracted = await bedrock_client.process_image(image_bytes)
    
    if not extracted:
        # Safety: Do not fall back to mock data in production/test.
        logger.error("Bedrock image processing failed - returning error state")
        return {
            "extracted_data": None,
            "input_type": "image",
            "messages": [AIMessage(content="⚠️ Image analysis failed or no text found. Please try again or type the prescription manually.")]
        }
        
    return {
        "extracted_data": extracted,
        "input_type": "image",
        # "confidence_score": 0.95, # Nova Lite doesn't give a score easily, assume high if success
        # "messages": ["✅ Image analysis complete (Nova Lite)"]
    }

async def text_intake_node(state: PatientState) -> dict:
    logger.info("Text intake node")

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
                # "confidence_score": 0.85,
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
            prompt=extraction_prompt,
            model=bedrock_client.MODEL_PRO # Use Pro for complex JSON structure
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
                # "messages": [f"Prescription extracted: {len(prescriptions_list)} drugs found ({', '.join(p.drug_name for p in prescriptions_list)})"]
            }

    except Exception as e:
        logger.warning("LLM prescription extraction failed: %s", e)
    
    # Ultimate fallback if LLM fails
    return {
        "prescriptions": [],
        "extracted_data": None,
        # "messages": ["Could not extract prescription details. Please rephrase."]
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
        logger.debug("No text provided, fetching tools")
        return "tools_node"
    
    # Path for Chat / Questions
    if intent == "CLINICAL_QUERY":
        return "fetch_patient"
         

    if intent == "MEDICAL_KNOWLEDGE":
        return "fetch_medical_knowledge"
        
    if intent == "GENERAL_CHAT":
        logger.debug("General chat detected, fetching assistant")
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
    
    logger.info("Fetching patient profile for ID: %s", state['patient_id'])
    
    async with AsyncSessionLocal() as db:
        patient = await get_patient(db, state["patient_id"])
        
        if not patient:
            return {
                "patient_profile": None,
                # "messages": [f"❌ Patient ID {state['patient_id']} not found"]
            }
        
        # Prepare full profile dictionary
        # HIPAA DE-IDENTIFICATION: Replace name with ID to prevent PHI exposure to LLMs
        active_meds = [d for d in patient.drug_history if d.is_active]
        allergies = patient.allergies
        reactions = patient.adverse_reactions
        labs = patient.lab_results
        pgx = patient.genetic_markers

        current_egfr = patient.egfr
        latest_egfr_lab = next((lab for lab in sorted(labs, key=lambda x: x.collected_at, reverse=True) if "egfr" in lab.test_name.lower()), None)
        if latest_egfr_lab:
            current_egfr = latest_egfr_lab.value

        profile = {
            "id": patient.id,
            "name": f"Patient-{patient.id}", # DE-IDENTIFIED
            "age_years": patient.age_years,
            "weight": patient.weight,
            "height": patient.height,
            "is_pregnant": patient.is_pregnant,
            "is_nursing": patient.is_nursing,
            "egfr": current_egfr,
            "medical_record_number": "REDACTED", # DE-IDENTIFIED
            "allergies": [
                {
                    "allergen": a.allergen,
                    "type": a.allergy_type,
                    "severity": a.severity,
                    "symptoms": a.symptoms
                }
                for a in allergies
            ],
            "active_medications": [
                {
                    "drug": med.drug_name,
                    "dose": med.dose,
                    "frequency": med.frequency
                }
                for med in active_meds
            ],
            "drug_history_all": [
                {
                    "drug": med.drug_name,
                    "dose": med.dose,
                    "frequency": med.frequency,
                    "is_active": med.is_active,
                    "start_date": med.start_date.isoformat() if getattr(med, "start_date", None) else None,
                    "end_date": med.end_date.isoformat() if getattr(med, "end_date", None) else None
                }
                for med in patient.drug_history
            ],
            "adverse_reactions": [
                {
                    "drug": r.drug_name,
                    "reaction": r.symptoms,
                    "severity": r.severity
                }
                for r in reactions
            ],
            "lab_results": [
                {
                    "test_name": lab.test_name,
                    "value": lab.value,
                    "unit": lab.unit,
                    "is_abnormal": lab.is_abnormal,
                    "collected_at": lab.collected_at.isoformat() if lab.collected_at else None
                }
                for lab in labs
            ],
            "genetic_markers": [
                {
                    "gene": g.gene,
                    "phenotype": g.phenotype,
                    "tested_at": g.tested_at.isoformat() if g.tested_at else None
                }
                for g in pgx
            ]
        }
        
        return {
            "patient_profile": profile,
            "lab_results": profile.get("lab_results", [])
        }


async def fetch_medical_knowledge_node(state: PatientState) -> dict:
    from nova_guard.services.openfda import openfda_client
    from nova_guard.services.bedrock import bedrock_client

    prescriptions = state.get("prescriptions", [])

    # Clinical research via Nova Pro
    query = state.get("prescription_text") or ""
    bio_research = query and await bedrock_client.research(query)
    logger.info("Clinical research completed (%d chars)", len(bio_research) if bio_research else 0)
    
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
            except Exception as e:
                logger.warning("Drug name extraction fallback failed: %s", e)

    if not prescriptions:
         # return {"messages": ["⚠️ No identifiable drugs for knowledge lookup"]}
         return {}

    logger.info("Fetching FDA labels for: %s", [p.drug_name for p in prescriptions])

    drug_info_map = {}
    
    for prescription in prescriptions:
        drug_name = prescription.drug_name
        
        # 1. Fetch OpenFDA Label (Text Source) - Keep for general sections
        label = await openfda_client.get_drug_label(drug_name)
        
        # 2. Fetch Precision Data (RxNav / DailyMed)
        from nova_guard.services.clinical_services import clinical_service
        rxcui = await clinical_service.get_rxcui(drug_name)
        
        # Interactions (RxNav)
        interaction_text = "No critical interactions found."
        if rxcui:
            # We check interactions against ITSELF? No, usually against other drugs.
            # But here we just want general interaction info? 
            # RxNav Interaction API usually checks PAIRS.
            # To get "All interactions" for a single drug is a different endpoint: /interaction/interaction.json?rxcui=...
            # The current clinical_service.check_interactions takes a LIST of rxcuis.
            # Let's fallback to OpenFDA text for single-drug context, 
            # BUT if we have multiple drugs in context, we could run the batch check.
            pass
            
        # Boxed Warning (DailyMed/OpenFDA JSON)
        boxed_flag = await clinical_service.check_boxed_warning(drug_name, label)
        boxed_text = boxed_flag.message if boxed_flag else "None"

        if not label and not rxcui:
            continue

        refined = {
            "drug_name": drug_name,
            "indications": clinical_service.get_label_field(label or {}, "indications_and_usage"),
            "dosage": clinical_service.get_label_field(label or {}, "dosage_and_administration"),
            "contraindications": clinical_service.get_label_field(label or {}, "contraindications"),
            "boxed_warning": boxed_text,
            "warnings": clinical_service.get_label_field(label or {}, "warnings"),
            "interactions": clinical_service.get_label_field(label or {}, "drug_interactions"),
            "source_url": openfda_client._get_citation(label or {}) or "—",
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

def check_duplicate_therapies(rx, index, current_drugs, prescriptions, flags):
    """Helper to check for duplicate therapies against current and new meds."""
    from nova_guard.schemas.patient import SafetyFlag
    drug_name = rx.drug_name.lower()
    
    # 1. vs Current Meds
    if drug_name in current_drugs:
        flags.append(SafetyFlag(
            severity="warning",
            category="therapeutic_duplication",
            message=f"Patient already taking **{rx.drug_name}**",
            source="Current medication list"
        ))
        
    # 2. vs Other New Prescriptions
    for j, other_rx in enumerate(prescriptions):
        if index < j and drug_name == other_rx.drug_name.lower():
            flags.append(SafetyFlag(
                severity="warning",
                category="duplicate_therapy",
                message=f"Duplicate prescription in current request: **{rx.drug_name}** appears multiple times.",
                source="Current Request"
            ))

def calculate_polypharmacy_score(prescriptions, current_drugs) -> dict:
    """Calculates a basic polypharmacy risk score."""
    rx_names = [r.drug_name.lower() for r in prescriptions]
    total_drugs = list(set(rx_names + current_drugs))
    
    count = len(total_drugs)
    if count < 5:
        return {"score": 0, "risk": "Low", "count": count, "details": "Fewer than 5 medications."}
        
    score = count - 4
    high_risk_classes = ["amitriptyline", "diphenhydramine", "oxybutynin", "promethazine", "quetiapine", "zolpidem", "tramadol", "codeine", "alprazolam", "lorazepam"]
    burden = sum(1 for d in total_drugs if any(hr in d for hr in high_risk_classes))
    
    score += (burden * 2)
    
    if score >= 5:
        risk = "High"
    elif score >= 3:
        risk = "Moderate"
    else:
        risk = "Low"
        
    return {"score": score, "risk": risk, "count": count, "details": f"Patient is taking {count} active medications. High-risk burden: {burden}."}

def auditor_node(state: PatientState) -> dict:
    from nova_guard.schemas.patient import SafetyFlag

    flags = []
    prescriptions = state.get("prescriptions", [])
    profile = state.get("patient_profile", {})

    if not prescriptions or not profile:
        return {"safety_flags": flags}

    current_drugs = [d["drug"].lower() for d in profile.get("active_medications", [])]
    
    # Check each new prescription
    for i, rx in enumerate(prescriptions):
        drug_name = rx.drug_name.lower()
        
        # 1. Prior Adverse Reaction Check
        for reaction in profile.get("adverse_reactions", []):
            if drug_name in reaction.get("drug", "").lower():
                flags.append(SafetyFlag(
                    severity="warning",
                    category="prior_adverse_reaction",
                    message=f"Prior {reaction['severity']} reaction to {reaction['drug']}: {reaction['reaction']}",
                    source="Patient history"
                ))

        # 2. Duplicate Therapy Checks
        check_duplicate_therapies(rx, i, current_drugs, prescriptions, flags)
        
        # 3. Longitudinal Discontinuation Check
        for past_med in profile.get("drug_history_all", []):
            if not past_med.get("is_active") and drug_name in past_med.get("drug", "").lower():
                end_date_str = past_med.get("end_date") or "the past"
                flags.append(SafetyFlag(
                    severity="warning",
                    category="prior_discontinuation",
                    message=f"Patient was previously prescribed **{rx.drug_name}** but it was discontinued on {end_date_str}. Ensure re-challenge is intentional.",
                    source="Longitudinal History"
                ))

    # 4. Polypharmacy Risk Score
    poly_eval = calculate_polypharmacy_score(prescriptions, current_drugs)
    if poly_eval["risk"] in ["Moderate", "High"]:
        severity = "critical" if poly_eval["risk"] == "High" else "warning"
        flags.append(SafetyFlag(
            severity=severity,
            category="polypharmacy",
            message=f"**Polypharmacy Risk ({poly_eval['risk']}):** {poly_eval['details']} Increased risk of adverse events and non-adherence.",
            source="Scoring Algorithm"
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
            f"Answer strictly using provided FDA reference data and bio-research data: {state.get('research_report', '')}. "
            "If multiple drugs are involved, structure the answer clearly for EACH drug. "
            "Include: mechanism of action, approved indications, "
            "standard dosing & key adjustments (renal/hepatic/elderly), "
            "black box warnings (quote if present), major contraindications, "
            "serious warnings, clinically important interactions, "
            "pregnancy/lactation risks. Use precise, professional language. "
            "If the drug name is ambiguous or could map to multiple agents, ask the pharmacist to clarify."
        ),
        "CLINICAL_QUERY": (
            "Act as high-reliability patient-safety clinical decision support. "
            "Cross-reference ALL extracted drugs against allergies / ADRs / comorbidities / organ function / "
            "age / pregnancy status. "
            "Clearly highlight: allergy/cross-reactivity risk, serious DDIs (Drug-Drug Interactions), "
            "duplicate therapy, required dose adjustments, critical monitoring. "
            "Use cautious, factual, non-alarmist tone. "
            "If you need more clinical insight from the pharmacist to safely answer the query, explicitly ask them a clarifying question."
        ),
        "AUDIT": (
            "Explain automated prescription safety audit results to pharmacist. "
            "Structure answer:\n"
            "1. Overall verdict (Red/Yellow/Green)\n"
            "2. Triggered Rules/Flags (Grouped by Drug if applicable)\n"
            "3. Drug-Drug Interactions (if any)\n"
            "4. Clinical rationale & severity for each finding\n"
            "5. Primary patient safety implication\n"
            "6. Recommended pharmacist actions\n"
            "If the prescription details or patient profile is missing critical context to make a safe judgment, explicitly ask the user to clarify."
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
        except Exception:
            return str(obj)[:800] + "…" if len(str(obj)) > 800 else str(obj)

    # The patient profile in state is already de-identified by fetch_patient_node
    # to maintain HIPAA compliance.
    patient_profile_str = json.dumps(state.get("patient_profile", {}), indent=2)
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
        • If GENETIC MARKERS (PGx) exist in the patient profile, CHECK for gene-drug interactions (e.g., CYP2D6 poor metabolizer + codeine)
        • If LAB RESULTS exist in the patient profile, CHECK for organ impairment (low eGFR → renal dose adjust, elevated ALT/AST → hepatic caution)
        • Be extremely cautious regarding: anaphylaxis risk, cross-reactivity, QT prolongation, serotonin syndrome, major CYP/DDI risks
        • Use professional, precise, pharmacist-to-pharmacist language
        • If Red/Yellow flags exist — mention them EARLY and clearly (never bury safety info)
        • When data is missing/insufficient → clearly state: "Information not available in current context"
        • If you need additional clinical context to give a safe recommendation, ASK the pharmacist a clarifying question
        • NEVER give direct patient-facing advice — always frame as recommendation for the reviewing pharmacist
        • Answer only the current question — do not add unsolicited information
        • Think step-by-step before answering safety-sensitive questions

        OUTPUT FORMATTING — STRICTLY ENFORCE:
        • Format using clean Markdown: headings, bullets, **bold critical warnings**, tables when comparing
        • ONLY include content that is directly relevant to answering the user's question — omit sections with no data
        • NEVER output empty bullet points, empty braces {{}}, empty brackets [], or placeholder text like "N/A" or "None"
        • If a "References" section has no actual URLs to show, DO NOT include the section at all
        • If you include references, format each as: **Source Name** — [URL](URL) — only if you have a real URL
        • Do NOT show raw JSON, empty objects, or data structure artifacts in the response
        • Keep the response concise and scannable — no filler paragraphs
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
    logger.info("Tools node: executing clinical system action")
    
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
        if not drug:
            return {
                "messages": messages + [AIMessage(content="⚠️ Could not determine which drug to look up. Please specify a drug name.")],
                "system_action": None
            }
        source_url = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?query={drug}"
        return {
            "messages": messages + [AIMessage(content=f"🔗 Generated clinical reference link for {drug}.")],
            "external_url": source_url,
            "system_action": None
        }

    # 2. Action: Generate PDF Audit Report
    if action == "generate_report":
        report_status = "📄 Clinical Audit Report (PDF) is being generated... You can download it directly from the top of the chat panel."
        return {
            "messages": messages + [AIMessage(content=report_status)],
            "system_action": None
        }

    # Fallback: unrecognized action — clear to prevent re-execution loop
    return {
        "messages": messages + [AIMessage(content=f"⚠️ Unrecognized tool action '{action}'. Available actions: open_source, generate_report.")],
        "system_action": None
    }

async def clinical_safety_node(state: PatientState) -> dict:
    """
    Orchestrates high-precision clinical safety checks using specialized NLM/FDA APIs.
    Replaces broad OpenFDA checks with structured data from RxNav, DailyMed, and RxClass.
    """
    from nova_guard.services.openfda import openfda_client
    from nova_guard.services.clinical_services import clinical_service
    from nova_guard.services.bedrock import bedrock_client
    
    logger.info("Running Clinical Safety Checks (Precision APIs)")
    
    prescriptions = state.get("prescriptions", [])
    profile = state.get("patient_profile") or {}
    
    if not prescriptions:
        return {"safety_flags": []}
    
    all_flags = []
    rxcuis = []
    drug_Label_map = {}

    # 1. PER-DRUG CHECKS
    for rx in prescriptions:
        # A. Get OpenFDA Label (for text analysis source)
        label = await openfda_client.get_drug_label(rx.drug_name)
        drug_Label_map[rx.drug_name] = label
        
        # B. Get RxCUI (Normalization)
        rxcui = await clinical_service.get_rxcui(rx.drug_name)
        if rxcui:
            rxcuis.append(rxcui)
            
        # C. Check Recalls
        all_flags.extend(await openfda_client.check_drug_recall(rx.drug_name))

        if label:
            # D. Structured Checks (DailyMed / RxClass)
            # Beers Criteria (Geriatric)
            if (profile.get("age_years") or 0) >= 65:
                beers_flag = await clinical_service.check_beers_criteria(rx.drug_name, profile.get("age_years"))
                if beers_flag: all_flags.append(beers_flag)
                
            # Boxed Warning (DailyMed Source)
            boxed_flag = await clinical_service.check_boxed_warning(rx.drug_name, label)
            if boxed_flag: all_flags.append(boxed_flag)

            # Pharmacokinetics (Renal/Hepatic Section 12.3)
            # Only add if patient has risk factors to reduce noise.
            pk_flags = await clinical_service.check_pharmacokinetics(rx.drug_name, label)
            for flag in pk_flags:
                if "Renal" in flag.message:
                    # Show if eGFR is low (< 60)
                    if float(profile.get("egfr") or 100) < 60:
                        all_flags.append(flag)
                elif "Hepatic" in flag.message:
                    # Show if liver condition exists
                    conditions = " ".join([c.get("condition", "") for c in profile.get("medical_conditions", [])]).lower()
                    has_hepatic_risk = any(x in conditions for x in ["liver", "cirrhosis", "hepatitis", "hepatic", "jaundice"])
                    
                    # Also check lab results for abnormal liver enzymes
                    for lab in profile.get("lab_results", []):
                        test_name = lab.get("test_name", "").lower()
                        if lab.get("is_abnormal") and any(x in test_name for x in ["alt", "ast", "bilirubin", "alk", "alp"]):
                            has_hepatic_risk = True
                            break
                            
                    if has_hepatic_risk:
                        all_flags.append(flag)

            # E. Text-Based Checks (OpenFDA/DailyMed Logic)
            # All clinical reasoning now consolidated in ClinicalKnowledgeService
            
            all_flags.extend(await clinical_service.check_contraindications(rx.drug_name, label))
            all_flags.extend(await clinical_service.check_drug_allergy(rx.drug_name, label, profile))
            
            # Renal (using eGFR as proxy for CrCl)
            if profile.get("egfr"):
                all_flags.extend(await clinical_service.check_renal_dosing(rx.drug_name, label, profile))

            # Pregnancy / Nursing
            if profile.get("is_pregnant"):
                 all_flags.extend(await clinical_service.check_pregnancy_safety(rx.drug_name, label, profile))

            
        else:
            # AI FALLBACK (No Label Found)
            logger.warning(f"No FDA label data found for {rx.drug_name} — triggering AI Fallback")
            ai_flags = await bedrock_client.get_ai_safety_flags(rx.drug_name, profile)
            all_flags.extend(ai_flags)

    # 1.5 PGx SAFETY CHECKS (Pharmacogenomics)
    from nova_guard.schemas.patient import SafetyFlag
    pgx_markers = profile.get("genetic_markers", [])
    if pgx_markers:
        for rx in prescriptions:
            drug = rx.drug_name.lower()
            for marker in pgx_markers:
                gene = marker.get("gene", "").upper()
                phenotype = marker.get("phenotype", "").lower()
                
                # CYP2D6 Poor Metabolizer Checks
                if "CYP2D6" in gene and "poor" in phenotype:
                    if drug in ["codeine", "tramadol"]:
                        all_flags.append(SafetyFlag(
                            severity="critical",
                            category="pharmacogenomics",
                            message=f"**PGx Alert (CYP2D6 Poor Metabolizer):** Patient lacks CYP2D6 enzyme to convert **{rx.drug_name}** to its active metabolite. Significantly reduced efficacy; consider alternative.",
                            source="Patient genetic profile"
                        ))
                    elif drug in ["fluoxetine", "paroxetine", "venlafaxine"]:
                        all_flags.append(SafetyFlag(
                            severity="warning",
                            category="pharmacogenomics",
                            message=f"**PGx Alert (CYP2D6 Poor Metabolizer):** Reduced metabolism of **{rx.drug_name}**. Monitor for toxicity or consider lower starting dose.",
                            source="Patient genetic profile"
                        ))
                
                # CYP2C19 Poor Metabolizer Checks
                if "CYP2C19" in gene and "poor" in phenotype:
                    if drug in ["clopidogrel"]:
                        all_flags.append(SafetyFlag(
                            severity="critical",
                            category="pharmacogenomics",
                            message=f"**PGx Alert (CYP2C19 Poor Metabolizer):** Diminished antiplatelet effect of **{rx.drug_name}**. Consider alternative (e.g., prasugrel, ticagrelor).",
                            source="Patient genetic profile"
                        ))

    # 2. BATCH CHECKS (Interactions)
    if len(rxcuis) >= 2:
        interaction_flags = await clinical_service.check_interactions(rxcuis)
        all_flags.extend(interaction_flags)

    # Combine with existing (auditor) flags
    existing_flags = state.get("safety_flags", [])
    combined_flags = existing_flags + all_flags
    
    # Deduplicate flags based on content
    unique_flags = []
    seen = set()
    for f in combined_flags:
        # Create a unique key for the flag
        key = (f.category, f.severity, f.message)
        if key not in seen:
            seen.add(key)
            unique_flags.append(f)
    
    return {
        "safety_flags": unique_flags
    }


def verdict_node(state: PatientState) -> dict:
    from nova_guard.schemas.patient import SafetyVerdict
    logger.info(f"safety flags: {state.get('safety_flags')}")
    all_flags = state.get("safety_flags", [])

    # Filter flags for verdict calculation (same logic as Frontend)
    # We don't want "normalization" or generic "adverse_reaction" to trigger Red/Yellow
    relevant_flags = [
        f for f in all_flags 
        if f.category != "normalization"
        and not (f.category == "adverse_reaction" and f.source == "OpenFDA")
        and not (f.category == "mismatch" and "''" in f.message)
    ]

    critical = any(f.severity == "critical" for f in relevant_flags)
    warning  = any(f.severity == "warning"  for f in relevant_flags)

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
        flags=all_flags, # Keep ALL flags in the object, frontend filters display
        recommendation=msg,
        # confidence_score=state.get("confidence_score", 0.0)
    )

    return {
        "verdict": verdict,
        # "messages": [f"Verdict: **{status.upper()}** — {msg}"]
    }