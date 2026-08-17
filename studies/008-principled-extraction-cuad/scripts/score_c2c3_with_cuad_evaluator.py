import argparse
import importlib.util
import json
import os
import sys
from collections import defaultdict
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
RAW = STUDY / "data" / "raw"
TRACES = STUDY / "data" / "traces" / "2026-08-16-c2c3-harness-val"
SPLITS = STUDY / "data" / "processed" / "splits"


def load_upstream_evaluate():
    cwd = os.getcwd()
    os.chdir(RAW)
    try:
        spec = importlib.util.spec_from_file_location("cuad_evaluate", RAW / "evaluate.py")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["cuad_evaluate"] = mod
        spec.loader.exec_module(mod)
    finally:
        os.chdir(cwd)
    return mod


def load_categories():
    text = (STUDY / "scripts" / "config" / "category_subset.yaml").read_text()
    cats = []
    in_block = False
    for line in text.splitlines():
        if line.startswith("categories:"):
            in_block = True
            continue
        if in_block:
            if line.startswith("  - name: "):
                cats.append(line.split("  - name: ", 1)[1].strip())
            elif line and not line.startswith(" "):
                break
    return cats


def load_split(name):
    return [l.strip() for l in (SPLITS / f"{name}.txt").read_text().splitlines() if l.strip()]


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


def pr(ev, gt, preds):
    tp = fp = fn = 0
    for key in gt:
        answers, ps = gt[key], preds[key]
        if len(answers) == 0:
            fp += len(ps)
            continue
        for ans in answers:
            if any(ev.get_jaccard(ans, p) >= ev.IOU_THRESH for p in ps):
                tp += 1
            else:
                fn += 1
        for p in ps:
            if not any(ev.get_jaccard(ans, p) >= ev.IOU_THRESH for ans in answers):
                fp += 1
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall}


def check_against_upstream(ev, gt, preds):
    p, r = ev.compute_precision_recall(gt, preds)
    return float(p), float(r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(STUDY / "data" / "cuad-baseline" / "c2c3_cuad_scored.json"))
    args = ap.parse_args()

    ev = load_upstream_evaluate()
    categories = load_categories()
    harness_val = set(load_split("harness_val"))

    cuad = json.load(open(RAW / "CUADv1.json"))
    cuad = {"data": [c for c in cuad["data"] if c["title"] in harness_val]}
    assert len(cuad["data"]) == len(harness_val)
    gold_all = ev.get_answers(cuad)
    gold = {k: v for k, v in gold_all.items() if k.rsplit("__", 1)[-1] in categories}
    assert len(gold) == len(harness_val) * len(categories), (len(gold), len(harness_val), len(categories))

    trials, decisions = load_rows()
    scored = {tid: t for tid, t in trials.items() if t["outcome"] == "ok"}

    by_cond_contract = defaultdict(set)
    for t in scored.values():
        by_cond_contract[t["condition"]].add(t["contract_id"])
    intersection = sorted(by_cond_contract["C2"] & by_cond_contract["C3"])

    def build(cond, contracts, seeds=None):
        gt, preds = {}, {}
        n_trials = 0
        for tid, t in sorted(scored.items()):
            if t["condition"] != cond or t["contract_id"] not in contracts:
                continue
            if seeds is not None and t["seed"] not in seeds:
                continue
            n_trials += 1
            for d in decisions[tid]:
                key = f"{t['contract_id']}__{d['target']}#{tid}"
                gold_key = f"{t['contract_id']}__{d['target']}"
                gt[key] = gold[gold_key]
                spans = d["predicted"]["spans"] if d["decision_kind"] == "extraction" else []
                preds[key] = [s for s in (spans or []) if s]
        return gt, preds, n_trials

    results = {
        "gold_source": "data/raw/CUADv1.json via upstream evaluate.get_answers",
        "scorer": "data/raw/evaluate.py (unmodified import; compute_precision_recall / get_jaccard, IOU_THRESH=0.5)",
        "split": "harness_val",
        "split_provenance": "carved from CUAD's official TRAIN split; NOT their test split",
        "n_contracts_split": len(harness_val),
        "categories": categories,
        "n_gold_questions_split": len(gold),
        "intersection_contracts": intersection,
        "n_intersection": len(intersection),
        "conditions": {},
        "per_seed": {},
        "per_category": {},
        "pooled_all_scored": {},
    }

    for cond in ("C2", "C3"):
        gt, preds, n = build(cond, set(intersection))
        point = pr(ev, gt, preds)
        up_p, up_r = check_against_upstream(ev, gt, preds)
        point["upstream_agrees"] = (abs(up_p - point["precision"]) < 1e-12
                                    and abs(up_r - point["recall"]) < 1e-12)
        point["n_trials"] = n
        point["n_questions"] = len(gt)
        results["conditions"][cond] = point

        gt_a, preds_a, n_a = build(cond, by_cond_contract[cond])
        pa = pr(ev, gt_a, preds_a)
        pa["n_trials"] = n_a
        pa["n_questions"] = len(gt_a)
        pa["n_contracts"] = len(by_cond_contract[cond])
        results["pooled_all_scored"][cond] = pa

        results["per_seed"][cond] = {}
        for seed in (0, 1, 2):
            gs, ps, ns = build(cond, set(intersection), seeds={seed})
            pt = pr(ev, gs, ps)
            pt["n_trials"] = ns
            results["per_seed"][cond][str(seed)] = pt

        results["per_category"][cond] = {}
        for cat in categories:
            gc = {k: v for k, v in gt.items() if k.split("#", 1)[0].rsplit("__", 1)[-1] == cat}
            pc = {k: preds[k] for k in gc}
            results["per_category"][cond][cat] = pr(ev, gc, pc)

    gold_present = sum(1 for v in gold.values() if v)
    results["gold_profile"] = {
        "questions": len(gold),
        "with_gold_spans": gold_present,
        "empty": len(gold) - gold_present,
        "total_gold_spans": sum(len(v) for v in gold.values()),
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps({c: {k: v for k, v in results["conditions"][c].items()} for c in ("C2", "C3")}, indent=2))


if __name__ == "__main__":
    main()
