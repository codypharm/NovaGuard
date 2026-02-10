"""LangGraph workflow for prescription processing."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from nova_guard.graph.state import PatientState
from nova_guard.graph.nodes import (
    gateway_supervisor_node,
    route_input,
    image_intake_node,
    text_intake_node,
    voice_intake_node,
    fetch_patient_node,
    auditor_node,
    openfda_node,
    verdict_node,
    fetch_medical_knowledge_node,
    assistant_node,
    tools_node,
    conditional_fetch_patient,
)


def create_prescription_workflow():
    """
    Create the prescription processing workflow.
    
    Workflow Structure:
    1.  START → Gateway Supervisor (Intent Classification)
    2.  Supervisor → Router (Directs to AUDIT, ASSIST, or TOOLS)
    3.  Audit Path: Intake → HITL → Fetch Patient → Auditor → OpenFDA → Verdict
    4.  Assist Path: Fetch Patient → Assistant Node
    5.  Tools Path: Execute System Action (URL opening, etc.)
    """
    
    # Create the graph
    workflow = StateGraph(PatientState)
    
    # ========================================================================
    # Add all nodes
    # ========================================================================
    
    # The "Air Traffic Controller"
    workflow.add_node("gateway_supervisor", gateway_supervisor_node)
    
    # Intake nodes
    workflow.add_node("image_intake", image_intake_node)
    workflow.add_node("text_intake", text_intake_node)
    workflow.add_node("voice_intake", voice_intake_node)
    
    # Processing & Knowledge nodes
    workflow.add_node("fetch_patient", fetch_patient_node)
    workflow.add_node("fetch_medical_knowledge", fetch_medical_knowledge_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("openfda", openfda_node)
    workflow.add_node("verdict", verdict_node)
    
    # Dialogue & Action nodes
    workflow.add_node("assistant_node", assistant_node)
    workflow.add_node("tools_node", tools_node)
    
    # ========================================================================
    # Define edges (workflow flow)
    # ========================================================================
    
    # 1. Entry Point: Always start at the Supervisor
    workflow.set_entry_point("gateway_supervisor")

    # 2. Routing Logic: Direct traffic based on detected intent
    workflow.add_conditional_edges(
        "gateway_supervisor",
        route_input,
        {
            "image_intake": "image_intake",
            "text_intake": "text_intake",
            "voice_intake": "voice_intake",
            "fetch_patient": "fetch_patient",
            "fetch_medical_knowledge": "fetch_medical_knowledge",
            "tools_node": "tools_node",
            "assistant_node": "assistant_node"
        }
    )
    
    # 3. Intake to Processing (Human-in-the-Loop follows image/text extraction)
    workflow.add_edge("image_intake", "fetch_patient")
    workflow.add_edge("text_intake", "fetch_patient")
    workflow.add_edge("voice_intake", "fetch_patient")
    
    # 4. Processing Pipeline Routing
    workflow.add_conditional_edges(
        "fetch_patient", 
        conditional_fetch_patient, 
        {
            "auditor": "auditor",
            "fetch_medical_knowledge": "fetch_medical_knowledge",
            "assistant_node": "assistant_node", # If the intent was just a query
            "END": END
        }
    )
    
    # 5. Audit Loop
    workflow.add_edge("auditor", "openfda")
    workflow.add_edge("openfda", "verdict")
    workflow.add_edge("verdict", END) 
    
    # 6. Assistant & Tools completion
    workflow.add_edge("fetch_medical_knowledge", "assistant_node")
    workflow.add_edge("assistant_node", END)
    workflow.add_edge("tools_node", END)
    
    # ========================================================================
    # Compile with checkpointer (enables interrupts)
    # ========================================================================
    
    checkpointer = MemorySaver()
    
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["fetch_patient"]  # HITL: Pharmacist verifies extraction before audit
    )
    
    return app


# Create the compiled workflow
prescription_workflow = create_prescription_workflow()