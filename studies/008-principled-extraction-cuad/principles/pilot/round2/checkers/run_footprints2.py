import json
import math
import sys
from pathlib import Path

import yaml

ROUND2 = Path(__file__).resolve().parents[1]
PILOT = Path(__file__).resolve().parents[2]
STUDY = Path(__file__).resolve().parents[4]
for path in (str(STUDY / "scripts"), str(PILOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from checkers.run_footprints import examples_for, length_bucket  # noqa: E402
from cuad_dataset import CuadDataset  # noqa: E402
from round2.checkers.checkers2 import MATCHED, REGISTRY, set_corpus  # noqa: E402

SPLIT = "dev"

GOLD_DEPENDENCY = {
    "p01": "instance_only",
    "p02": "gold_absence",
    "p03": "corpus_and_instance",
    "p04": "instance_only",
    "p05": "universal",
    "p06": "instance_only",
    "p07": "gold_presence",
    "p08": "gold_span_content_own",
    "p09": "instance_only",
    "p10": "gold_span_content_own",
    "p11": "instance_only",
    "p12": "gold_presence",
    "p13": "instance_only",
    "p14": "instance_only",
    "p15": "gold_span_content_other",
    "p16": "gold_absence",
    "p17": "gold_presence_and_instance",
    "p18": "gold_span_content_own",
    "p19": "gold_span_content_own",
    "p20": "gold_span_content_own",
    "p21": "gold_presence_and_instance",
    "p22": "gold_presence",
    "p23": "gold_span_content_own",
}

STRUCTURAL_EMPTY = {
    "gold_presence": ["applicable_absent"],
    "gold_presence_and_instance": ["applicable_absent"],
    "gold_span_content_own": ["applicable_absent"],
    "gold_absence": ["applicable_present"],
    "instance_only": [],
    "corpus_and_instance": [],
    "gold_span_content_other": [],
    "universal": ["notapplicable_present", "notapplicable_absent"],
}

FAITHFULNESS_NOTE = {
    "p03": (
        "Sketch names a 400+ character substring shared with 'another contract' and points at "
        "scan_split_contamination.py. Implemented as an exact 400-character shared-window test "
        "against the other 39 dev contracts on whitespace-normalised text, since the sketch's "
        "containment-score artifact is not part of this deliverable."
    ),
    "p04": (
        "Sketch asks for first ~3000 characters or the signature block; implemented as head 3000 "
        "plus trailing 3000 characters, and the 'bare comma where a date should follow an execution "
        "verb' clause is dropped because it fires on ordinary prose."
    ),
    "p21": (
        "Sketch's compliance half needs a date normaliser across corpus formats. Applicability is "
        "implemented as written (gold present, execution block located, at least one date literal "
        "after it); the date-equality subsetting the sketch asks for is a compliance-time concern "
        "and is not part of the footprint."
    ),
    "p17": (
        "Sketch's 'within 200 characters of a governing-law cue' is implemented as a window around "
        "the conflicts tail rather than a sentence test. The sketch's own regex is used verbatim, "
        "and it misses the very common 'without regard to ITS conflicts of laws' phrasing; the "
        "wide_tail variant repairs that and more than quadruples the firing count, which is the "
        "single largest instability in the round-2 set."
    ),
    "p20": (
        "Sketch requires the attachment heading search to start at the execution block; implemented "
        "exactly that way. Contracts with no locatable execution block are not applicable, as the "
        "sketch prescribes."
    ),
}


MEASUREMENT_NOTE = {
    "p03": (
        "The derivative cue alone fires on 4 of 40 dev contracts (48 decisions), but none of those "
        "four shares a 400-character window with any other dev contract, so the sketch as written "
        "is empty on dev. The shared-text half was computed within dev only; a wider corpus would "
        "likely find twins, which makes this a split-size artefact rather than a settled zero."
    ),
    "p08": (
        "The literal marker '<omitted>' occurs 0 times in dev contract text and 0 times in dev gold "
        "spans. The checker cannot fire on this corpus at all, which disqualifies the principle as "
        "a measurable rule here regardless of whether the Handbook prescribes it."
    ),
    "p19": (
        "Furniture is not rare in dev — the regex matches 219 times across 12 of 40 contracts — but "
        "no 12-category dev gold span contains a match strictly inside it, so applicability is 0. "
        "The complementary half of the sketch (no span is wholly furniture) is trivially satisfied "
        "and carries no signal."
    ),
    "p05": (
        "Applicable to every decision by construction. It cannot select, cannot discriminate, and "
        "will dominate any citation-frequency aggregate it is pooled into."
    ),
    "p13": (
        "A quantity token plus a bound cue is ambient contract language: it fires on 30 of 40 "
        "contracts and on three quarters of in-scope decisions. Applicability is close to "
        "unconditional within scope."
    ),
    "p15": (
        "Applicability reads gold span text, but of the sibling category rather than the decision's "
        "own, so it is not a pure restatement of the answer; it is still a gold-derived trigger and "
        "cannot be computed at inference time."
    ),
    "p20": (
        "Every firing sits on a gold-present decision, because applicability requires a gold span. "
        "What varies across contracts is only whether an attachment heading follows the execution "
        "block; that text test is doing real work, but it is gated behind the answer."
    ),
}


def phi(a, b, c, d):
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    if denom == 0:
        return None
    return (a * d - b * c) / denom


def build_rows(dataset):
    instances = [dataset.get_instance(cid) for cid in dataset.contract_ids(SPLIT)]
    rows = []
    for instance in instances:
        bucket = length_bucket(instance.n_tokens)
        for category in dataset.categories:
            label = instance.gold[category]
            rows.append(
                {
                    "contract_id": instance.contract_id,
                    "category": category,
                    "bucket": bucket,
                    "present": (not label.is_impossible) and bool(label.spans),
                    "instance": instance,
                }
            )
    return rows, dataset.categories


def two_by_two(fired, rows, index):
    a = sum(1 for i in index if fired[i] and rows[i]["present"])
    b = sum(1 for i in index if fired[i] and not rows[i]["present"])
    c = sum(1 for i in index if not fired[i] and rows[i]["present"])
    d = sum(1 for i in index if not fired[i] and not rows[i]["present"])
    return a, b, c, d


ZERO_RATE_STATUS = {
    "p08": "unimplementable",
    "p03": "never-fires-in-dev",
    "p19": "never-fires-in-dev",
}


def status_for(pid, rate_all, rate_scope, ph, dependency):
    if rate_all == 0:
        return ZERO_RATE_STATUS.get(pid, "never-fires-in-dev")
    if dependency == "universal":
        return "degenerate-universal"
    if dependency in (
        "gold_presence",
        "gold_presence_and_instance",
        "gold_span_content_own",
        "gold_absence",
    ):
        return "tautological-applicability"
    if rate_scope is not None and (rate_scope <= 0.02 or rate_scope >= 0.98):
        return "degenerate-frequency"
    if rate_scope is not None and rate_scope >= 0.75:
        return "near-degenerate-frequency"
    if ph is None or abs(ph) < 0.05:
        return "applies-but-non-discriminating"
    if rate_all <= 0.02:
        return "discriminating-but-rare"
    return "discriminating"


def measure(checker, rows, categories, n_contracts):
    pid = checker.id
    scope = checker.eligible or checker.scope or list(categories)
    fired = [checker.applies(row["instance"], row["category"]) for row in rows]
    total = len(rows)
    n_fired = sum(fired)
    in_scope = [i for i, row in enumerate(rows) if row["category"] in scope]
    n_scope = len(in_scope)
    n_fired_scope = sum(fired[i] for i in in_scope)

    per_category = []
    for category in categories:
        idx = [i for i, row in enumerate(rows) if row["category"] == category]
        n_app = sum(fired[i] for i in idx)
        per_category.append(
            {
                "key": category,
                "n_applicable": n_app,
                "n_units": len(idx),
                "rate": round(n_app / len(idx), 4) if idx else None,
            }
        )

    per_bucket = []
    for bucket in ("<=4k", "4k-8k", "8k-16k", ">16k"):
        idx = [i for i, row in enumerate(rows) if row["bucket"] == bucket]
        n_app = sum(fired[i] for i in idx)
        per_bucket.append(
            {
                "key": bucket,
                "n_applicable": n_app,
                "n_units": len(idx),
                "rate": round(n_app / len(idx), 4) if idx else None,
            }
        )

    per_contract = {}
    for i, row in enumerate(rows):
        if fired[i]:
            per_contract[row["contract_id"]] = per_contract.get(row["contract_id"], 0) + 1
    values = sorted(per_contract.values())

    a, b, c, d = two_by_two(fired, rows, in_scope)
    ph = phi(a, b, c, d)
    a_all, b_all, c_all, d_all = two_by_two(fired, rows, list(range(total)))
    phi_all = phi(a_all, b_all, c_all, d_all)

    dependency = GOLD_DEPENDENCY[pid]
    declared_empty = STRUCTURAL_EMPTY[dependency]
    cells = {
        "applicable_present": a,
        "applicable_absent": b,
        "notapplicable_present": c,
        "notapplicable_absent": d,
    }
    observed_empty = [name for name, value in cells.items() if value == 0]

    stability = {}
    for name, params in checker.variants.items():
        flags = [checker.applies(row["instance"], row["category"], **params) for row in rows]
        va, vb, vc, vd = two_by_two(flags, rows, in_scope)
        v_total = sum(flags)
        stability[name] = {
            "n_applicable_all_decisions": v_total,
            "rate_all_decisions": round(v_total / total, 4),
            "delta_vs_as_written": round((v_total - n_fired) / total, 4),
            "rate_in_scope": round(sum(flags[i] for i in in_scope) / n_scope, 4) if n_scope else None,
            "phi_in_scope": round(vp, 4) if (vp := phi(va, vb, vc, vd)) is not None else None,
        }
    swing = max(
        (abs(entry["delta_vs_as_written"]) for entry in stability.values()), default=0.0
    )

    rate_all = round(n_fired / total, 4)
    rate_scope = round(n_fired_scope / n_scope, 4) if n_scope else None
    status = status_for(pid, rate_all, rate_scope, ph, dependency)

    return {
        "id": pid,
        "status": status,
        "scope": checker.scope,
        "eligible_categories": scope,
        "faithfulness": checker.faithful,
        "faithfulness_note": FAITHFULNESS_NOTE.get(pid),
        "reused_checker": MATCHED.get(pid),
        "gold_dependency": dependency,
        "n_decisions": total,
        "n_contracts": n_contracts,
        "n_applicable": n_fired,
        "rate_all_decisions": rate_all,
        "n_decisions_in_scope": n_scope,
        "n_applicable_in_scope": n_fired_scope,
        "rate_in_scope": rate_scope,
        "per_category": per_category,
        "per_length_bucket": per_bucket,
        "concentration": {
            "n_contracts_with_any": len(per_contract),
            "n_contracts": n_contracts,
            "max_per_contract": max(values) if values else 0,
            "median_per_contract": values[len(values) // 2] if values else 0,
        },
        "twobytwo_in_scope": cells,
        "twobytwo_all_decisions": {
            "applicable_present": a_all,
            "applicable_absent": b_all,
            "notapplicable_present": c_all,
            "notapplicable_absent": d_all,
        },
        "phi_in_scope": round(ph, 4) if ph is not None else None,
        "phi_all_decisions": round(phi_all, 4) if phi_all is not None else None,
        "p_present_given_applicable": round(a / (a + b), 4) if (a + b) else None,
        "p_present_given_not_applicable": round(c / (c + d), 4) if (c + d) else None,
        "structurally_empty_cells": declared_empty,
        "observed_empty_cells": observed_empty,
        "stability": stability,
        "max_abs_rate_swing": round(swing, 4),
    }


SEPARABILITY_VERDICT = {
    "instance_only": (
        "pass",
        "Applicability reads contract text only; a decision can be applicable with the "
        "category gold-present or gold-absent, so compliance is not a restatement of the answer.",
    ),
    "corpus_and_instance": (
        "pass",
        "Applicability reads contract text plus a cross-contract text-overlap property; no "
        "gold field is consulted.",
    ),
    "universal": (
        "pass-but-vacuous",
        "Applicability consults nothing at all, so it cannot leak the answer — and cannot "
        "select anything either.",
    ),
    "gold_presence": (
        "fail",
        "Applicability is defined as the category being gold-present, so the applicable x "
        "gold-absent cell is empty by construction and any compliance rate computed on the "
        "applicable set is conditioned on the answer.",
    ),
    "gold_presence_and_instance": (
        "fail",
        "Applicability requires the category to be gold-present before any text test runs, so "
        "the applicable x gold-absent cell is empty by construction.",
    ),
    "gold_span_content_own": (
        "fail",
        "Applicability is computed from the category's own gold span text, which requires the "
        "category to be present; the applicable x gold-absent cell is empty by construction.",
    ),
    "gold_absence": (
        "fail",
        "Applicability requires gold is_impossible, so the applicable x gold-present cell is "
        "empty by construction and the principle can only ever be scored on absences.",
    ),
    "gold_span_content_other": (
        "partial",
        "Applicability reads gold span text, but of sibling categories rather than the decision's "
        "own, so both gold-present and gold-absent decisions can be applicable; the leak is "
        "indirect but real.",
    ),
}


def note_for(fp):
    parts = []
    parts.append(
        f"Fires on {fp['n_applicable']}/{fp['n_decisions']} decisions "
        f"({fp['rate_all_decisions']:.1%}) over the 12-category dev set"
    )
    if fp["n_decisions_in_scope"] != fp["n_decisions"]:
        parts[-1] += (
            f"; {fp['n_applicable_in_scope']}/{fp['n_decisions_in_scope']} "
            f"({fp['rate_in_scope']:.1%}) within its declared scope"
        )
    parts[-1] += "."
    verdict, why = SEPARABILITY_VERDICT[fp["gold_dependency"]]
    parts.append(f"Separability: {verdict} — {why}")
    if fp["phi_in_scope"] is None:
        parts.append("Phi against gold presence is undefined (a margin is zero).")
    else:
        parts.append(f"Phi against gold presence, in scope: {fp['phi_in_scope']}.")
    if fp["max_abs_rate_swing"] >= 0.05:
        parts.append(
            f"Unstable: a lexicon or threshold variant moves the rate by up to "
            f"{fp['max_abs_rate_swing']:.1%} of all decisions."
        )
    if fp["faithfulness_note"]:
        parts.append(fp["faithfulness_note"])
    if MEASUREMENT_NOTE.get(fp["id"]):
        parts.append(MEASUREMENT_NOTE[fp["id"]])
    return " ".join(parts)


def to_sidecar(measurements, rows, n_contracts, categories):
    principles = {}
    for pid, fp in measurements.items():
        checker = REGISTRY[pid]
        scope = fp["eligible_categories"]
        verdict, why = SEPARABILITY_VERDICT[fp["gold_dependency"]]
        positive = fp["p_present_given_applicable"]
        negative = fp["p_present_given_not_applicable"]
        lift = (
            round(positive - negative, 4)
            if positive is not None and negative is not None
            else None
        )
        principles[pid] = {
            "status": fp["status"],
            "note": note_for(fp),
            "applicability": {
                "n_applicable": fp["n_applicable"],
                "n_units": fp["n_decisions"],
                "rate": fp["rate_all_decisions"],
            },
            "distribution": {
                "by": "category",
                "rows": fp["per_category"],
                "concentration": fp["concentration"],
            },
            "discrimination": {
                "metric": (
                    "P(category present in gold) when the principle applies vs when it does "
                    "not, over in-scope decisions; phi is the 2x2 correlation"
                ),
                "pass_rate_positive": positive,
                "pass_rate_negative": negative,
                "lift": lift,
                "n_positive": fp["twobytwo_in_scope"]["applicable_present"]
                + fp["twobytwo_in_scope"]["applicable_absent"],
                "n_negative": fp["twobytwo_in_scope"]["notapplicable_present"]
                + fp["twobytwo_in_scope"]["notapplicable_absent"],
                "phi": fp["phi_in_scope"],
                "what_this_can_show": (
                    "Only whether applicability co-varies with the gold answer on dev. No model "
                    "outputs exist yet, so this is not compliance, not accuracy, and not evidence "
                    "that following the principle improves extraction."
                ),
                "what_this_cannot_show": (
                    "Whether a model that obeys the principle answers better than one that does "
                    "not. That needs the two-arm run."
                ),
            },
            "separability": {
                "verdict": verdict,
                "gold_dependency": fp["gold_dependency"],
                "why": why,
                "twobytwo_applicability_x_gold": fp["twobytwo_in_scope"],
                "twobytwo_all_decisions": fp["twobytwo_all_decisions"],
                "structurally_empty_cells": fp["structurally_empty_cells"],
                "observed_empty_cells": fp["observed_empty_cells"],
                "caveat": (
                    "The requested {passes, fails} x {gold present, gold absent} table cannot be "
                    "filled before model outputs exist; what is filled here is {applicable, not "
                    "applicable} x {gold present, gold absent}, which is the table that decides "
                    "whether compliance could ever be separable from correctness."
                ),
            },
            "scope_and_faithfulness": {
                "declared_scope": fp["scope"] or "all 12 categories",
                "eligible_categories": scope,
                "faithfulness": fp["faithfulness"],
                "faithfulness_note": fp["faithfulness_note"],
                "reused_existing_checker": fp["reused_checker"],
                "in_scope_applicability": {
                    "n_applicable": fp["n_applicable_in_scope"],
                    "n_units": fp["n_decisions_in_scope"],
                    "rate": fp["rate_in_scope"],
                },
            },
            "length_buckets": {"by": "contract token count", "rows": fp["per_length_bucket"]},
            "stability": {
                "max_abs_rate_swing_all_decisions": fp["max_abs_rate_swing"],
                "variants": fp["stability"],
            },
            "examples": examples_for(checker, rows, scope),
        }
    return {
        "schema_version": 1,
        "generated": "2026-08-15",
        "generator": {
            "script": (
                "studies/008-principled-extraction-cuad/principles/pilot/round2/checkers/"
                "run_footprints2.py"
            ),
            "version": "1.0",
        },
        "split": SPLIT,
        "population": {
            "unit": "decision (contract x category)",
            "n_units": len(rows),
            "n_contracts": n_contracts,
            "n_categories": len(categories),
        },
        "note": (
            "Headline applicability rate and denominator are over the full 12-category dev "
            "decision set (480 decisions). The rate restricted to a principle's declared scope "
            "is under scope_and_faithfulness.in_scope_applicability, and the discrimination 2x2 "
            "is computed on that in-scope subset. holdout was never loaded; ft_train was not used."
        ),
        "principles": principles,
    }


def main():
    dataset = CuadDataset()
    rows, categories = build_rows(dataset)
    contract_ids = dataset.contract_ids(SPLIT)
    set_corpus({cid: dataset.get_instance(cid).text for cid in contract_ids})
    measurements = {}
    for pid in sorted(REGISTRY):
        measurements[pid] = measure(REGISTRY[pid], rows, categories, len(contract_ids))
    out_dir = ROUND2
    (out_dir / "footprints.json").write_text(json.dumps(measurements, indent=2) + "\n")
    sidecar = to_sidecar(measurements, rows, len(contract_ids), categories)
    (out_dir / "footprint.yaml").write_text(
        yaml.safe_dump(sidecar, sort_keys=False, allow_unicode=True, width=100)
    )
    for pid, fp in measurements.items():
        print(
            pid,
            fp["status"],
            fp["rate_all_decisions"],
            fp["rate_in_scope"],
            fp["phi_in_scope"],
            SEPARABILITY_VERDICT[fp["gold_dependency"]][0],
        )


if __name__ == "__main__":
    main()
