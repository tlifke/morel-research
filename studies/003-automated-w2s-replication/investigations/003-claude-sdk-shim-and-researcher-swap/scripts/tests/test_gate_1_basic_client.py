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
        await client.query("Reply with exactly the word ok")
        text = ""
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, TextBlock):
                        text += block.text
    elapsed = time.time() - start
    print(f"wall_time_sec={elapsed:.2f}")
    print(f"response_text={text!r}")
    assert "ok" in text.lower(), f"expected 'ok' in response, got: {text!r}"
    print("GATE 1 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
