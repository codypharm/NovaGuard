
import httpx
import logging
import asyncio
from typing import List, Optional, Dict, Any
from nova_guard.schemas.patient import SafetyFlag

logger = logging.getLogger(__name__)

class ClinicalKnowledgeService:
    """
    Orchestrates high-precision clinical safety checks using specialized NLM/FDA APIs.
    Replacing broad OpenFDA checks with structured data from RxNav, DailyMed, and RxClass.
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
        self.rxnav_base = "https://rxnav.nlm.nih.gov/REST"
        self.dailymed_base = "https://dailymed.nlm.nih.gov/dailymed/services/v2"

    async def close(self):
        await self.client.aclose()

    # ========================================================================
    # 1. DRUG NAME NORMALIZATION (RxNav)
    # ========================================================================
    async def get_rxcui(self, drug_name: str) -> Optional[str]:
        """Resolves a drug name to its RxNorm Concept Unique Identifier (RxCUI)."""
        try:
            url = f"{self.rxnav_base}/rxcui.json"
            params = {"name": drug_name, "allsrc": 0} # 0 = strict match
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            # Extract RxCUI
            if "idGroup" in data and "rxnormId" in data["idGroup"]:
                return data["idGroup"]["rxnormId"][0]
                
            # Fallback: Approx search
            url = f"{self.rxnav_base}/approximateTerm.json"
            params = {"term": drug_name, "maxEntries": 1}
            resp = await self.client.get(url, params=params)
            data = resp.json()
            if "approximateGroup" in data and "candidate" in data["approximateGroup"]:
                return data["approximateGroup"]["candidate"][0]["rxcui"]
                
            logger.warning(f"Could not resolve RxCUI for '{drug_name}'")
            return None
            
        except Exception as e:
            logger.error(f"RxNav resolution failed for '{drug_name}': {e}")
            return None

    # ========================================================================
    # 2. DRUG-DRUG INTERACTIONS (RxNav)
    # ========================================================================
    async def check_interactions(self, input_rxcuis: List[str]) -> List[SafetyFlag]:
        """Checks for severe drug-drug interactions between a list of RxCUIs."""
        if len(input_rxcuis) < 2:
            return []
            
        flags = []
        try:
            # RxNav Interaction API supports list of RxCUIs
            ids_str = "+".join(input_rxcuis)
            url = f"{self.rxnav_base}/interaction/list.json"
            params = {"rxcuis": ids_str}
            
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            if "fullInteractionTypeGroup" not in data:
                return []
                
            for group in data["fullInteractionTypeGroup"]:
                for interaction_type in group.get("fullInteractionType", []):
                    # Each interaction pair
                    for interaction in interaction_type.get("interactionPair", []):
                        severity = interaction.get("severity", "N/A")
                        
                        # Only flag High severity to reduce noise
                        if severity != "High": 
                            continue
                            
                        desc = interaction.get("description")
                        concept = interaction.get("interactionConcept", [])
                        drug1 = concept[0].get("minConceptItem", {}).get("name")
                        drug2 = concept[1].get("minConceptItem", {}).get("name")
                        
                        flags.append(SafetyFlag(
                            severity="critical",
                            category="drug_interaction",
                            message=f"⛔ CRITICAL INTERACTION: {drug1} + {drug2} — {desc}",
                            source="RxNav Interaction API",
                            citation="https://rxnav.nlm.nih.gov/"
                        ))
                        
            return flags

        except Exception as e:
            logger.error(f"RxNav Interaction Check failed: {e}")
            return []

    # ========================================================================
    # 3. GERIATRIC / BEERS CRITERIA (RxClass)
    # ========================================================================
    async def check_beers_criteria(self, drug_name: str, age: int) -> Optional[SafetyFlag]:
        """Checks if a drug is on the Beers Criteria list (High Risk for Elderly)."""
        if age < 65:
            return None
            
        try:
            # RxClass API: Check membership in BEERS class
            # We search for the class by drug name relation
            url = f"{self.rxnav_base}/rxclass/class/byDrug.json"
            params = {"drugName": drug_name, "relSource": "BEERS"}
            
            resp = await self.client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            if "userInput" in data and "rxclassDrugInfoList" in data["rxclassDrugInfoList"]:
                classes = data["rxclassDrugInfoList"]["rxclassDrugInfoList"][0]["rxclassMinConceptItem"]["className"]
                
                return SafetyFlag(
                    severity="warning",
                    category="geriatric",
                    message=f"⚠️ BEERS CRITERIA: '{drug_name}' appears in '{classes}'. Potentially inappropriate for older adults.",
                    source="RxClass (Beers Criteria)",
                    citation="https://rxnav.nlm.nih.gov/RxClass"
                )
            
            return None

        except Exception as e:
            logger.warning(f"RxClass check failed for '{drug_name}': {e}")
            return None

    # ========================================================================
    # 4. BOXED WARNINGS (DailyMed / OpenFDA Fallback)
    # ========================================================================
    async def check_boxed_warning(self, drug_name: str, openfda_label: Optional[dict] = None) -> Optional[SafetyFlag]:
        """
        Retrieves Boxed Warning (Black Box).
        Prioritizes OpenFDA JSON as it is the most accessible structured source 
        derived from DailyMed SPLs.
        """
        # Note: Implementing true DailyMed REST parsing (XML) is complex.
        # OpenFDA provides this in JSON format at "boxed_warning".
        # We will use the passed openfda_label if available to avoid redundant calls.
        
        if not openfda_label:
            return None
            
        # Boxed warning is often a list of strings in OpenFDA
        warnings = openfda_label.get("boxed_warning", [])
        if not warnings:
            return None
            
        text = " ".join(warnings) if isinstance(warnings, list) else str(warnings)
        
        return SafetyFlag(
            severity="critical",
            category="boxed_warning",
            message=f"⚫ BOXED WARNING: {text[:300]}...",
            source="DailyMed / OpenFDA",
            citation=f"https://dailymed.nlm.nih.gov/"
        )

    # ========================================================================
    # 5. PHARMACOKINETICS (Section 12.3 - DailyMed / OpenFDA)
    # ========================================================================
    async def check_pharmacokinetics(self, drug_name: str, openfda_label: Optional[dict] = None) -> List[SafetyFlag]:
        """
        Extracts Section 12.3 (Pharmacokinetics) to check for Renal/Hepatic impairment logic.
        Detailed math often lives here.
        """
        if not openfda_label:
            return []
            
        flags = []
        
        # OpenFDA field for Section 12.3 is 'pharmacokinetics'
        pk_text = openfda_label.get("pharmacokinetics", [])
        if not pk_text:
             # Fallback to general Clinical Pharmacology (Section 12)
             pk_text = openfda_label.get("clinical_pharmacology", [])
             
        text = " ".join(pk_text) if isinstance(pk_text, list) else str(pk_text)
        text_lower = text.lower()
        
        # 1. Renal Impairment Check
        if any(k in text_lower for k in ["renal impairment", "creatinine clearance", "kidney disease", "dialysis"]):
            # Extract relevant snippet (naive sentence extraction specific to renal)
            snippet = "..."
            sentences = text.split('.')
            relevant_sentences = [s.strip() for s in sentences if any(k in s.lower() for k in ["renal", "creatinine", "dialysis"])]
            if relevant_sentences:
                snippet = ". ".join(relevant_sentences[:2]) # Take first 2 relevant sentences

            flags.append(SafetyFlag(
                severity="info", # Info because it needs correlation with patient data (handled in nodes.py logic or context)
                category="pharmacokinetics",
                message=f"🧬 PHARMACOKINETICS (Renal): {snippet[:300]}...",
                source="DailyMed (Section 12.3)",
                citation="https://dailymed.nlm.nih.gov/"
            ))
            
        # 2. Hepatic Impairment Check
        if any(k in text_lower for k in ["hepatic impairment", "liver disease", "cirrhosis", "child-pugh"]):
            # Extract relevant snippet
            snippet = "..."
            sentences = text.split('.')
            relevant_sentences = [s.strip() for s in sentences if any(k in s.lower() for k in ["hepatic", "liver", "cirrhosis"])]
            if relevant_sentences:
                snippet = ". ".join(relevant_sentences[:2])

            flags.append(SafetyFlag(
                severity="info",
                category="pharmacokinetics",
                message=f"🧬 PHARMACOKINETICS (Hepatic): {snippet[:300]}...",
                source="DailyMed (Section 12.3)",
                citation="https://dailymed.nlm.nih.gov/"
            ))
            
        return flags

    # ========================================================================
    # 6. RENAL DOSING (Section 12.3 + Dosage)
    # ========================================================================
    async def check_renal_dosing(self, drug_name: str, label: dict, patient_profile: dict) -> List[SafetyFlag]:
        """
        Check if renal dose adjustment is needed based on eGFR/CrCl.
        
        DATA SOURCE: Using an OpenFDA-indexed label (JSON representation of DailyMed SPL).
        - Section 12.3: `label.get("pharmacokinetics")`
        - Section 2:    `label.get("dosage_and_administration")`
        - Section 5:    `label.get("warnings")`
        
        This avoids complex HL7/XML parsing of raw DailyMed responses by using the FDA's
        JSON index of the same SPL data.
        """
        flags = []
        if not patient_profile: return []
        
        egfr = patient_profile.get("egfr")
        if egfr is None:
             return []
        
        creatinine_clearance = float(egfr)
            
        # Extract text from Dosage and Warnings
        def _get_text(lbl, field):
            val = lbl.get(field)
            if isinstance(val, list): return " ".join(val)
            return val or ""

        text = (_get_text(label, "dosage_and_administration") or "").lower() + \
               (_get_text(label, "warnings") or "").lower() + \
               (_get_text(label, "pharmacokinetics") or "").lower()
               
        validation_keywords = ['renal', 'kidney', 'creatinine', 'impairment', 'dialysis', 'gfr']
        if not any(k in text for k in validation_keywords):
            return []
            
        # If patient has low CrCl (< 60) and label mentions renal adjustment
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
                message=f"🚽 RENAL ADJUSTMENT (CrCl {creatinine_clearance} mL/min): {snippet[:300]}...",
                source="DailyMed (Dosage/PK)",
                citation="https://dailymed.nlm.nih.gov/"
            ))
        return flags

    # ========================================================================
    # 7. CONTRAINDICATIONS, PREGNANCY, ALLERGY (Migrated from OpenFDA)
    # ========================================================================
    
    def _extract_field(self, label: dict, field: str) -> Optional[str]:
        """Extract a field from the drug label, joining arrays if needed."""
        value = label.get(field)
        if isinstance(value, list):
            return " ".join(value)
        return value

    def get_label_field(self, label: dict, field_name: str) -> str:
        """Public accessor for label sections (e.g., contraindications, warnings)."""
        return self._extract_field(label, field_name) or "—"

    async def check_contraindications(self, drug_name: str, label: dict) -> List[SafetyFlag]:
        """Check for contraindications in the label."""
        flags = []
        contraindications = self._extract_field(label, "contraindications")
        
        if contraindications:
            flags.append(SafetyFlag(
                severity="critical",
                category="contraindication",
                message=f"⛔ CONTRAINDICATION: {contraindications[:300]}...",
                source="DailyMed / OpenFDA",
                citation="https://dailymed.nlm.nih.gov/"
            ))
        return flags
    
    async def check_pregnancy_safety(self, drug_name: str, label: dict, patient_profile: dict) -> List[SafetyFlag]:
        """
        Check pregnancy safety using FDA Categories and keywords.
        """
        flags = []
        # Only check if patient is pregnant
        if not patient_profile or not patient_profile.get("is_pregnant"):
            return []

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
        
        citation = "https://dailymed.nlm.nih.gov/"
        
        if category == "CATEGORY X" or (is_unsafe and category == "CATEGORY D"):
            flags.append(SafetyFlag(
                severity="critical",
                category="pregnancy",
                message=f"🤰 PREGNANCY CONTRAINDICATION ({category or 'Unsafe'}): {pregnancy_text[:150]}...",
                source="DailyMed / OpenFDA",
                citation=citation
            ))
        elif category in ["CATEGORY D", "CATEGORY C"] or "risk" in pregnancy_text:
            flags.append(SafetyFlag(
                severity="warning",
                category="pregnancy",
                message=f"🤰 PREGNANCY RISK ({category or 'Caution'}): {pregnancy_text[:150]}...",
                source="DailyMed / OpenFDA",
                citation=citation
            ))
            
        return flags

    async def check_drug_allergy(self, drug_name: str, label: dict, patient_profile: dict) -> List[SafetyFlag]:
        """
        Check for direct allergies and cross-reactivity using RxClass.
        Fetches drug classes (VA, EPC, PE) to detect if patient is allergic to the class (e.g., 'Penicillins').
        """
        flags = []
        if not patient_profile or not patient_profile.get("allergies"):
             return []
             
        patient_allergies = patient_profile["allergies"]
        
        # 1. Direct Match (Brand/Generic Name)
        generic = (self._extract_field(label, "generic_name") or "").lower()
        brand = (self._extract_field(label, "brand_name") or "").lower()
        
        for allergy in patient_allergies:
            allergen = allergy.get("allergen", "").lower()
            if allergen in brand or allergen in generic:
                flags.append(SafetyFlag(
                    severity="critical",
                    category="allergy",
                    message=f"🚨 ALLERGY ALERT: Patient allergic to '{allergen}' (Direct match with prescribed drug).",
                    source="Patient History",
                    citation="Patient Profile"
                ))

        # 2. Cross-Reactivity (Dynamic RxClass Lookup + Fallback)
        rxcui = await self.get_rxcui(drug_name)
        
        # Try Dynamic Check First
        dynamic_check_success = False
        if rxcui:
            try:
                # Fetch all classes for this drug
                url = f"{self.rxnav_base}/rxclass/class/byRxcui.json"
                params = {"rxcui": rxcui}
                resp = await self.client.get(url, params=params)
                data = resp.json()
                
                drug_classes = []
                if "rxclassDrugInfoList" in data and "rxclassDrugInfoList" in data["rxclassDrugInfoList"]:
                    for info in data["rxclassDrugInfoList"]["rxclassDrugInfoList"]:
                        concept = info.get("rxclassMinConceptItem", {})
                        cls_name = concept.get("className", "")
                        if cls_name:
                            drug_classes.append(cls_name.lower())
                
                if drug_classes:
                    dynamic_check_success = True
                    # Check if any patient allergy matches a drug class
                    for allergy in patient_allergies:
                        allergen = allergy.get("allergen", "").lower()
                        matched_class = next((c for c in drug_classes if allergen in c), None)
                        
                        if matched_class:
                            flags.append(SafetyFlag(
                                severity="warning",
                                category="cross_reactivity",
                                message=f"⚠️ CROSS-REACTIVITY: drug '{drug_name}' belongs to class '{matched_class}', which matches patient allergy '{allergen}'.",
                                source="RxClass (Chemical Structure)",
                                citation="https://rxnav.nlm.nih.gov/RxClass"
                            ))
                            
            except Exception as e:
                logger.warning(f"RxClass allergy check failed for '{drug_name}' (Network/API Error): {e}")

        # Fallback to Nova Lite (LLM) if dynamic check failed or yielded no class info
        if not dynamic_check_success:
            logger.info(f"Using Nova Lite fallback for allergy check: {drug_name}")
            from nova_guard.services.bedrock import bedrock_client
            import json

            for allergy in patient_allergies:
                allergen = allergy.get("allergen", "").lower()
                
                system_prompt = "You are a conservative clinical pharmacist. Output JSON only."
                user_query = f"""
                Patient Allergy: {allergen}
                Prescribed Drug: {drug_name}
                
                Is there a clinically significant cross-reactivity or direct allergy risk?
                Return ONLY valid JSON: {{"risk": boolean, "reason": "short explanation (max 15 words)"}}
                """
                
                response = await bedrock_client.chat_lite(system_prompt, user_query)
                
                try:
                    # Clean JSON output if needed
                    text = response.strip()
                    if "```" in text:
                        start = text.find("{")
                        end = text.rfind("}")
                        if start != -1 and end != -1:
                            text = text[start:end+1]
                    
                    data = json.loads(text)
                    if data.get("risk"):
                        flags.append(SafetyFlag(
                            severity="warning",
                            category="cross_reactivity",
                            message=f"⚠️ {data.get('reason')} (AI-Verified Risk)",
                            source="Nova Lite (Clinical Reasoning)",
                            citation="Clinical Pharmacology"
                        ))
                except Exception as e:
                    logger.warning(f"Nova Lite allergy check failed: {e}")

        return flags

# Singleton instance
clinical_service = ClinicalKnowledgeService()
