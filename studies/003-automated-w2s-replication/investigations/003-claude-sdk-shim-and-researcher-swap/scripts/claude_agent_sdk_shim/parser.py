import json
import re
import uuid
from typing import Any, Dict, List, Optional, Tuple


_FUNCTION_CALL_TAG_RE = re.compile(
    r"<function_call>\s*(.*?)\s*</function_call>",
    re.DOTALL,
)
_TOOL_CALL_TAG_RE = re.compile(
    r"<tool_call>\s*(.*?)\s*</tool_call>",
    re.DOTALL,
)
_FENCED_JSON_RE = re.compile(
    r"```(?:json|tool_code|tool_call)?\s*\n?(\{.*?\})\s*\n?```",
    re.DOTALL,
)


def _synth_id() -> str:
    return f"toolu_synth_{uuid.uuid4().hex[:16]}"


_NAME_KEYS = ("name", "function", "function_name", "tool", "tool_name")
_ARG_KEYS = ("arguments", "parameters", "input", "args")


def _extract_arguments(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for key in _ARG_KEYS:
        if key in obj:
            val = obj[key]
            if isinstance(val, dict):
                return val
            if isinstance(val, str):
                try:
                    parsed = json.loads(val)
                    if isinstance(parsed, dict):
                        return parsed
                except Exception:
                    return None
            return None
    remainder = {k: v for k, v in obj.items() if k not in _NAME_KEYS}
    if remainder:
        return remainder
    return None


def _extract_name(obj: Any) -> Optional[str]:
    if not isinstance(obj, dict):
        return None
    for key in _NAME_KEYS:
        val = obj.get(key)
        if isinstance(val, str) and val:
            return val
    return None


def _is_tool_call_obj(obj: Any) -> bool:
    if not isinstance(obj, dict):
        return False
    if _extract_name(obj) is None:
        return False
    return _extract_arguments(obj) is not None


def _candidate_to_call(obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not _is_tool_call_obj(obj):
        return None
    return {"name": _extract_name(obj), "arguments": _extract_arguments(obj) or {}}


def _find_balanced_json_objects(text: str) -> List[Tuple[int, int, str]]:
    results: List[Tuple[int, int, str]] = []
    i = 0
    n = len(text)
    while i < n:
        if text[i] != "{":
            i += 1
            continue
        depth = 0
        in_str = False
        esc = False
        start = i
        while i < n:
            c = text[i]
            if in_str:
                if esc:
                    esc = False
                elif c == "\\":
                    esc = True
                elif c == '"':
                    in_str = False
            else:
                if c == '"':
                    in_str = True
                elif c == "{":
                    depth += 1
                elif c == "}":
                    depth -= 1
                    if depth == 0:
                        results.append((start, i + 1, text[start : i + 1]))
                        i += 1
                        break
            i += 1
        else:
            break
    return results


def extract_tool_calls(text: str, known_tool_names: Optional[set] = None) -> Tuple[str, List[Dict[str, Any]]]:
    calls: List[Dict[str, Any]] = []
    matched_spans: List[Tuple[int, int]] = []

    def _try_consume(raw: str) -> Optional[Dict[str, Any]]:
        raw = raw.strip()
        if not raw:
            return None
        try:
            obj = json.loads(raw)
        except Exception:
            return None
        if isinstance(obj, list):
            extracted: List[Dict[str, Any]] = []
            for item in obj:
                call = _candidate_to_call(item) if isinstance(item, dict) else None
                if call is None:
                    return None
                extracted.append(call)
            return {"_multi": extracted}
        if not isinstance(obj, dict):
            return None
        return _candidate_to_call(obj)

    for regex in (_FUNCTION_CALL_TAG_RE, _TOOL_CALL_TAG_RE):
        for m in regex.finditer(text):
            inner = m.group(1)
            consumed = _try_consume(inner)
            if consumed is None:
                continue
            if "_multi" in consumed:
                calls.extend(consumed["_multi"])
            else:
                calls.append(consumed)
            matched_spans.append((m.start(), m.end()))

    for m in _FENCED_JSON_RE.finditer(text):
        if any(s <= m.start() < e for s, e in matched_spans):
            continue
        consumed = _try_consume(m.group(1))
        if consumed is None:
            continue
        if "_multi" in consumed:
            calls.extend(consumed["_multi"])
        else:
            calls.append(consumed)
        matched_spans.append((m.start(), m.end()))

    for start, end, raw in _find_balanced_json_objects(text):
        if any(s <= start < e for s, e in matched_spans):
            continue
        consumed = _try_consume(raw)
        if consumed is None:
            continue
        if "_multi" in consumed:
            sub = consumed["_multi"]
        else:
            sub = [consumed]
        if known_tool_names is not None:
            if not all(c["name"] in known_tool_names for c in sub):
                continue
        calls.extend(sub)
        matched_spans.append((start, end))

    if not matched_spans:
        return text, []

    matched_spans.sort()
    pieces: List[str] = []
    cursor = 0
    for s, e in matched_spans:
        if s > cursor:
            pieces.append(text[cursor:s])
        cursor = e
    if cursor < len(text):
        pieces.append(text[cursor:])
    residual = "".join(pieces).strip()
    return residual, calls


def synthesize_tool_use_blocks(text: str, known_tool_names: Optional[set] = None):
    from .types import ToolUseBlock

    residual, calls = extract_tool_calls(text, known_tool_names=known_tool_names)
    blocks = [
        ToolUseBlock(id=_synth_id(), name=c["name"], input=c.get("arguments") or {})
        for c in calls
    ]
    return residual, blocks
