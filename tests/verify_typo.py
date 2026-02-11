import asyncio
from nova_guard.services.rxnorm import rxnorm_client
from nova_guard.services.openfda import openfda_client

async def test_typo():
    print("🧪 Testing Typo Correction (Amodiapine -> Amodiaquine)...\n")
    
    # 1. Test RxNorm normalization directly
    result = await rxnorm_client.normalize_drug_name("amodiapine")
    print(f"RxNorm Result: {result}")
    
    if result["success"]:
        print(f"✅ Typo Corrected: {result['input_name']} -> {result['preferred_name']} (RxCUI: {result['rxcui']})")
    else:
        print(f"❌ RxNorm Failed: {result.get('error')}")

    # 2. Test OpenFDA flow with typo
    print("\n🧪 Testing OpenFDA flow with typo...")
    flags = await openfda_client.run_all_checks("amodiapine", {})
    
    if len(flags) > 0:
        print(f"✅ OpenFDA found data for typo'd name (Flags: {len(flags)})")
        for f in flags:
            print(f" - {f.category}: {f.message[:50]}...")
    else:
        print("❌ OpenFDA returned no flags for typo'd name")

    await rxnorm_client.close()
    await openfda_client.client.aclose()

if __name__ == "__main__":
    asyncio.run(test_typo())
