import asyncio
from src.nova_guard.services.nova_tts import generate_speech

async def main():
    print("Starting generation...")
    audio = await generate_speech("Testing the audio system.")
    print(f"Generated {len(audio)} bytes of audio.")

asyncio.run(main())
