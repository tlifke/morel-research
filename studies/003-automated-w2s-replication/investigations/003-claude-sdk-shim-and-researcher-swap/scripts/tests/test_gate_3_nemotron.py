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
    ToolUseBlock,
    tool,
    create_sdk_mcp_server,
)

MODEL = sys.argv[1] if len(sys.argv) > 1 else "nemotron-3-nano:4b"


@tool("add", "Add two integers and return the sum", {"a": int, "b": int})
async def add(args):
    return {"content": [{"type": "text", "text": f"sum={args['a'] + args['b']}"}]}


async def main() -> int:
    start = time.time()
    calc_server = create_sdk_mcp_server(name="calc", version="1.0.0", tools=[add])
    options = ClaudeAgentOptions(
        model=MODEL,
        mcp_servers={"calc": calc_server},
        allowed_tools=["mcp__calc__add"],
    )
    tool_call_inputs = []
    text_chunks = []
    saw_tool_call = False
    saw_correct_answer = False
    async with ClaudeSDKClient(options) as client:
        await client.query("Use the add tool to compute 5+3. Report the result.")
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        tool_call_inputs.append({"name": block.name, "input": block.input})
                        if block.name == "add" and block.input == {"a": 5, "b": 3}:
                            saw_tool_call = True
                    if isinstance(block, TextBlock):
                        text_chunks.append(block.text)
                        if "8" in block.text:
                            saw_correct_answer = True
    elapsed = time.time() - start
    print(f"MODEL={MODEL}")
    print(f"wall_time_sec={elapsed:.2f}")
    print(f"tool_calls={tool_call_inputs}")
    print(f"text_chunks={text_chunks}")
    print(f"saw_tool_call={saw_tool_call}")
    print(f"saw_correct_answer={saw_correct_answer}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
