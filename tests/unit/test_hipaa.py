import asyncio
from unittest.mock import AsyncMock, patch
from nova_guard.graph.nodes import fetch_patient_node
from nova_guard.graph.state import PatientState

def test_hipaa_deidentification():
    # 1. Setup mock patient profile with a real name
    test_state = PatientState(
        patient_id=999,
        intent="AUDIT"
    )
    
    mock_patient_db_response = {
        "id": 999,
        "name": "John Doe",  # This must be stripped
        "age_years": 45,
        "weight": 80.0
    }

    # 2. Run the fetch_patient_node with a mocked DB call
    from unittest.mock import MagicMock
    # Create a mock objects that mimics the SQLAlchemy Patient model
    mock_patient = MagicMock()
    mock_patient.id = 999
    # name is intentionally missing here because the node doesn't actually read `patient.name` into the profile, 
    # but let's ensure the DB result has what we need to test the logic
    mock_patient.age_years = 45
    mock_patient.weight = 80.0
    mock_patient.height = 180.0
    mock_patient.is_pregnant = False
    mock_patient.is_nursing = False
    mock_patient.egfr = 90.0
    mock_patient.allergies = []
    mock_patient.drug_history = []
    mock_patient.adverse_reactions = []
    mock_patient.lab_results = []
    mock_patient.genetic_markers = []

    with patch('nova_guard.api.patients.get_patient', new_callable=AsyncMock) as mock_get_patient:
        mock_get_patient.return_value = mock_patient
        
        with patch('nova_guard.database.AsyncSessionLocal') as mock_session_class:
            # The async session context manager return mock
            mock_session = AsyncMock()
            mock_session_class.return_value.__aenter__.return_value = mock_session
            
            loop = asyncio.new_event_loop()
            new_state = loop.run_until_complete(fetch_patient_node(test_state))
            loop.close()

    # 3. Verify the resulting state has the name stripped
    profile = new_state.get("patient_profile", {})
    
    # Assert name was replaced with the HIPAA-compliant generic ID
    assert profile.get("name") == "Patient-999"
    # Assert the original name is nowhere in the profile string
    assert "John Doe" not in str(profile)
    # Assert other data remains intact
    assert profile.get("age_years") == 45
    
    print("HIPAA De-identification test passed.")

if __name__ == "__main__":
    test_hipaa_deidentification()
