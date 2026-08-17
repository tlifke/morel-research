import importlib.util
import json
import random
from collections import defaultdict
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
SCORER = STUDY / "scripts" / "score_c2c3_with_cuad_evaluator.py"
OUT = STUDY / "reviews" / "c2-c3-bootstrap-data.json"

N_BOOT = 10000
RNG_SEED = 20260816


def load_scorer():
    spec = importlib.util.spec_from_file_location("c2c3_scorer", SCORER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    S = load_scorer()
    ev = S.load_upstream_evaluate()
    categories = S.load_categories()
    harness_val = set(S.load_split("harness_val"))

    cuad = json.load(open(S.RAW / "CUADv1.json"))
    cuad = {"data": [c for c in cuad["data"] if c["title"] in harness_val]}
    gold_all = ev.get_answers(cuad)
    gold = {k: v for k, v in gold_all.items() if k.rsplit("__", 1)[-1] in categories}

    trials, decisions = S.load_rows()
    scored = {tid: t for tid, t in trials.items() if t["outcome"] == "ok"}

    by_cond_contract = defaultdict(set)
    for t in scored.values():
        by_cond_contract[t["condition"]].add(t["contract_id"])
    intersection = sorted(by_cond_contract["C2"] & by_cond_contract["C3"])
    inter = set(intersection)

    cell = defaultdict(dict)
    cell_cat = defaultdict(dict)
    for tid, t in sorted(scored.items()):
        if t["contract_id"] not in inter:
            continue
        gt, preds = {}, {}
        for d in decisions[tid]:
            key = f"{t['contract_id']}__{d['target']}#{tid}"
            gt[key] = gold[f"{t['contract_id']}__{d['target']}"]
            spans = d["predicted"]["spans"] if d["decision_kind"] == "extraction" else []
            preds[key] = [s for s in (spans or []) if s]
        c = S.pr(ev, gt, preds)
        cell[(t["condition"], t["contract_id"])][t["seed"]] = (c["tp"], c["fp"], c["fn"])
        for cat in categories:
            gc = {k: v for k, v in gt.items() if k.split("#", 1)[0].rsplit("__", 1)[-1] == cat}
            pc = {k: preds[k] for k in gc}
            cc = S.pr(ev, gc, pc)
            cell_cat[(t["condition"], t["contract_id"], cat)][t["seed"]] = (cc["tp"], cc["fp"], cc["fn"])

    def avg(d):
        n = len(d)
        vals = list(d.values())
        return tuple(sum(v[i] for v in vals) / n for i in range(3))

    per_contract = {}
    for cond in ("C2", "C3"):
        per_contract[cond] = {c: avg(cell[(cond, c)]) for c in intersection}
    per_contract_seeds = {cond: {c: sorted(cell[(cond, c)]) for c in intersection} for cond in ("C2", "C3")}

    def metrics(tp, fp, fn):
        p = tp / (tp + fp) if tp + fp else None
        r = tp / (tp + fn) if tp + fn else None
        f = 2 * p * r / (p + r) if p and r else None
        return p, r, f

    def agg(contracts, cond):
        tp = fp = fn = 0.0
        for c in contracts:
            a, b, d = per_contract[cond][c]
            tp += a
            fp += b
            fn += d
        return metrics(tp, fp, fn), (tp, fp, fn)

    point = {}
    for cond in ("C2", "C3"):
        (p, r, f), (tp, fp, fn) = agg(intersection, cond)
        point[cond] = {"precision": p, "recall": r, "micro_f1": f,
                       "tp": tp, "fp": fp, "fn": fn}

    obs = {
        "precision": point["C3"]["precision"] - point["C2"]["precision"],
        "recall": point["C3"]["recall"] - point["C2"]["recall"],
        "micro_f1": point["C3"]["micro_f1"] - point["C2"]["micro_f1"],
    }

    n = len(intersection)
    idx = list(range(n))
    arr = {cond: [per_contract[cond][c] for c in intersection] for cond in ("C2", "C3")}

    def run_boot(n_boot, rng_seed):
        rng = random.Random(rng_seed)
        draws = {"precision": [], "recall": [], "micro_f1": []}
        for _ in range(n_boot):
            pick = [rng.choice(idx) for _ in range(n)]
            vals = {}
            for cond in ("C2", "C3"):
                tp = fp = fn = 0.0
                a = arr[cond]
                for i in pick:
                    x, y, z = a[i]
                    tp += x
                    fp += y
                    fn += z
                vals[cond] = metrics(tp, fp, fn)
            for j, k in enumerate(("precision", "recall", "micro_f1")):
                draws[k].append(vals["C3"][j] - vals["C2"][j])
        out = {}
        for k, v in draws.items():
            s = sorted(v)
            lo = s[int(0.025 * n_boot)]
            hi = s[int(0.975 * n_boot) - 1]
            out[k] = {"delta": obs[k], "ci_low": lo, "ci_high": hi,
                      "frac_above_zero": sum(1 for x in v if x > 0) / n_boot,
                      "excludes_zero": (lo > 0 or hi < 0)}
        return out

    boot = run_boot(N_BOOT, RNG_SEED)
    stability = []
    for nb in (10000, 100000):
        for rs in (RNG_SEED, RNG_SEED + 1, RNG_SEED + 2):
            b = run_boot(nb, rs)["precision"]
            stability.append({"n_boot": nb, "rng_seed": rs, "ci_low": b["ci_low"],
                              "ci_high": b["ci_high"], "frac_above_zero": b["frac_above_zero"],
                              "excludes_zero": b["excludes_zero"]})

    fp_diff = []
    for c in intersection:
        c2, c3 = per_contract["C2"][c], per_contract["C3"][c]
        fp_diff.append({
            "contract_id": c,
            "c2_fp_mean": c2[1], "c3_fp_mean": c3[1],
            "diff": c3[1] - c2[1],
            "c2_seeds": len(per_contract_seeds["C2"][c]),
            "c3_seeds": len(per_contract_seeds["C3"][c]),
            "c2_fp_raw": sum(v[1] for v in cell[("C2", c)].values()),
            "c3_fp_raw": sum(v[1] for v in cell[("C3", c)].values()),
        })
    fp_diff.sort(key=lambda r: r["diff"])

    cat_fp = []
    for cat in categories:
        row = {"category": cat}
        for cond in ("C2", "C3"):
            tot = 0.0
            raw = 0
            for c in intersection:
                d = cell_cat[(cond, c, cat)]
                tot += sum(v[1] for v in d.values()) / len(d)
                raw += sum(v[1] for v in d.values())
            row[f"{cond.lower()}_fp_mean"] = tot
            row[f"{cond.lower()}_fp_raw"] = raw
        row["diff_mean"] = row["c3_fp_mean"] - row["c2_fp_mean"]
        row["diff_raw"] = row["c3_fp_raw"] - row["c2_fp_raw"]
        cat_fp.append(row)
    cat_fp.sort(key=lambda r: r["diff_mean"])

    raw_pooled = json.load(open(STUDY / "data" / "cuad-baseline" / "c2c3_cuad_scored.json"))["conditions"]

    top = sorted(fp_diff, key=lambda r: r["diff"])
    neg = [r for r in fp_diff if r["diff"] < 0]
    pos = [r for r in fp_diff if r["diff"] > 0]
    zero = [r for r in fp_diff if r["diff"] == 0]
    tot_neg = sum(r["diff"] for r in neg)

    out = {
        "method": {
            "unit": "contract (paired; same resampled contract set used in both arms)",
            "n_contracts": n,
            "seed_handling": "per-contract TP/FP/FN averaged over that contract's scored seeds before aggregation; resampling unit stays the contract",
            "estimator": "micro-pooled over resampled contracts: precision = sum(TP)/(sum(TP)+sum(FP)), recall = sum(TP)/(sum(TP)+sum(FN)), micro-F1 = harmonic mean",
            "scorer": "data/raw/evaluate.py via scripts/score_c2c3_with_cuad_evaluator.py (unmodified upstream get_jaccard, IOU_THRESH=0.5)",
            "n_boot": N_BOOT,
            "rng": f"python random.Random({RNG_SEED}), sampling with replacement",
            "interval": "95% percentile",
        },
        "point_seed_averaged": point,
        "point_raw_pooled": raw_pooled,
        "bootstrap": boot,
        "precision_ci_stability": stability,
        "recall_identity": {
            "c2_recall_raw": raw_pooled["C2"]["recall"],
            "c3_recall_raw": raw_pooled["C3"]["recall"],
            "raw_diff": raw_pooled["C3"]["recall"] - raw_pooled["C2"]["recall"],
            "c2_counts": [raw_pooled["C2"]["tp"], raw_pooled["C2"]["fn"]],
            "c3_counts": [raw_pooled["C3"]["tp"], raw_pooled["C3"]["fn"]],
            "exact": raw_pooled["C2"]["recall"] == raw_pooled["C3"]["recall"],
        },
        "fp_by_contract": fp_diff,
        "fp_by_contract_summary": {
            "n_down": len(neg), "n_up": len(pos), "n_flat": len(zero),
            "total_reduction_mean_units": sum(r["diff"] for r in fp_diff),
            "largest_single_reduction": top[0],
            "top5_share_of_reduction": sum(r["diff"] for r in neg[:5]) / tot_neg if tot_neg else None,
            "top1_share_of_reduction": neg[0]["diff"] / tot_neg if tot_neg else None,
            "raw_fp_total": {"C2": sum(r["c2_fp_raw"] for r in fp_diff), "C3": sum(r["c3_fp_raw"] for r in fp_diff)},
        },
        "fp_by_category": cat_fp,
    }
    OUT.write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({"bootstrap": boot, "point": point,
                      "recall_identity": out["recall_identity"],
                      "fp_summary": out["fp_by_contract_summary"]}, indent=2))
    print("\nFP by category (C3-C2, seed-averaged):")
    for r in cat_fp:
        print(f'  {r["category"]:26s} C2 {r["c2_fp_mean"]:6.2f}  C3 {r["c3_fp_mean"]:6.2f}  diff {r["diff_mean"]:+6.2f}  (raw {r["diff_raw"]:+d})')
    print("\nFP by contract, most negative first:")
    for r in fp_diff[:8]:
        print(f'  {r["diff"]:+6.2f}  {r["contract_id"][:60]}')
    print("  ...")
    for r in fp_diff[-4:]:
        print(f'  {r["diff"]:+6.2f}  {r["contract_id"][:60]}')


if __name__ == "__main__":
    main()
