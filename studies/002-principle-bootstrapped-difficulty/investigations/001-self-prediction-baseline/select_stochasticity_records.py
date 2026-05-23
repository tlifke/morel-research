"""Pick ~20 records spanning all 6 tools for the stochasticity pre-experiment.

Output: a JSONL slice of bulk_seeds.jsonl with one row per selected record.
Selection: ~3-4 records per tool, mix of expected_tool_call=true/false.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
import random

HERE = Path(__file__).resolve().parent
STUDIES_ROOT = HERE.parents[2]
STUDY_001_ROOT = STUDIES_ROOT / "001-tool-calibration"
SEEDS = STUDY_001_ROOT / "bulk_seeds.jsonl"
OUT = HERE / "stochasticity_records.jsonl"

PER_TOOL = 4
RNG = random.Random(20260522)


def main() -> None:
    by_tool: dict[tuple[str, bool], list[dict]] = defaultdict(list)
    for line in SEEDS.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        by_tool[(r["tool_target"], r["expected_tool_call"])].append(r)

    selected: list[dict] = []
    tools = sorted({k[0] for k in by_tool})
    for tool in tools:
        for expected in (True, False):
            pool = by_tool.get((tool, expected), [])
            if not pool:
                continue
            n = min(PER_TOOL // 2, len(pool))
            selected.extend(RNG.sample(pool, n))

    OUT.write_text("\n".join(json.dumps(r) for r in selected) + "\n")
    print(f"wrote {len(selected)} records → {OUT}")
    counts: dict[str, int] = defaultdict(int)
    for r in selected:
        counts[r["tool_target"]] += 1
    for tool, c in sorted(counts.items()):
        print(f"  {tool:<28} {c}")


if __name__ == "__main__":
    main()
