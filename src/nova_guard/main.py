"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from nova_guard.database import get_db
from nova_guard.api import patients as patient_crud
from nova_guard.schemas.patient import (
    PatientCreate,
    PatientResponse,
    DrugHistoryCreate,
    DrugHistoryResponse,
    AllergyCreate,
    AllergyResponse,
    AdverseReactionCreate,
    AdverseReactionResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan manager."""
    # Startup
    print("🚀 Nova Clinical Guard starting up...")
    yield
    # Shutdown
    print("👋 Nova Clinical Guard shutting down...")


app = FastAPI(
    title="Nova Clinical Guard",
    description="AI-powered prescription safety auditing system",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "nova-clinical-guard"}


# ============================================================================
# Patient Endpoints
# ============================================================================

@app.post("/patients", response_model=PatientResponse, status_code=201)
async def create_patient(
    patient: PatientCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new patient."""
    return await patient_crud.create_patient(db, patient)


@app.get("/patients/{patient_id}", response_model=PatientResponse)
async def get_patient(
    patient_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get patient by ID with full medical history."""
    patient = await patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.get("/patients/lookup/{mrn}", response_model=PatientResponse)
async def lookup_patient_by_mrn(
    mrn: str,
    db: AsyncSession = Depends(get_db),
):
    """Lookup patient by Medical Record Number."""
    patient = await patient_crud.get_patient_by_mrn(db, mrn)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.get("/patients", response_model=list[PatientResponse])
async def list_patients(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List all patients."""
    return await patient_crud.get_patients(db, skip=skip, limit=limit)


# ============================================================================
# Drug History Endpoints
# ============================================================================

@app.post("/patients/{patient_id}/drugs", response_model=DrugHistoryResponse, status_code=201)
async def add_drug_to_history(
    patient_id: int,
    drug: DrugHistoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add drug to patient's medication history."""
    # Verify patient exists
    patient = await patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Override patient_id from path
    drug.patient_id = patient_id
    return await patient_crud.add_drug_to_history(db, drug)


# ============================================================================
# Allergy Endpoints
# ============================================================================

@app.post("/patients/{patient_id}/allergies", response_model=AllergyResponse, status_code=201)
async def add_allergy(
    patient_id: int,
    allergy: AllergyCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add allergy to patient's registry."""
    # Verify patient exists
    patient = await patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Override patient_id from path
    allergy.patient_id = patient_id
    return await patient_crud.add_allergy(db, allergy)


# ============================================================================
# Adverse Reaction Endpoints
# ============================================================================

@app.post(
    "/patients/{patient_id}/adverse-reactions",
    response_model=AdverseReactionResponse,
    status_code=201,
)
async def add_adverse_reaction(
    patient_id: int,
    reaction: AdverseReactionCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add adverse reaction to patient's history."""
    # Verify patient exists
    patient = await patient_crud.get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Override patient_id from path
    reaction.patient_id = patient_id
    return await patient_crud.add_adverse_reaction(db, reaction)


# ============================================================================
# Prescription Processing Endpoint (LangGraph Workflow)
# ============================================================================

@app.post("/clinical-interaction/process")
async def process_clinical_interaction(
    patient_id: int = Form(...),
    prescription_text: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """
    Unified endpoint for all clinical interactions. 
    Handles images, text prescriptions, and assistant follow-ups.
    """
    from nova_guard.graph.workflow import prescription_workflow
    
    # 1. Prepare Input Data
    image_bytes = await file.read() if file else None
    
    # 2. Initialize State 
    initial_state = {
        "patient_id": patient_id,
        "prescription_text": prescription_text,
        "prescription_image": image_bytes,
        "chat_history": [], 
        "messages": []
    }
    
    # 3. Execution Config (Threaded by Patient ID for persistence)
    config = {"configurable": {"thread_id": f"session-{1}"}}
    
    try:
        # Initial invocation triggers the Gateway Supervisor
        result = await prescription_workflow.ainvoke(initial_state, config)
        
        # 4. Handle Human-in-the-Loop (HITL) for Extraction
        # If the graph is waiting for confirmation, we return the current state
        state_snapshot = await prescription_workflow.aget_state(config)
        
        if state_snapshot.next:
            # The graph is paused (likely at fetch_patient for verification)
            return {
                "status": "awaiting_verification",
                "extracted_data": result.get("extracted_data"),
                "intent": result.get("intent")
            }
             
        # Helper to extract string from message
        def get_msg_content(msg):
            if hasattr(msg, "content"): return msg.content
            if isinstance(msg, dict): return msg.get("content", str(msg))
            return str(msg)

        last_msg = result.get("messages")[-1] if result.get("messages") else None
        
        return {
            "status": "completed",
            "intent": result.get("intent"),
            "verdict": result.get("verdict"),
            "assistant_response": get_msg_content(last_msg) if last_msg else None,
            "safety_flags": result.get("safety_flags", [])
        }

    except Exception as e:
        print(f"❌ Workflow Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Natural Language Query Endpoint
# ============================================================================

@app.get("/query")
async def natural_language_query(
    q: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Natural language query interface for patient safety checks.
    
    Examples:
    - GET /query?q=is patient 1 allergic to paracetamol
    - GET /query?q=does john doe id 123 have penicillin allergy
    - GET /query?q=check if patient 1 has aspirin allergy
    """
    from nova_guard.services.nlp import parse_allergy_query
    
    result = await parse_allergy_query(q, db)
    return result
