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

HARNESS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(HARNESS_DIR.parent))
from harness.parser import classify_trial  # noqa: E402

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


def _rescore_row(row: dict) -> tuple[bool, str | None]:
    """Re-derive (success, error_type) from output_preview using the
    current classify_trial. The stored values can be stale if the
    classifier evolved after the run (e.g. wrong_tool was introduced
    after the 4B run wrote `under_call` for those cases).
    """
    pseudo_record = {
        "tool_target": row["tool_target"],
        "expected_tool_call": row["expected_tool_call"],
    }
    return classify_trial(pseudo_record,
                          row.get("output") or row.get("output_preview", ""))


def aggregate(rows: list[dict], checkpoints: list[int],
              rescore: bool = False) -> dict:
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
            scored = [
                _rescore_row(t) if rescore else (t["success"], t.get("error_type"))
                for t in window
            ]
            successes = sum(1 for ok, _ in scored if ok)
            sr = successes / len(window)
            ck_results[k] = {
                "n": len(window),
                "success_rate": sr,
                "bucket": bucket_for(sr),
                "over_calls": sum(1 for _, e in scored if e == "over_call"),
                "under_calls": sum(1 for _, e in scored if e == "under_call"),
                "wrong_tool": sum(1 for _, e in scored if e == "wrong_tool"),
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
    print(f"  {'record_id':60s}  over  under  wrong_tool")
    interesting = [(r, a) for r, a in agg.items()
                   if biggest in a["checkpoints"]
                   and any(a["checkpoints"][biggest].get(k, 0) > 0
                           for k in ("over_calls", "under_calls", "wrong_tool"))]
    if not interesting:
        print("  (none — every record at perfect calibration)")
    for rid, rec in sorted(interesting):
        cp = rec["checkpoints"][biggest]
        print(f"  {rid:60s}  {cp['over_calls']:^4d}  {cp['under_calls']:^5d}  "
              f"{cp.get('wrong_tool', 0):^10d}")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--model", help="Model id (looks up results/<model>/*.jsonl).")
    p.add_argument("--results", help="Explicit results JSONL path(s).", nargs="+")
    p.add_argument("--checkpoints", type=int, nargs="+", default=[5, 10, 20])
    p.add_argument("--rescore", action="store_true",
                   help="Re-derive success/error_type from output_preview "
                        "using the current classify_trial. Useful after the "
                        "classifier evolves (e.g. when wrong_tool was added). "
                        "WARNING: output_preview is 400 chars; long outputs "
                        "with tool calls past char 400 will be misclassified "
                        "as under_call. Trust original fields for long-output "
                        "records unless full outputs are stored.")
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

    agg = aggregate(rows, args.checkpoints, rescore=args.rescore)
    report(agg, args.checkpoints)
    return 0


if __name__ == "__main__":
    sys.exit(main())
