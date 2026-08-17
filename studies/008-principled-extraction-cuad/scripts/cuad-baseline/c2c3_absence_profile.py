import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(STUDY / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

import score_c2c3_with_cuad_evaluator as base
import score_split_runs as sp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ev = base.load_upstream_evaluate()
    cats = base.load_categories()
    harness_val = set(base.load_split("harness_val"))

    cuad = json.loads((STUDY / "data" / "raw" / "CUADv1.json").read_text())
    cuad = {"data": [c for c in cuad["data"] if c["title"] in harness_val]}
    gold_all = ev.get_answers(cuad)
    gold = {k: v for k, v in gold_all.items() if k.rsplit("__", 1)[-1] in cats}

    trials, decisions = base.load_rows()
    scored = {t: v for t, v in trials.items() if v["outcome"] == "ok"}
    by_cond = defaultdict(set)
    for t in scored.values():
        by_cond[t["condition"]].add(t["contract_id"])
    intersection = by_cond["C2"] & by_cond["C3"]

    out = {
        "note": "C2/C3 harness_val, contract intersection, same scorer as "
        "score_split_runs.point_pr (upstream get_jaccard, IOU 0.5)",
        "conditions": {},
    }
    for cond in ("C2", "C3"):
        gt, preds = {}, {}
        for tid, t in sorted(scored.items()):
            if t["condition"] != cond or t["contract_id"] not in intersection:
                continue
            for d in decisions[tid]:
                key = f"{t['contract_id']}__{d['target']}#{tid}"
                gt[key] = gold[f"{t['contract_id']}__{d['target']}"]
                spans = d["predicted"]["spans"] if d["decision_kind"] == "extraction" else []
                preds[key] = [x for x in (spans or []) if x]
        entry = {"pooled": sp.point_pr(ev, gt, preds), "per_category": {}}
        for cat in cats:
            gc = {
                k: v
                for k, v in gt.items()
                if k.split("#", 1)[0].rsplit("__", 1)[-1] == cat
            }
            entry["per_category"][cat] = sp.point_pr(ev, gc, {k: preds[k] for k in gc})
        out["conditions"][cond] = entry

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2) + "\n")
    for cond in ("C2", "C3"):
        print(cond, json.dumps(out["conditions"][cond]["pooled"]))


if __name__ == "__main__":
    main()
