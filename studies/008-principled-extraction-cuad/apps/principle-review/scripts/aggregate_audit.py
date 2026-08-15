from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import yaml

APP_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(APP_DIR))

from review_app import record_types, yaml_io

AGGREGATOR_VERSION = "gold-audit-aggregator-v3"
CLEAN = "clean"
UNRULED = (
    "redaction_dependent",
    "cross_category_overlap",
    "inconsistent_across_duplicates",
)


def rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def summarize(counts: Counter, pending: set[str]) -> dict:
    adjudicated = sum(v for k, v in counts.items() if k not in pending)
    defective = sum(v for k, v in counts.items() if k not in pending and k != CLEAN)
    unruled = sum(v for k, v in counts.items() if k in UNRULED)
    return {
        "n_records": sum(counts.values()),
        "n_adjudicated": adjudicated,
        "n_defective": defective,
        "defect_rate": rate(defective, adjudicated),
        "n_in_unruled_classes": unruled,
        "defect_rate_excluding_unruled": rate(defective - unruled, adjudicated),
        "decisions": dict(sorted(counts.items())),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aggregate_audit")
    parser.add_argument("reviewed")
    parser.add_argument("--out", default=str(APP_DIR / "audits" / "gold_noise_floor.yaml"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    rt = record_types.get("gold_audit")
    pending = set(rt.pending_decisions)
    known = set(rt.decision_names())
    records = yaml_io.load_records(Path(args.reviewed))
    if not records:
        sys.exit("no records in input")

    seeds = sorted({record_types.dotted(r, "sample.seed") for r in records})
    versions = sorted(
        {record_types.dotted(r, "sample.sampler_version") for r in records}
    )
    context = sorted({record_types.dotted(r, "sample.context_chars") for r in records})

    overall = Counter()
    census = Counter()
    unreviewed = 0
    census_total = 0
    by_category: dict[str, Counter] = defaultdict(Counter)
    by_split: dict[str, Counter] = defaultdict(Counter)
    reviewers = set()
    unknown_decisions = set()

    for record in records:
        decision = record_types.dotted(record, f"{rt.review_key}.decision")
        reviewer = record_types.dotted(record, f"{rt.review_key}.reviewer")
        draw = record_types.dotted(record, "sample.draw") or "random"
        if reviewer:
            reviewers.add(reviewer)
        if draw != "random":
            census_total += 1
            if decision:
                census[decision] += 1
            continue
        if not decision:
            unreviewed += 1
            continue
        if decision not in known:
            unknown_decisions.add(decision)
        overall[decision] += 1
        by_category[record.get("category", "?")][decision] += 1
        by_split[record.get("split", "?")][decision] += 1

    if unknown_decisions:
        sys.exit(f"unknown decisions in input: {sorted(unknown_decisions)}")

    report = {
        "artifact": "cuad_gold_noise_floor",
        "aggregator_version": AGGREGATOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": str(Path(args.reviewed).resolve()),
        "provenance": {
            "sampler_seeds": seeds,
            "sampler_versions": versions,
            "context_chars": context,
            "reviewers": sorted(reviewers),
            "decision_vocabulary": rt.decision_names(),
            "pending_decisions": list(rt.pending_decisions),
            "unruled_classes": list(UNRULED),
            "attribution": (
                "Gold spans from the Contract Understanding Atticus Dataset (CUAD) v1, "
                "The Atticus Project, licensed CC BY 4.0."
            ),
        },
        "denominator": {
            "unit": "one gold span",
            "n_records_in_file": len(records),
            "n_sampled": len(records) - census_total,
            "n_unreviewed": unreviewed,
            "definition": (
                "defect_rate = spans with any decision other than 'clean', over spans "
                "with a decision that is not in pending_decisions; unreviewed and "
                "deferred spans are excluded from both numerator and denominator. "
                "Only records with sample.draw == 'random' are counted: the "
                "duplicate census is a targeted enumeration of suspected defects and "
                "would bias every rate upward if pooled"
            ),
            "open_question": (
                "Tyler has not ruled on whether the unruled_classes count as gold "
                "being WRONG or merely gold being HARD or INCONSISTENT. "
                "defect_rate includes them; defect_rate_excluding_unruled is the same "
                "quantity with all of them removed from the numerator. The ruling is "
                "expressed in exactly one place in the aggregator, the CLEAN constant "
                "plus the UNRULED tuple; nothing else branches on decision identity."
            ),
        },
        "overall": summarize(overall, pending),
        "per_category": {
            category: summarize(counts, pending)
            for category, counts in sorted(by_category.items())
        },
        "per_split": {
            split: summarize(counts, pending) for split, counts in sorted(by_split.items())
        },
        "duplicate_census": {
            "n_records": census_total,
            "n_reviewed": sum(census.values()),
            "decisions": dict(sorted(census.items())),
            "is_a_rate": False,
            "definition": (
                "exhaustive enumeration of spans whose passage appears verbatim in "
                "another contract carrying the opposite label. Counts here are a "
                "confirmation rate for that enumeration, not a corpus rate, and are "
                "excluded from every figure above"
            ),
        },
        "per_defect": {
            decision: {
                "n": overall[decision],
                "share_of_adjudicated": rate(
                    overall[decision],
                    sum(v for k, v in overall.items() if k not in pending),
                ),
            }
            for decision in rt.decision_names()
            if decision not in pending
        },
        "note": (
            "This artifact reports observed gold-defect rates only. Translating a "
            "defect rate into a ceiling on achievable span-F1 is an analysis step and "
            "is deliberately not performed here."
        ),
        "note_absence_labels": (
            "inconsistent_across_duplicates is predominantly a defect in ABSENCE "
            "labels: the sampled span is annotated, and a near-identical passage in "
            "another contract is not. Its rate therefore bounds absence accuracy in a "
            "way the other classes do not, and it is reported separately for that "
            "reason."
        ),
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if args.json or out.suffix == ".json":
        out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    else:
        out.write_text(
            yaml.safe_dump(report, sort_keys=False, allow_unicode=True, width=88),
            encoding="utf-8",
        )
    print(
        f"{report['overall']['n_adjudicated']} adjudicated, "
        f"defect_rate={report['overall']['defect_rate']} -> {out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
