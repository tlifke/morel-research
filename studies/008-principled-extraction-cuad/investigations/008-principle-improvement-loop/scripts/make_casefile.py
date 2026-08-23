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

MAJORITY = 2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--failure-class", required=True)
    ap.add_argument("--category", default=None)
    ap.add_argument("--max-cells", type=int, default=8)
    args = ap.parse_args()

    task = TaskDefinition.load()
    ledger = Ledger(args.run_id)
    rows = [
        json.loads(l)
        for l in (ledger.dir / "failures.jsonl").read_text().splitlines()
        if l.strip()
    ]

    rows = [r for r in rows if r["failure_class"] == args.failure_class]
    if args.category:
        rows = [r for r in rows if r["category"] == args.category]

    by_cell = collections.defaultdict(list)
    for r in rows:
        by_cell[(r["contract_id"], r["category"])].append(r)

    persistent = {k: v for k, v in by_cell.items() if len(v) >= MAJORITY}
    ranked = sorted(persistent.items(), key=lambda kv: (-len(kv[1]), kv[0]))

    cells = []
    for (cid, category), instances in ranked[: args.max_cells]:
        sample = instances[0]
        cells.append(
            {
                "contract_id": cid,
                "category": category,
                "question": task.questions[category],
                "n_repeats_failing": len(instances),
                "n_gold": sample["n_gold"],
                "n_pred": sample["n_pred"],
                "best_jaccard": sample["best_jaccard"],
                "gold_sample": sample["gold_sample"],
                "pred_sample": sample["pred_sample"],
            }
        )

    payload = {
        "run_id": args.run_id,
        "failure_class": args.failure_class,
        "category_filter": args.category,
        "n_cells_matching": len(by_cell),
        "n_cells_persistent": len(persistent),
        "majority_rule": f"{MAJORITY} of 3 repeats",
        "categories_by_frequency": collections.Counter(
            c for (_, c) in persistent
        ).most_common(),
        "cells": cells,
    }
    out = ledger.dir / f"casefile-{args.failure_class}{'-' + args.category.replace('/', '_') if args.category else ''}.json"
    out.write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({k: payload[k] for k in ("failure_class", "n_cells_matching", "n_cells_persistent", "categories_by_frequency")}, indent=2))


if __name__ == "__main__":
    main()
