import json
import base64
import logging
import boto3
import os
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError
from openai import OpenAI

logger = logging.getLogger(__name__)

from nova_guard.config import settings
from nova_guard.schemas.patient import PrescriptionData
from nova_guard.services.cache import cached_research

class BedrockClient:
    """Client for interacting with Amazon Nova models (via OpenAI-compatible API)."""
    
    # Model IDs (Nova OpenAI-compatible)
    # Using v1 models as v2 seems restricted/unavailable for this account
    MODEL_MICRO = "nova-micro-v1" 
    MODEL_LITE = "nova-2-lite-v1"
    MODEL_PRO = "nova-pro-v1"
    
    def _clean_json(self, text: str) -> str:
        """Removes markdown code blocks and ensures valid JSON string."""
        if not text: return "{}"
        clean = text.strip()
        if "```" in clean:
            # Find the first { and last }
            start = clean.find("{")
            end = clean.rfind("}")
            if start != -1 and end != -1:
                return clean[start:end+1]
        return clean

    def __init__(self):
        # OpenAI Client for Text/Chat
        self.api_key = settings.nova_api_key
        self.base_url = "https://api.nova.amazon.com/v1"
        self._openai_client = None
        
        # AWS Client for Vision (Legacy/Fallback)
        self.region = settings.aws_region
        self._boto3_client = None
        
    @property
    def openai_client(self):
        if not self._openai_client and self.api_key:
            try:
                self._openai_client = OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except Exception as e:
                logger.warning("Failed to initialize OpenAI client: %s", e)
        return self._openai_client

    @property
    def boto3_client(self):
        if not self._boto3_client:
            try:
                self._boto3_client = boto3.client(
                    "bedrock-runtime",
                    region_name=self.region,
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key
                )
            except Exception as e:
                logger.warning("Failed to initialize Boto3 client: %s", e)
        return self._boto3_client

    # ========================================================================
    # NEW: Intent Classification (Nova Micro)
    # ========================================================================
    async def classify_intent(self, text: str, has_image: bool, prompt: str) -> str:
        """Uses Nova Micro via OpenAI API to determine user intent."""
        # Fallback if no key (or offline)
        if not self.openai_client:
            logger.warning("No Nova API Key found. Using offline keyword fallback.")
            return self._offline_fallback(text)

        input_context = f"Message: {text}\nHas Image: {has_image}"
        
        try:
            # Note: synchronous call wrapped in async method for now
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_MICRO,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": input_context}
                ],
                temperature=0.0
            )
            return response.choices[0].message.content.strip().upper()
        except Exception as e:
            logger.error("Intent classification failed: %s", e)
            return self._offline_fallback(text)

    def _offline_fallback(self, text: str) -> str:
        """Offline keyword matching for intent."""
        text_lower = text.lower()
        if "open" in text_lower or "show" in text_lower:
            return "SYSTEM_ACTION"
        if "check" in text_lower or "allergic" in text_lower or "allergy" in text_lower:
            return "CLINICAL_QUERY"
        if "what is" in text_lower or "dosage" in text_lower:
            return "MEDICAL_KNOWLEDGE"
        return "AUDIT"

    # ========================================================================
    # NEW: Chat Interface (Nova Pro)
    # ========================================================================
    async def chat(self, system_prompt: str, user_query: str, history: List[Dict] = []) -> str:
        """Uses Nova Pro via OpenAI API for conversational clinical reasoning."""
        if not self.openai_client: return "Error: AI not available (check NOVA_API_KEY)."

        messages = [{"role": "system", "content": system_prompt}]
        # Add history if format matches, otherwise skip for now or adapt
        # history usually comes as LangChain messages, might need adaptation
        # For now, simplistic approach:
        messages.append({"role": "user", "content": user_query})

        try:
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_PRO,
                messages=messages,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Chat completion failed: %s", e)
            return "I'm sorry, I'm having trouble processing that clinical question right now."

    async def chat_lite(self, system_prompt: str, user_query: str) -> str:
        """Uses Nova Lite via OpenAI API for faster/cheaper reasoning."""
        if not self.openai_client: return "Error: AI not available."

        try:
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                temperature=0.0
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Nova Lite chat failed: %s", e)
            return ""

    # ========================================================================
    # Clinical Research (Nova Pro)
    # ========================================================================
    @cached_research
    async def research(self, query: str) -> str:
        """
        Provides detailed clinical research using Nova Pro.
        Supplements the FDA label data already fetched by the workflow.
        """
        if not self.openai_client:
            return ""

        system_prompt = """You are an evidence-based clinical pharmacist and drug information specialist.

            For the given drug(s), provide a comprehensive, structured research summary in valid JSON format.

            REQUIRED JSON STRUCTURE:
            {
            "drugs": [
                {
                "drug_name": "string",
                "mechanism_of_action": "string (150-300 words)",
                "pharmacokinetics": {
                    "absorption": "string",
                    "distribution": "string (Vd, protein binding)",
                    "metabolism": "string (CYP pathways, metabolites)",
                    "elimination": "string (route, half-life)",
                    "bioavailability": "string"
                },
                "clinical_evidence": [
                    {
                    "study_name": "string",
                    "citation": "string (Author Year, Journal)",
                    "key_findings": "string",
                    "level_of_evidence": "string"
                    }
                ],
                "adverse_effects": {
                    "common": ["list of effects with frequency"],
                    "serious": ["list with description"],
                    "black_box_warnings": ["if applicable"]
                },
                "drug_interactions": {
                    "major": [
                    {
                        "interacting_drug": "string",
                        "mechanism": "string (CYP450 or other)",
                        "clinical_significance": "string"
                    }
                    ],
                    "moderate": ["brief list"]
                },
                "special_populations": {
                    "renal_impairment": "dosing adjustments and considerations",
                    "hepatic_impairment": "dosing adjustments and considerations",
                    "pediatric": "safety and dosing considerations",
                    "geriatric": "special considerations",
                    "pregnancy": "category/data and recommendations",
                    "lactation": "safety data"
                },
                "clinical_pearls": ["2-4 key practice points"]
                }
            ],
            "summary": "Brief comparative summary if multiple drugs",
            "references": ["Complete reference list"]
            }

            GUIDELINES:
            - Use precise pharmacological terminology
            - Cite 3-5 landmark trials per drug where available
            - Include specific numerical data (half-lives, protein binding %, etc.)
            - For CYP interactions, specify substrate/inhibitor/inducer status
            - If data is limited or unavailable for a section, state this explicitly
            - If a drug name is ambiguous or not found, request clarification

            Return ONLY valid JSON, no additional text before or after."""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_PRO,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.2,
                
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Clinical research failed: %s", e)
            return ""

    # ========================================================================
    # RESTORED: Clinical Utilities & Entity Extraction
    # ========================================================================
    async def extract_entity(self, text: str, prompt: str, model: str = None) -> str:
        """
        Uses Nova Micro (default) to extract specific entities.
        Can override model for complex JSON extraction.
        """
        target_model = model or self.MODEL_MICRO
        if not self.openai_client:
            return text

        try:
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_MICRO,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Input: {text}"}
                ],
                temperature=0.0
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Entity extraction failed: %s", e)
            return text

    async def get_equivalents(self, drug_name: str) -> str:
        """Maps therapeutic classmates and 2026 interchangeable biosimilars."""
        if not self.openai_client: return "Unable to retrieve equivalents at this time."

        prompt = f"""
        # Therapeutic Equivalents: {drug_name}
        Identify equivalents including:
        1. Classmates (potency comparisons).
        2. Biosimilars (2026 Interchangeable standards).
        3. Interchangeability Rules.
        Return Markdown.
        """
        try:
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Error: {e}"

    async def get_interaction_insights(self, drugs: List[str]) -> str:
        """Analyzes drug-drug interactions with metabolic pathway detail."""
        if not self.openai_client: return "Unable to analyze interactions."

        prompt = f"Analyze drug-drug interactions for: {', '.join(drugs)}. Include CYP450 details and clinical action."
        try:
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_PRO, # Upgraded to Pro for safety
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception:
            return "Interaction analysis failed."

    async def get_safety_and_counseling(self, medications: List[Any]) -> str:
        """Generates a clinical safety matrix and patient counseling."""
        if not self.openai_client: return "Safety profile unavailable."

        med_list = [getattr(m, 'drug_name', str(m)) for m in medications]
        prompt = f"Provide a Safety Matrix (Pregnancy, Lactation, etc.) and Patient Counseling for: {', '.join(med_list)}."
        try:
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_PRO,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception:
            return "Safety analysis failed."

    async def get_renal_adjustment(self, drug_name: str, crcl: float, weight_info: str) -> str:
        """Provides renal dosing recommendations."""
        if not self.openai_client: return "Renal dosing guidance unavailable."

        prompt = f"Renal Dosing Assessment for {drug_name}. CrCl: {crcl} mL/min ({weight_info}). Provide Dosing Strategy and Rationale."
        try:
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
        except Exception:
            return "Renal guidance failed."

    # ========================================================================
    # EXISTING: Image Processing (Boto3 / Nova Lite)
    # ========================================================================
    
    # ========================================================================
    # NEW: AI SAFETY FALLBACK (For non-FDA drugs)
    # ========================================================================
    
    async def process_lab_image(self, image_bytes: bytes) -> List[Dict[str, Any]]:
        """Extracts structured lab results from an image using Nova Lite."""
        if not self.openai_client:
             return []
             
        encoded_image = base64.b64encode(image_bytes).decode("utf-8")
        
        prompt = """
        Extract laboratory test biomarkers from this image.
        Format the output as a valid JSON array of objects.
        
        REQUIRED SCHEMA (List of objects):
        [
            {
                "test_name": "string (e.g. Serum Creatinine, eGFR, ALT)",
                "value": float,
                "unit": "string (e.g. mg/dL, units/L)",
                "reference_range": "string (e.g. 0.7-1.2)",
                "is_abnormal": boolean (true if value is outside reference range)
            }
        ]
        
        Return ONLY the JSON array.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0.0
            )
            
            content = self._clean_json(response.choices[0].message.content)
            parsed = json.loads(content)
            if isinstance(parsed, dict) and len(parsed.keys()) == 1:
                parsed = list(parsed.values())[0]
            
            if isinstance(parsed, list):
                return parsed
            return []
            
        except Exception as e:
            logger.error("Lab image processing failed: %s", e)
            return []
    async def get_ai_safety_flags(self, drug_name: str, patient_profile: dict) -> List[Any]:
        """
        Generates safety flags using Nova Pro when FDA label is missing.
        """
        from nova_guard.schemas.patient import SafetyFlag
        import json
        
        if not self.openai_client:
            return []

        # Convert profile to string for prompt
        # Use a minimal representation to avoid confusing the model
        minimal_profile = {
            "age": patient_profile.get("age_years"),
            "pregnant": patient_profile.get("is_pregnant"),
            "nursing": patient_profile.get("is_nursing"),
            "egfr": patient_profile.get("egfr"),
            "allergies": [a.get("allergen") for a in patient_profile.get("allergies", []) if isinstance(a, dict)],
            "current_meds": [m.get("drug") for m in patient_profile.get("active_medications", []) if isinstance(m, dict)],
            "adverse_reactions": [r.get("reaction") for r in patient_profile.get("adverse_reactions", []) if isinstance(r, dict)]
        }
        profile_str = json.dumps(minimal_profile, default=str)
        
        system_prompt = """
        You are a highly conservative clinical safety auditor.
        The user has requested a safety check for a drug that has NO FDA LABEL (likely international or unapproved in US).
        You must use your internal pharmacological knowledge to identify critical safety issues.

        Analyze the drug against the patient profile.
        Check for:
        1. Contraindications (Absolute)
        2. Major Drug-Drug Interactions (with current meds)
        3. Pregnancy/Lactation Risks
        4. Renal/Hepatic Adjustments
        5. Black Box Warnings (Global consensus)

        Return a JSON object with a list of flags:
        {
            "flags": [
                {
                    "severity": "critical" | "warning" | "info",
                    "category": "contraindication" | "interaction" | "pregnancy" | "dosing" | "warning",
                    "message": "Clear, concise clinical warning message.",
                    "citation": "International Label / Clinical Pharmacology"
                }
            ]
        }
        
        If no major issues found, return {"flags": []}.
        Be conservative. If unsure, flag as warning "Insufficient Data".
        """

        try:
            prompt = f"Drug: {drug_name}\nPatient Profile: {profile_str}"
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_PRO,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0
            )
            
            content = self._clean_json(response.choices[0].message.content)
            data = json.loads(content)
            
            flags = []
            for item in data.get("flags", []):
                flags.append(SafetyFlag(
                    severity=item.get("severity", "warning"),
                    category=item.get("category", "general"),
                    message=f"⚠️ {item.get('message')} (AI-Generated)",
                    source="Clinical Knowledge (FDA Label Unavailable)",
                    citation=item.get("citation")
                ))
            return flags
            
        except Exception as e:
            logger.error("AI Safety Fallback failed: %s", e)
            return [
                SafetyFlag(
                    severity="warning",
                    category="system_error",
                    message=f"Could not perform safety check for {drug_name} (Label Missing & AI Failed)",
                    source="System",
                    citation=None
                )
            ]

    # ========================================================================
    # EXISTING: Image Processing (Boto3 / Nova Lite)
    # ========================================================================
    async def process_image(self, image_bytes: bytes) -> Optional[PrescriptionData]:
        """
        Extract prescription data from an image using Nova Pro via the
        OpenAI-compatible endpoint (api.nova.amazon.com). Falls back to
        Boto3 Converse API if the OpenAI client is unavailable.
        """
        if not self.openai_client:
            logger.warning("Nova API key required for image processing.")
            return None

        prompt = """
        Analyze this prescription image. Extract the following fields as JSON:
        - drug_names  ( list of drugs e.g., "Lisinopril", "Losartan", "Amlodipine")
        - doses ( list of doses associated with each drug in the same order as drug_names e.g., "10mg", "20mg", "5mg")
        - frequencies ( list of frequencies associated with each drug in the same order as drug_names e.g., "daily", "twice daily", "three times daily")
        - prescriber (optional, e.g., "Dr. Smith")
        - date (optional, e.g., "2022-01-01")
        - patient_name (optional, e.g., "John Doe")
        
        
        Return ONLY valid JSON with these exact keys.
        """

        try:
            encoded_image = base64.b64encode(image_bytes).decode("utf-8")

            # OpenAI vision format: image_url with base64 data URI
            response = self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{encoded_image}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0.0,
            )

            response_text = response.choices[0].message.content
            json_str = self._clean_json(response_text)
            data = json.loads(json_str)
            logger.info("Image processing successful: %s", data)
            return PrescriptionData(**data)

        except Exception as e:
            logger.error("Image processing failed: %s", e)
            return None

# Singleton
bedrock_client = BedrockClient()