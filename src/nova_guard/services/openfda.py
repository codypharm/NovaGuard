"""OpenFDA API client for comprehensive drug safety checks."""

import httpx
from typing import Optional, List
from datetime import datetime

from nova_guard.config import settings
from nova_guard.schemas.patient import SafetyFlag


class OpenFDAClient:
    """Client for interacting with the OpenFDA Drug Label API."""
    
    BASE_URL = "https://api.fda.gov/drug/label.json"
    
    def __init__(self):
        self.api_key = settings.openfda_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def get_drug_label(self, drug_name: str) -> Optional[dict]:
        """
        Fetch drug label from OpenFDA.
        
        Returns the first matching drug label or None if not found.
        """
        params = {
            "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
            "limit": 1
        }
        
        if self.api_key:
            params["api_key"] = self.api_key
        
        try:
            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("results"):
                return data["results"][0]
            return None
            
        except httpx.HTTPError as e:
            print(f"❌ OpenFDA API error: {e}")
            return None
    
    def _extract_field(self, label: dict, field: str) -> Optional[str]:
        """Extract a field from the drug label, joining arrays if needed."""
        value = label.get(field)
        if isinstance(value, list):
            return " ".join(value)
        return value

    def _get_citation(self, label: dict) -> Optional[str]:
        """Generate DailyMed citation URL from SPL Set ID."""
        openfda = label.get("openfda", {})
        # openfda fields are lists, take the first one
        spl_set_id = openfda.get("spl_set_id", [None])[0]
        
        if spl_set_id:
            return f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={spl_set_id}"
        return "https://open.fda.gov/"
    
    # ========================================================================
    # CORE SAFETY CHECKS
    # ========================================================================
    
    # ========================================================================
    # CORE SAFETY CHECKS
    # ========================================================================
    
    async def check_boxed_warning(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check for FDA Black Box warnings (most serious)."""
        flags = []
        boxed_warning = self._extract_field(label, "boxed_warning")
        
        if boxed_warning:
            flags.append(SafetyFlag(
                severity="critical",
                category="boxed_warning",
                message=f"⚫ BLACK BOX WARNING: {boxed_warning[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
    
    async def check_contraindications(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check for contraindications."""
        flags = []
        contraindications = self._extract_field(label, "contraindications")
        
        if contraindications:
            flags.append(SafetyFlag(
                severity="critical",
                category="contraindication",
                message=f"⛔ CONTRAINDICATION: {contraindications[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
    
    async def check_drug_interactions(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check for known drug interactions."""
        flags = []
        interactions = self._extract_field(label, "drug_interactions")
        
        if interactions:
            flags.append(SafetyFlag(
                severity="warning",
                category="drug_interaction",
                message=f"💊 DRUG INTERACTIONS: {interactions[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
    
    async def check_adverse_reactions(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check for known adverse reactions."""
        flags = []
        adverse = self._extract_field(label, "adverse_reactions")
        
        if adverse:
            flags.append(SafetyFlag(
                severity="info",
                category="adverse_reaction",
                message=f"⚠️ ADVERSE REACTIONS: {adverse[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
    
    async def check_warnings_and_cautions(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check for general warnings and cautions."""
        flags = []
        warnings = self._extract_field(label, "warnings_and_cautions") or \
                   self._extract_field(label, "warnings")
        
        if warnings:
            flags.append(SafetyFlag(
                severity="warning",
                category="warning",
                message=f"⚠️ WARNINGS: {warnings[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
    
    # ========================================================================
    # PATIENT-SPECIFIC CHECKS
    # ========================================================================
    
    async def check_pregnancy_safety(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check pregnancy safety warnings."""
        flags = []
        pregnancy = self._extract_field(label, "pregnancy") or \
                    self._extract_field(label, "pregnancy_or_breast_feeding") or \
                    self._extract_field(label, "teratogenic_effects")
        
        if pregnancy:
            flags.append(SafetyFlag(
                severity="warning",
                category="pregnancy",
                message=f"🤰 PREGNANCY: {pregnancy[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
    
    async def check_nursing_safety(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check safety for nursing mothers."""
        flags = []
        nursing = self._extract_field(label, "nursing_mothers")
        if nursing:
            flags.append(SafetyFlag(
                severity="warning",
                category="nursing",
                message=f"🤱 NURSING: {nursing[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
    
    async def check_pediatric_use(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check pediatric use warnings."""
        flags = []
        pediatric = self._extract_field(label, "pediatric_use")
        if pediatric:
            flags.append(SafetyFlag(
                severity="info",
                category="pediatric",
                message=f"👶 PEDIATRIC: {pediatric[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
    
    async def check_geriatric_use(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check geriatric use considerations."""
        flags = []
        geriatric = self._extract_field(label, "geriatric_use")
        if geriatric:
            flags.append(SafetyFlag(
                severity="info",
                category="geriatric",
                message=f"👴 GERIATRIC: {geriatric[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
    
    # ========================================================================
    # COMPREHENSIVE CHECK (runs all checks)
    # ========================================================================
    
    async def run_all_checks(self, drug_name: str, patient_profile: dict) -> List[SafetyFlag]:
        """
        Run all comprehensive safety checks.
        
        Main entry point that:
        1. Normalizes drug name (RxNorm)
        2. Fetches OpenFDA label (once)
        3. Generates citation
        4. Runs all check methods with cached label
        """
        from nova_guard.services.rxnorm import rxnorm_client
        
        all_flags = []
        
        print(f"💊 Running OpenFDA checks for: {drug_name}")
        
        # Step 1: Normalize Drug Name (RxNorm)
        check_name = drug_name
        try:
            normalization = await rxnorm_client.normalize_drug_name(drug_name)
            rxnorm_citation = None
            
            if normalization["success"]:
                rxnorm_name = normalization.get("preferred_name") or normalization.get("generic_name")
                if rxnorm_name:
                    print(f"✅ Normalized '{drug_name}' -> '{rxnorm_name}' (RxCUI: {normalization['rxcui']})")
                    check_name = rxnorm_name
                
                # RxNorm citation
                if normalization.get("rxcui"):
                     rxnorm_citation = f"https://rxnav.nlm.nih.gov/REST/rxcui/{normalization['rxcui']}"
                
                all_flags.append(SafetyFlag(
                    severity="info",
                    category="normalization",
                    message=f"Drug normalized to '{check_name}' (RxNorm ID: {normalization['rxcui']})",
                    source="RxNorm",
                    citation=rxnorm_citation
                ))
        except Exception as e:
            print(f"⚠️ RxNorm normalization failed: {e}")
        
        # Step 2: Fetch OpenFDA Label ONCE
        label = await self.get_drug_label(check_name)
        if not label:
            print(f"⚠️ No OpenFDA label found for '{check_name}'")
            return all_flags
            
        # Step 3: Get Citation
        citation = self._get_citation(label)
        
        # Step 4: Run Checks with Cached Label
        all_flags.extend(await self.check_boxed_warning(label, citation))
        all_flags.extend(await self.check_contraindications(label, citation))
        all_flags.extend(await self.check_drug_interactions(label, citation))
        all_flags.extend(await self.check_adverse_reactions(label, citation))
        all_flags.extend(await self.check_warnings_and_cautions(label, citation))
        
        # Patient-specific checks
        if patient_profile.get("is_pregnant"):
            all_flags.extend(await self.check_pregnancy_safety(label, citation))
        
        if patient_profile.get("is_nursing"):
            all_flags.extend(await self.check_nursing_safety(label, citation))
        
        if patient_profile.get("age_years"):
            age = patient_profile["age_years"]
            if age < 18:
                all_flags.extend(await self.check_pediatric_use(label, citation))
            elif age >= 65:
                all_flags.extend(await self.check_geriatric_use(label, citation))
        
        print(f"✅ OpenFDA checks complete: {len(all_flags)} flag(s) found")
        
        return all_flags


# Singleton instance
openfda_client = OpenFDAClient()
