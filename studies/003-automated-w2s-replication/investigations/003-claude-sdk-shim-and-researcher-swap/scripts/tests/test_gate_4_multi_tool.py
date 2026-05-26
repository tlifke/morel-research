import asyncio
import json
import os
import sys
import time
import urllib.request
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


SERVER_URL = os.getenv("W2S_SERVER_URL", "http://localhost:8000")


def _http_get(url: str, timeout: int = 30):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_post(url: str, payload: dict, timeout: int = 60):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


@tool(
    "evaluate_predictions",
    "Evaluate predictions and get PGR score. Ground truth is held server-side.",
    {
        "type": "object",
        "properties": {
            "predictions": {"type": "array", "items": {"type": "integer"}},
            "dataset": {"type": "string"},
            "weak_model": {"type": "string"},
            "strong_model": {"type": "string"},
        },
        "required": ["predictions", "dataset", "weak_model", "strong_model"],
    },
)
async def evaluate_predictions(args):
    try:
        result = _http_post(
            f"{SERVER_URL}/api/evaluate-predictions",
            {
                "predictions": args.get("predictions", []),
                "dataset": args.get("dataset", ""),
                "weak_model": args.get("weak_model", ""),
                "strong_model": args.get("strong_model", ""),
            },
            timeout=120,
        )
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "is_error": True}


@tool(
    "share_finding",
    "Share an empirical finding with other workers.",
    {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "title": {"type": "string"},
            "idea_name": {"type": "string"},
            "metrics": {"type": "object"},
            "config": {"type": "object"},
            "worked": {"type": "boolean"},
            "finding_type": {"type": "string"},
        },
        "required": ["summary"],
    },
)
async def share_finding(args):
    try:
        result = _http_post(f"{SERVER_URL}/api/findings/share", args, timeout=30)
        return {"content": [{"type": "text", "text": json.dumps(result)}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "is_error": True}


@tool(
    "get_leaderboard",
    "Get the leaderboard of best results ranked by PGR.",
    {"type": "object", "properties": {}, "required": []},
)
async def get_leaderboard(args):
    try:
        result = _http_get(f"{SERVER_URL}/api/leaderboard", timeout=30)
        entries = result.get("experiments", result.get("entries", []))
        top = entries[0].get("pgr") if entries else None
        return {"content": [{"type": "text", "text": json.dumps({"top_pgr": top, "count": len(entries), "entries": entries[:5]})}]}
    except Exception as e:
        return {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}], "is_error": True}


async def main() -> int:
    start = time.time()

    server = create_sdk_mcp_server(
        name="w2s",
        version="1.0.0",
        tools=[evaluate_predictions, share_finding, get_leaderboard],
    )

    options = ClaudeAgentOptions(
        model="qwen3:4b",
        mcp_servers={"w2s": server},
        allowed_tools=[
            "mcp__w2s__evaluate_predictions",
            "mcp__w2s__share_finding",
            "mcp__w2s__get_leaderboard",
        ],
        max_tokens=16384,
        system_prompt=(
            "You are a research assistant with access to W2S evaluation tools. "
            "You MUST call tools to answer questions about the leaderboard or to "
            "evaluate predictions. Do not guess or fabricate numbers. "
            "When the user asks for the leaderboard, call get_leaderboard. "
            "When the user asks to submit predictions, call evaluate_predictions "
            "with the exact arguments specified. After receiving the tool result, "
            "report the actual PGR number from the response in your final answer."
        ),
    )

    from claude_agent_sdk_shim import ResultMessage
    tool_calls = []
    text_chunks = []
    result_messages = []

    prompt = (
        "First, get the current leaderboard. "
        "Then submit these predictions: [0,1,0,1,0] for dataset='math', "
        "weak_model='Qwen/Qwen1.5-0.5B-Chat', strong_model='Qwen/Qwen3-4B-Base'. "
        "Finally tell me the PGR value returned."
    )

    async with ClaudeSDKClient(options) as client:
        await client.query(prompt)
        async for msg in client.receive_response():
            if isinstance(msg, AssistantMessage):
                for block in msg.content:
                    if isinstance(block, ToolUseBlock):
                        tool_calls.append({"name": block.name, "input": block.input})
                    if isinstance(block, TextBlock):
                        text_chunks.append(block.text)
            if isinstance(msg, ResultMessage):
                result_messages.append({"stop_reason": msg.stop_reason, "result": msg.result})

    elapsed = time.time() - start

    called_names = {tc["name"] for tc in tool_calls}
    saw_leaderboard = "get_leaderboard" in called_names
    saw_evaluate = "evaluate_predictions" in called_names

    final_text = "\n".join(text_chunks)
    import re
    pgr_match = re.search(r"-?\d+\.\d+|-?\d+", final_text)
    saw_pgr = pgr_match is not None

    print(f"wall_time_sec={elapsed:.2f}")
    print(f"tool_calls={tool_calls}")
    print(f"final_text={final_text!r}")
    print(f"saw_leaderboard={saw_leaderboard}")
    print(f"saw_evaluate={saw_evaluate}")
    print(f"saw_pgr_number={saw_pgr}")
    print(f"result_messages={result_messages}")

    assert saw_leaderboard, "Model did not invoke get_leaderboard"
    assert saw_evaluate, "Model did not invoke evaluate_predictions"
    assert saw_pgr, "Final text did not include a numeric PGR"
    print("GATE 4 PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
