"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Depends, HTTPException
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

@app.post("/prescriptions/process")
async def process_prescription(
    input_type: str,
    patient_id: int,
    prescription_text: str | None = None,
):
    """
    Process a prescription through the safety auditing workflow.
    
    Phase 1: Text input only (image and voice are mocked)
    
    Example:
    POST /prescriptions/process?input_type=text&patient_id=1
    Body: "Lisinopril 10mg once daily"
    """
    from nova_guard.graph.workflow import prescription_workflow
    
    # Initialize state
    initial_state = {
        "input_type": input_type,
        "patient_id": patient_id,
        "prescription_text": prescription_text,
        "prescription_image": None,
        "prescription_audio": None,
        "extracted_data": None,
        "confidence_score": 0.0,
        "patient_profile": None,
        "safety_flags": [],
        "verdict": None,
        "human_confirmed": False,
        "messages": []
    }
    
    # Run workflow (will pause at HITL interrupt)
    config = {"configurable": {"thread_id": "test-thread"}}
    
    # Step 1: Run until interrupt
    result = await prescription_workflow.ainvoke(initial_state, config)
    
    # In a real app, you'd return the extracted data here for human review
    # Then the human would call a separate endpoint to continue
    
    # For Phase 1 demo, we'll auto-continue (skip HITL)
    result["human_confirmed"] = True
    final_result = await prescription_workflow.ainvoke(None, config)
    
    return {
        "status": "completed",
        "verdict": final_result.get("verdict"),
        "messages": final_result.get("messages", []),
        "extracted_data": final_result.get("extracted_data"),
    }
