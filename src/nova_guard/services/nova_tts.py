import asyncio
import base64
import json
import ssl
import os
import wave
import io
import websockets
import logging

logger = logging.getLogger(__name__)

async def generate_speech(text: str) -> bytes:
    """Generates WAV audio bytes from text using Nova Sonic."""
    api_key = os.getenv("NOVA_API_KEY")
    if not api_key:
        raise ValueError("NOVA_API_KEY not found.")
        
    url = "wss://api.nova.amazon.com/v1/realtime?model=nova-2-sonic-v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Origin": "https://api.nova.amazon.com"
    }

    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    audio_chunks = []

    try:
        async with websockets.connect(url, ssl=ssl_context, additional_headers=headers) as ws:
            # 1. Configuration
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["audio"],
                    "voice": "alloy" # Optional voice parameter if supported
                }
            }))
            
            # 2. Add message 
            await ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": text}]
                }
            }))
            
            # 3. Create response
            await ws.send(json.dumps({"type": "response.create"}))
            
            # 4. Wait for audio stream
            while True:
                response = await ws.recv()
                event = json.loads(response)
                
                if event["type"] == "response.audio.delta":
                    audio_chunks.append(base64.b64decode(event["delta"]))
                elif event["type"] == "response.audio.done" or event["type"] == "response.done":
                    break
                elif event["type"] == "error":
                    logger.error(f"Nova TTS Error: {event}")
                    break
                    
    except Exception as e:
        logger.error(f"TTS Exception: {e}")
        
    pcm_data = b"".join(audio_chunks)
    
    if not pcm_data:
        return b""
        
    # Convert raw PCM16 24kHz to WAV header for easy browser playback
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm_data)
        
    return wav_io.getvalue()
