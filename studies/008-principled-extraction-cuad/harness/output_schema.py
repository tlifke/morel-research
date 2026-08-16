from __future__ import annotations

import copy
from typing import Any, Iterable, Literal, Optional, Sequence

from pydantic import BaseModel

SchemaVariant = Literal["field_present", "field_absent"]

CITATION_FIELD = "principles_cited"

CATEGORY_FIELD = "category"


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


def _constrain_field(node: Any, field: str, values: Sequence[str]) -> Any:
    if isinstance(node, dict):
        out = {}
        for k, v in node.items():
            if k == "properties" and isinstance(v, dict):
                props = {}
                for pk, pv in v.items():
                    pv = _constrain_field(pv, field, values)
                    if pk == field and isinstance(pv, dict):
                        pv = {**pv, "enum": list(values)}
                    props[pk] = pv
                v = props
            else:
                v = _constrain_field(v, field, values)
            out[k] = v
        return out
    if isinstance(node, list):
        return [_constrain_field(x, field, values) for x in node]
    return node


def json_schema_for(
    model: type[BaseModel],
    schema_variant: SchemaVariant,
    categories: Optional[Iterable[str]] = None,
) -> dict[str, Any]:
    """Serialise the output model's JSON Schema for the prompt.

    `categories` closes the gap between what the schema states and what
    `validate_output()` enforces: exact category matching was previously checked
    only after the fact, so the model was never told the constraint it was being
    scored on. Passing the target list writes it into the schema as an enum.
    """
    schema = copy.deepcopy(model.model_json_schema())
    if schema_variant == "field_absent":
        schema = _strip_field(schema, CITATION_FIELD)
    if categories is not None:
        values = list(categories)
        if values:
            schema = _constrain_field(schema, CATEGORY_FIELD, values)
    return schema


def schema_category_enum(schema: dict[str, Any]) -> list[list[str]]:
    found: list[list[str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            prop = node.get("properties", {}).get(CATEGORY_FIELD)
            if isinstance(prop, dict) and "enum" in prop:
                found.append(list(prop["enum"]))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(schema)
    return found


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
