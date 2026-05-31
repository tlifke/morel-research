"""Inv 005 probe: does shim_v2 round-trip a structured tool call against live
nemotron-3-nano:4b on the Mac without the turn-1 hang we see with v1?

Constraint: tiny. One fake tool ("echo") whose handler returns instantly.
No SFT, no Bash, no GPU. We just want to see:

  turn 0: model emits ToolUseBlock(name="echo", input={...})
  turn 1: agent emits tool_result; model responds with ResultMessage
          (stop_reason=end_turn) instead of hanging.

Run:
    OLLAMA_OPENAI_BASE_URL=http://100.106.241.33:11434 \
        uv run --with httpx python probe_nemotron.py

Exit code 0 = both turns landed. Non-zero = something to diagnose.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prototype.client import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)


@dataclass
class _FakeTool:
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Any


@dataclass
class _FakeServer:
    tools: Dict[str, _FakeTool] = field(default_factory=dict)


def make_echo_server() -> _FakeServer:
    invocations = []

    def echo_handler(args: Dict[str, Any]) -> Dict[str, Any]:
        invocations.append(args)
        return {"content": [{"type": "text", "text": f"echo received: {args}"}]}

    tool = _FakeTool(
        name="echo",
        description=(
            "Repeat the supplied message back to the caller. Use this once "
            "to test the tool-call round trip, then say 'done'."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The text to echo."}
            },
            "required": ["message"],
        },
        handler=echo_handler,
    )
    srv = _FakeServer()
    srv.tools["echo"] = tool
    srv.invocations = invocations  # type: ignore[attr-defined]
    return srv


SYSTEM_PROMPT = (
    "You are a tool-using assistant in a research-harness probe. There is "
    "exactly ONE tool available: 'echo'. Your single job is to call the "
    "'echo' tool once with `message=\"hello shim v2\"`, then receive the "
    "tool result, then say 'done.' and stop. Do not call any other tool. "
    "Do not refuse. Do not ask questions. Just call echo, read the result, "
    "say 'done.'"
)

USER_PROMPT = "Begin the probe."


async def run_probe() -> int:
    base_url = os.getenv("OLLAMA_OPENAI_BASE_URL", "http://100.106.241.33:11434")
    print(f"[probe] base_url={base_url}")

    server = make_echo_server()
    options = ClaudeAgentOptions(
        model=os.getenv("PROBE_MODEL", "nemotron-3-nano:4b"),
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"probe": server},
        base_url=base_url,
        max_tokens=512,
    )

    turns_assistant = 0
    turns_result = 0
    saw_tool_use = False
    saw_end_turn = False
    saw_text_after_tool = False
    last_blocks: list = []
    last_stop_reason: str | None = None

    start = time.time()

    async with ClaudeSDKClient(options=options) as client:
        await client.query(USER_PROMPT)

        async def consume_with_timeout() -> None:
            nonlocal turns_assistant, turns_result, saw_tool_use, saw_end_turn
            nonlocal saw_text_after_tool, last_blocks, last_stop_reason
            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    turns_assistant += 1
                    last_blocks = message.content
                    has_tool = False
                    has_text = False
                    for b in message.content:
                        if isinstance(b, ToolUseBlock):
                            has_tool = True
                            saw_tool_use = True
                            print(f"[probe] turn{turns_assistant} ToolUseBlock"
                                  f"  name={b.name}  input={b.input}")
                        elif isinstance(b, ThinkingBlock):
                            print(f"[probe] turn{turns_assistant} ThinkingBlock"
                                  f"  thinking={b.thinking[:120]!r}")
                        elif isinstance(b, TextBlock):
                            has_text = True
                            print(f"[probe] turn{turns_assistant} TextBlock"
                                  f"  text={b.text[:200]!r}")
                    if saw_tool_use and has_text and not has_tool:
                        saw_text_after_tool = True
                elif isinstance(message, ResultMessage):
                    turns_result += 1
                    last_stop_reason = message.stop_reason
                    print(f"[probe] ResultMessage stop_reason={message.stop_reason!r}")
                    if message.stop_reason == "end_turn":
                        saw_end_turn = True

        try:
            await asyncio.wait_for(consume_with_timeout(), timeout=180.0)
        except asyncio.TimeoutError:
            print("[probe] TIMEOUT after 180s — likely the same hang we see in v1")
            return 2

    elapsed = time.time() - start
    print(f"[probe] elapsed={elapsed:.1f}s  assistant_turns={turns_assistant}"
          f"  result_messages={turns_result}")
    print(f"[probe] echo_invocations={len(server.invocations)}")
    print(f"[probe] saw_tool_use={saw_tool_use}  saw_text_after_tool="
          f"{saw_text_after_tool}  saw_end_turn={saw_end_turn}")

    if not saw_tool_use:
        print("[probe] FAIL: model never emitted a ToolUseBlock")
        return 3
    if len(server.invocations) == 0:
        print("[probe] FAIL: tool handler never ran")
        return 4
    if turns_assistant < 2:
        print("[probe] FAIL: only one assistant turn — probably the v1 hang reproduced "
              "via the OpenAI-compat path too")
        return 5
    if not saw_end_turn:
        print("[probe] PARTIAL: turn 2 fired (no hang), but final stop_reason "
              f"was {last_stop_reason!r} not end_turn")
        return 1

    print("[probe] PASS: structured tool round-trip + end_turn on turn 2")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(run_probe()))
