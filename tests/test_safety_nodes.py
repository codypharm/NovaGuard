import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import nova_guard.database
from tempfile import NamedTemporaryFile

from nova_guard.graph.nodes import auditor_node, calculate_polypharmacy_score, clinical_safety_node, fetch_patient_node
from nova_guard.schemas.patient import SafetyFlag, PrescriptionData
from nova_guard.models.patient import Patient

def test_longitudinal_check():
    state = {
        "prescriptions": [PrescriptionData(drug_name="Lisinopril", dose="10mg", frequency="Daily")],
        "patient_profile": {
            "active_medications": [],
            "drug_history_all": [
                {"drug": "Lisinopril", "is_active": False, "end_date": "2023-01-01"}
            ],
            "adverse_reactions": []
        }
    }
    
    result = auditor_node(state)
    flags = result.get("safety_flags", [])
    
    assert len(flags) > 0
    assert any(f.category == "prior_discontinuation" for f in flags)
    assert any("2023-01-01" in f.message for f in flags)

def test_polypharmacy_score():
    prescriptions = [PrescriptionData(drug_name="Aspirin", dose="81mg", frequency="Daily")]
    current_drugs = ["lisinopril", "metformin", "atorvastatin"] # 4 total
    
    score_4 = calculate_polypharmacy_score(prescriptions, current_drugs)
    assert score_4["risk"] == "Low"
    assert score_4["count"] == 4
    
    current_drugs.append("amlodipine") # 5 total
    score_5 = calculate_polypharmacy_score(prescriptions, current_drugs)
    assert score_5["risk"] == "Low" or score_5["risk"] == "Moderate"

def test_polypharmacy_high_risk():
    prescriptions = [PrescriptionData(drug_name="Zolpidem", dose="5mg", frequency="Nightly")]
    current_drugs = ["lisinopril", "metformin", "atorvastatin", "amlodipine"] # 5 total
    
    score_high = calculate_polypharmacy_score(prescriptions, current_drugs)
    assert score_high["risk"] == "Moderate" or score_high["risk"] == "High"

@pytest.mark.asyncio
@patch("nova_guard.database.AsyncSessionLocal")
async def test_hipaa_deidentification(mock_session):
    mock_db = AsyncMock()
    mock_db.__aenter__.return_value = mock_db
    mock_session.return_value = mock_db
    
    mock_patient = Patient(id=99, name="Top Secret Name", age_years=30)
    mock_patient.allergies = []
    mock_patient.medical_conditions = []
    mock_patient.drug_history = []
    mock_patient.lab_results = []
    mock_patient.genetic_markers = []
    
    # Mock result.scalar_one_or_none()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_patient
    mock_db.execute.return_value = mock_result
    
    state = {"patient_id": 99, "prescriptions": []}
    result = await fetch_patient_node(state)
    
    profile = result["patient_profile"]
    assert "Top Secret Name" not in profile["name"]
    assert profile["name"] == "Patient-99"
    assert profile["id"] == 99

@pytest.mark.asyncio
async def test_pgx_cyp2d6_poor_metabolizer():
    state = {
        "prescriptions": [PrescriptionData(drug_name="Codeine", dose="30mg", frequency="Q6H")],
        "patient_profile": {
            "genetic_markers": [{"gene": "CYP2D6", "phenotype": "Poor Metabolizer"}],
            "medical_conditions": [],
            "lab_results": []
        },
        "safety_flags": []
    }
    
    # Needs to mock openfda and clinical_service to prevent real external API calls during unit testing
    with patch("nova_guard.services.openfda.openfda_client") as mock_fda, \
         patch("nova_guard.services.clinical_services.clinical_service") as mock_clinical, \
         patch("nova_guard.services.bedrock.bedrock_client") as mock_bedrock:
        
        mock_fda.get_drug_label = AsyncMock(return_value=None)
        mock_fda.check_drug_recall = AsyncMock(return_value=[])
        mock_clinical.get_rxcui = AsyncMock(return_value="12345")
        mock_clinical.check_interactions = AsyncMock(return_value=[])
        mock_bedrock.get_ai_safety_flags = AsyncMock(return_value=[])
        
        result = await clinical_safety_node(state)
        flags = result.get("safety_flags", [])
        
        print(f"FLAGS RETURNED: {flags}")
        
        assert any(f.category == "pharmacogenomics" for f in flags)
        assert any("CYP2D6 Poor Metabolizer" in f.message for f in flags)
        pgx_flag = next(f for f in flags if f.category == "pharmacogenomics")
        assert pgx_flag.severity == "critical"
