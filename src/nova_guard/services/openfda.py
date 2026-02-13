"""OpenFDA API client for comprehensive drug safety checks."""

import logging
import httpx
from typing import Optional, List
from datetime import datetime

from nova_guard.config import settings
from nova_guard.schemas.patient import SafetyFlag
from nova_guard.services.cache import cached_openfda

logger = logging.getLogger(__name__)


class OpenFDAClient:
    """Client for interacting with the OpenFDA Drug Label API."""
    
    BASE_URL = "https://api.fda.gov/drug/label.json"
    
    def __init__(self):
        self.api_key = settings.openfda_api_key
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    @cached_openfda
    async def get_drug_label(self, drug_name: str) -> Optional[dict]:
        """
        Fetch drug label from OpenFDA.
        
        Returns the first matching drug label or None if not found.
        """
        try:
            # 1. Try Exact Match First
            params = {
                "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
                "limit": 1
            }
            if self.api_key: params["api_key"] = self.api_key

            response = await self.client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("results"):
                return data["results"][0]
            return None
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.debug("Exact match failed for '%s', trying fuzzy search", drug_name)
                # 2. Fallback to Fuzzy Match (no quotes on fields)
                try:
                    params["search"] = f'openfda.brand_name:{drug_name} OR openfda.generic_name:{drug_name}'
                    response = await self.client.get(self.BASE_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
                    if data.get("results"):
                        return data["results"][0]
                except Exception as e2:
                    logger.debug("Fuzzy search failed for '%s', trying global search", drug_name)
                    # 3. Last Resort: Global Search (any field contains the name)
                    try:
                        params["search"] = f'"{drug_name}"'
                        response = await self.client.get(self.BASE_URL, params=params)
                        response.raise_for_status()
                        data = response.json()
                        if data.get("results"):
                            return data["results"][0]
                    except Exception as e3:
                         logger.warning("All OpenFDA searches failed for '%s': %s", drug_name, e3)
                         return None
            
            logger.error("OpenFDA API error for '%s': %s", drug_name, e)
            return None
        except Exception as e:
            logger.error("Unexpected OpenFDA error for '%s': %s", drug_name, e)
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
    
    async def check_drug_recall(self, drug_name: str) -> List[SafetyFlag]:
        """Check for active FDA drug recalls."""
        flags = []
        try:
            # Search for ongoing/pending recalls for this product
            params = {
                "search": f'product_description:"{drug_name}" AND status:(Ongoing OR Pending)',
                "limit": 5
            }
            if self.api_key: params["api_key"] = self.api_key
            
            url = "https://api.fda.gov/drug/enforcement.json"
            response = await self.client.get(url, params=params)
            
            # 404 means no recalls found, which is good
            if response.status_code == 404:
                return []
                
            response.raise_for_status()
            data = response.json()
            
            results = data.get("results", [])
            for recall in results:
                flags.append(SafetyFlag(
                    severity="critical",
                    category="recall",
                    message=f"🚨 RECALL ({recall.get('status')}): {recall.get('reason_for_recall')[:200]}...",
                    source="FDA Enforcement",
                    citation="https://api.fda.gov/drug/enforcement.json"
                ))
                
        except Exception as e:
            logger.warning("Recall check failed for '%s': %s", drug_name, e)
            
        return flags

    # ========================================================================
    # PATIENT-SPECIFIC CHECKS (ENHANCED)
    # ========================================================================
    
    async def check_pregnancy_safety(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check pregnancy safety with category parsing."""
        flags = []
        pregnancy_text = (self._extract_field(label, "pregnancy") or 
                          self._extract_field(label, "pregnancy_or_breast_feeding") or "").lower()
        
        if not pregnancy_text:
            return []

        # 1. Check for Category X/D/Warning keywords
        category = None
        for cat in ['category x', 'category d', 'category c', 'category b', 'category a']:
            if cat in pregnancy_text:
                category = cat.upper()
                break
        
        is_unsafe = any(w in pregnancy_text for w in ['contraindicated', 'must not be used', 'fetal harm', 'teratogenic'])
        
        if category == "CATEGORY X" or (is_unsafe and category == "CATEGORY D"):
            flags.append(SafetyFlag(
                severity="critical",
                category="pregnancy",
                message=f"🤰 PREGNANCY CONTRAINDICATION ({category or 'Unsafe'}): {pregnancy_text[:150]}...",
                source="OpenFDA",
                citation=citation
            ))
        elif category in ["CATEGORY D", "CATEGORY C"] or "risk" in pregnancy_text:
            flags.append(SafetyFlag(
                severity="warning",
                category="pregnancy",
                message=f"🤰 PREGNANCY RISK ({category or 'Caution'}): {pregnancy_text[:150]}...",
                source="OpenFDA",
                citation=citation
            ))
            
        return flags

    async def check_renal_dosing(self, label: dict, citation: str, creatinine_clearance: Optional[float]) -> List[SafetyFlag]:
        """Check if renal dose adjustment is needed."""
        flags = []
        if creatinine_clearance is None:
            return []
            
        text = (self._extract_field(label, "dosage_and_administration") or "").lower() + \
               (self._extract_field(label, "warnings") or "").lower()
               
        validation_keywords = ['renal', 'kidney', 'creatinine', 'impairment']
        if not any(k in text for k in validation_keywords):
            return []
            
        # If patient has low CrCl and label mentions renal adjustment
        if creatinine_clearance < 60:
            severity = "warning"
            if creatinine_clearance < 30: severity = "critical"
            
            # Extract a snippet
            snippet = "Refer to label for renal dosing."
            sentences = text.split('.')
            for s in sentences:
                if any(k in s for k in validation_keywords):
                    snippet = s.strip()
                    break
            
            flags.append(SafetyFlag(
                severity=severity,
                category="renal_dosing",
                message=f"🚽 RENAL ADJUSTMENT (CrCl {creatinine_clearance} mL/min): {snippet[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags

    async def check_pediatric_use(self, label: dict, citation: str, age_years: int) -> List[SafetyFlag]:
        """Check pediatric safety."""
        flags = []
        text = (self._extract_field(label, "pediatric_use") or "").lower()
        
        if not text: return []
        
        not_established = any(p in text for p in ['not established', 'not recommended', 'safety and effectiveness have not been established'])
        
        if not_established:
             flags.append(SafetyFlag(
                severity="warning",
                category="pediatric",
                message=f"👶 PEDIATRIC WARNING: Safety not established. {text[:150]}...",
                source="OpenFDA",
                citation=citation
            ))
        elif "weight" in text or "kg" in text:
             flags.append(SafetyFlag(
                severity="info",
                category="pediatric",
                message=f"👶 PEDIATRIC DOSING: Verify weight-based dosing. {text[:150]}...",
                source="OpenFDA",
                citation=citation
            ))
            
        return flags

    async def check_geriatric_use(self, label: dict, citation: str) -> List[SafetyFlag]:
        """Check geriatric considerations (Beers list check happens in Auditor)."""
        flags = []
        text = (self._extract_field(label, "geriatric_use") or "").lower()
        if not text: return []
        
        if any(w in text for w in ['hazardous', 'reduce dose', 'lower dose', 'start low']):
             flags.append(SafetyFlag(
                severity="warning",
                category="geriatric",
                message=f"👴 GERIATRIC PRECAUTION: {text[:200]}...",
                source="OpenFDA",
                citation=citation
            ))
        return flags
        
    async def check_drug_allergy(self, drug_name: str, label: dict, patient_allergies: List[dict]) -> List[SafetyFlag]:
        """
        Check for direct allergies and cross-reactivity.
        """
        flags = []
        drug_lower = drug_name.lower()
        generic_lower = (self._extract_field(label, "generic_name") or "").lower()
        
        # Cross-reactivity mapping
        cross_map = {
            'penicillin': ['amoxicillin', 'ampicillin', 'penicillin', 'augmentin'],
            'sulfa': ['sulfamethoxazole', 'trimethoprim', 'bactrim', 'septra'],
            'cephalosporin': ['cephalexin', 'keflex', 'cefazolin', 'ceftriaxone', 'rocephin']
        }

        for allergy in patient_allergies:
            allergen = allergy.get("allergen", "").lower()
            
            # 1. Direct Match
            if allergen in drug_lower or allergen in generic_lower:
                flags.append(SafetyFlag(
                    severity="critical",
                    category="allergy",
                    message=f"🚨 ALLERGY ALERT: Patient allergic to {allergen} (Direct match).",
                    source="Patient History",
                    citation="Patient Profile"
                ))
                continue
                
            # 2. Cross-Reactivity
            for class_name, drugs in cross_map.items():
                if class_name in allergen:
                    # If patient is allergic to a class (e.g. "Penicillin")
                    # Check if current drug is in that class list OR if generic name matches
                    is_related = any(d in drug_lower or d in generic_lower for d in drugs)
                    if is_related:
                         flags.append(SafetyFlag(
                            severity="warning",
                            category="cross_reactivity",
                            message=f"⚠️ CROSS-REACTIVITY: Patient has {class_name} allergy. Verify safety.",
                            source="Clinical Logic",
                            citation="Standard of Care"
                        ))
        return flags
    
    # ========================================================================
    # COMPREHENSIVE CHECK (runs all checks)
    # ========================================================================
    
    def check_duplicate_therapy(self, drug_name: str, current_drugs: List[dict], label: dict) -> List[SafetyFlag]:
        """Check for duplicate therapy (brand/generic)."""
        flags = []
        drug_lower = drug_name.lower()
        generic_lower = (self._extract_field(label, "generic_name") or "").lower()
        
        for drug in current_drugs:
            existing_name = drug.get("drug_name", "").lower()
            # Simplistic check: if names match or one contains the other
            if existing_name in drug_lower or drug_lower in existing_name:
                 flags.append(SafetyFlag(
                    severity="warning",
                    category="duplicate_therapy",
                    message=f"⚠️ DUPLICATE THERAPY: Patient already on {existing_name}.",
                    source="Patient History",
                    citation="Patient Profile"
                ))
            # Generic check would require fetching labels for *all* current drugs, skipping for now to keep speed high.
            # In a real system, we'd cache the generics of the patient's current meds.
            
        return flags

    # ========================================================================
    # COMPREHENSIVE CHECK (runs all checks)
    # ========================================================================
    
    async def run_all_checks(self, drug_name: str, patient_profile: dict) -> List[SafetyFlag]:
        """
        Run all comprehensive safety checks.
        """
        from nova_guard.services.rxnorm import rxnorm_client
        
        all_flags = []
        
        logger.info("Running advanced safety checks for: %s", drug_name)
        
        # Step 0: Check Recalls (Independent of Label)
        all_flags.extend(await self.check_drug_recall(drug_name))
        
        # Step 1: Normalize Drug Name (RxNorm)
        check_name = drug_name
        try:
            normalization = await rxnorm_client.normalize_drug_name(drug_name)
            rxnorm_citation = None
            
            if normalization["success"]:
                rxnorm_name = normalization.get("preferred_name") or normalization.get("generic_name")
                if rxnorm_name:
                    check_name = rxnorm_name
                
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
            logger.warning("RxNorm normalization failed for '%s': %s", drug_name, e)
        
        # Step 2: Fetch OpenFDA Label ONCE
        label = await self.get_drug_label(check_name)
        if not label:
            logger.warning("No OpenFDA label found for '%s'", check_name)
            return all_flags
            
        # Step 2b: Verify Label Match (Avoid False Positives from Global Search)
        # If we did a global search, we might get a label for "Drug A" that mentions "Drug B"
        # We need to warn the user if the returned label isn't actually for the requested drug.
        
        returned_brand = (self._extract_field(label, "brand_name") or "").lower()
        returned_generic = (self._extract_field(label, "generic_name") or "").lower()
        target_name = check_name.lower()
        
        # Check if target is in the returned names
        # We use a loose check because "Amodiaquine Hydrochloride" contains "Amodiaquine"
        match_found = (target_name in returned_brand) or (target_name in returned_generic)
        
        if not match_found:
             all_flags.append(SafetyFlag(
                severity="warning",
                category="mismatch",
                message=f"⚠️ INDIRECT MATCH: Found label for '{returned_brand or returned_generic}', which mentions '{check_name}'. Dosing may not apply directly.",
                source="OpenFDA",
                citation=self._get_citation(label)
            ))
            
        # Step 3: Get Citation
        citation = self._get_citation(label)
        
        # Step 4: Run Core FDA Checks
        all_flags.extend(await self.check_boxed_warning(label, citation))
        all_flags.extend(await self.check_contraindications(label, citation))
        all_flags.extend(await self.check_drug_interactions(label, citation))
        all_flags.extend(await self.check_adverse_reactions(label, citation))
        all_flags.extend(await self.check_warnings_and_cautions(label, citation))
        
        # Step 5: Advanced Patient-Specific Checks
        
        # Allergies (Enhanced)
        if patient_profile.get("allergies"):
            all_flags.extend(await self.check_drug_allergy(check_name, label, patient_profile["allergies"]))
            
        # Duplicates
        if patient_profile.get("current_drugs"):
            all_flags.extend(self.check_duplicate_therapy(check_name, patient_profile["current_drugs"], label))
        
        # Pregnancy / Nursing
        if patient_profile.get("is_pregnant"):
            all_flags.extend(await self.check_pregnancy_safety(label, citation))
        
        if patient_profile.get("is_nursing"):
            all_flags.extend(await self.check_nursing_safety(label, citation))
        
        # Age-based and Renal
        age = patient_profile.get("age_years")
        if age:
            if age < 18:
                all_flags.extend(await self.check_pediatric_use(label, citation, age))
            elif age >= 65:
                all_flags.extend(await self.check_geriatric_use(label, citation))
                
        # Renal (using eGFR as proxy for CrCl)
        egfr = patient_profile.get("egfr")
        if egfr:
            all_flags.extend(await self.check_renal_dosing(label, citation, float(egfr)))
        
        logger.info("Safety checks complete for '%s': %d flag(s)", drug_name, len(all_flags))
        
        return all_flags


# Singleton instance
openfda_client = OpenFDAClient()
