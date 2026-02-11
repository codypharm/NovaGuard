"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
import os

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from nova_guard.database import get_db
from nova_guard.api import patients as patient_crud
from nova_guard.api import sessions as session_crud
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

from dotenv import load_dotenv
load_dotenv(override=True)


from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from nova_guard.database import engine
from nova_guard.graph.workflow import create_prescription_workflow


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    print("🚀 Nova Clinical Guard starting up...")

    try:
        # Read directly from environment variable
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            raise ValueError("DATABASE_URL environment variable not set")
        
        # Convert asyncpg to psycopg format for LangGraph
        conn_string = database_url.replace("postgresql+asyncpg://", "postgresql://")
        
        # Mask password for logging
        if "@" in conn_string:
            parts = conn_string.split("@")
            credentials = parts[0].split("://")[1]
            if ":" in credentials:
                user = credentials.split(":")[0]
                masked = conn_string.replace(credentials, f"{user}:***")
                print(f"Checkpointer connection string (masked): {masked}")
        
        async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
            print("📥 Initializing Workflow with Postgres Persistence...")
            app.state.prescription_workflow = create_prescription_workflow(checkpointer)
            
            await checkpointer.setup()
            
            print("🗄️ Ensuring Database Tables...")
            from nova_guard.database import Base
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            yield

    except Exception as exc:
        print(f"❌ Lifespan startup failed: {exc}")
        raise

    finally:
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


@app.put("/patients/{patient_id}", response_model=PatientResponse)
async def update_patient(
    patient_id: int,
    patient: PatientCreate,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing patient."""
    updated = await patient_crud.update_patient(db, patient_id, patient)
    if not updated:
        raise HTTPException(status_code=404, detail="Patient not found")
    return updated


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
    patient_id: Optional[int] = Form(None),
    prescription_text: Optional[str] = Form(None),
    session_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    request: Request = None,  # Added to access app.state
):
    """
    Unified endpoint for all clinical interactions. 
    Handles images, text prescriptions, and assistant follow-ups.
    """
    # from nova_guard.graph.workflow import prescription_workflow
    from langchain_core.messages import HumanMessage
    
    # 1. Prepare Input Data
    image_bytes = await file.read() if file else None
    
    # 2. Initialize State 
    initial_messages = []
    if prescription_text:
        initial_messages.append(HumanMessage(content=prescription_text))
    
    initial_state = {
        "patient_id": patient_id,
        "prescription_text": prescription_text,
        "prescription_image": image_bytes,
        "messages": initial_messages,
    }
    
    # 3. Session Management
    # Ensure session exists and link to patient if provided
    if patient_id:
        await session_crud.update_session_patient(db, session_id, patient_id)
    else:
        # Just ensure session exists
        await session_crud.update_session_patient(db, session_id, None)

    # 4. Execution Config
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # Initial invocation triggers the Gateway Supervisor
        workflow = request.app.state.prescription_workflow
        result = await workflow.ainvoke(initial_state, config)
        
        # 4. Handle Human-in-the-Loop (HITL) for Extraction
        # If the graph is waiting for confirmation, we return the current state
        state_snapshot = await workflow.aget_state(config)
        
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
# Session Endpoints
# ============================================================================

@app.get("/sessions")
async def list_recent_sessions(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List recent sessions for sidebar."""
    print(f"GET /sessions limit={limit}")
    sessions = await session_crud.list_recent_sessions(db, limit=limit)
    print(f"Found {len(sessions)} sessions")
    return sessions


@app.post("/sessions")
async def create_session(
    session_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    """Create or initialize a session."""
    return await session_crud.update_session_patient(db, session_id, None)


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


@app.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: str,
    request: Request,
):
    """Retrieve chat history for a session."""
    workflow = request.app.state.prescription_workflow
    config = {"configurable": {"thread_id": session_id}}
    
    try:
        # Get state from checkpointer
        state_snapshot = await workflow.aget_state(config)
        if not state_snapshot.values:
            return []
            
        messages = state_snapshot.values.get("messages", [])
        
        # Transform to frontend format
        history = []
        
        # Phrases to filter out (internal system logs)
        ignored_prefixes = [
            "Intent classified as",
            "✅", "❌", "⚠️", "🔍", "💊", "🔗", "📄", "📷", "🎤", "⌨️", 
            "Verdict:", "Audit (history):"
        ]
        
        for msg in messages:
            role = "user" if msg.type == "human" else "assistant"
            content = msg.content
            
            # Skip internal system logs for the frontend
            if role == "assistant" and any(str(content).strip().startswith(p) for p in ignored_prefixes):
                continue

            # Simple ID generation (in reality, msg.id might exist or we use index)
            msg_id = getattr(msg, "id", f"{role}-{len(history)}")
            
            history.append({
                "id": msg_id,
                "role": role,
                "content": content,
                "timestamp": getattr(msg, "timestamp", None) # Timestamp might not be directly on msg
            })
            
        return history
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []
