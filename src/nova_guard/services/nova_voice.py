
import asyncio
import base64
import json
import ssl
import os
import io
import websockets

# Configuration from user script
SAMPLE_RATE = 24000
CHANNELS = 1
SAMPLE_WIDTH = 2 # 16-bit

async def transcribe_audio_stream(audio_bytes: bytes) -> str:
    """
    Connects to Nova 2 Sonic Realtime API and transcribes the given audio bytes.
    Expects raw PCM 16-bit 24kHz mono audio.
    """
    api_key = os.getenv("NOVA_API_KEY")
    if not api_key:
        raise ValueError("NOVA_API_KEY environment variable not set")
    
    url = "wss://api.nova.amazon.com/v1/realtime?model=nova-2-sonic-v1"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Origin": "https://api.nova.amazon.com"
    }
    
    # SSL Context - user script disabled verification
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    transcript = ""
    
    print(f"Connecting to Nova Realtime API... ({len(audio_bytes)} bytes)")

    try:
        async with websockets.connect(url, ssl=ssl_context, additional_headers=headers) as ws:
            # 1. Wait for session.created
            event = json.loads(await ws.recv())
            if event["type"] != "session.created":
                print(f"Unexpected event: {event}")
            
            # 2. Configure session
            # We want transcription only. We might try to suppress audio output.
            await ws.send(json.dumps({
                "type": "session.update",
                "session": {
                    "modalities": ["text"], # Try to restrict to text if possible, or just ignore audio
                    "instructions": "Transcribe the user input exactly. Do not provide a conversational response.",
                    "turn_detection": None, # Disable VAD to allow manual response.create
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                }
            }))
            
            # Wait for session.updated
            event = json.loads(await ws.recv())
            # print(f"Session updated: {event}")

            # 3. Send Audio in Chunks
            # Websockets often have a frame size limit (e.g. 64KB or 1MB).
            # We chunk the audio to ensure we don't hit "Message too big" errors.
            CHUNK_SIZE = 16384 * 2 # 32KB of bytes -> ~43KB base64. 
            # Or safer: 8192 bytes -> ~11KB base64.
            # 65536 is the limit reported. 8192 is safe.
            CHUNK_SIZE = 8192 
            
            for i in range(0, len(audio_bytes), CHUNK_SIZE):
                chunk = audio_bytes[i:i+CHUNK_SIZE]
                b64_chunk = base64.b64encode(chunk).decode('utf-8')
                
                await ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": b64_chunk
                }))
                # Small delay not strictly necessary but good for stability
                await asyncio.sleep(0.01)
            
            # Since VAD is enforced and response.create/commit are not supported:
            # We append silence to trigger VAD "turn end".
            silence_bytes = bytes(24000 * 2 * 1) # 1 second of silence (24k * 2 bytes * 1s)
            # Chunk the silence too
            for i in range(0, len(silence_bytes), CHUNK_SIZE):
                chunk = silence_bytes[i:i+CHUNK_SIZE]
                b64_chunk = base64.b64encode(chunk).decode('utf-8')
                await ws.send(json.dumps({
                    "type": "input_audio_buffer.append",
                    "audio": b64_chunk
                }))
                await asyncio.sleep(0.01)
            
            # Now we wait for VAD to trigger 'input_audio_transcription.completed'
            print("Sent audio + silence. Waiting for VAD...")
            
            # 4. Wait for transcription
            # We expect 'conversation.item.input_audio_transcription.completed'
            # Or 'error'
            
            timeout = 10.0
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    msg_str = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    msg = json.loads(msg_str)
                    
                    if msg["type"] == "conversation.item.input_audio_transcription.completed":
                        transcript = msg.get("transcript", "")
                        print(f"Transcription received: {transcript}")
                        return transcript
                    
                    if msg["type"] == "error":
                        print(f"Nova Error: {msg}")
                        break
                        
                    # Ignore other events
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"Websocket loop error: {e}")
                    break
                    
    except Exception as e:
        print(f"Transcription failed: {str(e)}")
        # In case of failure, return empty string or raise?
        raise
        
    return transcript
