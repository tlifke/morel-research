from __future__ import annotations

import copy
from typing import Any, Literal

from pydantic import BaseModel

SchemaVariant = Literal["field_present", "field_absent"]

CITATION_FIELD = "principles_cited"


def _strip_field(node: Any, field: str) -> Any:
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "properties" and isinstance(v, dict):
                v = {pk: _strip_field(pv, field) for pk, pv in v.items() if pk != field}
            elif k == "required" and isinstance(v, list):
                v = [r for r in v if r != field]
            else:
                v = _strip_field(v, field)
            out[k] = v
        return out
    if isinstance(node, list):
        return [_strip_field(x, field) for x in node]
    return node


def json_schema_for(
    model: type[BaseModel], schema_variant: SchemaVariant
) -> dict[str, Any]:
    schema = copy.deepcopy(model.model_json_schema())
    if schema_variant == "field_absent":
        schema = _strip_field(schema, CITATION_FIELD)
    return schema


def schema_has_citation_field(schema: dict[str, Any]) -> bool:
    found = False

    def walk(node: Any) -> None:
        nonlocal found
        if isinstance(node, dict):
            if CITATION_FIELD in node.get("properties", {}):
                found = True
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)
    return found
