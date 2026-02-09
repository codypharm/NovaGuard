"""RxNorm service for drug name normalization."""

import urllib.parse
import httpx
from typing import Dict, Any, Optional


class RxNormClient:
    """Client for interacting with the RxNav RxNorm API."""
    
    BASE_URL = "https://rxnav.nlm.nih.gov/REST"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
    
    async def normalize_drug_name(self, drug_name: str) -> Dict[str, Any]:
        """
        Normalize drug name using RxNorm API.
        Returns RxCUI, preferred name, ingredients, brand names, ATC classes, etc.
        """
        try:
            # Step 1: Find RxCUI
            encoded_name = urllib.parse.quote(drug_name)
            url = f"{self.BASE_URL}/drugs.json?name={encoded_name}"
            resp = await self.client.get(url)
            resp.raise_for_status()
            data = resp.json()
            
            concept_group = data.get("drugGroup", {}).get("conceptGroup", [])
            if not concept_group:
                return {"success": False, "error": "No match found in RxNorm", "raw_name": drug_name}
            
            # Prefer SCD/SBD/BN/IN
            # SCD = Semantic Clinical Drug, SBD = Semantic Branded Drug
            # BN = Brand Name, IN = Ingredient, PIN = Precise Ingredient
            target_ttys = ["SCD", "SBD", "BN", "IN", "PIN"]
            
            # Flatten all concepts
            all_concepts = []
            for group in concept_group:
                tty = group.get("tty")
                if tty in target_ttys and "conceptProperties" in group:
                    all_concepts.extend(group["conceptProperties"])
            
            if not all_concepts:
                # Fallback to any concept if preferred restricted types not found
                for group in concept_group:
                    if "conceptProperties" in group:
                        all_concepts.extend(group["conceptProperties"])
            
            if not all_concepts:
                 return {"success": False, "error": "No concepts found", "raw_name": drug_name}

            # Simple heuristic: pick the first one from our preferred list if possible
            best_concept = all_concepts[0]
            rxcui = best_concept.get("rxcui")
            
            if not rxcui:
                return {"success": False, "error": "No RxCUI found", "raw_name": drug_name}
            
            # Step 2: Get properties
            detail_url = f"{self.BASE_URL}/rxcui/{rxcui}/properties.json"
            detail_resp = await self.client.get(detail_url)
            props = detail_resp.json().get("propConceptGroup", {}).get("propConcept", [])
            
            def get_prop(name):
                return next((p["propValue"] for p in props if p["propName"] == name), None)

            preferred_name = get_prop("RxNorm Preferred Name") or drug_name
            generic_name = get_prop("RxNorm Generic Name")
            
            result = {
                "success": True,
                "rxcui": rxcui,
                "input_name": drug_name,
                "preferred_name": preferred_name,
                "generic_name": generic_name,
                "ingredients": [],
                "brand_names": [],
                "atc_classes": [],
            }
            
            # Step 3: Related concepts (ingredients, brands)
            rel_url = f"{self.BASE_URL}/rxcui/{rxcui}/related.json?tty=IN+MIN+PIN+BN"
            rel_resp = await self.client.get(rel_url)
            rel_data = rel_resp.json().get("relatedGroup", {}).get("conceptGroup", [])
            
            for group in rel_data:
                tty = group.get("tty")
                concepts = group.get("conceptProperties", [])
                if tty == "IN":
                    result["ingredients"] = [c["name"] for c in concepts]
                elif tty == "BN":
                    result["brand_names"] = [c["name"] for c in concepts]
            
            # Step 4: ATC classification (via RxClass)
            atc_url = f"https://rxnav.nlm.nih.gov/REST/rxclass/class/byRxcui.json?rxcui={rxcui}&classTypes=ATC"
            atc_resp = await self.client.get(atc_url)
            atc_data = atc_resp.json().get("rxclassDrugInfoList", {}).get("rxclassDrugInfo", [])
            
            if atc_data:
                # Add full ATC info, not just ID
                result["atc_classes"] = [
                    {
                        "id": item["rxclassMinConceptItem"]["classId"],
                        "name": item["rxclassMinConceptItem"]["className"]
                    }
                    for item in atc_data
                ]
            
            return result
        
        except Exception as e:
            print(f"❌ RxNorm API error: {e}")
            return {"success": False, "error": str(e), "raw_name": drug_name}


# Singleton instance
rxnorm_client = RxNormClient()
