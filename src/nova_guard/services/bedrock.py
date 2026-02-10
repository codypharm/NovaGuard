"""Amazon Bedrock client for AI intake methods."""

import json
import base64
import boto3
from typing import Optional, List, Dict
from botocore.exceptions import ClientError

from nova_guard.config import settings
from nova_guard.schemas.patient import PrescriptionData

class BedrockClient:
    """Client for interacting with Amazon Bedrock (Nova models)."""
    
    # Model IDs
    MODEL_IMAGE = "amazon.nova-lite-v1:0"   # Vision tasks
    MODEL_TEXT = "amazon.nova-micro-v1:0"   # Fast classification (Supervisor)
    MODEL_PRO = "amazon.nova-pro-v1:0"      # Deep reasoning (Assistant)
    
    def __init__(self):
        self.region = settings.aws_region
        self._client = None
        
    @property
    def client(self):
        if not self._client:
            try:
                self._client = boto3.client("bedrock-runtime", region_name=self.region)
            except Exception as e:
                print(f"⚠️ Failed to initialize Bedrock client: {e}")
                self._client = None
        return self._client

    # ========================================================================
    # NEW: Intent Classification (For Gateway Supervisor)
    # ========================================================================
    async def classify_intent(self, text: str, has_image: bool, prompt: str) -> str:
        """Uses Nova Micro to determine user intent."""
        if not self.client: return "CLINICAL_QUERY"

        input_context = f"User Text: {text}\nImage Provided: {has_image}"
        
        try:
            response = self.client.converse(
                modelId=self.MODEL_TEXT,
                messages=[{"role": "user", "content": [{"text": f"{prompt}\n\nInput: {input_context}"}]}],
                inferenceConfig={"temperature": 0.0}
            )
            return response["output"]["message"]["content"][0]["text"].strip()
        except Exception as e:
            print(f"❌ Intent Classification Error: {e}")
            return "CLINICAL_QUERY"

    # ========================================================================
    # NEW: Chat Interface (For Assistant Node)
    # ========================================================================
    async def chat(self, system_prompt: str, user_query: str, history: List[Dict] = []) -> str:
        """Uses Nova Pro for conversational clinical reasoning."""
        if not self.client: return "Error: AI not available."

        # Format history for Bedrock's Converse API if needed
        # (For Phase 1, we can just pass the current query)
        try:
            response = self.client.converse(
                modelId=self.MODEL_PRO,
                messages=[{"role": "user", "content": [{"text": user_query}]}],
                system=[{"text": system_prompt}],
                inferenceConfig={"temperature": 0.2, "maxTokens": 500}
            )
            return response["output"]["message"]["content"][0]["text"]
        except Exception as e:
            print(f"❌ Chat Error: {e}")
            return "I'm sorry, I'm having trouble processing that clinical question right now."

    # ========================================================================
    # EXISTING: Image Processing
    # ========================================================================
    async def process_image(self, image_bytes: bytes) -> Optional[PrescriptionData]:
        # ... keep your existing process_image code here ...
        # Ensure it returns the PrescriptionData object as before
        pass

# Singleton
bedrock_client = BedrockClient()