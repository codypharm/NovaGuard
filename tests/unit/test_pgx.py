import asyncio
from nova_guard.graph.nodes import clinical_safety_node
from nova_guard.graph.state import PatientState

def test_pgx_safety_check():
    from nova_guard.schemas.patient import PrescriptionData

    # 1. Setup State with PGx marker and conflicting drug
    test_state = PatientState(
        prescriptions=[
            PrescriptionData(drug_name="Codeine", dose="30mg", frequency="Q6H PRN")
        ],
        patient_profile={
            "genetic_markers": [
                {
                    "gene": "CYP2D6",
                    "phenotype": "Poor Metabolizer"
                }
            ]
        }
    )

    # 2. Run the clinical_safety_node
    # Need to mock the 3 external calls at the start of the node to avoid network:
    # openfda_client.get_drug_label, clinical_service.get_rxcui, openfda_client.check_drug_recall
    from unittest.mock import AsyncMock, patch

    with patch('nova_guard.services.openfda.openfda_client.get_drug_label', new_callable=AsyncMock) as mock_label:
        mock_label.return_value = {}
        with patch('nova_guard.services.clinical_services.clinical_service.get_rxcui', new_callable=AsyncMock) as mock_cui:
            mock_cui.return_value = None
            with patch('nova_guard.services.openfda.openfda_client.check_drug_recall', new_callable=AsyncMock) as mock_recall:
                mock_recall.return_value = []
                
                loop = asyncio.new_event_loop()
                new_state = loop.run_until_complete(clinical_safety_node(test_state))
                loop.close()

    # 3. Verify a critical PGx flag was generated
    flags = new_state.get("safety_flags", [])
    
    # We expect 1 flag for the PGx conflict
    pgx_flags = [f for f in flags if getattr(f, "category", "") == "pharmacogenomics"]
    
    assert len(pgx_flags) > 0, "No PGx safety flag was generated for Codeine + CYP2D6 PM"
    
    # Check flag content
    flag = pgx_flags[0]
    message = flag.message if hasattr(flag, 'message') else flag.get('message', '')
    assert "CYP2D6" in message
    assert "Codeine" in message
    assert "Poor Metabolizer" in message
    
    print("PGx Safety Check test passed.")

if __name__ == "__main__":
    test_pgx_safety_check()
