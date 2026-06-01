#!/usr/bin/env python3
"""inv 006: instrument BaseAgent.execute to write a full per-session JSONL
trace covering every message in either direction.

Why: the existing session log format
    [HH:MM:SS] AssistantMessage
    Tool: X
    Input: {...}

    [HH:MM:SS] UserMessage

drops three critical things:
1. Tool results for non-Bash tools (Read, Glob, evaluate_predictions
   ack, etc.) — the UserMessage line has no body.
2. The initial input to the agent (the patch text on iteration 0, or
   the handoff bootstrap on iterations 1+).
3. Any AssistantMessage text that isn't preceded/followed by a tool
   call cleanly (some prose contexts get dropped by simple regex
   parsers).

We want to be able to reconstruct exactly: \"this is the instruction
the researcher received, this is what it thought, this is what it
emitted, this is what came back\" for every iteration. So we write
a JSONL sidecar at $GATE5_RUN_DIR/logs/<agent_name>.jsonl with one
line per message:

    {"ts": "...", "kind": "input", "content": "<initial task text>"}
    {"ts": "...", "kind": "AssistantMessage", "content": [{"type": "TextBlock", "text": "..."}, {"type": "ToolUseBlock", "name": "Bash", "input": {...}, "id": "..."}]}
    {"ts": "...", "kind": "UserMessage", "content": [{"type": "ToolResultBlock", "tool_use_id": "...", "content": "...", "is_error": false}]}
    {"ts": "...", "kind": "ResultMessage", "content": [], "stop_reason": "end_turn"}

render_run.py preferentially reads this JSONL over the legacy .log
when both exist.

Applies to upstream w2s_research/research_loop/agent.py BaseAgent.execute.
Idempotent.
"""
from __future__ import annotations
from pathlib import Path

AGENT_PY = Path(
    "/home/tlifke/Projects/automated-w2s-research/"
    "w2s_research/research_loop/agent.py"
)


PATCH_MARKER = "# inv 006: full session trace"


def patch() -> bool:
    src = AGENT_PY.read_text()
    if PATCH_MARKER in src:
        print("[agent.py] full-session-logging already patched")
        return False

    anchor = (
        "            async with ClaudeSDKClient(options=options) as client:\n"
        "                await client.query(task)\n"
    )
    if anchor not in src:
        raise SystemExit("[agent.py] anchor not found — execute() signature changed?")

    new = (
        "            # inv 006: full session trace — open JSONL sidecar and record the\n"
        "            # initial input (patch text on iter 0; handoff bootstrap on iter N+1).\n"
        "            _trace_path = None\n"
        "            try:\n"
        "                import os as _os, json as _json\n"
        "                _run_dir = _os.environ.get(\"GATE5_RUN_DIR\")\n"
        "                if _run_dir:\n"
        "                    from pathlib import Path as _P\n"
        "                    _trace_path = _P(_run_dir) / \"logs\" / f\"{self.name}.jsonl\"\n"
        "                    _trace_path.parent.mkdir(parents=True, exist_ok=True)\n"
        "                    with open(_trace_path, \"w\") as _tf:\n"
        "                        _tf.write(_json.dumps({\n"
        "                            \"ts\": datetime.now().isoformat(),\n"
        "                            \"kind\": \"input\",\n"
        "                            \"content\": task,\n"
        "                        }) + \"\\n\")\n"
        "            except Exception as _e:\n"
        "                print(f\"[TraceJSONL] init failed: {_e}\", flush=True)\n"
        "\n"
        "            async with ClaudeSDKClient(options=options) as client:\n"
        "                await client.query(task)\n"
    )
    src = src.replace(anchor, new)

    # After the existing inv 005 msg_trace block, append a JSONL writer for the same message.
    msg_trace_anchor = (
        "                    try:\n"
        "                        with open(\"/tmp/inv005_msg_trace.log\", \"a\") as _df:\n"
        "                            _bnames = [type(b).__name__ for b in getattr(message, \"content\", []) or []]\n"
        "                            _df.write(f\"{datetime.now().isoformat()}  {type(message).__name__}  blocks={_bnames}\\n\")\n"
        "                    except Exception:\n"
        "                        pass\n"
    )
    if msg_trace_anchor not in src:
        raise SystemExit("[agent.py] msg_trace anchor not found — inv 005 trace removed?")

    new_full_trace = msg_trace_anchor + (
        "                    # inv 006: full session trace — serialize every block (incl tool_result content)\n"
        "                    if _trace_path is not None:\n"
        "                        try:\n"
        "                            import json as _json\n"
        "                            _blocks_out = []\n"
        "                            for _b in getattr(message, \"content\", []) or []:\n"
        "                                _entry = {\"type\": type(_b).__name__}\n"
        "                                for _attr in (\n"
        "                                    \"text\", \"thinking\", \"signature\",\n"
        "                                    \"name\", \"input\", \"id\",\n"
        "                                    \"tool_use_id\", \"content\", \"is_error\",\n"
        "                                ):\n"
        "                                    if hasattr(_b, _attr):\n"
        "                                        _v = getattr(_b, _attr)\n"
        "                                        try:\n"
        "                                            _json.dumps(_v)\n"
        "                                            _entry[_attr] = _v\n"
        "                                        except (TypeError, ValueError):\n"
        "                                            _entry[_attr] = str(_v)\n"
        "                                _blocks_out.append(_entry)\n"
        "                            _line = {\n"
        "                                \"ts\": datetime.now().isoformat(),\n"
        "                                \"kind\": type(message).__name__,\n"
        "                                \"content\": _blocks_out,\n"
        "                            }\n"
        "                            for _extra in (\"stop_reason\", \"result\", \"model\"):\n"
        "                                if hasattr(message, _extra):\n"
        "                                    _v = getattr(message, _extra)\n"
        "                                    if _v is not None:\n"
        "                                        _line[_extra] = _v if isinstance(_v, (str, int, float, bool)) else str(_v)\n"
        "                            with open(_trace_path, \"a\") as _tf:\n"
        "                                _tf.write(_json.dumps(_line, default=str) + \"\\n\")\n"
        "                        except Exception as _e:\n"
        "                            print(f\"[TraceJSONL] write failed: {_e}\", flush=True)\n"
    )
    src = src.replace(msg_trace_anchor, new_full_trace)

    AGENT_PY.write_text(src)
    print("[agent.py] patched: full session JSONL trace at $GATE5_RUN_DIR/logs/<agent>.jsonl")
    return True


if __name__ == "__main__":
    patch()
