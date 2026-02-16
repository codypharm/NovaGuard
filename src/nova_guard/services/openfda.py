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
                        response.raise_for_status()
                        data = response.json()
                        if data.get("results"):
                            # VALIDATION: Ensure the returned label actually belongs to the drug
                            candidate = data["results"][0]
                            if self._validate_label_match(candidate, drug_name):
                                return candidate
                            else:
                                logger.warning(f"Global search returned unrelated label for '{drug_name}'")
                    except Exception as e3:
                        logger.warning("All OpenFDA searches failed for '%s': %s", drug_name, e3)
                        return None
            
            logger.error("OpenFDA API error for '%s': %s", drug_name, e)
            return None
        except Exception as e:
            logger.error("Unexpected OpenFDA error for '%s': %s", drug_name, e)
            return None

    def _validate_label_match(self, label: dict, drug_name: str) -> bool:
        """
        Check if the returned label actually matches the drug name.
        This prevents getting a 'Pilocarpine' label when searching for 'Paracetamol'
        just because Pilocarpine mentions Paracetamol in interactions.
        """
        openfda = label.get("openfda", {})
        brands = [b.lower() for b in openfda.get("brand_name", [])]
        generics = [g.lower() for g in openfda.get("generic_name", [])]
        
        name_lower = drug_name.lower()
        
        # 1. Exact/Partial match in brand or generic fields
        if any(name_lower in b for b in brands) or any(name_lower in g for g in generics):
            return True
            
        return False
    
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
    

    
    # OpenFDAClient is now purely a data fetcher for:
    # 1. Labels (get_drug_label)
    # 2. Enforcement Reports (check_drug_recall - kept here as it's a distinct API call)
    
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
            seen_reasons = []  # List of (simplified_reason, full_reason)
            
            for recall in results:
                reason = recall.get("reason_for_recall", "")
                simp = " ".join(reason.lower().split())
                
                # Substring Deduplication:
                # If this reason is contained in an existing one (or vice versa), skip/merge.
                is_duplicate = False
                for i, (existing_simp, existing_full) in enumerate(seen_reasons):
                    if simp in existing_simp: # New is shorter/subset of existing -> Skip new
                        is_duplicate = True
                        break
                    elif existing_simp in simp: # New is longer/superset -> Replace existing? 
                        # Ideally we keep the one already added OR replace it. 
                        # For simplicity, let's just duplicate-check.
                        is_duplicate = True
                        break
                
                if is_duplicate:
                    continue
                    
                seen_reasons.append((simp, reason))
                
                flags.append(SafetyFlag(
                    severity="warning",
                    category="recall",
                    message=f"⚠️ [{drug_name}] RECALL ({recall.get('status')}): {reason[:200]}...",
                    source="FDA Enforcement",
                    citation="https://api.fda.gov/drug/enforcement.json"
                ))
            
        except Exception as e:
            logger.warning("Recall check failed for '%s': %s", drug_name, e)
            
        return flags


# Singleton instance
openfda_client = OpenFDAClient()
