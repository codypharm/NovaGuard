"""LangGraph workflow for prescription processing."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from nova_guard.graph.state import PatientState
from nova_guard.graph.nodes import (
    route_input,
    image_intake_node,
    text_intake_node,
    voice_intake_node,
    fetch_patient_node,
    auditor_node,
    openfda_node,
    verdict_node,
)


def create_prescription_workflow():
    """
    Create the prescription processing workflow.
    
    Workflow:
    1. START → Router (decides which intake node based on input_type)
    2. Intake Node (image/text/voice) → Extracts prescription data
    3. INTERRUPT (Human-in-the-Loop) → Human confirms extraction
    4. Fetch Patient → Loads patient medical history from database
    5. Auditor → Cross-references against patient history
    6. OpenFDA → Runs comprehensive safety checks
    7. Verdict → Generates final Green/Yellow/Red verdict
    8. END
    """
    
    # Create the graph
    workflow = StateGraph(PatientState)
    
    # ========================================================================
    # Add all nodes
    # ========================================================================
    
    # Intake nodes (one will be selected by router)
    workflow.add_node("image_intake", image_intake_node)
    workflow.add_node("text_intake", text_intake_node)
    workflow.add_node("voice_intake", voice_intake_node)
    
    # Processing nodes
    workflow.add_node("fetch_patient", fetch_patient_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("openfda", openfda_node)
    workflow.add_node("verdict", verdict_node)
    
    # ========================================================================
    # Define edges (workflow flow)
    # ========================================================================
    
    # START → Router (conditional edge based on input_type)
    workflow.set_conditional_entry_point(
        route_input,
        {
            "image_intake": "image_intake",
            "text_intake": "text_intake",
            "voice_intake": "voice_intake",
        }
    )
    
    # All intake nodes → fetch_patient (after HITL interrupt)
    # The interrupt happens automatically when we call .invoke() with interrupt_before
    workflow.add_edge("image_intake", "fetch_patient")
    workflow.add_edge("text_intake", "fetch_patient")
    workflow.add_edge("voice_intake", "fetch_patient")
    
    # Processing pipeline
    workflow.add_edge("fetch_patient", "auditor")
    workflow.add_edge("auditor", "openfda")
    workflow.add_edge("openfda", "verdict")
    workflow.add_edge("verdict", END)
    
    # ========================================================================
    # Compile with checkpointer (enables interrupts)
    # ========================================================================
    
    # MemorySaver allows us to pause/resume the workflow
    checkpointer = MemorySaver()
    
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["fetch_patient"]  # HITL: Pause before fetching patient
    )
    
    return app


# Create the compiled workflow
prescription_workflow = create_prescription_workflow()
