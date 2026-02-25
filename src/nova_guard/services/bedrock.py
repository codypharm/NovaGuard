import json
import base64
import logging
import boto3
import os
from typing import Optional, List, Dict, Any
from botocore.exceptions import ClientError
from openai import AsyncOpenAI
from datetime import datetime

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
    # MODEL_PRO = "nova-pro-v1"

    def _clean_json(self, text: str) -> str:
        """Removes markdown code blocks and ensures valid JSON string."""
        if not text: return "{}"
        clean = text.strip()
        if "```" in clean:
            # Find the first JSON-like character
            start_obj = clean.find("{")
            start_arr = clean.find("[")

            # Determine which starts first (if either exists)
            start = -1
            if start_obj != -1 and start_arr != -1:
                start = min(start_obj, start_arr)
            else:
                start = max(start_obj, start_arr)

            # Find the corresponding end character
            end = -1
            if start != -1:
                if clean[start] == "{":
                    end = clean.rfind("}")
                else:
                    end = clean.rfind("]")

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
                self._openai_client = AsyncOpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url,
                    default_headers={"Accept-Encoding": "identity"}
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
            response = await self.openai_client.chat.completions.create(
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

        # Parse LangChain conversation history
        for msg in history:
            role = getattr(msg, "type", "")
            if role == "human":
                role = "user"
            elif role == "ai":
                role = "assistant"

            content = getattr(msg, "content", "")
            if isinstance(content, list):
                # Extract text from multimodal payload
                text_parts = []
                for p in content:
                    if isinstance(p, dict):
                        # Handle {"type": "text", "text": "..."} format typical in LangChain multimodal
                        if p.get("type") == "text" and "text" in p:
                            text_parts.append(p["text"])
                        elif "text" in p:
                            text_parts.append(p["text"])
                    elif isinstance(p, str):
                        text_parts.append(p)
                content = " ".join(text_parts)
            elif not isinstance(content, str):
                content = str(content)

            if role in ["user", "assistant"] and content:
                # Merge consecutive same-role messages to satisfy Bedrock strict alternating requirements
                if len(messages) > 1 and messages[-1]["role"] == role:
                    messages[-1]["content"] += f"\n\n{content}"
                else:
                    messages.append({"role": role, "content": content})

        # Ensure the conversation doesn't end with a system message or assistant message if we have a direct query
        if hasattr(user_query, "strip") and user_query.strip():
            # If the last message is already a user message and ends with user_query, don't duplicate
            if len(messages) == 1 or messages[-1]["role"] != "user" or not messages[-1]["content"].endswith(user_query.strip()):
                if len(messages) > 1 and messages[-1]["role"] == "user":
                    messages[-1]["content"] += f"\n\n{user_query}"
                else:
                    messages.append({"role": "user", "content": user_query})

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
                messages=messages,
                temperature=0.2
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("Chat completion failed: %s", e, exc_info=True)
            raise e

    async def chat_lite(self, system_prompt: str, user_query: str) -> str:
        """Uses Nova Lite via OpenAI API for faster/cheaper reasoning."""
        if not self.openai_client: return "Error: AI not available."

        try:
            response = await self.openai_client.chat.completions.create(
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
            response = await self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
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
            response = await self.openai_client.chat.completions.create(
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
            response = await self.openai_client.chat.completions.create(
                model=self.MODEL_LITE, 
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
            response = await self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
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
            response = await self.openai_client.chat.completions.create(
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

        mime_type = "image/jpeg"
        if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            mime_type = "image/png"
        elif image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
            mime_type = "image/webp"
        elif image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
            mime_type = "image/gif"
        elif b"<svg" in image_bytes[:500]:
            mime_type = "image/svg+xml"

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
            response = await self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{encoded_image}"
                                },
                            },
                        ],
                    }
                ],
                temperature=0.0
            )


            raw_content = response.choices[0].message.content
            logger.info(f"Raw Vision API Response: {raw_content}")

            content = self._clean_json(raw_content)
            parsed = json.loads(content)
            if isinstance(parsed, dict) and len(parsed.keys()) == 1:
                parsed = list(parsed.values())[0]

            if isinstance(parsed, list):
                return parsed
            logger.warning(f"Parsed response is not a list: {type(parsed)}")
            return []

        except Exception as e:
            logger.error(f"Lab image processing failed: {str(e)}", exc_info=True)
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
        # Use a minimal representation in Markdown instead of JSON to avoid confusing the model
        profile_str = f"Age: {patient_profile.get('age_years')}\n"
        profile_str += f"Pregnant: {patient_profile.get('is_pregnant')}\n"
        profile_str += f"Nursing: {patient_profile.get('is_nursing')}\n"
        profile_str += f"eGFR: {patient_profile.get('egfr')}\n"
        profile_str += f"Allergies: {[a.get('allergen') for a in patient_profile.get('allergies', []) if isinstance(a, dict)]}\n"
        profile_str += f"Current Meds: {[m.get('drug') for m in patient_profile.get('active_medications', []) if isinstance(m, dict)]}\n"
        profile_str += f"Adverse Reactions: {[r.get('reaction') for r in patient_profile.get('adverse_reactions', []) if isinstance(r, dict)]}\n"

        lab_strings = []
        for l in patient_profile.get('lab_results', []):
            if isinstance(l, dict):
                lab_strings.append(f"{l.get('test_name')}: {l.get('value')} {l.get('unit')} (Collected: {str(l.get('collected_at'))[:10]})")
        profile_str += f"Recent Labs: {lab_strings}\n"

        system_prompt = f"""
        SYSTEM CLOCK: Current Date is {datetime.now().strftime('%Y-%m-%d')}. Use this to determine if labs or events are historical or acute.

        You are a highly conservative clinical safety auditor.
        The user has requested a safety check for a drug that has NO FDA LABEL (likely international or unapproved in US).
        You must use your internal pharmacological knowledge to identify critical safety issues.

        Analyze the drug against the patient profile.
        Check for:
        1. Contraindications (Absolute)
        2. Major Drug-Drug Interactions (with current meds)
        3. Pregnancy/Lactation Risks
        4. Renal/Hepatic Adjustments (compare patient labs to known cutoffs)
        5. Black Box Warnings (Global consensus)

        REQUIRED CHAIN OF THOUGHT:
        Before outputting the JSON, you MUST show your clinical reasoning inside <clinical_analysis> tags.
        Note the patient's organ function, any current meds, and calculate risk based on the provided Recent Labs and SYSTEM CLOCK.

        Return a JSON object with a list of flags:
        {{
            "flags": [
                {{
                    "severity": "critical" | "warning" | "info",
                    "category": "contraindication" | "interaction" | "pregnancy" | "dosing" | "warning",
                    "message": "Clear, concise clinical warning message.",
                    "citation": "International Label / Clinical Pharmacology"
                }}
            ]
        }}

        If no major issues found, return {{"flags": []}}.
        Be conservative. If unsure, flag as warning "Insufficient Data".
        """

        try:
            prompt_data = f"Drug: {drug_name}\nPatient Profile: {profile_str}"
            response = await self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt_data}
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
    async def process_image(self, image_bytes: bytes) -> Optional[List[PrescriptionData]]:
        """
        Extract prescription data from an image using Nova Pro via the
        OpenAI-compatible endpoint (api.nova.amazon.com). Falls back to
        Boto3 Converse API if the OpenAI client is unavailable.
        """
        if not self.openai_client:
            logger.warning("Nova API key required for image processing.")
            return None

        prompt = """
        Analyze this prescription image. Extract all medications.
        Return a JSON object with a "prescriptions" key containing a list of objects.

        EACH object must have these exact keys:
        - drug_name (e.g. "Lisinopril")
        - dose (e.g. "10mg")
        - frequency (e.g. "daily")
        - notes (optional, e.g. "Prescriber: Dr. Smith, Date: 2022-01-01, Refills: 6")

        Return ONLY valid JSON. Example:
        {"prescriptions": [{"drug_name": "Lisinopril", "dose": "10mg", "frequency": "daily", "notes": ""}]}
        """

        try:
            encoded_image = base64.b64encode(image_bytes).decode("utf-8")

            # Sniff basic mime types to avoid rejection by Nova
            mime_type = "image/jpeg"
            if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
                mime_type = "image/png"
            elif image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP":
                mime_type = "image/webp"
            elif image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
                mime_type = "image/gif"
            elif b"<svg" in image_bytes[:500]:
                mime_type = "image/svg+xml"

            # OpenAI vision format: image_url with base64 data URI
            response = await self.openai_client.chat.completions.create(
                model=self.MODEL_LITE,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{encoded_image}"
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

            prescriptions = []
            if "prescriptions" in data:
                for p in data["prescriptions"]:
                    prescriptions.append(PrescriptionData(**p))
            else:
                # Fallback if it returns a single object instead of a 'prescriptions' dict
                prescriptions.append(PrescriptionData(**data))

            return prescriptions

        except Exception as e:
            logger.error("Image processing failed: %s", e)
            return None

# Singleton
bedrock_client = BedrockClient()
