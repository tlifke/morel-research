from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

PAIR_NAMES = ("mined_pairs.jsonl", "pairs.jsonl")
FOOTPRINT_NAMES = (
    "footprint.yaml",
    "footprint.yml",
    "footprint.json",
    "footprints.yaml",
    "footprints.yml",
    "footprints.json",
    "principle_footprint.yaml",
    "principle_footprint.json",
    "principle_footprints.yaml",
    "principle_footprints.json",
)


def discover(directory: Path, names: tuple[str, ...]) -> Path | None:
    for name in names:
        candidate = directory / name
        if candidate.exists():
            return candidate
    return None


def _load_any(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        out = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
        return out
    if path.suffix == ".json":
        return json.loads(text)
    return yaml.safe_load(text)


def load_pairs(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    raw = _load_any(path)
    if isinstance(raw, dict):
        for key in ("pairs", "records"):
            if isinstance(raw.get(key), list):
                raw = raw[key]
                break
        else:
            return {str(k): v for k, v in raw.items()}
    if not isinstance(raw, list):
        return {}
    out: dict[str, Any] = {}
    for item in raw:
        if isinstance(item, dict):
            key = item.get("pair_id") or item.get("id")
            if key:
                out[str(key)] = item
    return out


def load_footprint(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    raw = _load_any(path)
    if not isinstance(raw, dict):
        return {}
    if not isinstance(raw.get("principles"), dict):
        header_keys = {
            "schema_version",
            "generated",
            "generator",
            "split",
            "population",
            "note",
        }
        entries = {k: v for k, v in raw.items() if k not in header_keys}
        header = {k: v for k, v in raw.items() if k in header_keys}
        if entries and all(isinstance(v, dict) for v in entries.values()):
            return {**header, "principles": entries}
        return {}
    return raw


class Sidecars:
    def __init__(
        self, pairs_path: Path | None = None, footprint_path: Path | None = None
    ):
        self.pairs_path = pairs_path
        self.footprint_path = footprint_path
        self._cache: dict[str, tuple[float, Any]] = {}

    def _cached(self, name: str, path: Path | None, loader) -> Any:
        if path is None or not path.exists():
            self._cache.pop(name, None)
            return {} if name != "pairs" else {}
        stamp = path.stat().st_mtime_ns
        hit = self._cache.get(name)
        if hit and hit[0] == stamp:
            return hit[1]
        value = loader(path)
        self._cache[name] = (stamp, value)
        return value

    def pairs(self) -> dict[str, Any]:
        return self._cached("pairs", self.pairs_path, load_pairs)

    def footprint(self) -> dict[str, Any]:
        return self._cached("footprint", self.footprint_path, load_footprint)

    def payload(self) -> dict[str, Any]:
        return {"pairs": self.pairs(), "footprint": self.footprint()}

    def paths(self) -> dict[str, str | None]:
        return {
            "pairs": str(self.pairs_path) if self.pairs_path else None,
            "footprint": str(self.footprint_path) if self.footprint_path else None,
        }


__all__ = [
    "FOOTPRINT_NAMES",
    "PAIR_NAMES",
    "Sidecars",
    "discover",
    "load_footprint",
    "load_pairs",
]
