import asyncio
import logging
import traceback
from nova_guard.services.bedrock import BedrockClient
from langchain_core.messages import HumanMessage, AIMessage

logging.basicConfig(level=logging.ERROR)

async def test():
    client = BedrockClient()
    history = [
        HumanMessage(content='![Prescription Image](/uploads/fake.jpg)\n\nreview this prescription')
    ]
    user_query = 'review this prescription'
    system_prompt = 'You are helpful.'
    try:
        res = await client.chat(system_prompt, user_query, history)
        print('Response:', res[:50])
    except Exception as e:
        traceback.print_exc()
        print('Exception:', e)

if __name__ == "__main__":
    asyncio.run(test())
