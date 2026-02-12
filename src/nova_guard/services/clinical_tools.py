import os
import math
from openai import AsyncOpenAI
from typing import Dict, Any, List

class ClinicalTools:
    def __init__(self):
        self.ai = AsyncOpenAI(
            api_key=os.getenv("NOVA_API_KEY"),
            base_url="https://api.nova.amazon.com/v1"
        )

    # ========================================================================
    # 1. RENAL CALCULATOR (Precise Cockcroft-Gault)
    # ========================================================================
    @staticmethod
    def calculate_crcl(age: int, weight_kg: float, height_cm: float, scr: float, sex: str) -> Dict[str, Any]:
        """
        Implements 2026 Pharmacy Standards: 
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
        
        return {"crcl": round(crcl, 2), "weight_used": "AdjBW" if bmi > 30 else "IBW"}

    # ========================================================================
    # 2. INTERACTION SANDBOX (CYP450 Insights)
    # ========================================================================
    async def get_interaction_insights(self, drugs: List[str]) -> str:
        """Analyzes drug-drug interactions with metabolic pathway detail."""
        prompt = f"""
        Analyze interactions between: {', '.join(drugs)}.
        Provide 'CYP450 Insights': Identify specific enzymes (3A4, 2D6, etc.) 
        being inhibited or induced. Explain the clinical consequence.
        Format: JSON with 'severity', 'mechanism', and 'action'.
        """
        response = await self.ai.chat.completions.create(
            model="nova-2-micro-v1",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    # ========================================================================
    # 3. SUBSTITUTION ENGINE (2026 Biosimilar/Generic Rules)
    # ========================================================================
    async def get_equivalents(self, drug_name: str) -> str:
        """Maps therapeutic classmates and 2026 interchangeable biosimilars."""
        prompt = f"""
        Identify therapeutic equivalents for {drug_name}. 
        Include: 
        1. Classmates (e.g., other Statins).
        2. 2026 Interchangeable Biosimilars (Purple Book standards).
        3. Potency Ratios (e.g., 10mg A = 20mg B).
        Return a structured JSON table.
        """
        response = await self.ai.chat.completions.create(
            model="nova-2-lite-v1",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content

    # ========================================================================
    # 4. SAFETY MATRIX & COUNSELING (Nova Pro)
    # ========================================================================
    async def generate_safety_and_counseling(self, drug_name: str) -> str:
        """Generates the At-A-Glance Matrix and Patient Counseling Card."""
        prompt = f"""
        For the drug {drug_name}:
        1. MATRIX: Rate safety (RED/YELLOW/GREEN) for Pregnancy, Lactation, Geriatric, Pediatric.
        2. COUNSELING: 3 simple bullets (Purpose, How to take, Red Flags).
        3. BBW: Extract the current FDA Black Box Warning if exists.
        Return as JSON.
        """
        response = await self.ai.chat.completions.create(
            model="nova-2-pro-v1",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content