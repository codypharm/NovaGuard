import asyncio
from nova_guard.services.nova_tts import generate_speech

async def main():
    print("Starting generation...")
    text = "The patient's laboratory results indicate an elevated serum creatinine. Dose adjustment is required for the new prescription. Please review the renal dosing guidelines."
    audio = await generate_speech(text)
    print(f"Generated {len(audio)} bytes of audio.")

asyncio.run(main())
