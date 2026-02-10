
import os
import asyncio
from dotenv import load_dotenv
from aurora_kernel.api import call_agent_builder_converse, AgentBuilderConfig

async def main():
    load_dotenv()
    cfg = AgentBuilderConfig(
        kibana_url=os.getenv("KIBANA_URL"),
        api_key=os.getenv("KIBANA_API_KEY"),
        connector_id=os.getenv("AGENT_BUILDER_CONNECTOR_ID"),
        agent_id=os.getenv("AGENT_BUILDER_AGENT_ID")
    )
    
    print(f"Testing Agent Builder Converse API...")
    print(f"Agent ID: {cfg.agent_id}")
    
    try:
        response = await call_agent_builder_converse(cfg, "Hello, can you help me with compliance?")
        print("Response received:")
        print(response)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
