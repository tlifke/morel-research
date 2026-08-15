from __future__ import annotations

import argparse
import hashlib
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

APP_DIR = Path(__file__).resolve().parent.parent
STUDY_DIR = APP_DIR.parent.parent
STUDY_SCRIPTS = STUDY_DIR / "scripts"
sys.path.insert(0, str(STUDY_SCRIPTS))

from cuad_dataset import CuadDataset

SAMPLER_VERSION = "gold-audit-sampler-v1"
DEFAULT_SPLITS = ("dev", "holdout")


def allocate(targets: dict[str, int], available: dict[str, int], n: int) -> dict[str, int]:
    alloc = {k: 0 for k in targets}
    remaining = n
    while remaining > 0:
        open_cats = [k for k in alloc if alloc[k] < available[k]]
        if not open_cats:
            break
        share = max(1, remaining // len(open_cats))
        for cat in sorted(open_cats, key=lambda c: (alloc[c], c)):
            if remaining <= 0:
                break
            take = min(share, available[cat] - alloc[cat], remaining)
            alloc[cat] += take
            remaining -= take
    return alloc


def context_slice(text: str, start: int, end: int, width: int) -> tuple[str, str]:
    return text[max(0, start - width):start], text[end:end + width]


def relation(a_start: int, a_end: int, b_start: int, b_end: int) -> str | None:
    if a_start == b_start and a_end == b_end:
        return "identical"
    if b_start <= a_start and b_end >= a_end:
        return "contains"
    if a_start <= b_start and a_end >= b_end:
        return "contained_by"
    if b_start < a_end and a_start < b_end:
        return "overlaps"
    return None


def collect_population(dataset: CuadDataset, splits: tuple[str, ...]) -> list[dict]:
    population = []
    for split in splits:
        for contract_id in dataset.contract_ids(split):
            instance = dataset.get_instance(contract_id)
            for category, label in instance.gold.items():
                for index, span in enumerate(label.spans):
                    population.append(
                        {
                            "split": split,
                            "contract_id": contract_id,
                            "category": category,
                            "span_index": index,
                            "n_spans_in_category": len(label.spans),
                            "start": span.start,
                            "end": span.end,
                        }
                    )
    population.sort(
        key=lambda r: (r["split"], r["contract_id"], r["category"], r["span_index"])
    )
    return population


def build_record(
    dataset: CuadDataset, item: dict, width: int, seed: int, stratum: str
) -> dict:
    instance = dataset.get_instance(item["contract_id"])
    text = instance.text
    start, end = item["start"], item["end"]
    before, after = context_slice(text, start, end, width)
    label = instance.gold[item["category"]]

    siblings = [
        {
            "span_index": i,
            "offsets": f"{s.start}-{s.end}",
            "n_chars": s.end - s.start,
            "gap_chars": s.start - end if s.start >= end else start - s.end,
            "text": s.text,
        }
        for i, s in enumerate(label.spans)
        if i != item["span_index"]
    ]

    overlaps = []
    for category, other in instance.gold.items():
        if category == item["category"]:
            continue
        for other_span in other.spans:
            rel = relation(start, end, other_span.start, other_span.end)
            if rel:
                overlaps.append(
                    {
                        "category": category,
                        "relation": rel,
                        "offsets": f"{other_span.start}-{other_span.end}",
                        "text": other_span.text,
                    }
                )

    return {
        "id": f"{item['split']}/{item['contract_id']}/{item['category']}/{item['span_index']}",
        "contract_id": item["contract_id"],
        "title": instance.title,
        "split": item["split"],
        "category": item["category"],
        "span_index": item["span_index"],
        "n_spans_in_category": item["n_spans_in_category"],
        "start": start,
        "end": end,
        "n_chars": end - start,
        "offsets": f"{start}-{end}",
        "span_text": text[start:end],
        "context_before": before,
        "context_after": after,
        "siblings": siblings,
        "overlaps": overlaps,
        "sample": {
            "seed": seed,
            "sampler_version": SAMPLER_VERSION,
            "stratum": stratum,
            "context_chars": width,
        },
        "review": {
            "decision": None,
            "reviewer": None,
            "date": None,
            "rationale": None,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sample_gold")
    parser.add_argument("--n", type=int, default=120)
    parser.add_argument("--seed", type=int, default=20260815)
    parser.add_argument("--splits", default=",".join(DEFAULT_SPLITS))
    parser.add_argument("--context", type=int, default=700)
    parser.add_argument("--out", default=str(APP_DIR / "audits" / "gold_audit_sample.yaml"))
    args = parser.parse_args(argv)

    splits = tuple(s.strip() for s in args.splits.split(",") if s.strip())
    for split in splits:
        if split not in ("dev", "holdout"):
            sys.exit(f"refusing to sample from {split!r}: audit draws from dev/holdout only")

    dataset = CuadDataset()
    categories = dataset.categories
    population = collect_population(dataset, splits)
    if not population:
        sys.exit("no gold spans found; check data/processed")

    available = {c: 0 for c in categories}
    for item in population:
        available[item["category"]] += 1
    alloc = allocate({c: 0 for c in categories}, available, args.n)

    rng = random.Random(args.seed)
    drawn = []
    for category in categories:
        pool = [p for p in population if p["category"] == category]
        take = alloc[category]
        if take:
            drawn.extend(rng.sample(pool, take))
    drawn.sort(key=lambda r: (r["category"], r["split"], r["contract_id"], r["span_index"]))

    records = [
        build_record(dataset, item, args.context, args.seed, item["category"])
        for item in drawn
    ]

    split_files = {
        split: hashlib.sha256(
            (dataset._processed / "splits" / f"{split}.txt").read_bytes()
        ).hexdigest()[:16]
        for split in splits
    }

    payload = {
        "sampling": {
            "sampler_version": SAMPLER_VERSION,
            "seed": args.seed,
            "drawn_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "splits": list(splits),
            "split_file_sha256_16": split_files,
            "context_chars": args.context,
            "requested_n": args.n,
            "drawn_n": len(records),
            "population_n": len(population),
            "categories": list(categories),
            "allocation": {c: alloc[c] for c in categories},
            "population_by_category": {c: available[c] for c in categories},
            "attribution": (
                "Gold spans from the Contract Understanding Atticus Dataset (CUAD) v1, "
                "The Atticus Project, licensed CC BY 4.0."
            ),
        },
        "records": records,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"{len(records)} spans -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
