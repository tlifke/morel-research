import argparse
import json
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

MODELS = ["roberta-base", "roberta-large", "deberta-v2-xlarge"]
DEPTHS = [1, 2, 3, 5, 8, 10, 20]
DUP_THRESH = 0.8


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--gold", required=True)
    ap.add_argument("--ckpt-root", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--models", nargs="+", default=MODELS)
    args = ap.parse_args()

    sys.path.insert(0, args.repo)
    import evaluate as ev

    raw_jaccard = ev.get_jaccard

    @lru_cache(maxsize=None)
    def cached_jaccard(gt, pred):
        return raw_jaccard(gt, pred)

    ev.get_jaccard = cached_jaccard

    gold_path = Path(args.gold)
    assert gold_path.name == "test.json"
    gt = ev.get_answers(json.loads(gold_path.read_text()))

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    summary = {"dup_thresh": DUP_THRESH, "depths": DEPTHS, "models": {}}

    for name in args.models:
        nbest = json.loads((Path(args.ckpt_root) / name / "nbest_predictions_.json").read_text())
        nonempty = {k: [d for d in v if d["text"] != ""] for k, v in nbest.items()}

        dedup = {}
        cluster_counts = []
        for k, cands in nonempty.items():
            kept = []
            for d in cands:
                if all(cached_jaccard(d["text"], e["text"]) < DUP_THRESH for e in kept):
                    kept.append(d)
            dedup[k] = kept
            cluster_counts.append(len(kept))

        span_cum = {}
        for depth in DEPTHS:
            hits = 0
            total = 0
            for k, answers in gt.items():
                if not answers:
                    continue
                substr_ok = "Parties" in k
                preds = [d["text"] for d in dedup[k][:depth]]
                for ans in answers:
                    total += 1
                    if any(
                        cached_jaccard(ans, p) >= ev.IOU_THRESH or (substr_ok and ans in p)
                        for p in preds
                    ):
                        hits += 1
            span_cum[depth] = {"hits": hits, "total": total, "frac": hits / total}

        curves = {}
        for depth in DEPTHS:
            trunc = {k: v[:depth] for k, v in dedup.items()}
            ps, rs, cs = ev.get_precisions_recalls(trunc, gt)
            p80, _ = ev.get_prec_at_recall(ps, rs, cs, recall_thresh=0.8)
            p90, _ = ev.get_prec_at_recall(ps, rs, cs, recall_thresh=0.9)
            curves[depth] = {
                "aupr": ev.get_aupr(ps, rs),
                "prec_at_80_recall": p80,
                "prec_at_90_recall": p90,
                "max_recall": max(rs),
            }
            print(name, "dedup", depth, json.dumps(curves[depth]), flush=True)

        summary["models"][name] = {
            "mean_clusters_per_question": sum(cluster_counts) / len(cluster_counts),
            "cluster_count_hist": dict(sorted(Counter(cluster_counts).items())),
            "dedup_span_recall_by_depth": span_cum,
            "dedup_curves_by_depth": curves,
        }

    (outdir / "nbest_dedup_depth.json").write_text(json.dumps(summary, indent=2))
    print("wrote", outdir / "nbest_dedup_depth.json")


if __name__ == "__main__":
    main()
