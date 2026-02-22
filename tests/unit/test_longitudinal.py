import asyncio
from nova_guard.graph.nodes import auditor_node
from nova_guard.graph.state import PatientState
from nova_guard.schemas.patient import SafetyFlag

def test_longitudinal_drug_record():
    from nova_guard.schemas.patient import PrescriptionData

    # 1. Setup State with a discontinued drug, a coincident allergy, and a new prescription in the same class
    test_state = PatientState(
        prescriptions=[
            PrescriptionData(drug_name="Lisinopril", dose="5mg", frequency="daily")
        ],
        patient_profile={
            "allergies": [
                {
                    "allergen": "Lisinopril",
                    "type": "allergy",
                    "symptoms": "Angioedema",
                    "severity": "severe"
                }
            ],
            "drug_history_all": [
                {
                    "drug": "Lisinopril", # ACE Inhibitor
                    "is_active": False,        # Discontinued
                    "end_date": "2023-01-15"
                }
            ]
        }
    )

    # 2. Run the auditor_node
    # auditor_node is synchronous
    new_state = auditor_node(test_state)

    # 3. Verify the flag was appended
    flags = new_state.get("safety_flags", [])
    
    assert len(flags) > 0, "No flags generated"
    flag_messages = [f.message for f in flags]
    
    assert any("Lisinopril" in msg for msg in flag_messages), "Cross-reactivity between new and discontinued drug was not flagged."
    
    print("Longitudinal Drug Record test passed.")

if __name__ == "__main__":
    test_longitudinal_drug_record()
