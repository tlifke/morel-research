#!/usr/bin/env python3
"""Fetch and merge per-token pricing for HF-hosted models.

Asset table lives at assets/model-pricing.json (repo root). Each run:
  1. queries the HF router (https://router.huggingface.co/v1/models) for
     live provider/model pricing
  2. merges what it finds into the local asset table
  3. writes the table back atomically

Usage:
  # show current table
  python fetch_pricing.py --show

  # refresh from the router (fetches live prices, merges, saves)
  python fetch_pricing.py --refresh

  # pin/update prices for one model
  python fetch_pricing.py --set glm-5.3-flash --input-per-1m 0.10 --output-per-1m 0.40
"""
from __future__ import annotations

import argparse
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
ASSET_PATH = REPO_ROOT / "assets" / "model-pricing.json"

ROUTER_URL = "https://router.huggingface.co/v1/models"


def _atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically: dump to a temp file in the same dir, then rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _load_table() -> dict:
    if ASSET_PATH.exists():
        return json.loads(ASSET_PATH.read_text(encoding="utf-8"))
    return {"version": 1, "models": {}}


def _save_table(table: dict) -> None:
    ASSET_PATH.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(ASSET_PATH, table)


def _fetch_router_models() -> list[dict]:
    """Pull the live model catalog from the HF router."""
    req = urllib.request.Request(
        ROUTER_URL,
        headers={
            "User-Agent": "morel-pricing-skill/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
        payload = json.loads(resp.read().decode("utf-8"))
    if isinstance(payload, dict):
        return payload.get("data", []) or []
    return payload or []


def _merge_pricing(existing: dict, model_id: str, provider: str, entry: dict) -> None:
    """Merge one provider's pricing entry for one model into the table."""
    models: dict = existing.setdefault("models", {})
    slot = models.setdefault(model_id, {})
    providers: dict = slot.setdefault("providers", {})
    providers[provider] = {
        "input_per_1m_usd": entry.get("input"),
        "output_per_1m_usd": entry.get("output"),
        "context_length": entry.get("context_length"),
        "status": entry.get("status"),
    }
    slot["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")


def refresh(table: dict) -> dict:
    """Fetch the live catalog and merge every model's pricing into `table`."""
    catalog = _fetch_router_models()
    count = 0
    for model in catalog:
        mid = model.get("id")
        if not mid:
            continue
        for prov in model.get("providers", []) or []:
            pricing = prov.get("pricing")
            if not pricing:
                continue
            slot = dict(pricing)
            slot["provider"] = prov.get("provider")
            slot["status"] = prov.get("status")
            slot["fetched_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            table.setdefault("models", {}).setdefault(mid, {}).setdefault(
                "providers", {}
            )[prov.get("provider", "unknown")] = slot
            count += 1
    print(f"Fetched pricing for {count} provider/model combination(s).")
    return table


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="fetch_pricing.py",
        description="Fetch / update per-token pricing for HF-hosted models.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("show", help="Show the current pricing table.")

    sp = sub.add_parser("set", help="Set/update prices for one model.")
    sp.add_argument("model", help="Model id, e.g. glm-5.3-flash")
    sp.add_argument("--input-per-1m", type=float, default=None,
                    help="USD per 1M input tokens")
    sp.add_argument("--output-per-1m", type=float, default=None,
                    help="USD per 1M output tokens")
    sp.add_argument("--context", type=int, default=None,
                    help="Max context window (tokens)")
    sp.add_argument("--source", default=None,
                    help="Free-text source label (e.g. 'hf', 'manual')")

    sub.add_parser("refresh", help="Re-fetch the live catalog and merge it.")

    args = p.parse_args(argv)

    table_path = REPO_ROOT / "assets" / "model-pricing.json"
    table: dict = {}
    if table_path.exists():
        table = json.loads(table_path.read_text(encoding="utf-8"))

    if args.command == "refresh":
        table = refresh(table)
        _save_table(table)
        print("Catalog refreshed.")
        return 0

    if args.command == "show":
        models = table.get("models", {})
        if not models:
            print("No pricing entries yet. Run refresh or set prices manually.")
            return 0
        for mid in sorted(models):
            entry = models[mid]
            provs = entry.get("providers", {})
            print(f"\n{mid}:")
            for pname, pdata in sorted(provs.items()):
                print(f"  {pname}:")
                print(f"    input  per 1M: ${pdata.get('input_per_1m_usd')}")
                print(f"    output per 1M: ${pdata.get('output_per_1m_usd')}")
                print(f"    context_length: {pdata.get('context_length')}")
                print(f"    status: {pdata.get('status')}")
        return 0

    return 0


if __name__ == "__main__":
    main(sys.argv[1:] if "sys" in globals() else None)
