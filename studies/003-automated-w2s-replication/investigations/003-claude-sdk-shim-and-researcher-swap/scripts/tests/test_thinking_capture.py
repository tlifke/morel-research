import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claude_agent_sdk_shim import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
)


@dataclass
class _Block:
    type: str
    text: Optional[str] = None
    thinking: Optional[str] = None
    id: Optional[str] = None
    name: Optional[str] = None
    input: Optional[dict] = None


@dataclass
class _Response:
    content: List[_Block]
    stop_reason: str = "end_turn"
    model: str = "stub"


class _Messages:
    def __init__(self, responses: List[_Response]):
        self._responses = list(responses)
        self.calls: List[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class _StubClient:
    def __init__(self, responses: List[_Response]):
        self.messages = _Messages(responses)

    async def close(self):
        return


def _drain(client: ClaudeSDKClient) -> List[Any]:
    async def go():
        out = []
        async for msg in client.receive_response():
            out.append(msg)
        return out

    return asyncio.get_event_loop().run_until_complete(go())


def _run(prompt: str, responses: List[_Response]):
    async def go():
        opts = ClaudeAgentOptions(model="stub:test")
        client = ClaudeSDKClient(opts)
        client._client = _StubClient(responses)
        await client.query(prompt)
        out = []
        async for msg in client.receive_response():
            out.append(msg)
        return out, client

    return asyncio.run(go())


def test_explicit_thinking_block_emitted():
    resp = _Response(
        content=[
            _Block(type="thinking", thinking="reasoning step 1"),
            _Block(type="text", text="final answer"),
        ],
    )
    msgs, _ = _run("hello", [resp])
    assistant = [m for m in msgs if isinstance(m, AssistantMessage)]
    assert len(assistant) == 1
    kinds = [type(b).__name__ for b in assistant[0].content]
    assert kinds == ["ThinkingBlock", "TextBlock"]
    tb = assistant[0].content[0]
    assert isinstance(tb, ThinkingBlock)
    assert tb.source == "block"
    assert tb.text == "reasoning step 1"


def test_sidecar_thinking_field_emitted():
    resp = _Response(
        content=[
            _Block(type="text", text="hello back", thinking="quietly counted words"),
        ],
    )
    msgs, _ = _run("hi", [resp])
    assistant = [m for m in msgs if isinstance(m, AssistantMessage)]
    kinds = [type(b).__name__ for b in assistant[0].content]
    assert kinds == ["ThinkingBlock", "TextBlock"]
    tb = assistant[0].content[0]
    assert tb.source == "sidecar"
    assert "quietly" in tb.text


def test_no_thinking_no_block():
    resp = _Response(
        content=[_Block(type="text", text="just a reply")],
    )
    msgs, _ = _run("hi", [resp])
    assistant = [m for m in msgs if isinstance(m, AssistantMessage)]
    kinds = [type(b).__name__ for b in assistant[0].content]
    assert kinds == ["TextBlock"]


def test_multi_turn_rebuild_includes_thinking():
    r1 = _Response(
        content=[
            _Block(type="thinking", thinking="step A"),
            _Block(type="text", text="first reply"),
        ],
    )
    r2 = _Response(content=[_Block(type="text", text="second reply")])

    async def go():
        opts = ClaudeAgentOptions(model="stub:test")
        client = ClaudeSDKClient(opts)
        client._client = _StubClient([r1, r2])
        await client.query("q1")
        async for _ in client.receive_response():
            pass
        await client.query("q2")
        async for _ in client.receive_response():
            pass
        return client

    client = asyncio.run(go())
    assistant_turns = [m for m in client._history if m["role"] == "assistant"]
    assert len(assistant_turns) == 2
    first_assistant_content = assistant_turns[0]["content"]
    thinking_entries = [c for c in first_assistant_content if c.get("type") == "thinking"]
    assert thinking_entries and thinking_entries[0]["thinking"] == "step A"
    call_msgs = client._client.messages.calls[1]["messages"]
    final_assistant = [m for m in call_msgs if m["role"] == "assistant"][0]
    assert any(c.get("type") == "thinking" for c in final_assistant["content"])


def test_sidecar_on_tool_use_block():
    resp = _Response(
        content=[
            _Block(
                type="tool_use",
                id="tu_1",
                name="add",
                input={"a": 1, "b": 2},
                thinking="planning the tool call",
            ),
        ],
        stop_reason="tool_use",
    )
    msgs, _ = _run("compute", [resp])
    assistant = [m for m in msgs if isinstance(m, AssistantMessage)]
    kinds = [type(b).__name__ for b in assistant[0].content]
    assert kinds[0] == "ThinkingBlock"
    assert "ToolUseBlock" in kinds
