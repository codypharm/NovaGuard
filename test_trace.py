import asyncio
import logging
from langchain_core.messages import HumanMessage, AIMessage
from nova_guard.services.bedrock import BedrockClient

logging.basicConfig(level=logging.ERROR)

async def test():
    client = BedrockClient()
    
    history = [
        HumanMessage(content="![Prescription Image](/uploads/dummy.jpg)\n\nreview this prescription"),
        AIMessage(content="I'm sorry, I'm having trouble processing that clinical question right now."),
        HumanMessage(content="![Prescription Image](/uploads/dummy.jpg)\n\nreview this prescription")
    ]
    
    user_query = "review this prescription"
    system_prompt = "You are helpful."
    
    try:
        res = await client.chat(system_prompt, user_query, history)
        print("Response ok:", res[:50])
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("Exception caught in script:", e)

if __name__ == "__main__":
    asyncio.run(test())
