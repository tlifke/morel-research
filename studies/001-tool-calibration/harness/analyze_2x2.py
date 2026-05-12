"""Analyze the 006 temperature × prompt 2×2 results.

Loads the four cells (A: neutral, temp=0 / B: directive, temp=0 /
C: neutral, temp=1 / D: directive, temp=1) and reports:

  - Per-cell overall success_rate (averaged across records)
  - Main effects: temperature (A vs C, B vs D), prompt (A vs B, C vs D)
  - Interaction: (D − C) − (B − A) — does prompt-engineering delta
    depend on temperature?
  - Per-record matrix: success_rate × cell, plus the per-record
    prompt delta and temperature delta
  - Error-type breakdown per cell (over_call / under_call /
    wrong_tool counts)

Usage:
    uv run analyze_2x2.py
    uv run analyze_2x2.py --model gemma3:4b-it-qat --date 2026-05-12
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
RESULTS_ROOT = STUDY_ROOT / "results"

sys.path.insert(0, str(STUDY_ROOT))
from harness.parser import classify_trial  # noqa: E402


def _rescore(row: dict) -> dict:
    """Re-derive success/error_type from output using the current parser.

    The parser evolved during the 2x2 run (added support for bare
    `tool_code\\n<call>` format alongside the fenced form). Rescoring
    from raw output ensures cells captured before vs. after the
    parser update are scored consistently.
    """
    output = row.get("output") or row.get("output_preview", "")
    ok, err = classify_trial(
        {"tool_target": row["tool_target"],
         "expected_tool_call": row["expected_tool_call"]},
        output,
    )
    return {**row, "success": ok, "error_type": err}

CELL_TAGS = {
    "A": "006_A_neutral_temp0",
    "B": "006_B_directive_temp0",
    "C": "006_C_neutral_temp1",
    "D": "006_D_directive_temp1",
}


def _load_cell(model_dir: Path, tag: str, date: str) -> list[dict]:
    path = model_dir / f"{tag}_{date}.jsonl"
    if not path.exists():
        return []
    rows = [json.loads(line) for line in path.read_text().splitlines() if line]
    return [_rescore(r) for r in rows]


def _safe_model_id(model: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _per_record(rows: list[dict]) -> dict[str, dict]:
    """Return {record_id: {success_rate, n, over, under, wrong}}."""
    by_rid: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_rid[r["record_id"]].append(r)
    out = {}
    for rid, trials in by_rid.items():
        n = len(trials)
        succ = sum(1 for t in trials if t.get("success"))
        out[rid] = {
            "n": n,
            "success_rate": succ / n if n else 0.0,
            "over_calls": sum(1 for t in trials if t.get("error_type") == "over_call"),
            "under_calls": sum(1 for t in trials if t.get("error_type") == "under_call"),
            "wrong_tool": sum(1 for t in trials if t.get("error_type") == "wrong_tool"),
        }
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="gemma3:4b-it-qat")
    p.add_argument("--date", default="2026-05-12")
    args = p.parse_args()

    model_dir = RESULTS_ROOT / _safe_model_id(args.model)
    cells: dict[str, list[dict]] = {}
    for k, tag in CELL_TAGS.items():
        cells[k] = _load_cell(model_dir, tag, args.date)
        print(f"Cell {k} ({tag}): {len(cells[k])} rows")
    if any(len(rows) == 0 for rows in cells.values()):
        print("\nNot all cells complete yet. Re-run when 2x2 finishes.")
        return 1

    per_record = {k: _per_record(rows) for k, rows in cells.items()}

    # Overall cell averages (mean of per-record success_rate)
    def cell_mean(per_rec: dict[str, dict]) -> float:
        if not per_rec:
            return 0.0
        return sum(r["success_rate"] for r in per_rec.values()) / len(per_rec)

    A = cell_mean(per_record["A"])
    B = cell_mean(per_record["B"])
    C = cell_mean(per_record["C"])
    D = cell_mean(per_record["D"])

    print()
    print("=" * 60)
    print("Cell averages (mean success_rate across records):")
    print(f"               neutral    directive   Δ prompt")
    print(f"  temp=0       {A:.3f}     {B:.3f}      {B-A:+.3f}")
    print(f"  temp=1.0     {C:.3f}     {D:.3f}      {D-C:+.3f}")
    print(f"  Δ temp       {C-A:+.3f}    {D-B:+.3f}")
    print()
    print(f"Interaction (Δprompt at temp=1 − Δprompt at temp=0): "
          f"{(D-C) - (B-A):+.3f}")
    print(f"  (positive → prompt helps MORE at temp=1.0)")
    print(f"  (negative → prompt helps MORE at temp=0)")
    print()

    # Error-type breakdown
    print("=" * 60)
    print("Error-type counts per cell (sum across all trials):")
    print(f"  cell        over_calls   under_calls   wrong_tool")
    for k in "ABCD":
        rows = cells[k]
        oc = sum(1 for r in rows if r.get("error_type") == "over_call")
        uc = sum(1 for r in rows if r.get("error_type") == "under_call")
        wt = sum(1 for r in rows if r.get("error_type") == "wrong_tool")
        print(f"  {k}            {oc:^11d}  {uc:^12d}  {wt:^11d}")

    # Per-record breakdown
    all_rids = sorted(set().union(*(set(r) for r in per_record.values())))
    print()
    print("=" * 60)
    print(f"{'record_id':60s}  sr_A  sr_B  sr_C  sr_D  Δprompt@0  Δprompt@1  Δtemp@neut")
    for rid in all_rids:
        srs = {k: per_record[k].get(rid, {}).get("success_rate", float("nan")) for k in "ABCD"}
        prompt_d0 = srs["B"] - srs["A"]
        prompt_d1 = srs["D"] - srs["C"]
        temp_dn = srs["C"] - srs["A"]
        print(f"{rid:60s}  {srs['A']:.2f}  {srs['B']:.2f}  {srs['C']:.2f}  "
              f"{srs['D']:.2f}  {prompt_d0:+.2f}      {prompt_d1:+.2f}      {temp_dn:+.2f}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
