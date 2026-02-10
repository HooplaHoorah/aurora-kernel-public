import os
import httpx
import json
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def test_agent():
    url = f"{os.getenv('KIBANA_URL')}/api/agent_builder/converse/async"
    # Try Basic Auth first since it seemed to get past 401
    auth = (os.getenv('ES_USERNAME'), os.getenv('ES_PASSWORD'))
    
    headers = {
        "Content-Type": "application/json",
        "kbn-xsrf": "aurora-studio",
    }
    
    payload = {
        "agent_id": os.getenv('AGENT_BUILDER_AGENT_ID'),
        "input": "Hello Aurora, can you confirm you are online and have access to the knowledge base?",
        "capabilities": {"visualizations": True}
    }
    
    print(f"Calling: {url}")
    print(f"Payload: {json.dumps(payload)}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("POST", url, auth=auth, headers=headers, json=payload) as response:
            print(f"Status: {response.status_code}")
            if response.status_code != 200:
                body = await response.aread()
                print(f"Error: {body.decode()}")
                return

            print("Response stream:")
            async for line in response.aiter_lines():
                if not line: continue
                print(line)

if __name__ == "__main__":
    asyncio.run(test_agent())
