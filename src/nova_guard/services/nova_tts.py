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
            # 0. Wait for session.created
            event = json.loads(await ws.recv())
            if event["type"] != "session.created":
                logger.warning(f"Unexpected initial event: {event}")
                
            # 1. Configuration
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["audio"],
                    "voice": "alloy",
                    "instructions": f"You are a pure text-to-speech engine. Your ONLY job is to read the following text exactly word-for-word from beginning to end without stopping. Do not summarize. Do not skip any sentences. Here is the text to read:\n\n{text}"
                }
            }))
            
            # 2. Add message 
            await ws.send(json.dumps({
                "type": "conversation.item.create",
                "item": {
                    "type": "message",
                    "role": "user",
                    "content": [{"type": "input_text", "text": "Begin reading."}]
                }
            }))
            
            # 3. Trigger VAD with silent audio buffer
            # Nova enforces Server VAD, so response.create is not supported.
            # We must trick VAD into thinking speech just ended.
            silent_pcm = bytes(24000 * 2 * 1) # 1 second of silence (16-bit 24kHz Mono = 48000 bytes)
            
            # Send the silence chunk in small 8192 byte blocks to avoid WebSocket frame limits
            CHUNK_SIZE = 8192
            for i in range(0, len(silent_pcm), CHUNK_SIZE):
                chunk = silent_pcm[i:i+CHUNK_SIZE]
                await ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": base64.b64encode(chunk).decode('utf-8')
                }))
                await asyncio.sleep(0.01)
            
            # Note: DO NOT send input_audio_buffer.commit or response.create. 
            # Nova automatically starts generating responses when VAD detects 1s of silence.
            
            # 4. Wait for audio stream
            while True:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=1.5)
                except asyncio.TimeoutError:
                    break
                    
                event = json.loads(response)
                print(f"Nova TTS Event: {event.get('type')}", flush=True)
                
                if event["type"] == "response.output_audio.delta":
                    audio_chunks.append(base64.b64decode(event["delta"]))
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
