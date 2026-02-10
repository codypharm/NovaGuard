import asyncio
from nova_guard.services.openfda import openfda_client

async def test_validation():
    print("🧪 Starting Validation Tools Test...\n")
    
    # Test 1: Allergy Cross-Reactivity
    print("--- Test 1: Allergy (Amoxicillin vs Penicillin) ---")
    mock_profile_allergy = {
        "allergies": [{"allergen": "Penicillin", "severity": "severe"}]
    }
    # We need to fetch the label first to pass it, or just call run_all_checks
    # Let's call run_all_checks for integration test
    flags = await openfda_client.run_all_checks("Amoxicillin", mock_profile_allergy)
    for f in flags:
        if f.category == "cross_reactivity":
            print(f"✅ PASSED: Detected cross-reactivity: {f.message}")
            
    # Test 2: Pregnancy (Lisinopril)
    print("\n--- Test 2: Pregnancy (Lisinopril - Category D) ---")
    mock_profile_preg = {
        "is_pregnant": True
    }
    flags = await openfda_client.run_all_checks("Lisinopril", mock_profile_preg)
    for f in flags:
        if f.category == "pregnancy":
             print(f"✅ PASSED: Detected pregnancy warning: {f.message[:100]}...")

    # Test 3: Renal (Gabapentin)
    print("\n--- Test 3: Renal (Gabapentin - CrCl 20) ---")
    mock_profile_renal = {
        "egfr": 20
    }
    flags = await openfda_client.run_all_checks("Gabapentin", mock_profile_renal)
    for f in flags:
        if f.category == "renal_dosing":
             print(f"✅ PASSED: Detected renal adjustment: {f.message[:100]}...")
             
    # Test 4: Recall (Valsartan - strict check might fail if no active recall, but logic runs)
    print("\n--- Test 4: Recall Check (Valsartan) ---")
    flags = await openfda_client.run_all_checks("Valsartan", {})
    recall_found = any(f.category == "recall" for f in flags)
    print(f"ℹ️ Recall check ran. Found recalls: {recall_found}")

    await openfda_client.close()

if __name__ == "__main__":
    asyncio.run(test_validation())
