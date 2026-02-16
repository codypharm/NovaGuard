
import asyncio
import logging
from nova_guard.services.clinical_services import clinical_service

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_clinical_service():
    print("WARNING: This test makes real API calls to RxNav/RxClass.")
    
    # 1. Test RxCUI Normalization
    drug_name = "Carbamazepine"
    rxcui = await clinical_service.get_rxcui(drug_name)
    print(f"RxCUI for {drug_name}: {rxcui}")
    assert rxcui is not None, "Failed to resolve RxCUI"

    # 2. Test Beers Criteria
    beers_flag = await clinical_service.check_beers_criteria(drug_name, 75)
    print(f"Beers Criteria for {drug_name} (Age 75): {beers_flag}")
    assert beers_flag is not None, "Failed to check Beers Criteria"

    # 3. Test Interaction Check (Need 2 drugs)
    # Warfarin (11289) + Aspirin (1191)
    interactions = await clinical_service.check_interactions(["11289", "1191"])
    print(f"Interactions for Warfarin + Aspirin: {len(interactions)}")
    for flag in interactions:
        print(f" - {flag.message}")
        
    await clinical_service.close()

if __name__ == "__main__":
    asyncio.run(test_clinical_service())
