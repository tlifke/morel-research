"""Small classifier + conditioned-correlation analysis."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).parent
ROWS = [json.loads(l) for l in open(HERE / "_rows.jsonl")]


def spearman(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    rx = _rank(xs); ry = _rank(ys)
    mx = sum(rx)/n; my = sum(ry)/n
    num = sum((a-mx)*(b-my) for a,b in zip(rx,ry))
    dx = sum((a-mx)**2 for a in rx)**0.5
    dy = sum((b-my)**2 for b in ry)**0.5
    if dx==0 or dy==0: return 0.0
    return num/(dx*dy)


def _rank(xs):
    idx = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0]*len(xs)
    i=0
    while i<len(xs):
        j=i
        while j+1<len(xs) and xs[idx[j+1]]==xs[idx[i]]:
            j+=1
        avg=(i+j)/2+1
        for k in range(i,j+1): ranks[idx[k]]=avg
        i=j+1
    return ranks


NUMERIC = [
    "curator_difficulty_ord","frequency_ord","feasibility_ord",
    "register_length_ord","pair_type_A","expected_tool_call",
    "prompt_length_words","prompt_length_chars",
    "has_first_person","has_temporal_word","has_date_or_year",
    "has_num_operator","num_count","has_tool_name_keyword",
    "has_compute_verb","has_convert_verb","has_today_now",
    "has_question_mark","has_declared_fact",
    "cond_warranted","cond_trivial","cond_none",
]


def conditioned_corr(rows, model, splitter_feat, value):
    sub = [r for r in rows if r["model"]==model and r[splitter_feat]==value]
    if len(sub)<5: return None, len(sub)
    ys = [r["success_rate"] for r in sub]
    out=[]
    for f in NUMERIC:
        if f==splitter_feat: continue
        xs=[r[f] for r in sub]
        rho = spearman(xs,ys)
        out.append((f,rho,len(sub)))
    return sorted(out, key=lambda x: -abs(x[1] or 0)), len(sub)


def main():
    print("=" * 70)
    print("CONDITIONED ON expected_tool_call (4B)")
    print("=" * 70)
    for v,label in [(1,"warranted"),(0,"no-call expected")]:
        res,n = conditioned_corr(ROWS,"4B","expected_tool_call",v)
        print(f"\n-- 4B, expected_tool_call={v} ({label}, n={n}) --")
        if not res: continue
        for f,rho,_ in res[:10]:
            if rho is None: continue
            print(f"  {f:30s} rho={rho:+.3f}")

    print("\n" + "=" * 70)
    print("CONDITIONED ON expected_tool_call (12B)")
    print("=" * 70)
    for v,label in [(1,"warranted"),(0,"no-call expected")]:
        res,n = conditioned_corr(ROWS,"12B","expected_tool_call",v)
        print(f"\n-- 12B, expected_tool_call={v} ({label}, n={n}) --")
        if not res: continue
        for f,rho,_ in res[:10]:
            if rho is None: continue
            print(f"  {f:30s} rho={rho:+.3f}")

    print("\n" + "=" * 70)
    print("PER-TOOL within expected_tool_call=True (4B)")
    print("=" * 70)
    sub = [r for r in ROWS if r["model"]=="4B" and r["expected_tool_call"]==1]
    by_tool={}
    for r in sub: by_tool.setdefault(r["tool_target"],[]).append(r)
    for t,rs in sorted(by_tool.items()):
        if len(rs)<5: continue
        ys=[r["success_rate"] for r in rs]
        print(f"\n  Tool {t} (n={len(rs)}, mean_sr={sum(ys)/len(ys):.3f})")
        scored=[]
        for f in NUMERIC:
            if f=="expected_tool_call": continue
            xs=[r[f] for r in rs]
            rho=spearman(xs,ys)
            if rho is None: continue
            scored.append((f,rho))
        for f,rho in sorted(scored,key=lambda x:-abs(x[1]))[:6]:
            print(f"    {f:30s} rho={rho:+.3f}")

    # Classifier
    try:
        from sklearn.linear_model import LogisticRegression
        from sklearn.tree import DecisionTreeClassifier
        from sklearn.model_selection import cross_val_score, LeaveOneOut
        import numpy as np
    except ImportError:
        print("\n(sklearn unavailable)")
        return

    print("\n" + "=" * 70)
    print("CLASSIFIER: predict success_rate >= 0.7 (per-record, 4B)")
    print("=" * 70)
    sub = [r for r in ROWS if r["model"]=="4B"]
    # Use a curated feature set; small, interpretable.
    feats = [
        "expected_tool_call","curator_difficulty_ord",
        "has_tool_name_keyword","has_compute_verb","has_first_person",
        "has_today_now","has_date_or_year","num_count",
        "cond_warranted","cond_none",
    ]
    X = np.array([[r[f] for f in feats] for r in sub])
    y = np.array([1 if r["success_rate"]>=0.7 else 0 for r in sub])
    print(f"  n={len(y)}, positive rate={y.mean():.3f}")

    for name, clf in [
        ("LogReg", LogisticRegression(max_iter=2000)),
        ("DTree(d=3)", DecisionTreeClassifier(max_depth=3, random_state=0)),
        ("DTree(d=5)", DecisionTreeClassifier(max_depth=5, random_state=0)),
    ]:
        scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
        print(f"  {name:12s} 5-fold acc: mean={scores.mean():.3f}  std={scores.std():.3f}")

    # Curator-only baseline
    Xb = np.array([[r["curator_difficulty_ord"]] for r in sub])
    scores = cross_val_score(LogisticRegression(max_iter=2000), Xb, y, cv=5, scoring="accuracy")
    print(f"  Baseline (curator only):       mean={scores.mean():.3f}  std={scores.std():.3f}")

    # Fit a small tree and print its rules
    from sklearn.tree import export_text
    dt = DecisionTreeClassifier(max_depth=3, random_state=0).fit(X,y)
    print("\n  DecisionTree(d=3) rules:")
    print(export_text(dt, feature_names=feats))

    # Same for 12B (smaller)
    print("=" * 70)
    print("CLASSIFIER: predict success_rate >= 0.7 (per-record, 12B)")
    print("=" * 70)
    sub = [r for r in ROWS if r["model"]=="12B"]
    X = np.array([[r[f] for f in feats] for r in sub])
    y = np.array([1 if r["success_rate"]>=0.7 else 0 for r in sub])
    print(f"  n={len(y)}, positive rate={y.mean():.3f}")
    for name, clf in [
        ("LogReg", LogisticRegression(max_iter=2000)),
        ("DTree(d=3)", DecisionTreeClassifier(max_depth=3, random_state=0)),
    ]:
        scores = cross_val_score(clf, X, y, cv=5, scoring="accuracy")
        print(f"  {name:12s} 5-fold acc: mean={scores.mean():.3f}  std={scores.std():.3f}")

    Xb = np.array([[r["curator_difficulty_ord"]] for r in sub])
    scores = cross_val_score(LogisticRegression(max_iter=2000), Xb, y, cv=5, scoring="accuracy")
    print(f"  Baseline (curator only):       mean={scores.mean():.3f}  std={scores.std():.3f}")


if __name__=="__main__":
    main()
