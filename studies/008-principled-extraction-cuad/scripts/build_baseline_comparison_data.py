import csv
import json
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
DATA = STUDY / "data" / "cuad-baseline"
REVIEWS = STUDY / "reviews"
OUT = REVIEWS / "baseline-comparison-data.json"

MODELS = [
    ("roberta-base", "RoBERTa-base"),
    ("roberta-large", "RoBERTa-large"),
    ("deberta-v2-xlarge", "DeBERTa-v2-xlarge"),
]
HEADLINE_CONF = "0.5"
OPEN_CONF = "0.1"


def load(p):
    with open(p) as fh:
        return json.load(fh)


def read_curve(key):
    rows = []
    with open(DATA / "table2" / f"pr_curve_{key}.csv") as fh:
        for r in csv.DictReader(fh):
            rows.append(
                {
                    "conf": None if r["conf"] in ("", "None") else float(r["conf"]),
                    "recall": float(r["recall"]),
                    "precision": float(r["precision"]),
                    "interpolated_precision": float(r["interpolated_precision"]),
                }
            )
    return rows


def rate(num, den):
    return None if not den else num / den


def f1(p, r):
    if p is None or r is None or (p + r) == 0:
        return 0.0
    return 2 * p * r / (p + r)


def norm(name):
    return name.lower().replace("-", " ").replace("/", " ").split()


def key_of(name):
    return " ".join(norm(name))


def spearman(a, b):
    n = len(a)
    mean_a, mean_b = sum(a) / n, sum(b) / n
    num = sum((x - mean_a) * (y - mean_b) for x, y in zip(a, b))
    da = sum((x - mean_a) ** 2 for x in a) ** 0.5
    db = sum((y - mean_b) ** 2 for y in b) ** 0.5
    return num / (da * db)


def main():
    t2 = load(DATA / "table2" / "table2_reproduction.json")
    splits = load(DATA / "baseline_on_train_splits.json")
    ours_scored = load(DATA / "c2c3_cuad_scored.json")
    ours_profile = load(DATA / "c2c3_absence_profile.json")
    boot = load(REVIEWS / "c2-c3-bootstrap-data.json")
    page = load(REVIEWS / "c2-c3-results-data.json")

    hv = splits["by_split"]["harness_val"]
    cats = splits["provenance"]["categories"]

    table2 = []
    for key, label in MODELS:
        m = t2["models"][key]
        table2.append(
            {
                "model": label,
                "key": key,
                "aupr_published": m["published"]["aupr"],
                "aupr_recovered": m["aupr"] * 100,
                "p80_published": m["published"]["p80"],
                "p80_recovered": m["prec_at_80_recall"] * 100,
                "p90_published": m["published"]["p90"],
                "p90_recovered": m["prec_at_90_recall"] * 100,
                "max_recall": m["max_recall"],
                "operating_point_80": m["operating_point_at_80_recall"],
            }
        )

    test_curves = {label: read_curve(key) for key, label in MODELS}

    their_hv = {}
    for key, label in MODELS:
        m = hv["models"][key]
        sweep = []
        for conf in sorted(m["conf_sweep"], key=float):
            s = m["conf_sweep"][conf]
            sweep.append(
                {
                    "conf": float(conf),
                    "precision": s["precision"],
                    "recall": s["recall"],
                    "tp": s["tp"],
                    "fp": s["fp"],
                    "fn": s["fn"],
                    "fp_on_gold_absent_questions": s["fp_on_gold_absent_questions"],
                    "fp_on_gold_present_questions": s["fp_on_gold_present_questions"],
                    "questions_gold_present": s["questions_gold_present"],
                    "questions_gold_absent": s["questions_gold_absent"],
                    "gold_present_questions_with_no_prediction": s["gold_present_questions_with_no_prediction"],
                    "gold_absent_questions_with_a_prediction": s["gold_absent_questions_with_a_prediction"],
                }
            )
        their_hv[label] = {"curve": m["curve"], "sweep": sweep}

    our_hv = {}
    for cond in ("C2", "C3"):
        pooled = ours_profile["conditions"][cond]["pooled"]
        scored = ours_scored["conditions"][cond]
        our_hv[cond] = {
            "precision": pooled["precision"],
            "recall": pooled["recall"],
            "tp": pooled["tp"],
            "fp": pooled["fp"],
            "fn": pooled["fn"],
            "fp_on_gold_absent_questions": pooled["fp_on_gold_absent_questions"],
            "fp_on_gold_present_questions": pooled["fp_on_gold_present_questions"],
            "questions_gold_present": pooled["questions_gold_present"],
            "questions_gold_absent": pooled["questions_gold_absent"],
            "gold_present_questions_with_no_prediction": pooled["gold_present_questions_with_no_prediction"],
            "gold_absent_questions_with_a_prediction": pooled["gold_absent_questions_with_a_prediction"],
            "n_trials": scored["n_trials"],
            "n_questions": scored["n_questions"],
            "per_seed": [
                {"seed": s, **ours_scored["per_seed"][cond][s]}
                for s in sorted(ours_scored["per_seed"][cond])
            ],
        }

    per_category = []
    for cat in cats:
        row = {"category": cat, "their": {}, "ours": {}}
        ref = hv["models"]["roberta-large"]["per_category"][cat]
        gold_spans = ref["tp"] + ref["fn"]
        row["gold_spans"] = gold_spans
        row["questions_gold_present"] = ref["questions_gold_present"]
        row["questions_gold_absent"] = ref["questions_gold_absent"]
        row["gold_spans_per_question"] = rate(gold_spans, ref["questions_gold_present"])
        for key, label in MODELS:
            pc = hv["models"][key]["per_category"][cat]
            row["their"][label] = {
                "precision": pc["precision"],
                "recall": pc["recall"],
                "aupr": pc["aupr"],
                "max_recall": pc["max_recall"],
            }
            open_pc = hv["models"][key]["per_category_by_conf"][OPEN_CONF][cat]
            row["their"][label]["open"] = {
                "precision": open_pc["precision"],
                "recall": open_pc["recall"],
            }
        for cond in ("C2", "C3"):
            pc = ours_profile["conditions"][cond]["per_category"][cat]
            row["ours"][cond] = {
                "precision": pc["precision"],
                "recall": pc["recall"],
                "fp": pc["fp"],
                "fp_on_gold_absent_questions": pc["fp_on_gold_absent_questions"],
                "fp_on_gold_present_questions": pc["fp_on_gold_present_questions"],
            }
        per_category.append(row)

    error_profile = []
    for key, label in MODELS:
        s = hv["models"][key]["conf_sweep"][HEADLINE_CONF]
        error_profile.append(
            {
                "system": label,
                "kind": "their",
                "declines": s["gold_present_questions_with_no_prediction"],
                "questions_gold_present": s["questions_gold_present"],
                "overclaims": s["gold_absent_questions_with_a_prediction"],
                "questions_gold_absent": s["questions_gold_absent"],
                "fp_absent": s["fp_on_gold_absent_questions"],
                "fp_present": s["fp_on_gold_present_questions"],
                "fp": s["fp"],
            }
        )
    for cond in ("C2", "C3"):
        p = ours_profile["conditions"][cond]["pooled"]
        error_profile.append(
            {
                "system": f"{cond} (9B, 3 seeds)",
                "kind": "ours",
                "declines": p["gold_present_questions_with_no_prediction"],
                "questions_gold_present": p["questions_gold_present"],
                "overclaims": p["gold_absent_questions_with_a_prediction"],
                "questions_gold_absent": p["questions_gold_absent"],
                "fp_absent": p["fp_on_gold_absent_questions"],
                "fp_present": p["fp_on_gold_present_questions"],
                "fp": p["fp"],
            }
        )
    for r in error_profile:
        r["decline_rate"] = rate(r["declines"], r["questions_gold_present"])
        r["overclaim_rate"] = rate(r["overclaims"], r["questions_gold_absent"])
        r["fp_absent_share"] = rate(r["fp_absent"], r["fp"])
        r["fp_present_share"] = rate(r["fp_present"], r["fp"])

    exp_classes = ["calendar_date", "duration", "event", "other"]
    expiration = []
    for cls in exp_classes:
        row = {"cls": cls, "their": {}, "ours": {}}
        for key, label in MODELS:
            t = hv["models"][key]["expiration_taxonomy"][HEADLINE_CONF].get(cls)
            if t:
                row["n_gold_spans"] = t["gold_spans"]
                row["their"][label] = {
                    "presence_recall": t["presence_recall"],
                    "span_iou_recall": t["span_iou_recall"],
                }
        for cond in ("C2", "C3"):
            t = ours_profile["conditions"][cond]["expiration_taxonomy"].get(cls)
            if t:
                row["ours"][cond] = {
                    "n_decisions": t["decisions"],
                    "presence_recall": t["presence_recall"],
                    "span_iou_recall": t["span_iou_recall"],
                }
        expiration.append(row)

    paper_fig4 = load(DATA / "paper_figure4_category_order.json")
    paper_rank = {key_of(c): i for i, c in enumerate(paper_fig4["order"])}
    ours_12 = {key_of(c) for c in cats}
    fig4_ref = "deberta-v2-xlarge"
    fig4_rows = []
    for cat, pcv in t2["models"][fig4_ref]["per_category"].items():
        fig4_rows.append(
            {
                "category": cat,
                "aupr": pcv["aupr"],
                "prec_at_80_recall": pcv["prec_at_80_recall"],
                "max_recall": pcv["max_recall"],
                "n_questions": pcv["n_questions"],
                "n_substring_matches": pcv["n_substring_matches"],
                "in_our_subset": key_of(cat) in ours_12,
                "paper_rank": paper_rank.get(key_of(cat)),
                "other_models": {
                    label: t2["models"][k]["per_category"][cat]["aupr"] for k, label in MODELS
                },
            }
        )
    fig4_rows.sort(key=lambda r: -r["aupr"])
    for i, r in enumerate(fig4_rows):
        r["our_rank"] = i
    paired = [(r["paper_rank"], r["our_rank"]) for r in fig4_rows if r["paper_rank"] is not None]
    subset_auprs = [r["aupr"] for r in fig4_rows if r["in_our_subset"]]
    rest_auprs = [r["aupr"] for r in fig4_rows if not r["in_our_subset"]]
    figure4a = {
        "model": "DeBERTa-v2-xlarge",
        "paper_presentation": paper_fig4,
        "split": "test",
        "rows": fig4_rows,
        "rank_agreement_spearman": spearman([p for p, _ in paired], [o for _, o in paired]),
        "n_ranked_together": len(paired),
        "not_in_paper_figure": [r["category"] for r in fig4_rows if r["paper_rank"] is None],
        "subset_mean_aupr": sum(subset_auprs) / len(subset_auprs),
        "rest_mean_aupr": sum(rest_auprs) / len(rest_auprs),
        "subset_median_rank": sorted(r["our_rank"] for r in fig4_rows if r["in_our_subset"])[len(subset_auprs) // 2],
    }

    figure4b = []
    for cat in cats:
        row = {"category": cat, "their": {}, "their_open": {}, "ours": {}}
        for key, label in MODELS:
            pc = hv["models"][key]["per_category"][cat]
            row["their"][label] = f1(pc["precision"], pc["recall"])
            op = hv["models"][key]["per_category_by_conf"][OPEN_CONF][cat]
            row["their_open"][label] = f1(op["precision"], op["recall"])
        for cond in ("C2", "C3"):
            pc = ours_profile["conditions"][cond]["per_category"][cat]
            row["ours"][cond] = f1(pc["precision"], pc["recall"])
        fig4b_ref = [r for r in fig4_rows if key_of(r["category"]) == key_of(cat)][0]
        row["their_test_aupr"] = fig4b_ref["aupr"]
        row["their_test_rank"] = fig4b_ref["our_rank"] + 1
        figure4b.append(row)
    figure4b.sort(key=lambda r: -r["their_test_aupr"])

    pooled_f1 = {
        **{
            label: f1(
                hv["models"][k]["conf_sweep"][HEADLINE_CONF]["precision"],
                hv["models"][k]["conf_sweep"][HEADLINE_CONF]["recall"],
            )
            for k, label in MODELS
        },
        **{c: f1(our_hv[c]["precision"], our_hv[c]["recall"]) for c in ("C2", "C3")},
    }

    comparability = {
        "their_contracts": hv["n_contracts"],
        "their_questions": hv["n_questions"],
        "their_gold_present": hv["gold_present_questions"],
        "their_gold_spans": hv["gold_spans"],
        "our_contracts": ours_scored["n_intersection"],
        "our_split_contracts": ours_scored["n_contracts_split"],
        "our_gold_profile": ours_scored["gold_profile"],
        "their_gold_present_share": rate(hv["gold_present_questions"], hv["n_questions"]),
        "our_gold_present_share": {
            c: rate(
                our_hv[c]["questions_gold_present"],
                our_hv[c]["questions_gold_present"] + our_hv[c]["questions_gold_absent"],
            )
            for c in ("C2", "C3")
        },
        "test_questions": t2["n_questions"],
        "test_categories": 41,
        "hv_categories": len(cats),
    }

    out = {
        "generated_from": {
            "table2": "data/cuad-baseline/table2/table2_reproduction.json",
            "test_curves": "data/cuad-baseline/table2/pr_curve_*.csv",
            "their_on_train_splits": "data/cuad-baseline/baseline_on_train_splits.json",
            "ours_scored": "data/cuad-baseline/c2c3_cuad_scored.json",
            "ours_profile": "data/cuad-baseline/c2c3_absence_profile.json",
            "bootstrap": "reviews/c2-c3-bootstrap-data.json",
            "run_meta": "reviews/c2-c3-results-data.json",
            "paper_figure4_order": "data/cuad-baseline/paper_figure4_category_order.json",
        },
        "scorer": splits["provenance"]["scorer"],
        "gold": splits["provenance"]["gold"],
        "split_provenance": splits["provenance"]["split_provenance"],
        "headline_conf": float(HEADLINE_CONF),
        "open_conf": float(OPEN_CONF),
        "categories": cats,
        "run": page["run"],
        "citation": page["citation"],
        "outcomes": page["outcomes"],
        "table2": table2,
        "test_curves": test_curves,
        "test_meta": page["cuad_meta"],
        "harness_val": {
            "their": their_hv,
            "ours": our_hv,
            "comparability": comparability,
        },
        "figure4a": figure4a,
        "figure4b": {"rows": figure4b, "pooled_f1": pooled_f1},
        "per_category": per_category,
        "error_profile": error_profile,
        "expiration": expiration,
        "bootstrap": {
            "method": boot["method"],
            "point_seed_averaged": boot["point_seed_averaged"],
            "point_raw_pooled": boot["point_raw_pooled"],
            "intervals": boot["bootstrap"],
            "precision_ci_stability": boot["precision_ci_stability"],
            "fp_by_category": boot["fp_by_category"],
            "fp_by_contract_summary": boot["fp_by_contract_summary"],
        },
    }

    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(STUDY)}")


if __name__ == "__main__":
    main()
