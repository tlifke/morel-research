from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import yaml

from .record_types import RecordType


class ImportError_(ValueError):
    pass


def load_records(path: Path) -> list[dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if raw is None:
        return []
    if isinstance(raw, dict):
        for key in ("candidates", "records", "principles"):
            if key in raw and isinstance(raw[key], list):
                raw = raw[key]
                break
        else:
            raise ImportError_(
                "mapping at top level must carry a 'candidates', 'records' or "
                "'principles' list"
            )
    if not isinstance(raw, list):
        raise ImportError_("expected a YAML list of records")
    out = []
    for i, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ImportError_(f"record {i} is not a mapping")
        out.append(item)
    return out


def normalize_review(record: dict[str, Any], rt: RecordType) -> dict[str, Any]:
    block = record.get(rt.review_key)
    if not isinstance(block, dict):
        return record
    prior = block.get(rt.edited_from_key)
    if isinstance(prior, str) and prior.strip():
        block[rt.edited_from_key] = {rt.headline_key: prior}
    return record


def order_keys(record: dict[str, Any], key_order: tuple[str, ...]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in key_order:
        if key in record:
            ordered[key] = record[key]
    for key in record:
        if key not in ordered:
            ordered[key] = record[key]
    return ordered


def canonicalize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: canonicalize(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, list):
        return [canonicalize(v) for v in value]
    return value


def dump_yaml(records: list[dict[str, Any]], rt: RecordType) -> str:
    ordered = [order_keys(r, rt.key_order) for r in records]
    return yaml.safe_dump(
        ordered,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=88,
    )


def canonical_dump(records: list[dict[str, Any]]) -> str:
    return yaml.safe_dump(
        [canonicalize(r) for r in records],
        sort_keys=True,
        allow_unicode=True,
        default_flow_style=False,
        width=88,
    )


def build_export_record(
    source: dict[str, Any],
    edits: dict[str, Any] | None,
    review: dict[str, Any] | None,
    rt: RecordType,
) -> dict[str, Any]:
    record = copy.deepcopy(source)
    for key, value in (edits or {}).items():
        parts = key.split(".")
        cur = record
        for part in parts[:-1]:
            nxt = cur.get(part)
            if not isinstance(nxt, dict):
                nxt = {}
                cur[part] = nxt
            cur = nxt
        cur[parts[-1]] = value
    if review:
        block: dict[str, Any] = {}
        existing = source.get(rt.review_key)
        if isinstance(existing, dict):
            block.update(copy.deepcopy(existing))
        for key in rt.review_key_order:
            value = review.get(key)
            if value in (None, ""):
                block.pop(key, None)
            else:
                block[key] = value
        record[rt.review_key] = order_keys(block, rt.review_key_order)
    return record


__all__ = [
    "ImportError_",
    "build_export_record",
    "canonical_dump",
    "canonicalize",
    "dump_yaml",
    "load_records",
    "normalize_review",
    "order_keys",
]
