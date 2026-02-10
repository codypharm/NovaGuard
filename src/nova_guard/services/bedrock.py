import json
import base64
import boto3
import os
from typing import Optional, List, Dict
from botocore.exceptions import ClientError
from openai import OpenAI

from nova_guard.config import settings
from nova_guard.schemas.patient import PrescriptionData

class BedrockClient:
    """Client for interacting with Amazon Nova models (via OpenAI-compatible API)."""
    
    # Model IDs (Nova OpenAI-compatible)
    MODEL_MICRO = "nova-2-lite-v1" # Using Lite for now as Micro seems unavailable
    MODEL_LITE = "nova-2-lite-v1"
    MODEL_PRO = "nova-2-pro-v1"
    
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
                print(f"⚠️ Failed to initialize OpenAI client: {e}")
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
                print(f"⚠️ Failed to initialize Boto3 client: {e}")
        return self._boto3_client

    # ========================================================================
    # NEW: Intent Classification (Nova Micro)
    # ========================================================================
    async def classify_intent(self, text: str, has_image: bool, prompt: str) -> str:
        """Uses Nova Micro via OpenAI API to determine user intent."""
        # Fallback if no key (or offline)
        if not self.openai_client:
            print("⚠️ No Nova API Key found. Using offline keyword fallback.")
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
            print(f"❌ Intent Classification Error: {e}")
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
            print(f"❌ Chat Error: {e}")
            return "I'm sorry, I'm having trouble processing that clinical question right now."

    # ========================================================================
    # EXISTING: Image Processing (Boto3 / Nova Lite)
    # ========================================================================
    async def process_image(self, image_bytes: bytes) -> Optional[PrescriptionData]:
        """
        Uses Nova Lite (via Bedrock Boto3) for vision tasks.
        OpenAI-compatible endpoint might not support image bytes directly yet.
        """
        if not self.boto3_client:
            print("⚠️ AWS credentials required for image processing (Vision).")
            return None

        prompt = """
        Analyze this prescription image. Extract:
        - Patient Name
        - Medication Name
        - Dosage
        - Frequency
        - Date
        
        Return ONLY valid JSON.
        """
        
        try:
            # Prepare request for Bedrock Converse API (Vision)
            encoded_image = base64.b64encode(image_bytes).decode('utf-8')
            
            message = {
                "role": "user",
                "content": [
                    {"text": prompt},
                    {
                        "image": {
                            "format": "jpeg", # Assuming JPEG for now, or detect
                            "source": {"bytes": image_bytes}    
                        }
                    }
                ]
            }
            
            # Note: We still use the 'us.amazon.nova-lite-v1:0' ID for Bedrock
            response = self.boto3_client.converse(
                modelId="us.amazon.nova-lite-v1:0",
                messages=[message],
                inferenceConfig={"temperature": 0.0}
            )
            
            response_text = response["output"]["message"]["content"][0]["text"]
            
            # Simple cleanup for JSON extraction
            json_str = response_text.replace("```json", "").replace("```", "").strip()
            data = json.loads(json_str)
            
            return PrescriptionData(**data)
            
        except Exception as e:
            print(f"❌ Image Processing Error: {e}")
            return None

# Singleton
bedrock_client = BedrockClient()