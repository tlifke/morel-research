"""Parse pi session JSONL into UI-friendly structures."""

import json
from pathlib import Path
from typing import Any


def parse_session(session_file: str | Path, truncate: bool = True) -> dict:
    """Return {header, custom, events} where events is a chronological list of
    message events: {kind, role, index, blocks}.

    truncate=True limits toolResult text to 4000 chars (UI display); exports
    pass truncate=False to get the exact trace (SPEC section 7)."""
    header: dict[str, Any] = {}
    custom: dict[str, Any] | None = None
    events: list[dict[str, Any]] = []
    message_index = 0

    for line in Path(session_file).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = entry.get("type")
        if etype == "session":
            header = entry
        elif etype == "custom" and entry.get("customType") == "pi-clean-experiment":
            custom = entry.get("data")
        elif etype == "message":
            msg = entry.get("message", {})
            role = msg.get("role")
            blocks: list[dict[str, Any]] = []
            if role == "assistant":
                for bi, block in enumerate(msg.get("content") or []):
                    btype = block.get("type")
                    if btype == "text":
                        blocks.append({"kind": "text", "text": block.get("text", ""), "block_index": bi})
                    elif btype == "thinking":
                        # pi stores reasoning under `thinking` (with
                        # `thinkingSignature`), not `text` — check both.
                        blocks.append({"kind": "thinking", "text": block.get("thinking") or block.get("text", ""), "block_index": bi})
                    elif btype == "toolCall":
                        blocks.append(
                            {
                                "kind": "toolCall",
                                "name": block.get("name"),
                                "arguments": block.get("arguments"),
                                "block_index": bi,
                            }
                        )
            elif role == "toolResult":
                # toolResult content may be text or structured; keep raw pieces
                out = []
                for block in msg.get("content") or []:
                    btype = block.get("type")
                    if btype == "text":
                        text = block.get("text", "")
                        if truncate:
                            text = text[:4000]
                        out.append({"kind": "text", "text": text})
                    else:
                        raw = _jsonify(block)
                        if truncate:
                            raw = raw[:2000]
                        out.append({"kind": str(btype), "raw": raw})
                blocks = out
                blocks.append({"kind": "meta", "tool_name": msg.get("toolName"), "is_error": msg.get("isError")})
            elif role == "user":
                for block in msg.get("content") or []:
                    if block.get("type") == "text":
                        blocks.append({"kind": "text", "text": block.get("text", ""), "block_index": len(blocks)})
            events.append(
                {
                    "kind": "message",
                    "role": role,
                    "index": message_index,
                    "blocks": blocks,
                    "timestamp": entry.get("timestamp"),
                }
            )
            message_index += 1

    return {"header": header, "custom": custom, "events": events}


def assistant_turns(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Assistant message dicts (content blocks as-is) for export shapes."""
    turns = []
    for e in events:
        if e["kind"] == "message" and e["role"] == "assistant":
            turns.append(e)
    return turns


def _jsonify(obj: Any) -> str:
    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        return str(obj)
