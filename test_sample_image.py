import asyncio
import logging
from nova_guard.services.bedrock import BedrockClient

logging.basicConfig(level=logging.INFO)

async def test():
    client = BedrockClient()
    file_path = 'prescriptions/image00553-1.jpeg'
    with open(file_path, 'rb') as f:
        image_bytes = f.read()
    
    try:
        print('Testing process_image with:', file_path)
        res = await client.process_image(image_bytes)
        print('Response:', res)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print('Exception:', e)

if __name__ == "__main__":
    asyncio.run(test())
