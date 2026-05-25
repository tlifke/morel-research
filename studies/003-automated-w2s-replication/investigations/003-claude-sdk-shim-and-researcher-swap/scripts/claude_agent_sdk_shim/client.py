import asyncio
import inspect
import json
import os
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

import anthropic

from .types import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
)
from .tools import SdkMcpServer, SdkTool
from .parser import synthesize_tool_use_blocks


DEFAULT_BASE_URL = os.getenv("OLLAMA_ANTHROPIC_BASE_URL", "http://100.97.4.17:11434")


class ClaudeSDKClient:
    def __init__(self, options: Optional[ClaudeAgentOptions] = None):
        self.options = options or ClaudeAgentOptions()
        self._history: List[Dict[str, Any]] = []
        self._pending_queue: Optional[asyncio.Queue] = None
        self._client: Optional[anthropic.AsyncAnthropic] = None
        self._tool_index: Dict[str, SdkTool] = {}
        self._anthropic_tools: List[Dict[str, Any]] = []
        self._build_tool_index()

    def _build_tool_index(self) -> None:
        allowed = set(self.options.allowed_tools or [])
        for server_key, server in (self.options.mcp_servers or {}).items():
            if not isinstance(server, SdkMcpServer):
                continue
            for tool_name, t in server.tools.items():
                qualified = f"mcp__{server_key}__{tool_name}"
                if allowed and qualified not in allowed and t.name not in allowed:
                    continue
                self._tool_index[t.name] = t
                self._anthropic_tools.append({
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.input_schema,
                })

    async def __aenter__(self) -> "ClaudeSDKClient":
        base_url = self.options.base_url or DEFAULT_BASE_URL
        api_key = self.options.api_key or os.getenv("ANTHROPIC_API_KEY") or "ollama"
        self._client = anthropic.AsyncAnthropic(base_url=base_url, api_key=api_key)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.close()
        self._client = None

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

    async def _run_turn(self) -> None:
        queue = self._pending_queue
        assert queue is not None
        try:
            while True:
                kwargs: Dict[str, Any] = {
                    "model": self.options.model or "gemma3:4b-it-qat",
                    "max_tokens": self.options.max_tokens,
                    "messages": self._history,
                }
                if self.options.system_prompt:
                    kwargs["system"] = self.options.system_prompt
                if self._anthropic_tools:
                    kwargs["tools"] = self._anthropic_tools

                response = await self._client.messages.create(**kwargs)

                blocks_out: List[Any] = []
                tool_uses: List[ToolUseBlock] = []
                assistant_content_for_history: List[Dict[str, Any]] = []
                known_tool_names = set(self._tool_index.keys())
                synthesized_any = False
                for block in response.content:
                    btype = getattr(block, "type", None)
                    if btype == "text":
                        residual, synth = synthesize_tool_use_blocks(
                            block.text, known_tool_names=known_tool_names
                        )
                        if synth:
                            synthesized_any = True
                            if residual:
                                blocks_out.append(TextBlock(text=residual))
                                assistant_content_for_history.append({"type": "text", "text": residual})
                            for tu in synth:
                                blocks_out.append(tu)
                                tool_uses.append(tu)
                                assistant_content_for_history.append({
                                    "type": "tool_use",
                                    "id": tu.id,
                                    "name": tu.name,
                                    "input": tu.input,
                                })
                        else:
                            blocks_out.append(TextBlock(text=block.text))
                            assistant_content_for_history.append({"type": "text", "text": block.text})
                    elif btype == "tool_use":
                        tu = ToolUseBlock(id=block.id, name=block.name, input=block.input or {})
                        blocks_out.append(tu)
                        tool_uses.append(tu)
                        assistant_content_for_history.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input or {},
                        })

                await queue.put(AssistantMessage(content=blocks_out, model=response.model))

                effective_stop = response.stop_reason
                if synthesized_any and effective_stop != "tool_use":
                    effective_stop = "tool_use"

                if not tool_uses or effective_stop != "tool_use":
                    self._history.append({"role": "assistant", "content": assistant_content_for_history})
                    await queue.put(ResultMessage(stop_reason=response.stop_reason))
                    await queue.put(None)
                    return

                self._history.append({"role": "assistant", "content": assistant_content_for_history})

                tool_result_blocks: List[Dict[str, Any]] = []
                for tu in tool_uses:
                    result = await self._invoke_tool(tu)
                    tool_result_blocks.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": result.get("content", []),
                        "is_error": bool(result.get("is_error", False)),
                    })

                self._history.append({"role": "user", "content": tool_result_blocks})
        except Exception as e:
            await queue.put(ResultMessage(result=f"error: {e}", stop_reason="error"))
            await queue.put(None)

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
