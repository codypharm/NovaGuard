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
    
    # ========================================================================
    # CORE SAFETY CHECKS
    # ========================================================================
    
    async def check_boxed_warning(self, drug_name: str) -> List[SafetyFlag]:
        """Check for FDA Black Box warnings (most serious)."""
        label = await self.get_drug_label(drug_name)
        flags = []
        
        if not label:
            return flags
        
        boxed_warning = self._extract_field(label, "boxed_warning")
        if boxed_warning:
            flags.append(SafetyFlag(
                severity="critical",
                category="boxed_warning",
                message=f"⚫ BLACK BOX WARNING: {boxed_warning[:200]}...",
                source="OpenFDA"
            ))
        
        return flags
    
    async def check_contraindications(self, drug_name: str) -> List[SafetyFlag]:
        """Check for contraindications (conditions where drug must NOT be used)."""
        label = await self.get_drug_label(drug_name)
        flags = []
        
        if not label:
            return flags
        
        contraindications = self._extract_field(label, "contraindications")
        if contraindications:
            flags.append(SafetyFlag(
                severity="critical",
                category="contraindication",
                message=f"⛔ CONTRAINDICATION: {contraindications[:200]}...",
                source="OpenFDA"
            ))
        
        return flags
    
    async def check_drug_interactions(self, drug_name: str) -> List[SafetyFlag]:
        """Check for known drug interactions."""
        label = await self.get_drug_label(drug_name)
        flags = []
        
        if not label:
            return flags
        
        interactions = self._extract_field(label, "drug_interactions")
        if interactions:
            flags.append(SafetyFlag(
                severity="warning",
                category="drug_interaction",
                message=f"💊 DRUG INTERACTIONS: {interactions[:200]}...",
                source="OpenFDA"
            ))
        
        return flags
    
    async def check_adverse_reactions(self, drug_name: str) -> List[SafetyFlag]:
        """Check for known adverse reactions."""
        label = await self.get_drug_label(drug_name)
        flags = []
        
        if not label:
            return flags
        
        adverse = self._extract_field(label, "adverse_reactions")
        if adverse:
            flags.append(SafetyFlag(
                severity="info",
                category="adverse_reaction",
                message=f"⚠️ ADVERSE REACTIONS: {adverse[:200]}...",
                source="OpenFDA"
            ))
        
        return flags
    
    async def check_warnings_and_cautions(self, drug_name: str) -> List[SafetyFlag]:
        """Check for general warnings and cautions."""
        label = await self.get_drug_label(drug_name)
        flags = []
        
        if not label:
            return flags
        
        warnings = self._extract_field(label, "warnings_and_cautions") or \
                   self._extract_field(label, "warnings")
        
        if warnings:
            flags.append(SafetyFlag(
                severity="warning",
                category="warning",
                message=f"⚠️ WARNINGS: {warnings[:200]}...",
                source="OpenFDA"
            ))
        
        return flags
    
    # ========================================================================
    # PATIENT-SPECIFIC CHECKS
    # ========================================================================
    
    async def check_pregnancy_safety(self, drug_name: str) -> List[SafetyFlag]:
        """Check pregnancy safety warnings."""
        label = await self.get_drug_label(drug_name)
        flags = []
        
        if not label:
            return flags
        
        pregnancy = self._extract_field(label, "pregnancy") or \
                    self._extract_field(label, "pregnancy_or_breast_feeding") or \
                    self._extract_field(label, "teratogenic_effects")
        
        if pregnancy:
            flags.append(SafetyFlag(
                severity="warning",
                category="pregnancy",
                message=f"🤰 PREGNANCY: {pregnancy[:200]}...",
                source="OpenFDA"
            ))
        
        return flags
    
    async def check_nursing_safety(self, drug_name: str) -> List[SafetyFlag]:
        """Check safety for nursing mothers."""
        label = await self.get_drug_label(drug_name)
        flags = []
        
        if not label:
            return flags
        
        nursing = self._extract_field(label, "nursing_mothers")
        if nursing:
            flags.append(SafetyFlag(
                severity="warning",
                category="nursing",
                message=f"🤱 NURSING: {nursing[:200]}...",
                source="OpenFDA"
            ))
        
        return flags
    
    async def check_pediatric_use(self, drug_name: str) -> List[SafetyFlag]:
        """Check pediatric use warnings."""
        label = await self.get_drug_label(drug_name)
        flags = []
        
        if not label:
            return flags
        
        pediatric = self._extract_field(label, "pediatric_use")
        if pediatric:
            flags.append(SafetyFlag(
                severity="info",
                category="pediatric",
                message=f"👶 PEDIATRIC: {pediatric[:200]}...",
                source="OpenFDA"
            ))
        
        return flags
    
    async def check_geriatric_use(self, drug_name: str) -> List[SafetyFlag]:
        """Check geriatric use considerations."""
        label = await self.get_drug_label(drug_name)
        flags = []
        
        if not label:
            return flags
        
        geriatric = self._extract_field(label, "geriatric_use")
        if geriatric:
            flags.append(SafetyFlag(
                severity="info",
                category="geriatric",
                message=f"👴 GERIATRIC: {geriatric[:200]}...",
                source="OpenFDA"
            ))
        
        return flags
    
    # ========================================================================
    # COMPREHENSIVE CHECK (runs all checks)
    # ========================================================================
    
    async def run_all_checks(self, drug_name: str, patient_profile: dict) -> List[SafetyFlag]:
        """
        Run all comprehensive safety checks.
        
        This is the main function called by the openfda_node.
        """
        all_flags = []
        
        print(f"💊 Running OpenFDA checks for: {drug_name}")
        
        # Core safety checks (always run)
        all_flags.extend(await self.check_boxed_warning(drug_name))
        all_flags.extend(await self.check_contraindications(drug_name))
        all_flags.extend(await self.check_drug_interactions(drug_name))
        all_flags.extend(await self.check_adverse_reactions(drug_name))
        all_flags.extend(await self.check_warnings_and_cautions(drug_name))
        
        # Patient-specific checks (conditional)
        if patient_profile.get("is_pregnant"):
            all_flags.extend(await self.check_pregnancy_safety(drug_name))
        
        if patient_profile.get("is_nursing"):
            all_flags.extend(await self.check_nursing_safety(drug_name))
        
        if patient_profile.get("age_years"):
            age = patient_profile["age_years"]
            if age < 18:
                all_flags.extend(await self.check_pediatric_use(drug_name))
            elif age >= 65:
                all_flags.extend(await self.check_geriatric_use(drug_name))
        
        print(f"✅ OpenFDA checks complete: {len(all_flags)} flag(s) found")
        
        return all_flags


# Singleton instance
openfda_client = OpenFDAClient()
