"""Dispatch dry-run: verify every seed's tool_target resolves to a
working tool implementation in the study-level tools/ module.

This does NOT call any target language model. It only confirms that
every distinct tool_target referenced in seeds.jsonl maps to a
callable in tools/ that returns a non-error value when invoked with a
canonical argument shape. Used as a Phase A2 sanity check before
wiring up real model trials in Phase A4.

Usage:
    uv run check_tool_dispatch.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent.parent
sys.path.insert(0, str(STUDY_ROOT))

from tools import (  # noqa: E402
    calculator,
    python_execute,
    datetime_now,
    unit_convert,
    general_knowledge_lookup,
    user_knowledge_lookup,
)

SEEDS_PATH = STUDY_ROOT / "seeds.jsonl"

# Canonical exercise arguments — one example per tool. The real harness
# (Phase A4) will derive arguments from the target model's tool call;
# this script just confirms the implementation responds.
CANONICAL = {
    "calculator": lambda: calculator("2 + 2"),
    "python_execute": lambda: python_execute("print('ok')"),
    "datetime_now": lambda: datetime_now(),
    "unit_convert": lambda: unit_convert(1, "kg", "g"),
    "general_knowledge_lookup": lambda: general_knowledge_lookup("nla paper"),
    "user_knowledge_lookup": lambda: user_knowledge_lookup("anniversary"),
    "none": lambda: None,
}


def main() -> int:
    if not SEEDS_PATH.exists():
        print(f"ERROR: {SEEDS_PATH} not found — run build_seeds.py first.")
        return 2

    records = [json.loads(line) for line in SEEDS_PATH.read_text().splitlines() if line]
    targets = Counter(r["tool_target"] for r in records)

    print(f"loaded {len(records)} records covering {len(targets)} unique tool_targets")
    for target, count in sorted(targets.items()):
        if target not in CANONICAL:
            print(f"  ✗ {target}: NO IMPLEMENTATION ({count} records reference this)")
            return 1
        try:
            out = CANONICAL[target]()
            preview = repr(out)[:80] if out is not None else "(no-op)"
            print(f"  ✓ {target}: {count} records → {preview}")
        except Exception as e:
            print(f"  ✗ {target}: {count} records → raised {type(e).__name__}: {e}")
            return 1

    print()
    print(f"all {len(targets)} tool targets dispatch successfully")
    return 0


if __name__ == "__main__":
    sys.exit(main())
