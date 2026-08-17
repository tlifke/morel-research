import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parents[2]
RAW = STUDY / "data" / "raw"
SPLITS = STUDY / "data" / "processed" / "splits"
CATS = STUDY / "data" / "processed" / "categories.json"

sys.path.insert(0, str(Path(__file__).parent))
import expiration_taxonomy as tax

MODELS = ["roberta-base", "roberta-large", "deberta-v2-xlarge"]
CONFS = [0.0, 0.1, 0.3, 0.5, 0.7, 0.9]


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


def load_split(name):
    if name == "test":
        raise SystemExit("test split is sealed until G4")
    return [
        l.strip()
        for l in SPLITS.joinpath(name + ".txt").read_text().splitlines()
        if l.strip()
    ]


def merge_nbest(preds_root, model, split):
    merged = {}
    for shard in sorted((preds_root / model).glob(f"{split}_g*")):
        f = shard / "nbest_predictions_.json"
        d = json.loads(f.read_text())
        overlap = set(d) & set(merged)
        assert not overlap, sorted(overlap)[:3]
        merged.update(d)
    return merged


def point_pr(ev, gt, preds):
    tp = fp = fn = 0
    fp_absent = fp_present = 0
    q_present = q_absent = 0
    declined_present = claimed_absent = 0
    for key in gt:
        answers, ps = gt[key], preds[key]
        if len(answers) == 0:
            q_absent += 1
            fp += len(ps)
            fp_absent += len(ps)
            claimed_absent += int(len(ps) > 0)
            continue
        q_present += 1
        declined_present += int(len(ps) == 0)
        for ans in answers:
            if any(ev.get_jaccard(ans, p) >= ev.IOU_THRESH for p in ps):
                tp += 1
            else:
                fn += 1
        for p in ps:
            if not any(ev.get_jaccard(ans, p) >= ev.IOU_THRESH for ans in answers):
                fp += 1
                fp_present += 1
    prec = tp / (tp + fp) if tp + fp else None
    rec = tp / (tp + fn) if tp + fn else None
    return {
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": prec,
        "recall": rec,
        "fp_on_gold_absent_questions": fp_absent,
        "fp_on_gold_present_questions": fp_present,
        "questions_gold_present": q_present,
        "questions_gold_absent": q_absent,
        "gold_present_questions_with_no_prediction": declined_present,
        "gold_absent_questions_with_a_prediction": claimed_absent,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--preds-root", required=True)
    ap.add_argument("--splits", nargs="+", default=["harness_val", "principle_train"])
    ap.add_argument("--headline-conf", type=float, default=0.5)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    ev = load_upstream_evaluate()
    subset = json.loads(CATS.read_text())["subset"]
    raw = json.loads((RAW / "CUADv1.json").read_text())
    by_title = {d["title"]: d for d in raw["data"]}
    preds_root = Path(args.preds_root)

    tax_rows = tax.build(args.splits)
    tax_by_qid = {}
    for r in tax_rows:
        tax_by_qid.setdefault(r["qid"], {})[r["span_index"]] = r

    results = {
        "provenance": {
            "gold": "data/raw/CUADv1.json via upstream evaluate.get_answers",
            "scorer": "data/raw/evaluate.py, unmodified import (get_jaccard, IOU_THRESH=0.5)",
            "splits": args.splits,
            "split_provenance": "both carved from CUAD's official TRAIN split; these "
            "contracts are inside the released checkpoints' fine-tuning data",
            "categories": subset,
            "headline_conf": args.headline_conf,
            "conf_sweep": CONFS,
        },
        "by_split": {},
    }

    for split in args.splits:
        members = load_split(split)
        data = {"data": [by_title[t] for t in members]}
        gold_all = ev.get_answers(data)
        gold = {k: v for k, v in gold_all.items() if k.rsplit("__", 1)[-1] in subset}
        assert len(gold) == len(members) * len(subset), len(gold)

        split_res = {
            "n_contracts": len(members),
            "n_questions": len(gold),
            "gold_present_questions": sum(1 for v in gold.values() if v),
            "gold_spans": sum(len(v) for v in gold.values()),
            "models": {},
        }

        for model in MODELS:
            nbest = merge_nbest(preds_root, model, split)
            assert sorted(nbest.keys()) == sorted(gold.keys()), "question id mismatch"

            precisions, recalls, confs = ev.get_precisions_recalls(nbest, gold)
            p80, _ = ev.get_prec_at_recall(precisions, recalls, confs, recall_thresh=0.8)
            p90, _ = ev.get_prec_at_recall(precisions, recalls, confs, recall_thresh=0.9)
            m = {
                "curve": {
                    "aupr": round(ev.get_aupr(precisions, recalls), 4),
                    "prec_at_80_recall": round(float(p80), 4),
                    "prec_at_90_recall": round(float(p90), 4),
                    "max_recall": round(float(max(recalls)), 4),
                },
                "conf_sweep": {},
                "per_category": {},
                "expiration_taxonomy": {},
            }

            for c in CONFS:
                p = ev.get_preds(nbest, conf=c)
                m["conf_sweep"][str(c)] = point_pr(ev, gold, p)

            m["per_category_by_conf"] = {}
            for c in CONFS:
                pc_all = ev.get_preds(nbest, conf=c)
                m["per_category_by_conf"][str(c)] = {
                    cat: point_pr(
                        ev,
                        {k: v for k, v in gold.items() if k.rsplit("__", 1)[-1] == cat},
                        pc_all,
                    )
                    for cat in subset
                }
            m["per_category"] = json.loads(
                json.dumps(m["per_category_by_conf"][str(args.headline_conf)])
            )
            for cat in subset:
                ps, rs, cs = ev.get_precisions_recalls(nbest, gold, category=cat)
                m["per_category"][cat]["aupr"] = round(ev.get_aupr(ps, rs), 4)
                m["per_category"][cat]["max_recall"] = round(float(max(rs)), 4)

            for c in CONFS:
                pc = ev.get_preds(nbest, conf=c)
                bucket = {}
                for qid, spans in tax_by_qid.items():
                    if qid not in gold:
                        continue
                    for i, ans in enumerate(gold[qid]):
                        row = spans.get(i)
                        if row is None:
                            continue
                        hit = any(
                            ev.get_jaccard(ans, p) >= ev.IOU_THRESH for p in pc[qid]
                        )
                        present = len(pc[qid]) > 0
                        keys = [row["class"]]
                        if row["class"] == "calendar_date":
                            keys.append(
                                "calendar_terminal"
                                if row["terminal_date"]
                                else "calendar_start_only"
                            )
                        for key in keys:
                            b = bucket.setdefault(
                                key,
                                {"gold_spans": 0, "matched": 0, "claimed_present": 0},
                            )
                            b["gold_spans"] += 1
                            b["matched"] += int(hit)
                            b["claimed_present"] += int(present)
                for k, v in bucket.items():
                    v["span_iou_recall"] = round(v["matched"] / v["gold_spans"], 4)
                    v["presence_recall"] = round(
                        v["claimed_present"] / v["gold_spans"], 4
                    )
                exp_fp = 0
                for qid in gold:
                    if qid.rsplit("__", 1)[-1] != "Expiration Date":
                        continue
                    if not gold[qid]:
                        exp_fp += len(pc[qid])
                        continue
                    for p in pc[qid]:
                        if not any(
                            ev.get_jaccard(a, p) >= ev.IOU_THRESH for a in gold[qid]
                        ):
                            exp_fp += 1
                bucket["_false_positives_all_expiration"] = exp_fp
                m["expiration_taxonomy"][str(c)] = bucket

            split_res["models"][model] = m

        results["by_split"][split] = split_res

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(results, indent=2) + "\n")
    for split in args.splits:
        for model in MODELS:
            m = results["by_split"][split]["models"][model]
            print(
                split,
                model,
                m["curve"],
                "@conf%.1f" % args.headline_conf,
                {
                    k: round(v, 4) if isinstance(v, float) else v
                    for k, v in m["conf_sweep"][str(args.headline_conf)].items()
                },
            )


if __name__ == "__main__":
    main()
