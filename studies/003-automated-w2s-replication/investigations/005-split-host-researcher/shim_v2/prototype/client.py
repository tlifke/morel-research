"""Shim v2 prototype: OpenAI-compat wire to Ollama, Anthropic-shape facade.

Minimal, runnable. Not a full reimplementation — just enough to prove the
conversion-function design described in ../README.md. The Anthropic-shape
dataclasses below mirror the names agent.py imports.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import os
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union

import httpx


_DEFAULT_BASE_URL_FALLBACK = "http://100.97.4.17:11434"


def _resolve_default_base_url() -> str:
    return os.getenv("OLLAMA_OPENAI_BASE_URL", _DEFAULT_BASE_URL_FALLBACK)


@dataclass
class TextBlock:
    text: str


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class ThinkingBlock:
    thinking: str = ""
    signature: Optional[str] = None


@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: Any
    is_error: bool = False


@dataclass
class AssistantMessage:
    content: List[Union[TextBlock, ThinkingBlock, ToolUseBlock]]
    model: Optional[str] = None


@dataclass
class ResultMessage:
    result: Optional[str] = None
    stop_reason: Optional[str] = None


@dataclass
class ClaudeAgentOptions:
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: List[str] = field(default_factory=list)
    mcp_servers: Dict[str, Any] = field(default_factory=dict)
    permission_mode: Optional[str] = None
    cwd: Optional[str] = None
    setting_sources: Optional[List[str]] = None
    betas: Optional[List[str]] = None
    cli_path: Optional[str] = None
    max_tokens: int = 8192
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    tool_invocation_hint: Optional[str] = None
    bash_cwd: Optional[str] = None
    bash_env: Optional[Dict[str, str]] = None


def _anthropic_tools_to_openai_tools(
    anthropic_tools: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convert Anthropic tools array → OpenAI tools array.

    Anthropic shape: [{"name", "description", "input_schema": {...JSON Schema...}}]
    OpenAI shape:    [{"type": "function", "function": {"name", "description", "parameters": {...}}}]

    input_schema and parameters are both JSON Schema. Pass through verbatim.
    """
    out: List[Dict[str, Any]] = []
    for t in anthropic_tools:
        name = t.get("name")
        if not name:
            continue
        out.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema") or {"type": "object", "properties": {}},
                },
            }
        )
    return out


_TOOL_CALL_TAG_RE = re.compile(r"<tool_call>\s*(\{.*?\})\s*</tool_call>", re.DOTALL)


def _parse_hermes_tool_calls(text: str) -> Tuple[str, List[ToolUseBlock]]:
    """Parse Qwen3.5 Hermes-style <tool_call>{...}</tool_call> tags from text.

    Returns (residual_text_with_tags_stripped, list_of_ToolUseBlocks).
    """
    blocks: List[ToolUseBlock] = []
    for m in _TOOL_CALL_TAG_RE.finditer(text):
        try:
            payload = json.loads(m.group(1))
            name = payload.get("name") or ""
            args = payload.get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {"_raw": args}
            blocks.append(
                ToolUseBlock(id=f"call_{uuid.uuid4().hex[:12]}", name=name, input=args)
            )
        except json.JSONDecodeError:
            continue
    residual = _TOOL_CALL_TAG_RE.sub("", text).strip()
    return residual, blocks


def _openai_response_to_anthropic_blocks(
    openai_response: Dict[str, Any],
    *,
    parse_hermes_tags: bool = False,
) -> Tuple[List[Union[TextBlock, ThinkingBlock, ToolUseBlock]], str]:
    """Convert OpenAI chat.completion response → Anthropic-shape content blocks.

    Returns (blocks, stop_reason). stop_reason normalized to Anthropic
    vocabulary: "tool_use" | "end_turn" | "max_tokens".
    """
    choices = openai_response.get("choices") or []
    if not choices:
        return [], "end_turn"
    choice = choices[0]
    msg = choice.get("message") or {}
    finish_reason = choice.get("finish_reason") or "stop"

    blocks: List[Union[TextBlock, ThinkingBlock, ToolUseBlock]] = []

    reasoning = msg.get("reasoning_content") or msg.get("thinking")
    if reasoning:
        blocks.append(ThinkingBlock(thinking=str(reasoning), signature=None))

    content = msg.get("content")
    tool_calls = msg.get("tool_calls") or []

    synthesized_from_text: List[ToolUseBlock] = []
    if isinstance(content, str) and content:
        if parse_hermes_tags:
            residual, synthesized_from_text = _parse_hermes_tool_calls(content)
            if residual:
                blocks.append(TextBlock(text=residual))
        else:
            blocks.append(TextBlock(text=content))

    for tc in tool_calls:
        func = tc.get("function") or {}
        name = func.get("name") or ""
        raw_args = func.get("arguments")
        if isinstance(raw_args, str):
            try:
                parsed_args = json.loads(raw_args) if raw_args else {}
            except json.JSONDecodeError:
                parsed_args = {"_raw": raw_args}
        elif isinstance(raw_args, dict):
            parsed_args = raw_args
        else:
            parsed_args = {}
        tu_id = tc.get("id") or f"call_{uuid.uuid4().hex[:12]}"
        blocks.append(ToolUseBlock(id=tu_id, name=name, input=parsed_args))

    blocks.extend(synthesized_from_text)

    any_tool_use = any(isinstance(b, ToolUseBlock) for b in blocks)
    if any_tool_use:
        stop_reason = "tool_use"
    elif finish_reason == "length":
        stop_reason = "max_tokens"
    else:
        stop_reason = "end_turn"

    return blocks, stop_reason


def _make_tool_result_payload(
    tool_use_id: str,
    anthropic_tool_result_content: Any,
    *,
    is_error: bool = False,
) -> Dict[str, Any]:
    """Build the OpenAI-shape tool result message.

    OpenAI shape: {"role": "tool", "tool_call_id": <id>, "content": <str>}.
    Anthropic shape uses a content array; collapse to a single string,
    prefixing an error marker if needed.
    """
    if isinstance(anthropic_tool_result_content, str):
        text = anthropic_tool_result_content
    elif isinstance(anthropic_tool_result_content, list):
        parts: List[str] = []
        for item in anthropic_tool_result_content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(item.get("text", ""))
                else:
                    parts.append(json.dumps(item))
            else:
                parts.append(str(item))
        text = "\n".join(parts)
    else:
        text = json.dumps(anthropic_tool_result_content)
    if is_error:
        text = f"[tool error]\n{text}"
    return {"role": "tool", "tool_call_id": tool_use_id, "content": text}


class _Adapter:
    name = "generic"
    parse_hermes_tags = False

    def shape_request(
        self,
        *,
        system_prompt: Optional[str],
        openai_tools: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: int,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "model": model,
            "messages": list(messages),
            "max_tokens": max_tokens,
        }
        if system_prompt:
            payload["messages"] = [{"role": "system", "content": system_prompt}] + payload["messages"]
        if openai_tools:
            payload["tools"] = openai_tools
            payload["tool_choice"] = "auto"
        return payload


class OpenAINativeAdapter(_Adapter):
    name = "openai-native"


class Qwen35HermesEmbedAdapter(_Adapter):
    """Workaround for ollama/ollama#14601.

    Do not pass `tools` to Ollama (the renderer is broken). Instead, embed
    a Hermes-style tool definition block in the system prompt and parse
    <tool_call>{...}</tool_call> tags out of the model's content.
    """

    name = "qwen35-hermes-embed"
    parse_hermes_tags = True

    def shape_request(
        self,
        *,
        system_prompt: Optional[str],
        openai_tools: List[Dict[str, Any]],
        messages: List[Dict[str, Any]],
        model: str,
        max_tokens: int,
    ) -> Dict[str, Any]:
        tool_lines = [json.dumps(t) for t in openai_tools]
        hermes_block = (
            "# Tools\n\nYou have access to the following functions. Call them by "
            'emitting <tool_call>{"name": ..., "arguments": ...}</tool_call> on '
            "its own line.\n\n<tools>\n" + "\n".join(tool_lines) + "\n</tools>"
        )
        combined_system = (
            (system_prompt + "\n\n" + hermes_block).strip()
            if system_prompt
            else hermes_block
        )
        payload: Dict[str, Any] = {
            "model": model,
            "messages": [{"role": "system", "content": combined_system}] + list(messages),
            "max_tokens": max_tokens,
        }
        return payload


_ADAPTERS = (
    (("nemotron",), OpenAINativeAdapter),
    (("qwen3.5",), Qwen35HermesEmbedAdapter),
)


def pick_adapter(model: Optional[str]) -> _Adapter:
    if model:
        m = model.lower()
        for prefixes, cls in _ADAPTERS:
            if any(p in m for p in prefixes):
                return cls()
    return _Adapter()


class ClaudeSDKClient:
    def __init__(self, options: Optional[ClaudeAgentOptions] = None):
        self.options = options or ClaudeAgentOptions()
        self._history: List[Dict[str, Any]] = []
        self._pending_queue: Optional[asyncio.Queue] = None
        self._http: Optional[httpx.AsyncClient] = None
        self._tool_index: Dict[str, Any] = {}
        self._anthropic_tools: List[Dict[str, Any]] = []
        self._openai_tools: List[Dict[str, Any]] = []
        self._adapter: _Adapter = pick_adapter(self.options.model)
        self._build_tool_index()

    def _build_tool_index(self) -> None:
        allowed = set(self.options.allowed_tools or [])
        for server_key, server in (self.options.mcp_servers or {}).items():
            if not hasattr(server, "tools") or not isinstance(getattr(server, "tools", None), dict):
                continue
            for tool_name, t in server.tools.items():
                qualified = f"mcp__{server_key}__{tool_name}"
                if allowed and qualified not in allowed and t.name not in allowed:
                    continue
                self._tool_index[t.name] = t
                self._anthropic_tools.append(
                    {
                        "name": t.name,
                        "description": getattr(t, "description", "") or "",
                        "input_schema": getattr(t, "input_schema", None)
                        or {"type": "object", "properties": {}},
                    }
                )
        self._openai_tools = _anthropic_tools_to_openai_tools(self._anthropic_tools)

    async def __aenter__(self) -> "ClaudeSDKClient":
        base_url = self.options.base_url or _resolve_default_base_url()
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=10.0),
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._http is not None:
            await self._http.aclose()
        self._http = None

    async def query(self, prompt: str) -> None:
        self._history.append({"role": "user", "content": prompt})
        self._pending_queue = asyncio.Queue()
        asyncio.create_task(self._run_turn())

    async def receive_response(self) -> AsyncIterator[Any]:
        if self._pending_queue is None:
            return
        queue = self._pending_queue
        while True:
            item = await queue.get()
            if item is None:
                return
            yield item

    async def _post_chat_completions(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        assert self._http is not None
        resp = await self._http.post("/v1/chat/completions", json=payload)
        resp.raise_for_status()
        return resp.json()

    async def _run_turn(self) -> None:
        queue = self._pending_queue
        assert queue is not None
        try:
            while True:
                base_system = self.options.system_prompt or ""
                hint = self.options.tool_invocation_hint or os.getenv(
                    "CLAUDE_AGENT_SDK_SHIM_TOOL_INVOCATION_HINT"
                )
                if hint:
                    base_system = (base_system + "\n\n" + hint).strip()

                payload = self._adapter.shape_request(
                    system_prompt=base_system or None,
                    openai_tools=self._openai_tools,
                    messages=self._history,
                    model=self.options.model or "nemotron-3-nano:4b",
                    max_tokens=self.options.max_tokens,
                )

                response = await self._post_chat_completions(payload)
                blocks, stop_reason = _openai_response_to_anthropic_blocks(
                    response, parse_hermes_tags=self._adapter.parse_hermes_tags
                )

                tool_uses = [b for b in blocks if isinstance(b, ToolUseBlock)]
                assistant_history_entry = self._blocks_to_history_entry(blocks, response)

                await queue.put(
                    AssistantMessage(content=blocks, model=response.get("model"))
                )

                if not tool_uses or stop_reason != "tool_use":
                    self._history.append(assistant_history_entry)
                    await queue.put(ResultMessage(stop_reason=stop_reason))
                    await queue.put(None)
                    return

                self._history.append(assistant_history_entry)
                for tu in tool_uses:
                    result = await self._invoke_tool(tu)
                    self._history.append(
                        _make_tool_result_payload(
                            tu.id,
                            result.get("content", ""),
                            is_error=bool(result.get("is_error", False)),
                        )
                    )
        except Exception as e:
            await queue.put(ResultMessage(result=f"error: {e}", stop_reason="error"))
            await queue.put(None)

    @staticmethod
    def _blocks_to_history_entry(
        blocks: List[Union[TextBlock, ThinkingBlock, ToolUseBlock]],
        openai_response: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Reconstruct an OpenAI-shape assistant message from blocks.

        We do not round-trip thinking text into history (no OpenAI field
        for it; would only inflate context). Tool calls are reconstructed
        so the next-turn POST is well-formed.
        """
        text_parts: List[str] = []
        tool_calls: List[Dict[str, Any]] = []
        for b in blocks:
            if isinstance(b, TextBlock):
                text_parts.append(b.text)
            elif isinstance(b, ToolUseBlock):
                tool_calls.append(
                    {
                        "id": b.id,
                        "type": "function",
                        "function": {
                            "name": b.name,
                            "arguments": json.dumps(b.input),
                        },
                    }
                )
        entry: Dict[str, Any] = {"role": "assistant"}
        entry["content"] = "\n".join(text_parts) if text_parts else None
        if tool_calls:
            entry["tool_calls"] = tool_calls
        return entry

    async def _invoke_tool(self, tu: ToolUseBlock) -> Dict[str, Any]:
        handler = self._tool_index.get(tu.name)
        if handler is None:
            return {
                "content": [{"type": "text", "text": f"unknown tool: {tu.name}"}],
                "is_error": True,
            }
        try:
            result = handler.handler(tu.input)
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, dict) and "content" in result:
                return result
            return {"content": [{"type": "text", "text": json.dumps(result)}]}
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"tool error: {e}"}],
                "is_error": True,
            }
