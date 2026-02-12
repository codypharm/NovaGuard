from typing import Dict, Any, List
from nova_guard.services.bedrock import bedrock_client

class ClinicalTools:
    def __init__(self):
        self.bedrock = bedrock_client

    # ========================================================================
    # 1. RENAL CALCULATOR (AI-Enhanced Cockcroft-Gault)
    # ========================================================================
    async def calculate_crcl(self, age: int, weight_kg: float, height_cm: float, scr: float, sex: str, drug_name: str = None) -> Dict[str, Any]:
        """
        Implements 2026 Pharmacy Standards with AI Recommendation.
        Uses IBW if Actual > IBW, and AdjBW if BMI > 30.
        """
        # 1. Calculate IBW (Devine)
        ht_in = height_cm / 2.54
        ibw = (50 if sex == "male" else 45.5) + 2.3 * (ht_in - 60)
        
        # 2. Determine Dosing Weight
        bmi = weight_kg / ((height_cm/100)**2)
        if weight_kg < ibw:
            dosing_weight = weight_kg # Use Actual if underweight
        elif bmi > 30:
            dosing_weight = ibw + 0.4 * (weight_kg - ibw) # Adjusted BW for Obese
        else:
            dosing_weight = ibw # Standard IBW
            
        # 3. Cockcroft-Gault
        crcl = ((140 - age) * dosing_weight) / (72 * scr)
        if sex == "female": crcl *= 0.85
        
        result = {
            "crcl": round(crcl, 2), 
            "weight_used": "AdjBW" if bmi > 30 else ("IBW" if weight_kg >= ibw else "Actual BW")
        }

        # 4. Integrate AI Recommendation if drug_name provided
        if drug_name:
            result["recommendation"] = await self.bedrock.get_renal_adjustment(drug_name, result["crcl"], result["weight_used"])
        
        return result

    # ========================================================================
    # 2. INTERACTION SANDBOX (CYP450 Insights)
    # ========================================================================
    async def get_interaction_insights(self, drugs: List[str]) -> str:
        """Analyzes drug-drug interactions with metabolic pathway detail."""
        return await self.bedrock.get_interaction_insights(drugs)

    # ========================================================================
    # 3. SUBSTITUTION ENGINE (2026 Biosimilar/Generic Rules)
    # ========================================================================
    async def get_equivalents(self, drug_name: str) -> str:
        """Maps therapeutic classmates and 2026 interchangeable biosimilars."""
        return await self.bedrock.get_equivalents(drug_name)

    # ========================================================================
    # 4. SAFETY MATRIX & COUNSELING (Nova Pro)
    # ========================================================================
    async def generate_safety_and_counseling(self, drug_name: str) -> str:
        """Generates the At-A-Glance Matrix and Patient Counseling Card."""
        return await self.bedrock.get_safety_and_counseling(drug_name)