"""Retrospective analysis of calibration trial results.

Reads `results/{model_id}/*.jsonl` and aggregates per record:
  - success_rate at each N checkpoint (5, 10, 20 by default)
  - over_call / under_call counts
  - whether the model would have been bucketed differently at smaller N

Surfaces:
  - which records had clean signal early (n=5 success_rate matches n=20)
  - which records were noisy (success_rate drifted as N grew)
  - per-record error-type breakdown (over vs. under)

Usage:
    uv run analyze_results.py --model gemma3:4b-it-qat
    uv run analyze_results.py --results results/gemma3_4b-it-qat/2026-05-12.jsonl
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

# Per calibration_methodology.md, success_rate → difficulty bucket
_BUCKETS = [
    (0.05, "extreme"),
    (0.30, "hard"),
    (0.70, "medium"),
    (0.95, "easy"),
    (1.01, "trivial"),
]


def bucket_for(success_rate: float) -> str:
    for threshold, label in _BUCKETS:
        if success_rate < threshold:
            return label
    return "trivial"


def load_results(paths: list[Path]) -> list[dict]:
    rows: list[dict] = []
    for p in paths:
        for line in p.read_text().splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def aggregate(rows: list[dict], checkpoints: list[int]) -> dict:
    """Group rows by (record_id, run_id) then by record_id; compute
    success_rate at each checkpoint N for the *latest* run of each
    record. (Different run_ids should not be averaged together —
    they may have used different runner versions.)
    """
    by_record_run: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        by_record_run[(r["record_id"], r["run_id"])].append(r)

    # Latest run per record by max(trial_idx written).
    latest_per_record: dict[str, list[dict]] = {}
    for (rid, run_id), trials in by_record_run.items():
        trials.sort(key=lambda t: t["trial_idx"])
        if rid not in latest_per_record or len(trials) > len(latest_per_record[rid]):
            latest_per_record[rid] = trials

    out = {}
    for rid, trials in latest_per_record.items():
        trials.sort(key=lambda t: t["trial_idx"])
        n = len(trials)
        ck_results = {}
        for k in checkpoints:
            window = trials[:k]
            if not window:
                continue
            successes = sum(1 for t in window if t["success"])
            sr = successes / len(window)
            ck_results[k] = {
                "n": len(window),
                "success_rate": sr,
                "bucket": bucket_for(sr),
                "over_calls": sum(1 for t in window if t.get("error_type") == "over_call"),
                "under_calls": sum(1 for t in window if t.get("error_type") == "under_call"),
            }
        out[rid] = {
            "n_trials": n,
            "model": trials[0]["model"],
            "tool_target": trials[0]["tool_target"],
            "expected_tool_call": trials[0]["expected_tool_call"],
            "pair_id": trials[0]["pair_id"],
            "checkpoints": ck_results,
        }
    return out


def report(agg: dict, checkpoints: list[int]) -> None:
    # Bucket-stability table
    print()
    print(f"{'record_id':60s} " + " ".join(f"sr@{k:<3d}" for k in checkpoints)
          + "  bucket_stable?")
    for rid, rec in sorted(agg.items()):
        cps = rec["checkpoints"]
        srs = [f"{cps[k]['success_rate']:.2f}" if k in cps else "----"
               for k in checkpoints]
        buckets = [cps[k]["bucket"] for k in checkpoints if k in cps]
        stable = "y" if len(set(buckets)) == 1 else "n"
        print(f"{rid:60s} {'    '.join(srs)}    {stable}")

    # Error-type breakdown at largest checkpoint
    biggest = max(checkpoints)
    print()
    print(f"Error breakdown at n={biggest}:")
    print(f"  {'record_id':60s}  over_calls  under_calls")
    interesting = [(r, a) for r, a in agg.items()
                   if biggest in a["checkpoints"]
                   and (a["checkpoints"][biggest]["over_calls"] > 0
                        or a["checkpoints"][biggest]["under_calls"] > 0)]
    if not interesting:
        print("  (none — every record at perfect calibration)")
    for rid, rec in sorted(interesting):
        cp = rec["checkpoints"][biggest]
        print(f"  {rid:60s}  {cp['over_calls']:^10d}  {cp['under_calls']:^11d}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", help="Model id (looks up results/<model>/*.jsonl).")
    p.add_argument("--results", help="Explicit results JSONL path(s).", nargs="+")
    p.add_argument("--checkpoints", type=int, nargs="+", default=[5, 10, 20])
    args = p.parse_args()

    paths: list[Path] = []
    if args.results:
        paths = [Path(p) for p in args.results]
    elif args.model:
        safe = args.model.replace("/", "_").replace(":", "_")
        paths = sorted((RESULTS_ROOT / safe).glob("*.jsonl"))
    if not paths:
        print("no result files; pass --model or --results", file=sys.stderr)
        return 2

    print(f"loading {len(paths)} file(s):")
    for p in paths:
        print(f"  {p}")
    rows = load_results(paths)
    print(f"  → {len(rows)} trial rows")

    agg = aggregate(rows, args.checkpoints)
    report(agg, args.checkpoints)
    return 0


if __name__ == "__main__":
    sys.exit(main())
