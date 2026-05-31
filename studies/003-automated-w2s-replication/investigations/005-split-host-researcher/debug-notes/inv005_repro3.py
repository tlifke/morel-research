import asyncio
import os
import sys
sys.path.insert(0, "/home/tlifke/inv003_shim/shim_pkg")

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, create_builtin_tools_server
from claude_agent_sdk.types import AssistantMessage, ResultMessage

os.environ["OLLAMA_ANTHROPIC_BASE_URL"] = "http://100.106.241.33:11434"

async def one_session(label):
    print(f"[{label}] enter", flush=True)
    srv = create_builtin_tools_server(cwd="/tmp")
    opts = ClaudeAgentOptions(
        model="nemotron-3-nano:4b",
        system_prompt="Answer briefly. Do not call any tool unless explicitly told.",
        mcp_servers={"builtin": srv},
        max_tokens=128,
    )
    async with ClaudeSDKClient(options=opts) as client:
        await client.query("Say hi in one word.")
        async for m in client.receive_response():
            print(f"[{label}] msg: {type(m).__name__}", flush=True)
            if isinstance(m, ResultMessage):
                print(f"[{label}] break on ResultMessage", flush=True)
                break
    print(f"[{label}] exited", flush=True)

async def main():
    await one_session("S0")
    print("--- starting S1 ---", flush=True)
    try:
        await asyncio.wait_for(one_session("S1"), timeout=60)
    except asyncio.TimeoutError:
        print("S1 TIMEOUT (HANG REPRODUCED)", flush=True)

asyncio.run(main())
