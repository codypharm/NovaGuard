"""Amazon Bedrock client for AI intake methods."""

import json
import base64
import boto3
from typing import Optional
from botocore.exceptions import ClientError

from nova_guard.config import settings
from nova_guard.schemas.patient import PrescriptionData

class BedrockClient:
    """Client for interacting with Amazon Bedrock (Nova models)."""
    
    # Model IDs
    MODEL_IMAGE = "amazon.nova-lite-v1:0"
    MODEL_TEXT = "amazon.nova-micro-v1:0"
    
    def __init__(self):
        self.region = settings.aws_region
        self._client = None
        
    @property
    def client(self):
        """Lazy initialization of Bedrock client to avoid startup errors if creds missing."""
        if not self._client:
            try:
                self._client = boto3.client("bedrock-runtime", region_name=self.region)
            except Exception as e:
                print(f"⚠️ Failed to initialize Bedrock client: {e}")
                self._client = None
        return self._client
        
    async def process_image(self, image_bytes: bytes) -> Optional[PrescriptionData]:
        """
        Analyze prescription image using Amazon Nova Lite.
        Returns extracted prescription data.
        """
        if not self.client:
            print("⚠️ Bedrock client not available. Skipping image analysis.")
            return None
            
        try:
            # Encode image
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Construct prompt for prescription extraction
            system_prompt = "You are a specialized medical assistant. specific task: Extract prescription details strictly."
            user_message = {
                "role": "user",
                "content": [
                    {"image": {"format": "jpeg", "source": {"bytes": image_bytes}}},
                    {"text": "Extract the following details from this prescription: drug name, dose, frequency, and patient name (if visible). Return JSON only."}
                ]
            }
            
            # Prepare request body for Nova Lite (using Converse API pattern or InvokeModel)
            # Nova models use the converse API structure usually
            
            # Using converse API (standard for Nova)
            response = self.client.converse(
                modelId=self.MODEL_IMAGE,
                messages=[user_message],
                system=[{"text": system_prompt}],
                inferenceConfig={"temperature": 0.0, "maxTokens": 1000}
            )
            
            output_text = response["output"]["message"]["content"][0]["text"]
            
            # Parse JSON from output
            # Simple heuristic cleaning
            json_str = output_text.strip()
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
                
            data = json.loads(json_str)
            
            return PrescriptionData(
                drug_name=data.get("drug_name", "Unknown"),
                dose=data.get("dose", "Unknown"),
                frequency=data.get("frequency", "Unknown"),
                # Extract other fields if model provides them
            )
            
        except ClientError as e:
            print(f"❌ AWS Bedrock Error: {e}")
            return None
        except Exception as e:
            print(f"❌ Image Processing Error: {e}")
            return None

    async def process_voice(self, audio_bytes: bytes) -> Optional[PrescriptionData]:
        """
        Process voice input using Nova Sonic (or Transcribe + Nova).
        Placeholder for Step 3.1.
        """
        # For Phase 2 "Bit by Bit", we leave this as a placeholder or mock
        # Real implementation will likely use Amazon Transcribe + Bedrock or Nova Sonic
        print("ℹ️ Voice processing via Bedrock is planned for Step 3.1")
        return None

# Singleton
bedrock_client = BedrockClient()
