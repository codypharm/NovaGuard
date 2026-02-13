"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, List, Dict, Any
import logging
import os

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from nova_guard.database import get_db
from nova_guard.api import patients as patient_crud
from nova_guard.api import sessions as session_crud
from nova_guard.api.auth import get_current_user
from nova_guard.models.user import User
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
from nova_guard.schemas.session import SessionResponse

from dotenv import load_dotenv
load_dotenv(override=True)


from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from nova_guard.database import engine
from nova_guard.graph.workflow import create_prescription_workflow


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    logging.getLogger(__name__).info("Nova Clinical Guard starting up")

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
                logging.getLogger(__name__).info("Checkpointer connection: %s", masked)
        
        async with AsyncPostgresSaver.from_conn_string(conn_string) as checkpointer:
            logging.getLogger(__name__).info("Initializing workflow with Postgres persistence")
            app.state.prescription_workflow = create_prescription_workflow(checkpointer)
            
            await checkpointer.setup()
            
            logging.getLogger(__name__).info("Ensuring database tables")
            from nova_guard.database import Base
            import nova_guard.models.audit  # noqa: F401 — register AuditLog table
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            yield

    except Exception as exc:
        logging.getLogger(__name__).error("Lifespan startup failed: %s", exc)
        raise

    finally:
        logging.getLogger(__name__).info("Nova Clinical Guard shutting down")

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
    # For Form data, we need to extract the token manually or use a workaround as Depends headers don't strictly mix well with Form
    # However, FastAPI handles Bearer token in headers fine even with Form data.
    current_user: User = Depends(get_current_user), 
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
    # Ensure session exists and link to patient if provided OR update title with content
    preview_text = prescription_text or ("Image Uploaded" if file else "New Session")
    
    session = await session_crud.update_session_patient(
        db, 
        session_id, 
        current_user.id,
        patient_id, 
        preview_text=preview_text
    )
    
    if not session:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    # 4. Execution Config
    config = {"configurable": {"thread_id": session_id}}
    
    result = None
    last_msg = None

    # Helper to extract string from message
    def get_msg_content(msg):
        if hasattr(msg, "content"): return msg.content
        if isinstance(msg, dict): return msg.get("content", str(msg))
        return str(msg)

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

        last_msg = result.get("messages", [])[-1] if result.get("messages") else None
        
        return {
            "status": "completed",
            "intent": result.get("intent"),
            "verdict": result.get("verdict"),
            "assistant_response": get_msg_content(last_msg) if last_msg else None,
            "safety_flags": result.get("safety_flags", [])
        }

    except Exception as e:
        logging.getLogger(__name__).error("Workflow failed for session %s: %s", session_id, e)
        return {
            "status": "error",
            "error_code": "WORKFLOW_ERROR",
            "message": "Something went wrong processing your request. Please try again.",
            "detail": str(e) if os.getenv("ENVIRONMENT") == "development" else None,
        }
    finally:
        # Non-blocking audit log — never fails the user request
        try:
            from nova_guard.services.audit_service import log_interaction
            resp_text = get_msg_content(last_msg)[:500] if last_msg else None
            verdict_obj = result.get("verdict") if result else None
            await log_interaction(
                db,
                session_id=session_id,
                user_id=current_user.id,
                action="clinical_interaction",
                intent=result.get("intent") if result else None,
                query=(prescription_text or "")[:500],
                response_summary=resp_text,
                verdict_status=verdict_obj.get("status") if isinstance(verdict_obj, dict) else None,
                flag_count=len(result.get("safety_flags", [])) if result else 0,
            )
        except Exception:
            pass  # Audit failure is never user-facing


# ============================================================================
# Streaming Endpoint (SSE — Phase 1: node-level progress)
# ============================================================================

# Human-readable labels for each graph node
_NODE_LABELS = {
    "gateway_supervisor": "Classifying your request…",
    "image_intake": "Reading prescription image…",
    "text_intake": "Parsing prescription text…",
    "voice_intake": "Transcribing voice input…",
    "fetch_patient": "Loading patient profile…",
    "fetch_medical_knowledge": "Searching medical literature…",
    "auditor": "Analyzing prescriptions…",
    "openfda": "Checking FDA safety database…",
    "verdict": "Generating safety verdict…",
    "assistant_node": "Preparing response…",
    "tools_node": "Executing clinical action…",
}


@app.post("/clinical-interaction/stream")
async def stream_clinical_interaction(
    patient_id: Optional[int] = Form(None),
    prescription_text: Optional[str] = Form(None),
    session_id: str = Form(...),
    file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    request: Request = None,
):
    """
    SSE streaming endpoint — emits progress events as each graph node completes.
    Frontend consumes via fetch + ReadableStream.
    """
    import json as _json
    from fastapi.responses import StreamingResponse
    from langchain_core.messages import HumanMessage

    # ── All DB / auth / file work happens HERE (before generator starts) ──
    image_bytes = await file.read() if file else None

    initial_messages = []
    if prescription_text:
        initial_messages.append(HumanMessage(content=prescription_text))

    initial_state = {
        "patient_id": patient_id,
        "prescription_text": prescription_text,
        "prescription_image": image_bytes,
        "messages": initial_messages,
    }

    preview_text = prescription_text or ("Image Uploaded" if file else "New Session")
    session = await session_crud.update_session_patient(
        db, session_id, current_user.id, patient_id, preview_text=preview_text
    )
    if not session:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")

    config = {"configurable": {"thread_id": session_id}}
    workflow = request.app.state.prescription_workflow

    # Capture user info for audit (avoids touching Depends objects inside generator)
    _user_id = current_user.id
    _query_text = (prescription_text or "")[:500]

    def get_msg_content(msg):
        if hasattr(msg, "content"): return msg.content
        if isinstance(msg, dict): return msg.get("content", str(msg))
        return str(msg)

    async def event_generator():
        """Yields SSE events. No Depends-injected objects used here."""
        result = None
        last_msg = None

        try:
            async for chunk in workflow.astream(initial_state, config, stream_mode="updates"):
                for node_name, node_output in chunk.items():
                    # Skip internal LangGraph nodes
                    if node_name.startswith("__"):
                        continue

                    label = _NODE_LABELS.get(node_name, f"Processing {node_name}…")
                    yield f"data: {_json.dumps({'event': 'progress', 'node': node_name, 'label': label})}\n\n"

                    if isinstance(node_output, dict):
                        if result is None:
                            result = {}
                        result.update(node_output)

            # ── Stream complete ──
            if result:
                last_msg = result.get("messages", [])[-1] if result.get("messages") else None
                final = {
                    "event": "complete",
                    "status": "completed",
                    "intent": result.get("intent"),
                    "verdict": result.get("verdict"),
                    "assistant_response": get_msg_content(last_msg) if last_msg else None,
                    "safety_flags": result.get("safety_flags", []),
                }
                yield f"data: {_json.dumps(final, default=str)}\n\n"
            else:
                yield f"data: {_json.dumps({'event': 'complete', 'status': 'completed'})}\n\n"

        except Exception as e:
            logging.getLogger(__name__).error("Stream failed for session %s: %s", session_id, e)
            error_payload = {
                "event": "error",
                "message": "Something went wrong. Please try again.",
                "detail": str(e) if os.getenv("ENVIRONMENT") == "development" else None,
            }
            yield f"data: {_json.dumps(error_payload)}\n\n"

        finally:
            # Audit log with its own DB session (Depends session may be closed)
            try:
                from nova_guard.services.audit_service import log_interaction
                from nova_guard.database import AsyncSessionLocal
                async with AsyncSessionLocal() as audit_db:
                    resp_text = get_msg_content(last_msg)[:500] if last_msg else None
                    verdict_obj = result.get("verdict") if result else None
                    await log_interaction(
                        audit_db,
                        session_id=session_id,
                        user_id=_user_id,
                        action="clinical_interaction",
                        intent=result.get("intent") if result else None,
                        query=_query_text,
                        response_summary=resp_text,
                        verdict_status=verdict_obj.get("status") if isinstance(verdict_obj, dict) else None,
                        flag_count=len(result.get("safety_flags", [])) if result else 0,
                    )
            except Exception:
                pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================================
# Session Endpoints
# ============================================================================

@app.get("/sessions", response_model=list[SessionResponse])
async def list_recent_sessions(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent sessions for sidebar."""
    logging.getLogger(__name__).debug("GET /sessions limit=%d user=%s", limit, current_user.id)
    sessions = await session_crud.list_recent_sessions(db, current_user.id, limit=limit)
    logging.getLogger(__name__).debug("Found %d sessions", len(sessions))
    return sessions


@app.post("/sessions", response_model=SessionResponse)
async def create_session(
    session_id: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create or initialize a session."""
    return await session_crud.update_session_patient(db, session_id, current_user.id, None)


@app.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a session."""
    deleted = await session_crud.delete_session(db, session_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return None


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
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve chat history for a session."""
    # Verify ownership
    session = await session_crud.get_session(db, session_id)
    if session and session.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
        
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
        logging.getLogger(__name__).error("Error fetching history: %s", e)
        return []

# ============================================================================
# Clinical Tools Endpoints
# ============================================================================

from nova_guard.services.clinical_tools import ClinicalTools
from pydantic import BaseModel
import json

# Initialize the service
clinical_service = ClinicalTools()

class CrClRequest(BaseModel):
    age: int
    weight_kg: float
    height_cm: float
    scr: float
    sex: str
    drug_name: Optional[str] = None

class InteractionRequest(BaseModel):
    drugs: list[str]

class MedicationItem(BaseModel):
    name: str
    dosage: Optional[str] = None
    duration: Optional[str] = None

class SafetyRequest(BaseModel):
    medications: List[MedicationItem]

@app.post("/clinical/calculate-crcl")
async def calculate_crcl(data: CrClRequest):
    """Calculate Creatinine Clearance with AI recommendations."""
    return await clinical_service.calculate_crcl(
        data.age, data.weight_kg, data.height_cm, data.scr, data.sex, data.drug_name
    )

@app.post("/clinical/interactions")
async def check_interactions(data: InteractionRequest):
    """Get AI-driven interaction insights (Markdown)."""
    return await clinical_service.get_interaction_insights(data.drugs)

@app.get("/clinical/substitutions/{drug_name}")
async def get_substitutions(drug_name: str):
    """Get therapeutic equivalents (Markdown)."""
    return await clinical_service.get_equivalents(drug_name)

@app.post("/clinical/safety-profile")
async def get_safety_profile(request: SafetyRequest):
    """Get safety matrix and counseling (Markdown) for a complete medication regimen."""
    return await clinical_service.generate_safety_and_counseling(request.medications)


# ============================================================================
# Audit Log Endpoint
# ============================================================================

@app.get("/audit-log")
async def get_audit_log(
    session_id: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve audit trail for the current user's clinical interactions."""
    from sqlalchemy import select, desc
    from nova_guard.models.audit import AuditLog

    query = select(AuditLog).where(AuditLog.user_id == current_user.id)
    if session_id:
        query = query.where(AuditLog.session_id == session_id)
    query = query.order_by(desc(AuditLog.created_at)).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "session_id": log.session_id,
            "action": log.action,
            "intent": log.intent,
            "query": log.query,
            "response_summary": log.response_summary,
            "verdict_status": log.verdict_status,
            "flag_count": log.flag_count,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        }
        for log in logs
    ]
