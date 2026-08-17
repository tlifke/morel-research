import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

STUDY = Path(__file__).resolve().parents[1]
TRACES = STUDY / "data" / "traces" / "2026-08-16-c2c3-harness-val"
TABLE2 = STUDY / "data" / "cuad-baseline" / "table2"
SCORED = STUDY / "data" / "cuad-baseline" / "c2c3_cuad_scored.json"
OUT = STUDY / "reviews" / "c2-c3-results-data.json"

MODELS = [
    ("roberta-base", "RoBERTa-base"),
    ("roberta-large", "RoBERTa-large"),
    ("deberta-v2-xlarge", "DeBERTa-v2-xlarge"),
]

CATEGORIES = [
    "Agreement Date", "Anti-Assignment", "Cap On Liability", "Exclusivity",
    "Expiration Date", "Governing Law", "License Grant", "Minimum Commitment",
    "Most Favored Nation", "Revenue/Profit Sharing", "Source Code Escrow",
    "Volume Restriction",
]


def load_rows():
    trials, decisions = {}, defaultdict(list)
    for shard in sorted(TRACES.glob("shard*")):
        for line in (shard / "trials.jsonl").read_text().splitlines():
            if line.strip():
                t = json.loads(line)
                trials[t["trial_id"]] = t
        for line in (shard / "decisions.jsonl").read_text().splitlines():
            if line.strip():
                d = json.loads(line)
                decisions[d["trial_id"]].append(d)
    return trials, decisions


def f1(p, r):
    return 2 * p * r / (p + r) if (p + r) else 0.0


def cells_to_metrics(c):
    tp, fp, fn, tn = c["TP"], c["FP"], c["FN"], c["TN"]
    n = tp + fp + fn + tn
    pp = tp / (tp + fp) if tp + fp else 0.0
    pr_ = tp / (tp + fn) if tp + fn else 0.0
    ap = tn / (tn + fn) if tn + fn else 0.0
    ar = tn / (tn + fp) if tn + fp else 0.0
    present = tp + fn
    absent = tn + fp
    bp = present / n if n else 0.0
    ba = absent / n if n else 0.0
    return {
        "counts": {"TP": tp, "FP": fp, "FN": fn, "TN": tn, "n": n},
        "presence_precision": pp, "presence_recall": pr_, "presence_f1": f1(pp, pr_),
        "absent_precision": ap, "absent_recall": ar, "absent_f1": f1(ap, ar),
        "decision_kind_accuracy": (tp + tn) / n if n else 0.0,
        "always_present_presence_f1": 2 * bp / (bp + 1) if bp else 0.0,
        "always_absent_absent_f1": 2 * ba / (ba + 1) if ba else 0.0,
        "always_absent_decision_accuracy": ba,
        "always_present_decision_accuracy": bp,
        "n_gold_present": present, "n_gold_absent": absent,
    }


TRIAL_METRICS = {
    "macro_presence_f1": lambda t: t["answer"]["level_a"]["macro_presence_class"]["f1"],
    "macro_absent_f1": lambda t: t["answer"]["level_a"]["macro_absent_class"]["f1"],
    "decision_kind_accuracy": lambda t: t["answer"]["level_a"]["micro"]["decision_kind_accuracy"],
    "false_present": lambda t: t["answer"]["level_a"]["micro"]["false_present"],
    "false_absent": lambda t: t["answer"]["level_a"]["micro"]["false_absent"],
    "span_f1": lambda t: t["answer"]["level_b"].get("span_f1"),
    "span_precision": lambda t: t["answer"]["level_b"].get("span_precision"),
    "span_recall": lambda t: t["answer"]["level_b"].get("span_recall"),
    "exact_match_rate": lambda t: t["answer"]["level_b"].get("exact_match_rate"),
    "verbatim_exact_rate": lambda t: t["answer"]["level_b"].get("verbatim_exact_rate"),
    "verbatim_normalized_only_rate": lambda t: t["answer"]["level_b"].get("verbatim_normalized_only_rate"),
    "verbatim_not_found_rate": lambda t: t["answer"]["level_b"].get("verbatim_not_found_rate"),
    "completion_tokens": lambda t: t["n_completion_tokens"],
    "prompt_tokens": lambda t: t["n_prompt_tokens"],
}

METRIC_LABELS = [
    ("macro_presence_f1", "presence-class F1 (macro, per-trial)"),
    ("macro_absent_f1", "absent-class F1 (macro, per-trial)"),
    ("decision_kind_accuracy", "decision-kind accuracy"),
    ("false_present", "false-present count per trial"),
    ("false_absent", "false-absent count per trial"),
    ("span_f1", "span F1 (TP cell)"),
    ("span_precision", "span precision"),
    ("span_recall", "span recall"),
    ("exact_match_rate", "exact-match rate"),
    ("verbatim_exact_rate", "verbatim exact rate"),
    ("verbatim_normalized_only_rate", "verbatim normalised-only rate"),
    ("verbatim_not_found_rate", "verbatim not-found rate"),
    ("completion_tokens", "completion tokens"),
    ("prompt_tokens", "prompt tokens"),
]


def paired_contrast(trials, intersection, rng, n_boot=10000):
    out = []
    for key, label in METRIC_LABELS:
        fn_ = TRIAL_METRICS[key]
        per = {}
        for cid in intersection:
            vals = {}
            for cond in ("C2", "C3"):
                xs = [fn_(t) for t in trials.values()
                      if t["outcome"] == "ok" and t["condition"] == cond and t["contract_id"] == cid]
                xs = [x for x in xs if x is not None]
                vals[cond] = float(np.mean(xs)) if xs else None
            if vals["C2"] is not None and vals["C3"] is not None:
                per[cid] = vals
        diffs = np.array([per[c]["C3"] - per[c]["C2"] for c in sorted(per)])
        n = len(diffs)
        idx = rng.integers(0, n, size=(n_boot, n))
        boot = diffs[idx].mean(axis=1)
        lo, hi = np.percentile(boot, [2.5, 97.5])
        sd = diffs.std(ddof=1)
        out.append({
            "key": key, "label": label,
            "n_contracts": n,
            "mean_c2": float(np.mean([per[c]["C2"] for c in per])),
            "mean_c3": float(np.mean([per[c]["C3"] for c in per])),
            "delta": float(diffs.mean()),
            "ci_low": float(lo), "ci_high": float(hi),
            "t": float(diffs.mean() / (sd / np.sqrt(n))) if sd > 0 else None,
            "up": int((diffs > 0).sum()), "down": int((diffs < 0).sum()),
            "excludes_zero": bool(lo > 0 or hi < 0),
        })
    return out


def main():
    rng = np.random.default_rng(20260816)
    trials, decisions = load_rows()
    scored = json.load(open(SCORED))
    table2 = json.load(open(TABLE2 / "table2_reproduction.json"))

    ok = {c: [t for t in trials.values() if t["condition"] == c and t["outcome"] == "ok"]
          for c in ("C2", "C3")}
    intersection = sorted(set(t["contract_id"] for t in ok["C2"]) & set(t["contract_id"] for t in ok["C3"]))

    data = {
        "run": {
            "run_id": "2026-08-16-c2c3-harness-val",
            "model": sorted({t["model"] for t in trials.values()})[0],
            "backend": "Tinker",
            "temperature": sorted({t["temperature"] for t in trials.values()})[0],
            "seeds": sorted({t["seed"] for t in trials.values()}),
            "seed_honored": sorted({t["seed_honored"] for t in trials.values()}),
            "max_output_tokens": sorted({t["max_output_tokens"] for t in trials.values()})[0],
            "max_repair_attempts": sorted({t["max_repair_attempts"] for t in trials.values()})[0],
            "schema_variant": sorted({t["schema_variant"] for t in trials.values()})[0],
            "principle_set_version": sorted({t["principle_set_version"] for t in trials.values()})[0],
            "prompt_template_version": sorted({t["prompt_template_version"] for t in trials.values()})[0],
            "harness_git_sha": sorted({t["harness_git_sha"] for t in trials.values()})[0],
            "split": sorted({t["split"] for t in trials.values()})[0],
            "n_trials": len(trials),
            "n_contracts": len({t["contract_id"] for t in trials.values()}),
            "n_categories": len(CATEGORIES),
            "categories": CATEGORIES,
            "intersection": intersection,
        },
    }

    data["outcomes"] = {}
    for cond in ("C2", "C3"):
        ts = [t for t in trials.values() if t["condition"] == cond]
        c = Counter(t["outcome"] for t in ts)
        reached = len(ts) - c["infeasible_at_length"] - c["api_error"]
        stage = Counter(t["failure_detail"].get("stage") if isinstance(t.get("failure_detail"), dict) else None
                        for t in ts if t["outcome"] == "parse_failure")
        data["outcomes"][cond] = {
            "trials": len(ts), "ok": c["ok"], "parse_failure": c["parse_failure"],
            "api_error": c["api_error"], "infeasible_at_length": c["infeasible_at_length"],
            "truncated": sum(1 for t in ts if t["completion_truncated"]),
            "reached_model": reached,
            "conformance": c["ok"] / reached if reached else None,
            "parse_stages": {str(k): v for k, v in stage.items()},
        }

    data["truncations"] = sorted(
        [{"condition": t["condition"], "seed": t["seed"], "bucket": t["length_bucket"],
          "contract_id": t["contract_id"], "n_contract_tokens": t["n_contract_tokens"],
          "outcome": t["outcome"],
          "stage": (t["failure_detail"] or {}).get("stage") if isinstance(t.get("failure_detail"), dict) else None}
         for t in trials.values() if t["completion_truncated"]],
        key=lambda r: (r["condition"], r["seed"], r["contract_id"]))

    data["citation"] = {}
    for cond in ("C2", "C3"):
        n_dec = sum(len(decisions[t["trial_id"]]) for t in ok[cond])
        cited = Counter()
        n_nonempty = 0
        for t in ok[cond]:
            for d in decisions[t["trial_id"]]:
                if d["principles_cited"]:
                    n_nonempty += 1
                    for p in d["principles_cited"]:
                        cited[p] += 1
        leak = sum(t["leakage"]["text_field_principle_refs"] for t in ok[cond])
        data["citation"][cond] = {
            "n_decisions": n_dec, "n_cited": n_nonempty,
            "rate": n_nonempty / n_dec if n_dec else None,
            "leakage": leak,
            "by_principle": dict(sorted(cited.items(), key=lambda kv: -kv[1])),
        }

    data["level_a"] = {}
    data["per_category"] = {}
    for cond in ("C2", "C3"):
        cells = Counter()
        percat = defaultdict(Counter)
        for t in ok[cond]:
            for d in decisions[t["trial_id"]]:
                cells[d["answer_score"]["cell"]] += 1
                percat[d["target"]][d["answer_score"]["cell"]] += 1
        base = {k: cells.get(k, 0) for k in ("TP", "FP", "FN", "TN")}
        m = cells_to_metrics(base)
        percat_metrics = {
            cat: cells_to_metrics({k: percat[cat].get(k, 0) for k in ("TP", "FP", "FN", "TN")})
            for cat in CATEGORIES
        }
        m["macro_presence_f1"] = float(np.mean([percat_metrics[c]["presence_f1"] for c in CATEGORIES]))
        m["macro_absent_f1"] = float(np.mean([percat_metrics[c]["absent_f1"] for c in CATEGORIES]))
        m["macro_note"] = "mean over the 12 categories of each category's pooled F1"
        m["n_trials"] = len(ok[cond])
        data["level_a"][cond] = m
        data["per_category"][cond] = percat_metrics

    data["level_b"] = {}
    for cond in ("C2", "C3"):
        tp_dec = spans = ex = no = nf = 0
        fp_dec = fp_spans = fp_ex = fp_nf = 0
        soft_p = soft_r = soft_f = 0.0
        em = 0
        n_gold_pred = [0, 0]
        msr = []
        for t in ok[cond]:
            for d in decisions[t["trial_id"]]:
                a = d["answer_score"]
                if a["cell"] == "TP":
                    tp_dec += 1
                    v = a["verbatim_fidelity"]
                    spans += v["n_spans"]; ex += v["n_exact"]; no += v["n_normalized_only"]; nf += v["n_not_found"]
                    soft_p += a["soft"]["precision"]; soft_r += a["soft"]["recall"]; soft_f += a["soft"]["f1"]
                    em += a["exact_match_rate"]
                    n_gold_pred[0] += a["multi_span_recovery"]["n_gold"]
                    n_gold_pred[1] += a["multi_span_recovery"]["n_predicted"]
                    msr.append(a["multi_span_recovery"]["ratio"])
                elif a["cell"] == "FP":
                    fp_dec += 1
                    v = a["verbatim_fidelity"]
                    fp_spans += v["n_spans"]; fp_ex += v["n_exact"]; fp_nf += v["n_not_found"]
        data["level_b"][cond] = {
            "tp_denominator": tp_dec, "spans": spans,
            "soft_precision": soft_p / tp_dec, "soft_recall": soft_r / tp_dec, "soft_f1": soft_f / tp_dec,
            "exact_match_rate": em / tp_dec,
            "verbatim_exact": ex, "verbatim_normalized_only": no, "verbatim_not_found": nf,
            "verbatim_exact_rate": ex / spans, "verbatim_normalized_only_rate": no / spans,
            "verbatim_not_found_rate": nf / spans,
            "multi_span_ratio": float(np.mean(msr)),
            "multi_span_ratio_pooled": n_gold_pred[1] / n_gold_pred[0],
            "fp_cell": {"decisions": fp_dec, "spans": fp_spans, "exact": fp_ex, "not_found": fp_nf,
                        "exact_rate": fp_ex / fp_spans if fp_spans else None,
                        "not_found_rate": fp_nf / fp_spans if fp_spans else None},
        }

    data["contrast"] = paired_contrast(trials, intersection, rng)

    data["cost"] = {}
    for cond in ("C2", "C3"):
        p = [t["n_prompt_tokens"] for t in ok[cond]]
        c = [t["n_completion_tokens"] for t in ok[cond]]
        lat = [t["latency_ms"] / 1000 for t in ok[cond]]
        data["cost"][cond] = {
            "n": len(p),
            "prompt_tokens_mean": float(np.mean(p)),
            "completion_tokens_mean": float(np.mean(c)),
            "latency_s_mean": float(np.mean(lat)),
        }
    data["cost"]["run_totals"] = {
        "prompt_tokens": sum(t["n_prompt_tokens"] or 0 for t in trials.values()),
        "completion_tokens": sum(t["n_completion_tokens"] or 0 for t in trials.values()),
        "model_hours": sum(t["latency_ms"] or 0 for t in trials.values()) / 3.6e6,
        "n_trial_rows": len(trials),
    }

    data["cuad_table2"] = []
    for key, label in MODELS:
        m = table2["models"][key]
        data["cuad_table2"].append({
            "model": label, "key": key,
            "aupr_published": m["published"]["aupr"], "aupr_recovered": m["aupr"] * 100,
            "p80_published": m["published"]["p80"], "p80_recovered": m["prec_at_80_recall"] * 100,
            "p90_published": m["published"]["p90"], "p90_recovered": m["prec_at_90_recall"] * 100,
            "max_recall": m["max_recall"],
            "operating_point_80": m.get("operating_point_at_80_recall"),
        })
    data["cuad_meta"] = {
        "n_questions": table2["n_questions"],
        "gold": "CUAD official test split (102 contracts x 41 categories)",
    }

    data["cuad_curves"] = {}
    for key, label in MODELS:
        rows = list(csv.DictReader(open(TABLE2 / f"pr_curve_{key}.csv")))
        data["cuad_curves"][label] = [
            {"recall": float(r["recall"]), "precision": float(r["precision"]),
             "interpolated_precision": float(r["interpolated_precision"]),
             "conf": float(r["conf"]) if r["conf"] else None}
            for r in rows
        ]

    data["our_cuad_points"] = {
        "scorer": scored["scorer"],
        "gold_source": scored["gold_source"],
        "split": scored["split"],
        "split_provenance": scored["split_provenance"],
        "gold_profile": scored["gold_profile"],
        "n_intersection": scored["n_intersection"],
        "conditions": scored["conditions"],
        "per_seed": scored["per_seed"],
        "per_category": scored["per_category"],
        "pooled_all_scored": scored["pooled_all_scored"],
    }

    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
