import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[1])))
import evaluate as ev

gt = ev.get_answers(json.loads(Path(sys.argv[2]).read_text()))
out = Path(sys.argv[3])
pred = json.loads((out / "nbest_predictions_.json").read_text())

assert sorted(gt.keys()) == sorted(pred.keys()), "question id mismatch"

precisions, recalls, confs = ev.get_precisions_recalls(pred, gt)
p80, _ = ev.get_prec_at_recall(precisions, recalls, confs, recall_thresh=0.8)
p90, _ = ev.get_prec_at_recall(precisions, recalls, confs, recall_thresh=0.9)
res = {
    "model": out.name,
    "questions": len(gt),
    "aupr": round(ev.get_aupr(precisions, recalls), 4),
    "prec_at_80_recall": round(p80, 4),
    "prec_at_90_recall": round(p90, 4),
    "max_recall": round(max(recalls), 4),
}

cats = sorted({k.rsplit("__", 1)[-1] for k in gt})
res["per_category"] = {}
for c in cats:
    ps, rs, cs = ev.get_precisions_recalls(pred, gt, category=c)
    res["per_category"][c] = {
        "aupr": round(ev.get_aupr(ps, rs), 4),
        "max_recall": round(max(rs), 4),
    }
    n_sub = sum(1 for k in gt if c in k)
    n_exact = sum(1 for k in gt if k.rsplit("__", 1)[-1] == c)
    if n_sub != n_exact:
        res["per_category"][c]["substring_filter_leak"] = [n_exact, n_sub]

print(json.dumps(res, indent=2))
