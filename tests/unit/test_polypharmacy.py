import asyncio
from nova_guard.graph.nodes import auditor_node
from nova_guard.graph.state import PatientState
from nova_guard.schemas.patient import SafetyFlag

def test_polypharmacy_score():
    # 1. Setup State with 5 concurrent active drugs
    from nova_guard.schemas.patient import PrescriptionData

    test_state = PatientState(
        prescriptions=[
            PrescriptionData(drug_name="Amitriptyline", dose="25mg", frequency="QHS")
        ],
        patient_profile={
            "active_medications": [
                {"drug": "Oxybutynin", "is_active": True}, # Anticholinergic
                {"drug": "Diphenhydramine", "is_active": True}, # Anticholinergic
                {"drug": "Lisinopril", "is_active": True}, 
                {"drug": "Metformin", "is_active": True}
            ]
        }
    )

    # 2. Run the logic
    # auditor_node is synchronous
    new_state = auditor_node(test_state)

    # 3. Verify flag
    flags = new_state.get("safety_flags", [])
    poly_flags = [f for f in flags if getattr(f, "category", "") == "polypharmacy"]
    
    assert len(poly_flags) > 0, "Polypharmacy flag not generated for 5+ drugs."
    assert "High-risk burden" in poly_flags[0].message
    
    print("Polypharmacy Score test passed.")

if __name__ == "__main__":
    test_polypharmacy_score()
