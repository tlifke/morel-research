from __future__ import annotations

import json
from pathlib import Path

STUDY = Path(__file__).resolve().parents[3]
INSTANCES = STUDY / "data/processed/instances.jsonl"
SPLIT = STUDY / "data/processed/splits/principle_train.txt"
OUT = Path(__file__).resolve().parents[1] / "mvp_slice.json"

TOKEN_CAP = 25_000
BUCKET_ORDER = ["<=4k", "4k-8k", "8k-16k", ">16k"]
N = 5


def load():
    keep = {s for s in SPLIT.read_text().split("\n") if s.strip()}
    rows = [json.loads(line) for line in INSTANCES.read_text().splitlines()]
    return [r for r in rows if r["contract_id"] in keep]


def positives(row):
    return frozenset(c for c, g in row["gold"].items() if not g["is_impossible"])


def pick(candidates, covered):
    ranked = sorted(
        candidates,
        key=lambda r: (-len(positives(r) - covered), r["contract_id"]),
    )
    return ranked[0]


def main():
    rows = [r for r in load() if r["n_tokens"] <= TOKEN_CAP]
    chosen, covered = [], set()

    for bucket in BUCKET_ORDER:
        pool = [r for r in rows if r["length_bucket"] == bucket and r not in chosen]
        if not pool:
            continue
        row = pick(pool, covered)
        chosen.append(row)
        covered |= positives(row)

    while len(chosen) < N:
        pool = [r for r in rows if r not in chosen]
        row = pick(pool, covered)
        chosen.append(row)
        covered |= positives(row)

    all_categories = sorted(rows[0]["gold"])
    payload = {
        "split": "principle_train",
        "selection_rule": {
            "token_cap": TOKEN_CAP,
            "bucket_order": BUCKET_ORDER,
            "objective": "one per length bucket, greedy maximum marginal positive-category coverage, ties broken by contract_id",
            "n": N,
        },
        "categories_total": len(all_categories),
        "categories_covered": sorted(covered),
        "categories_uncovered": [c for c in all_categories if c not in covered],
        "contracts": [
            {
                "contract_id": r["contract_id"],
                "title": r["title"],
                "length_bucket": r["length_bucket"],
                "n_tokens": r["n_tokens"],
                "n_positive_all": r["n_positive_all"],
                "positive_categories": sorted(positives(r)),
            }
            for r in chosen
        ],
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    main()
