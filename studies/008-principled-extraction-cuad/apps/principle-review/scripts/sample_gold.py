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
from duplicates import DISAGREEING_LABELS, MIN_MATCH_CHARS, Corpus
from fuzzy_twins import FuzzyTwins, load_config

FUZZY_MIN_CONTAINMENT = 0.15

SAMPLER_VERSION = "gold-audit-sampler-v5"
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
    dataset: CuadDataset,
    item: dict,
    width: int,
    seed: int,
    stratum: str,
    corpus: Corpus | None = None,
    draw: str = "random",
    fuzzy: list[dict] | None = None,
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

    counterparts, n_with_passage = ([], 0)
    if corpus is not None:
        counterparts, n_with_passage = corpus.find_counterparts(
            item["contract_id"], item["category"], text[start:end]
        )
    seen_pairs = {(c["contract_id"], c["offsets"]) for c in counterparts}
    for hit in fuzzy or []:
        if (hit["contract_id"], hit["offsets"]) not in seen_pairs:
            counterparts.append(hit)
    detectors = sorted({c["detector"] for c in counterparts})

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
        "duplicate_counterparts": counterparts,
        "n_contracts_with_passage": n_with_passage,
        "has_counterpart": "yes" if counterparts else "no",
        "detected_by": ", ".join(detectors) if detectors else "none",
        "sample": {
            "seed": seed,
            "sampler_version": SAMPLER_VERSION,
            "stratum": stratum,
            "draw": draw,
            "context_chars": width,
            "duplicate_min_match_chars": MIN_MATCH_CHARS,
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
    parser.add_argument("--no-duplicates", action="store_true")
    parser.add_argument("--no-duplicate-census", action="store_true")
    parser.add_argument("--no-fuzzy", action="store_true")
    parser.add_argument("--fuzzy-min-containment", type=float,
                        default=FUZZY_MIN_CONTAINMENT)
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

    corpus = None if args.no_duplicates else Corpus(dataset)

    fuzzy_hits: dict[tuple, list[dict]] = {}
    fuzzy_raw: dict[tuple, list[dict]] = {}
    fuzzy_meta: dict = {"enabled": False}
    if corpus is not None and not args.no_fuzzy:
        mining = load_config()
        detector = FuzzyTwins(dataset, categories, mining)
        fuzzy_raw = detector.run(population, dataset.texts, corpus, 0.0)
        fuzzy_hits = detector.run(
            population, dataset.texts, corpus, args.fuzzy_min_containment
        )
        fuzzy_meta = {
            "enabled": True,
            "implementation": (
                "scripts/mine_contrastive_pairs.py (Space, jaccard_block, terms, "
                "chunk_text), imported, not reimplemented"
            ),
            "mining_config_version": mining["version"],
            "metric": mining["similarity"]["metric"],
            "similarity_threshold": detector.threshold,
            "min_terms_per_unit": detector.min_terms,
            "top_k_per_query": detector.top_k,
            "context_expansion": detector.ctx,
            "min_doc_containment": args.fuzzy_min_containment,
            "gate_rationale": (
                "the miner's present_absent threshold answers 'does a passage "
                "resembling category C exist where C is absent', which is a broader "
                "question than 'is there a near-duplicate document with the opposite "
                "label'. Ungated it returns mostly unrelated contracts sharing legal "
                "boilerplate. The document-containment floor restricts it to genuine "
                "near-twins; see detector_comparison for what the gate discards. "
                "Known residual failure mode at this gate: CUAD entries that are "
                "fragments of one filing (a continuation excerpt or annex) score "
                "moderate containment and share boilerplate, but their absence "
                "labels are legitimately correct because the fragment does not "
                "contain the clause. Read the passage before trusting a fuzzy hit"
            ),
        }

    def hits_for(item, table):
        return table.get(
            (item["contract_id"], item["category"], item["span_index"]), []
        )

    records = [
        build_record(
            dataset, item, args.context, args.seed, item["category"], corpus,
            fuzzy=hits_for(item, fuzzy_hits),
        )
        for item in drawn
    ]

    def disagrees(counterparts):
        return any(c["twin_label"] in DISAGREEING_LABELS for c in counterparts)

    census: list[dict] = []
    exact_keys: set = set()
    fuzzy_keys: set = set()
    fuzzy_raw_keys: set = set()
    if corpus is not None and not args.no_duplicate_census:
        seen = {r["id"] for r in records}
        for item in population:
            key = (item["contract_id"], item["category"], item["span_index"])
            instance = dataset.get_instance(item["contract_id"])
            span_text = instance.text[item["start"]:item["end"]]
            exact, _ = corpus.find_counterparts(
                item["contract_id"], item["category"], span_text
            )
            fuzzy = hits_for(item, fuzzy_hits)
            if disagrees(exact):
                exact_keys.add(key)
            if disagrees(fuzzy):
                fuzzy_keys.add(key)
            if disagrees(hits_for(item, fuzzy_raw)):
                fuzzy_raw_keys.add(key)
            if key not in exact_keys and key not in fuzzy_keys:
                continue
            record = build_record(
                dataset, item, args.context, args.seed, "duplicate_census",
                corpus, draw="duplicate_census", fuzzy=fuzzy,
            )
            if record["id"] in seen:
                continue
            census.append(record)
        records.extend(census)

    split_files = {
        split: hashlib.sha256(dataset.split_file(split).read_bytes()).hexdigest()[:16]
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
            "duplicate_search": {
                "enabled": not args.no_duplicates,
                "scope": "all 510 CUAD contracts, including ft_train",
                "method": (
                    "exact whitespace-normalized passage match of the gold span in "
                    "another contract; counterparts ranked by document containment "
                    "over 8-gram sketches; a passage shorter than "
                    f"{MIN_MATCH_CHARS} normalized characters is not searched"
                ),
                "min_match_chars": MIN_MATCH_CHARS,
                "n_records_with_counterpart": sum(
                    1 for r in records if r["duplicate_counterparts"]
                ),
                "n_records_searched": sum(
                    1 for r in records
                    if len(" ".join(r["span_text"].split())) >= MIN_MATCH_CHARS
                ),
            },
            "fuzzy_detector": fuzzy_meta,
            "detector_comparison": {
                "unit": "one gold span with at least one disagreeing counterpart",
                "exact_normalized": len(exact_keys),
                "fuzzy_idf_jaccard": len(fuzzy_keys),
                "fuzzy_idf_jaccard_ungated": len(fuzzy_raw_keys),
                "both": len(exact_keys & fuzzy_keys),
                "exact_only": len(exact_keys - fuzzy_keys),
                "fuzzy_only": len(fuzzy_keys - exact_keys),
                "union": len(exact_keys | fuzzy_keys),
                "discarded_by_containment_gate": len(fuzzy_raw_keys - fuzzy_keys),
                "note": (
                    "counts are over the whole population of the sampled splits, not "
                    "over the random draw. exact_only and fuzzy_only are both "
                    "non-empty: the detectors have different failure modes and "
                    "neither subsumes the other"
                ),
            },
            "draws": {
                "random": len(records) - len(census),
                "duplicate_census": len(census),
                "census_definition": (
                    "every gold span in the sampled splits whose passage appears "
                    "verbatim in another contract where the same category is "
                    "marked_absent, not_annotated, or annotated only elsewhere in "
                    "that contract. This is an exhaustive census of "
                    "candidates for inconsistent_across_duplicates, NOT a random "
                    "draw: label disagreement is ~0.3% of spans, so a random sample "
                    "would contain none. Census records must be reported separately "
                    "and must never enter the random sample's defect rate."
                ),
            },
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
