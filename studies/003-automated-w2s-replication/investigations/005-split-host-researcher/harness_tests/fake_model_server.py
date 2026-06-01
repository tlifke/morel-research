"""Deterministic fake model server speaking OpenAI-compat
/v1/chat/completions. Returns scripted assistant responses from a
scenario YAML so the inv 005 harness can be tested without any live
LLM or GPU.

Scenario format (see scenarios/*.yaml):

    turns:
      - tool_calls:
          - name: Bash
            arguments: {command: "python -m w2s_research.ideas..."}
      - text: "I will now submit predictions."
        tool_calls:
          - name: mcp__server-api-tools__evaluate_predictions
            arguments: {predictions: [1, 0, 1, ...]}
      - text: "Done."
        finish_reason: stop

Each scenario plays its `turns` list in order. After the last scripted
turn, the server returns `{finish_reason: "stop"}` so the agent loop
ends naturally.

Run standalone for manual probing:
    uv run --with aiohttp --with pyyaml python fake_model_server.py \
        --scenario scenarios/q1_happy_path.yaml --port 8800
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiohttp import web
import yaml


class ScenarioPlayback:
    """Plays a scenario YAML one turn per /v1/chat/completions request.

    Tracks which request maps to which scripted turn by counting calls.
    Records all received requests for later assertion.
    """

    def __init__(self, scenario_path: Path):
        with open(scenario_path) as f:
            data = yaml.safe_load(f)
        self.turns: List[Dict[str, Any]] = data.get("turns", [])
        self.received_requests: List[Dict[str, Any]] = []
        self.turn_index = 0

    def next_response(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        self.received_requests.append(
            {
                "messages": list(request_body.get("messages", [])),
                "tools": list(request_body.get("tools", [])),
                "model": request_body.get("model"),
                "timestamp": time.time(),
            }
        )

        if self.turn_index >= len(self.turns):
            # Out of script — return a stop turn
            scripted = {"text": "(end of scripted scenario)", "finish_reason": "stop"}
        else:
            scripted = self.turns[self.turn_index]
            self.turn_index += 1

        return self._scripted_to_openai_response(scripted, request_body)

    def _scripted_to_openai_response(
        self, scripted: Dict[str, Any], request_body: Dict[str, Any]
    ) -> Dict[str, Any]:
        choices_message: Dict[str, Any] = {"role": "assistant"}

        if scripted.get("text") is not None:
            choices_message["content"] = scripted["text"]
        else:
            choices_message["content"] = None

        scripted_tool_calls = scripted.get("tool_calls") or []
        if scripted_tool_calls:
            choices_message["tool_calls"] = [
                {
                    "id": f"call_{uuid.uuid4().hex[:12]}",
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": json.dumps(tc.get("arguments", {})),
                    },
                }
                for tc in scripted_tool_calls
            ]
            finish = "tool_calls"
        else:
            finish = scripted.get("finish_reason", "stop")

        return {
            "id": f"chatcmpl-{uuid.uuid4().hex[:16]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request_body.get("model", "fake-model"),
            "choices": [
                {"index": 0, "message": choices_message, "finish_reason": finish}
            ],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        }


def make_app(playback: ScenarioPlayback) -> web.Application:
    app = web.Application()

    async def chat_completions(request: web.Request) -> web.Response:
        body = await request.json()
        resp = playback.next_response(body)
        return web.json_response(resp)

    async def health(_: web.Request) -> web.Response:
        return web.json_response({"ok": True, "turn": playback.turn_index})

    async def replay(_: web.Request) -> web.Response:
        """For test assertions: return the full record of received requests."""
        return web.json_response(
            {"received": playback.received_requests, "turn_index": playback.turn_index}
        )

    app.router.add_post("/v1/chat/completions", chat_completions)
    app.router.add_get("/healthz", health)
    app.router.add_get("/_replay", replay)
    app["playback"] = playback
    return app


def run_server(scenario_path: Path, port: int) -> None:
    playback = ScenarioPlayback(scenario_path)
    app = make_app(playback)
    web.run_app(app, host="127.0.0.1", port=port, print=lambda *a, **kw: None)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", required=True, type=Path)
    parser.add_argument("--port", type=int, default=8800)
    args = parser.parse_args()
    print(f"fake_model_server: scenario={args.scenario}  port={args.port}",
          file=sys.stderr, flush=True)
    run_server(args.scenario, args.port)
