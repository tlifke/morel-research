from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel, ValidationError


class ParseFailure(Exception):
    def __init__(self, stage: str, detail: str) -> None:
        super().__init__(f"{stage}: {detail}")
        self.stage = stage
        self.detail = detail


def _balanced_object(text: str) -> Optional[str]:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("```")[1]
        if stripped.startswith("json"):
            stripped = stripped[4:]
        stripped = stripped.strip()
    try:
        loaded = json.loads(stripped)
    except json.JSONDecodeError:
        candidate = _balanced_object(text)
        if candidate is None:
            raise ParseFailure("json_decode", "no JSON object found in response")
        try:
            loaded = json.loads(candidate)
        except json.JSONDecodeError as exc:
            raise ParseFailure("json_decode", str(exc)) from exc
    if not isinstance(loaded, dict):
        raise ParseFailure("json_decode", f"top-level value is {type(loaded).__name__}")
    return loaded


def parse_output(text: str, output_model: type[BaseModel]) -> BaseModel:
    payload = extract_json(text)
    try:
        return output_model.model_validate(payload)
    except ValidationError as exc:
        raise ParseFailure("schema_validation", exc.errors(include_url=False).__repr__()) from exc
