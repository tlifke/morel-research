import json
import math
import sys
from pathlib import Path

import yaml

STUDY = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(STUDY / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from checkers.checkers import REGISTRY  # noqa: E402
from checkers.lexicons import PILOT_CATEGORIES  # noqa: E402
from cuad_dataset import CuadDataset  # noqa: E402

GOLD_DEPENDENCY = {
    "g01": "gold_presence",
    "g02": "gold_span_content",
    "g03": "gold_span_content",
    "g04": "instance_only",
    "g05": "instance_only",
    "g06": "instance_only",
    "g07": "gold_presence",
    "g08": "instance_only",
    "d01": "gold_span_content",
    "d02": "gold_span_content",
    "d03": "gold_span_content",
    "d04": "instance_only",
    "d05": "instance_only",
    "d06": "gold_presence",
    "d07": "gold_span_content",
    "d08": "gold_presence",
}


VERDICTS = {
    "g01": (
        "degenerate",
        "Fires on 100% of yes/no extraction decisions and 0% of absences, so it "
        "carries no information beyond the presence call itself.",
    ),
    "g02": (
        "unimplementable",
        "The <omitted> marker appears in zero CUAD v1 contracts and zero gold "
        "spans, so applicability is 0% and the checker can never fire.",
    ),
    "g03": (
        "discriminating-but-rare",
        "2.5% of decisions; a genuine multi-label partition, but duplicated "
        "exactly by d02 on dev.",
    ),
    "g04": (
        "discriminating",
        "52.5% of Governing Law decisions, instance-only, phi 0.40 against gold "
        "presence; the cleanest non-tautological footprint in the set.",
    ),
    "g05": (
        "discriminating-applicability-failed-proxy",
        "Applicability is healthy (57.5%) but the span-level compliance proxy "
        "fails its own pre-registered audit: 33% false-fail on gold spans and "
        "140 candidate false-passes in Revenue/Profit-Sharing-absent contracts.",
    ),
    "g06": (
        "discriminating-but-rare",
        "12.5% of Revenue/Profit Sharing decisions, 6 trigger sentences in dev, "
        "2 of 6 hand-judged not administration at all.",
    ),
    "g07": (
        "degenerate",
        "Fires on 95% of Agreement Date decisions by construction: applicability "
        "is gold presence.",
    ),
    "g08": (
        "discriminating-but-rare",
        "12.5% of Agreement Date decisions, instance-only, and all 5 firings sit "
        "on gold-present contracts; a narrow but real subcase.",
    ),
    "d01": (
        "degenerate",
        "70% of Agreement Date decisions, but applicability is defined by gold "
        "already having the clipped shape, so the checker restates the answer. "
        "The apparent clash with g01 is not real: g01 exempts the date categories.",
    ),
    "d02": (
        "discriminating-but-rare",
        "Identical firing set to g03 on dev (12 decisions); the two are the same "
        "principle reached from two sources.",
    ),
    "d03": (
        "discriminating",
        "15% of in-scope decisions, phi 0.47, the strongest gold association in "
        "the set; applicability reads gold span text, so treat with care.",
    ),
    "d04": (
        "discriminating-after-widening",
        "35% in scope as written and misses half the gold-present contracts; "
        "widening the verb lexicon raises phi 0.21 to 0.47 and recall 6/12 to "
        "10/12.",
    ),
    "d05": (
        "near-degenerate",
        "Fires on 75% of Minimum Commitment and Volume Restriction decisions and "
        "on 30 of 40 contracts; a quantity plus a bound cue is ambient legalese.",
    ),
    "d06": (
        "degenerate",
        "One firing in 480 decisions; the evidence base was already n=1 and dev "
        "does not enlarge it.",
    ),
    "d07": (
        "degenerate",
        "Zero firings on dev; only 10 gold spans in the whole 12-category "
        "dev+ft_train pool contain furniture strictly inside.",
    ),
    "d08": (
        "degenerate-by-construction",
        "Fires on 55% of Minimum Commitment decisions but only ever on gold-absent "
        "ones, because applicability requires is_impossible.",
    ),
}


def length_bucket(n_tokens):
    if n_tokens <= 4000:
        return "<=4k"
    if n_tokens <= 8000:
        return "4k-8k"
    if n_tokens <= 16000:
        return "8k-16k"
    return ">16k"


def phi(a, b, c, d):
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    if denom == 0:
        return None
    return (a * d - b * c) / denom


def evaluate(dataset, split="dev"):
    instances = [dataset.get_instance(cid) for cid in dataset.contract_ids(split)]
    categories = dataset.categories
    rows = []
    for instance in instances:
        bucket = length_bucket(instance.n_tokens)
        for category in categories:
            label = instance.gold[category]
            rows.append(
                {
                    "contract_id": instance.contract_id,
                    "category": category,
                    "bucket": bucket,
                    "present": (not label.is_impossible) and bool(label.spans),
                    "n_gold_spans": len(label.spans),
                    "instance": instance,
                }
            )
    return rows, categories


def footprint(checker, rows, categories):
    scope = checker.eligible or checker.scope or list(categories)
    fired = []
    for row in rows:
        row_fired = checker.applies(row["instance"], row["category"])
        fired.append(row_fired)

    total = len(rows)
    n_fired = sum(fired)
    in_scope = [i for i, row in enumerate(rows) if row["category"] in scope]
    n_scope = len(in_scope)
    n_fired_scope = sum(fired[i] for i in in_scope)

    per_category = {}
    for category in categories:
        idx = [i for i, row in enumerate(rows) if row["category"] == category]
        per_category[category] = {
            "n_decisions": len(idx),
            "n_applicable": sum(fired[i] for i in idx),
        }

    pilot_idx = [i for i, row in enumerate(rows) if row["category"] in PILOT_CATEGORIES]
    per_pilot = {
        "n_decisions": len(pilot_idx),
        "n_applicable": sum(fired[i] for i in pilot_idx),
    }

    per_bucket = {}
    for bucket in ("<=4k", "4k-8k", "8k-16k", ">16k"):
        idx = [i for i in in_scope if rows[i]["bucket"] == bucket]
        per_bucket[bucket] = {
            "n_decisions": len(idx),
            "n_applicable": sum(fired[i] for i in idx),
        }

    a = sum(1 for i in in_scope if fired[i] and rows[i]["present"])
    b = sum(1 for i in in_scope if fired[i] and not rows[i]["present"])
    c = sum(1 for i in in_scope if not fired[i] and rows[i]["present"])
    d = sum(1 for i in in_scope if not fired[i] and not rows[i]["present"])

    contracts_fired = len({rows[i]["contract_id"] for i in range(total) if fired[i]})

    stability = {}
    for name, params in checker.variants.items():
        flags = [checker.applies(row["instance"], row["category"], **params) for row in rows]
        variant_fired = sum(flags)
        va = sum(1 for i in in_scope if flags[i] and rows[i]["present"])
        vb = sum(1 for i in in_scope if flags[i] and not rows[i]["present"])
        vc = sum(1 for i in in_scope if not flags[i] and rows[i]["present"])
        vd = sum(1 for i in in_scope if not flags[i] and not rows[i]["present"])
        stability[name] = {
            "n_applicable": variant_fired,
            "rate_all_decisions": round(variant_fired / total, 4),
            "delta_vs_as_written": round((variant_fired - n_fired) / total, 4),
            "in_scope_2x2": {
                "applicable_present": va,
                "applicable_absent": vb,
                "notapplicable_present": vc,
                "notapplicable_absent": vd,
            },
            "phi": (lambda v: round(v, 4) if v is not None else None)(phi(va, vb, vc, vd)),
        }

    return {
        "principle_id": checker.id,
        "verdict": VERDICTS[checker.id][0],
        "verdict_reason": VERDICTS[checker.id][1],
        "scope": checker.scope,
        "eligible_categories": scope,
        "faithfulness": checker.faithful,
        "gold_dependency": GOLD_DEPENDENCY[checker.id],
        "n_decisions_total": total,
        "n_applicable": n_fired,
        "applicability_rate_all_decisions": round(n_fired / total, 4),
        "n_decisions_in_scope": n_scope,
        "n_applicable_in_scope": n_fired_scope,
        "applicability_rate_in_scope": round(n_fired_scope / n_scope, 4) if n_scope else None,
        "n_contracts_with_any_firing": contracts_fired,
        "per_category": per_category,
        "pilot_categories_slice": per_pilot,
        "per_length_bucket": per_bucket,
        "discrimination": {
            "basis": "in-scope decisions; applicable x gold-present",
            "applicable_present": a,
            "applicable_absent": b,
            "notapplicable_present": c,
            "notapplicable_absent": d,
            "p_present_given_applicable": round(a / (a + b), 4) if (a + b) else None,
            "p_present_given_not_applicable": round(c / (c + d), 4) if (c + d) else None,
            "lift": (
                round((a / (a + b)) / (c / (c + d)), 4)
                if (a + b) and (c + d) and c
                else None
            ),
            "phi": (lambda v: round(v, 4) if v is not None else None)(phi(a, b, c, d)),
            "tautological": GOLD_DEPENDENCY[checker.id] != "instance_only",
        },
        "stability": stability,
    }


def snippet(row, limit=180):
    label = row["instance"].gold[row["category"]]
    if label.spans:
        return " ".join(label.spans[0].text.split())[:limit]
    return " ".join(row["instance"].text[:400].split())[:limit]


def examples_for(checker, rows, scope):
    out = []
    hits = [
        row
        for row in rows
        if row["category"] in scope and checker.applies(row["instance"], row["category"])
    ]
    misses = [
        row
        for row in rows
        if row["category"] in scope
        and not checker.applies(row["instance"], row["category"])
        and row["present"]
    ]
    for row in hits[:3]:
        out.append(
            {
                "verdict": "applies",
                "contract_id": row["contract_id"],
                "category": row["category"],
                "gold_present": row["present"],
                "text": snippet(row),
            }
        )
    for row in misses[:1]:
        out.append(
            {
                "verdict": "does not apply",
                "contract_id": row["contract_id"],
                "category": row["category"],
                "gold_present": True,
                "text": snippet(row),
            }
        )
    return out


def to_app_schema(out, rows):
    principles = {}
    for pid, fp in out["principles"].items():
        checker = REGISTRY[pid]
        scope = fp["eligible_categories"]
        disc = fp["discrimination"]
        positive = disc["p_present_given_applicable"]
        negative = disc["p_present_given_not_applicable"]
        lift = (
            round(positive - negative, 4)
            if positive is not None and negative is not None
            else None
        )
        counts = [
            (category, fp["per_category"][category])
            for category in scope
            if fp["per_category"][category]["n_decisions"]
        ]
        per_contract = {}
        for row in rows:
            if row["category"] in scope and checker.applies(
                row["instance"], row["category"]
            ):
                per_contract[row["contract_id"]] = per_contract.get(row["contract_id"], 0) + 1
        values = sorted(per_contract.values())
        principles[pid] = {
            "status": fp["verdict"],
            "note": (
                f"{fp['verdict_reason']} Rate over all 480 decisions: "
                f"{fp['applicability_rate_all_decisions']:.1%}. "
                f"Applicability is computed from {fp['gold_dependency'].replace('_', ' ')}; "
                + (
                    "the discrimination number is therefore arithmetic, not evidence."
                    if disc["tautological"]
                    else "the discrimination number is a real association."
                )
            ),
            "applicability": {
                "n_applicable": fp["n_applicable_in_scope"],
                "n_units": fp["n_decisions_in_scope"],
                "rate": fp["applicability_rate_in_scope"],
            },
            "distribution": {
                "by": "category",
                "rows": [
                    {
                        "key": category,
                        "n_applicable": entry["n_applicable"],
                        "n_units": entry["n_decisions"],
                        "rate": round(entry["n_applicable"] / entry["n_decisions"], 4),
                    }
                    for category, entry in counts
                ],
                "concentration": {
                    "n_contracts_with_any": len(per_contract),
                    "n_contracts": out["n_contracts"],
                    "max_per_contract": max(values) if values else 0,
                    "median_per_contract": values[len(values) // 2] if values else 0,
                },
            },
            "discrimination": {
                "metric": "P(category present in gold) when applicable vs when not",
                "pass_rate_positive": positive,
                "pass_rate_negative": negative,
                "lift": lift,
                "n_positive": disc["applicable_present"] + disc["applicable_absent"],
                "n_negative": disc["notapplicable_present"] + disc["notapplicable_absent"],
            },
            "length_buckets": fp["per_length_bucket"],
            "stability": fp["stability"],
            "examples": examples_for(checker, rows, scope),
        }
        if "hand_score" in fp:
            principles[pid]["hand_score"] = fp["hand_score"]
    return {
        "schema_version": 1,
        "generated": "2026-08-15",
        "generator": {
            "script": "studies/008-principled-extraction-cuad/principles/pilot/checkers/run_footprints.py",
            "version": "1.0",
        },
        "split": out["split"],
        "population": {
            "unit": "decision (contract x category)",
            "n_units": out["n_decisions"],
            "n_contracts": out["n_contracts"],
        },
        "note": (
            "Applicability rate and denominator are over in-scope decisions "
            "(the categories a principle can govern); the rate over all 480 "
            "decisions is repeated in each note."
        ),
        "principles": principles,
    }


def main():
    dataset = CuadDataset()
    rows, categories = evaluate(dataset, "dev")
    out = {
        "split": "dev",
        "n_contracts": len(dataset.contract_ids("dev")),
        "n_categories": len(categories),
        "n_decisions": len(rows),
        "pilot_categories": list(PILOT_CATEGORIES),
        "principles": {},
    }
    for pid, checker in REGISTRY.items():
        out["principles"][pid] = footprint(checker, rows, categories)
    hand = Path(__file__).resolve().parent / "handscore.json"
    if hand.exists():
        scores = json.loads(hand.read_text())
        out["principles"]["g05"]["hand_score"] = {
            "gold_span_agreement": scores["g05"]["gold_span_agreement"],
            "negative_sentence_scan": scores["g05"]["negative_sentence_scan"],
        }
        out["principles"]["g06"]["hand_score"] = scores["g06"]["trigger_agreement"]
    directory = Path(__file__).resolve().parent
    (directory / "footprints.json").write_text(json.dumps(out, indent=2) + "\n")
    app_view = to_app_schema(out, rows)
    (directory / "footprint.yaml").write_text(
        yaml.safe_dump(app_view, sort_keys=False, allow_unicode=True, width=100)
    )
    for pid, fp in out["principles"].items():
        print(
            pid,
            fp["applicability_rate_all_decisions"],
            fp["applicability_rate_in_scope"],
            fp["discrimination"]["phi"],
        )


if __name__ == "__main__":
    main()
