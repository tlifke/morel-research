import argparse
import csv
import json
import sys
from pathlib import Path

PUBLISHED = {
    "roberta-base": {"aupr": 42.6, "p80": 31.1, "p90": 0.0},
    "roberta-large": {"aupr": 48.2, "p80": 38.1, "p90": 0.0},
    "deberta-v2-xlarge": {"aupr": 47.8, "p80": 44.0, "p90": 17.8},
}


def subset(d, category):
    return {k: v for k, v in d.items() if k.rsplit("__", 1)[-1] == category}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--gold", required=True)
    ap.add_argument("--ckpt-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--models", nargs="+", default=list(PUBLISHED))
    ap.add_argument("--per-category", action="store_true")
    args = ap.parse_args()

    sys.path.insert(0, args.repo)
    import evaluate as ev

    gold_path = Path(args.gold)
    assert gold_path.name == "test.json", "reproduction scores the authors' released test gold"
    gt = ev.get_answers(json.loads(gold_path.read_text()))

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    summary = {"gold": str(gold_path), "n_questions": len(gt), "models": {}}

    for name in args.models:
        pred_path = Path(args.ckpt_root) / name / "nbest_predictions_.json"
        pred = json.loads(pred_path.read_text())
        keys_match = sorted(pred.keys()) == sorted(gt.keys())

        precisions, recalls, confs = ev.get_precisions_recalls(pred, gt)
        p80, conf80 = ev.get_prec_at_recall(precisions, recalls, confs, recall_thresh=0.8)
        p90, conf90 = ev.get_prec_at_recall(precisions, recalls, confs, recall_thresh=0.9)
        aupr = ev.get_aupr(precisions, recalls)
        interp = ev.process_precisions(list(precisions))

        with (outdir / f"pr_curve_{name}.csv").open("w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["conf", "precision", "recall", "interpolated_precision"])
            for i, (p, r, ip) in enumerate(zip(precisions, recalls, interp)):
                c = "" if i == 0 else confs[i - 1]
                w.writerow([c, p, r, ip])

        pub = PUBLISHED[name]
        rec = {
            "n_pred_keys": len(pred),
            "keys_match_gold": keys_match,
            "aupr": aupr,
            "prec_at_80_recall": p80,
            "prec_at_90_recall": p90,
            "published": pub,
            "delta_aupr": round(aupr * 100 - pub["aupr"], 2),
            "delta_p80": round(p80 * 100 - pub["p80"], 2),
            "delta_p90": round(p90 * 100 - pub["p90"], 2),
            "max_recall": max(recalls),
            "conf_at_80_recall_reported": conf80,
            "conf_at_90_recall_reported": conf90,
            "curve_points": len(precisions),
            "curve_csv": f"pr_curve_{name}.csv",
        }

        for thresh in (0.8, 0.9):
            for i, (r, p) in enumerate(zip(recalls, interp)):
                if r >= thresh:
                    rec[f"operating_point_at_{int(thresh * 100)}_recall"] = {
                        "conf": confs[i - 1] if i > 0 else None,
                        "recall": r,
                        "raw_precision": precisions[i],
                        "interpolated_precision": p,
                    }
                    break

        if args.per_category:
            cats = sorted({k.rsplit("__", 1)[-1] for k in gt})
            percat = {}
            for c in cats:
                g, pr = subset(gt, c), subset(pred, c)
                ps, rs, cs = ev.get_precisions_recalls(pr, g)
                cp80, _ = ev.get_prec_at_recall(ps, rs, cs, recall_thresh=0.8)
                percat[c] = {
                    "n_questions": len(g),
                    "n_substring_matches": sum(1 for k in gt if c in k),
                    "aupr": ev.get_aupr(ps, rs),
                    "prec_at_80_recall": cp80,
                    "max_recall": max(rs),
                }
            rec["per_category"] = percat

        summary["models"][name] = rec
        print(json.dumps({name: {k: v for k, v in rec.items() if k != "per_category"}}, indent=2), flush=True)

    (outdir / "table2_reproduction.json").write_text(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
