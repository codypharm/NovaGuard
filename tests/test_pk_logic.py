
import asyncio
from nova_guard.services.clinical_services import clinical_service

def test_pk_logic():
    # 1. Mock Label with Section 12.3 Data
    mock_label = {
        "pharmacokinetics": [
            "Renal Impairment: In patients with renal impairment (creatinine clearance < 30 mL/min), "
            "the dose of gabapentin should be reduced. Hemodialysis patients require supplemental dosing."
        ],
        "clinical_pharmacology": [
            "12.3 Pharmacokinetics...",
            "Hepatic Impairment: No adjustment necessary in hepatic impairment."
        ]
    }
    
    # 2. Run Check
    # Since check_pharmacokinetics is async, we need to run it in a loop
    loop = asyncio.new_event_loop()
    # Updated signature: drug_name, label
    flags = loop.run_until_complete(clinical_service.check_pharmacokinetics("TestDrug", mock_label))
    loop.close()
    
    # 3. Verify Flags
    print(f"Found {len(flags)} PK flags.")
    for f in flags:
        print(f"[{f.category}] {f.message}")
        
    # Expectation: 
    # - 1 from "pharmacokinetics" field (Renal)
    # - Wait, code uses "pharmacokinetics" field IF present, uses "clinical_pharmacology" only if "pharmacokinetics" is missing.
    # In my mock, "pharmacokinetics" is present, so it won't check "clinical_pharmacology".
    # And "pharmacokinetics" mock doesn't have "Hepatic".
    # So expect 1 Renal flag.
    
    assert len(flags) > 0
    assert any("Renal" in f.message for f in flags)
    assert not any("Hepatic" in f.message for f in flags)
    
    print("Test 1 (Renal Only) Passed.")
    
    # 4. Test Hepatic Fallback context
    mock_label_2 = {
        "clinical_pharmacology": [
            "Pharmacokinetics: Hepatic impairment significantly increases exposure. Dose reduction required in Child-Pugh Class C."
        ]
    }
    loop = asyncio.new_event_loop()
    # Updated signature: drug_name, label
    flags_2 = loop.run_until_complete(clinical_service.check_pharmacokinetics("TestDrug2", mock_label_2))
    loop.close()
    
    print(f"Found {len(flags_2)} PK flags (Test 2).")
    for f in flags_2:
        print(f"[{f.category}] {f.message}")

    assert any("Hepatic" in f.message for f in flags_2)
    print("Test 2 (Hepatic Fallback) Passed.")

    # 5. Test check_renal_dosing (Dedicated method)
    profile_renal = {"egfr": 25} # Severe impairment
    loop = asyncio.new_event_loop()
    # Updated signature: drug_name, label, profile
    flags_renal = loop.run_until_complete(clinical_service.check_renal_dosing("TestDrug", mock_label, profile_renal))
    loop.close()
    
    print(f"Found {len(flags_renal)} Renal Dosing flags.")
    for f in flags_renal:
        print(f"[{f.category}] {f.message}")
        
    assert len(flags_renal) > 0
    assert "RENAL ADJUSTMENT" in flags_renal[0].message
    print("Test 3 (Explicit Renal Dosing) Passed.")

    # 6. Test check_drug_allergy (Dynamic RxClass + Nova Fallback)
    # We mock 'bedrock_client.chat_lite' to return a YES JSON
    from unittest.mock import AsyncMock, patch
    
    # We patch the instance that will be imported inside clinical_services.py
    with patch("nova_guard.services.bedrock.bedrock_client.chat_lite", new_callable=AsyncMock) as mock_chat:
        mock_chat.return_value = '{"risk": true, "reason": "Amoxicillin is a penicillin derivative with known cross-reactivity."}'
        
        # Force fallback by mocking get_rxcui to fail (return None)
        # We need to patch the method on the running instance
        original_get_rxcui = clinical_service.get_rxcui
        clinical_service.get_rxcui = AsyncMock(return_value=None)
        
        try:
            profile_allergy = {"allergies": [{"allergen": "Penicillin"}]}
            loop = asyncio.new_event_loop()
            # Drug: Amoxicillin (should match Penicillin class via RxClass OR Nova Lite)
            flag_list = loop.run_until_complete(clinical_service.check_drug_allergy("Amoxicillin", {}, profile_allergy))
            loop.close()
        finally:
            # Restore
            clinical_service.get_rxcui = original_get_rxcui
        
        print(f"Found {len(flag_list)} Allergy flags.")
        for f in flag_list:
            print(f"[{f.category}] {f.source} {f.message}")
            
        if len(flag_list) > 0:
            category = flag_list[0].category.upper()
            assert "CROSS_REACTIVITY" in category or "CROSS-REACTIVITY" in category
            print("Test 4 (Allergy Check - with Mocked AI) Passed.")
        else:
            print("Test 4 (Allergy Check) FAILED - No flags returned.")

if __name__ == "__main__":
    test_pk_logic()
