import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claude_agent_sdk_shim import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AssistantMessage,
    TextBlock,
)


async def main() -> int:
    start = time.time()
    async with ClaudeSDKClient(ClaudeAgentOptions(model="gemma3:4b-it-qat")) as client:
        await client.query("My name is Tyler. Remember it.")
        async for msg in client.receive_response():
            pass
        await client.query("What is my name?")
        full_response = ""
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        full_response += block.text
    elapsed = time.time() - start
    print(f"wall_time_sec={elapsed:.2f}")
    print(f"turn2_response={full_response!r}")
    assert "tyler" in full_response.lower(), f"expected 'tyler' in response, got: {full_response!r}"
    print("GATE 2 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
