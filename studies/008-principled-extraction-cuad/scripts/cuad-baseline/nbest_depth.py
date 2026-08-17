import argparse
import json
import sys
from collections import Counter
from functools import lru_cache
from pathlib import Path

MODELS = ["roberta-base", "roberta-large", "deberta-v2-xlarge"]
DEPTHS = [1, 2, 3, 5, 10, 20]
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
    summary = {"gold": str(gold_path), "n_questions": len(gt), "depths": DEPTHS, "models": {}}

    for name in args.models:
        pred_path = Path(args.ckpt_root) / name / "nbest_predictions_.json"
        nbest = json.loads(pred_path.read_text())
        assert sorted(nbest.keys()) == sorted(gt.keys())

        nonempty = {k: [d for d in v if d["text"] != ""] for k, v in nbest.items()}

        list_lens = Counter(len(v) for v in nbest.values())
        nonempty_lens = Counter(len(v) for v in nonempty.values())

        rank_of_first_correct = {}
        for k, answers in gt.items():
            if not answers:
                continue
            substr_ok = "Parties" in k
            hit = None
            for i, d in enumerate(nonempty[k]):
                pred = d["text"]
                for ans in answers:
                    m = cached_jaccard(ans, pred) >= ev.IOU_THRESH or (substr_ok and ans in pred)
                    if m:
                        hit = i + 1
                        break
                if hit:
                    break
            rank_of_first_correct[k] = hit

        with_gold = list(rank_of_first_correct)
        recoverable = [k for k in with_gold if rank_of_first_correct[k]]
        rank_hist = Counter(rank_of_first_correct[k] for k in recoverable)
        cum = {}
        for d in DEPTHS:
            cum[d] = sum(v for r, v in rank_hist.items() if r <= d)

        gold_span_ranks = []
        for k, answers in gt.items():
            if not answers:
                continue
            substr_ok = "Parties" in k
            for ans in answers:
                hit = None
                for i, d in enumerate(nonempty[k]):
                    pred = d["text"]
                    if cached_jaccard(ans, pred) >= ev.IOU_THRESH or (substr_ok and ans in pred):
                        hit = i + 1
                        break
                gold_span_ranks.append(hit)
        span_hist = Counter(r for r in gold_span_ranks if r)
        span_cum = {d: sum(v for r, v in span_hist.items() if r <= d) for d in DEPTHS}

        dup_num, dup_den, exact_num = 0, 0, 0
        per_q_dup = []
        for k, cands in nonempty.items():
            texts = [d["text"] for d in cands]
            n = len(texts)
            if n < 2:
                dup_den += n
                continue
            flags = [False] * n
            for i in range(n):
                for j in range(i + 1, n):
                    if cached_jaccard(texts[i], texts[j]) >= DUP_THRESH:
                        flags[i] = flags[j] = True
            dup_num += sum(flags)
            dup_den += n
            exact_num += n - len(set(texts))
            per_q_dup.append(sum(flags) / n)

        curves = {}
        for d in DEPTHS:
            trunc = {k: v[:d] for k, v in nonempty.items()}
            ps, rs, cs = ev.get_precisions_recalls(trunc, gt)
            p80, _ = ev.get_prec_at_recall(ps, rs, cs, recall_thresh=0.8)
            p90, _ = ev.get_prec_at_recall(ps, rs, cs, recall_thresh=0.9)
            curves[d] = {
                "aupr": ev.get_aupr(ps, rs),
                "prec_at_80_recall": p80,
                "prec_at_90_recall": p90,
                "max_recall": max(rs),
            }
            print(name, d, json.dumps(curves[d]), flush=True)

        cats = sorted({k.rsplit("__", 1)[-1] for k in gt})
        percat = {}
        for c in cats:
            ks = [k for k in gt if k.rsplit("__", 1)[-1] == c]
            kg = [k for k in ks if gt[k]]
            rec = [k for k in kg if rank_of_first_correct.get(k)]
            percat[c] = {
                "n_questions": len(ks),
                "n_with_gold": len(kg),
                "n_gold_spans": sum(len(gt[k]) for k in ks),
                "n_recoverable": len(rec),
                "rank1": sum(1 for k in rec if rank_of_first_correct[k] == 1),
                "top3": sum(1 for k in rec if rank_of_first_correct[k] <= 3),
                "top5": sum(1 for k in rec if rank_of_first_correct[k] <= 5),
                "top10": sum(1 for k in rec if rank_of_first_correct[k] <= 10),
            }

        summary["models"][name] = {
            "n_questions": len(nbest),
            "nbest_list_length_hist": dict(sorted(list_lens.items())),
            "nonempty_length_hist": dict(sorted(nonempty_lens.items())),
            "mean_nonempty": sum(len(v) for v in nonempty.values()) / len(nonempty),
            "n_with_gold": len(with_gold),
            "n_recoverable_at_20": len(recoverable),
            "rank_of_first_correct_hist": dict(sorted(rank_hist.items())),
            "cum_recoverable_by_depth": cum,
            "frac_of_recoverable_by_depth": {d: cum[d] / len(recoverable) for d in DEPTHS},
            "frac_of_with_gold_by_depth": {d: cum[d] / len(with_gold) for d in DEPTHS},
            "n_gold_spans": len(gold_span_ranks),
            "n_gold_spans_hit_at_20": sum(1 for r in gold_span_ranks if r),
            "gold_span_rank_hist": dict(sorted(span_hist.items())),
            "gold_spans_cum_by_depth": span_cum,
            "frac_gold_spans_by_depth": {d: span_cum[d] / len(gold_span_ranks) for d in DEPTHS},
            "near_dup_frac": dup_num / dup_den,
            "near_dup_thresh": DUP_THRESH,
            "exact_dup_frac": exact_num / dup_den,
            "mean_per_question_dup_frac": sum(per_q_dup) / len(per_q_dup),
            "curves_by_depth": curves,
            "per_category": percat,
        }

    (outdir / "nbest_depth.json").write_text(json.dumps(summary, indent=2))
    print("wrote", outdir / "nbest_depth.json")


if __name__ == "__main__":
    main()
