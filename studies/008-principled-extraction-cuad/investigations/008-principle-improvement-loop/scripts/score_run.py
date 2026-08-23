from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

INV = Path(__file__).resolve().parents[1]
STUDY = INV.parents[1]
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(INV))

from loop.ledger import Ledger
from loop.prompt import TaskDefinition
from loop.scoring import gold_for, score_trial, summarize


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--system", default="qwen3.5-9b-loop")
    args = ap.parse_args()

    task = TaskDefinition.load()
    ledger = Ledger(args.run_id)
    trials = ledger.read()
    if not trials:
        raise SystemExit(f"no trials in run {args.run_id}")

    contract_ids = sorted({t["key"]["contract_id"] for t in trials})
    gold = gold_for(contract_ids, task.categories)

    per_repeat = []
    all_failures = []
    conformance = []
    for trial in trials:
        if trial["outcome"] != "ok":
            per_repeat.append({"trial_id": trial["trial_id"], "outcome": trial["outcome"]})
            continue
        records, failures = score_trial(trial, gold, task.categories, args.system)
        agg = summarize(records)
        per_repeat.append(
            {
                "trial_id": trial["trial_id"],
                "contract_id": trial["key"]["contract_id"],
                "repeat_idx": trial["key"]["repeat_idx"],
                "outcome": "ok",
                "detection_micro": agg["micro"]["detection"],
                "detection_macro": agg["macro"]["detection"],
                "localization_micro": agg["micro"]["localization"],
            }
        )
        for f in failures:
            all_failures.append({**f.to_json(), "repeat_idx": trial["key"]["repeat_idx"]})
        conformance.append(trial["notes"]["conformance"])

    by_class = collections.Counter(f["failure_class"] for f in all_failures)
    by_class_category = collections.Counter(
        (f["failure_class"], f["category"]) for f in all_failures
    )
    n_ok = sum(1 for t in trials if t["outcome"] == "ok")

    payload = {
        "run_id": args.run_id,
        "n_trials": len(trials),
        "n_ok": n_ok,
        "n_parse_failure": len(trials) - n_ok,
        "task_definition_sha256": task.content_sha256,
        "failure_counts": dict(by_class.most_common()),
        "failure_counts_per_trial": {k: round(v / max(n_ok, 1), 2) for k, v in by_class.items()},
        "top_failure_cells": [
            {"failure_class": k[0], "category": k[1], "n": v}
            for k, v in by_class_category.most_common(25)
        ],
        "conformance_totals": {
            "n_missing": sum(len(c["missing"]) for c in conformance),
            "n_duplicate": sum(c["n_duplicate"] for c in conformance),
            "n_unknown": sum(len(c["unknown"]) for c in conformance),
            "n_kind_span_inconsistent": sum(c["n_kind_span_inconsistent"] for c in conformance),
        },
        "per_trial": per_repeat,
    }

    out = ledger.dir / "score.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    (ledger.dir / "failures.jsonl").write_text(
        "".join(json.dumps(f, sort_keys=True) + "\n" for f in all_failures)
    )
    print(json.dumps({k: payload[k] for k in ("n_trials", "n_ok", "failure_counts")}, indent=2))


if __name__ == "__main__":
    main()
