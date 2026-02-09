"""LangGraph state definition for prescription processing workflow."""

from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict

from langgraph.graph.message import add_messages

from nova_guard.schemas.patient import PrescriptionData, SafetyFlag, SafetyVerdict


class PatientState(TypedDict):
    """
    State that flows through the prescription processing graph.
    
    This state tracks:
    - Input modality (image/text/voice)
    - Raw input data
    - Extracted prescription information
    - Patient medical context
    - Safety analysis results
    - Human confirmation status
    """
    
    # ========================================================================
    # Input (one of these will be populated based on input_type)
    # ========================================================================
    input_type: Literal["image", "text", "voice"]
    prescription_image: Optional[bytes]  # For image input
    prescription_text: Optional[str]     # For typed text input
    prescription_audio: Optional[bytes]  # For voice input
    
    # ========================================================================
    # Extracted Data (normalized from any input modality)
    # ========================================================================
    extracted_data: Optional[PrescriptionData]  # drug, dose, frequency
    confidence_score: float  # 0.0 to 1.0 (90% threshold for HITL)
    
    # ========================================================================
    # Patient Context (from database)
    # ========================================================================
    patient_id: int
    patient_profile: Optional[dict]  # Full patient record with history
    
    # ========================================================================
    # Safety Analysis Results
    # ========================================================================
    safety_flags: list[SafetyFlag]  # Individual safety concerns
    verdict: Optional[SafetyVerdict]  # Final Green/Yellow/Red verdict
    
    # ========================================================================
    # Workflow Control
    # ========================================================================
    human_confirmed: bool  # Has human reviewed the extraction?
    
    # ========================================================================
    # Messages (for LangGraph's built-in message handling)
    # ========================================================================
    messages: Annotated[list, add_messages]  # Conversation/log messages
