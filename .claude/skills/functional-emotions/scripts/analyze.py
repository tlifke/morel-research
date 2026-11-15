"""Analysis helpers for steering / harness outputs.

  rates        behaviour rate +/- SEM by (direction, strength[, task]) for any boolean or
               label field. E.g. --field hack, or --field judge_sycophancy --positive mild strong
  correlate    does probe activation PREDICT behaviour in unsteered rollouts?
               Uses the harness `trace` (per-token scores + roles + assistant colons).
               Reports, per emotion, the point-biserial r between behaviour and
               (a) first-turn assistant-colon score (fixed per task: prompt-level signal),
               (b) mean score over assistant tokens, (c) mean score over the last 3 colons,
               after z-scoring every score against all traced tokens in the file
               (the paper z-scored against >6,000 reference transcripts).
  trace-html   paper-style token heatmap (red = up, blue = down, scaled so +/-1 = the
               99th percentile |score| on that transcript) for one record.

  python analyze.py rates --inp runs/m/rh.jsonl --field hack --by task
  python analyze.py correlate --inp runs/m/rh_baseline.jsonl --field hack
  python analyze.py trace-html --inp runs/m/rh.jsonl --index 3 --emotion desperate --out t.html
"""

from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

import emo_lib as E


def is_pos(r, field, positive):
    v = r.get(field)
    return bool(v) if not positive else v in positive


def cmd_rates(args):
    recs = E.read_jsonl(args.inp)
    groups = defaultdict(list)
    for r in recs:
        k = tuple(r.get(b) for b in (["direction", "strength"] + (args.by or [])))
        groups[k].append(is_pos(r, args.field, args.positive))
    rows = []
    for k in sorted(groups, key=lambda k: tuple(str(x) for x in k)):
        x = np.array(groups[k], float)
        sem = x.std(ddof=1) / np.sqrt(len(x)) if len(x) > 1 else float("nan")
        rows.append({"key": k, "n": len(x), "rate": x.mean(), "sem": sem})
        print(f"{str(k):<50} n={len(x):<4} rate={x.mean():.3f} +/- {sem:.3f}")
    return rows


def cmd_correlate(args):
    recs = [r for r in E.read_jsonl(args.inp) if "trace" in r and r.get("strength", 0) == 0]
    if not recs:
        raise SystemExit("no unsteered records with traces (run rh_harness.py --strengths 0 --trace ...)")
    emotions = recs[0]["trace"]["emotions"]
    allS = np.concatenate([np.array(r["trace"]["scores"]) for r in recs])
    mu, sd = allS.mean(0), allS.std(0) + 1e-8
    y = np.array([is_pos(r, args.field, args.positive) for r in recs], float)
    feats = defaultdict(list)
    for r in recs:
        S = (np.array(r["trace"]["scores"]) - mu) / sd
        roles = np.array(r["trace"]["roles"])
        col = r["trace"]["assistant_colons"]
        feats["first_colon"].append(S[col[0]] if col else np.full(len(emotions), np.nan))
        feats["assistant_mean"].append(S[roles == "assistant"].mean(0))
        feats["last3_colons"].append(S[col[-3:]].mean(0) if col else np.full(len(emotions), np.nan))
    out = {}
    print(f"n={len(recs)} unsteered rollouts, base rate {y.mean():.3f}")
    for name, F in feats.items():
        F = np.array(F)
        out[name] = {}
        for j, e in enumerate(emotions):
            ok = ~np.isnan(F[:, j])
            r = np.corrcoef(F[ok, j], y[ok])[0, 1] if y[ok].std() > 0 else float("nan")
            out[name][e] = float(r)
        print(f"{name:<15} " + "  ".join(f"{e}: r={v:+.2f}" for e, v in out[name].items()))
    return out


def cmd_trace_html(args):
    r = E.read_jsonl(args.inp)[args.index]
    t = r["trace"]
    j = t["emotions"].index(args.emotion)
    s = np.array(t["scores"])[:, j]
    s = s - np.median(s)
    scale = np.percentile(np.abs(s), 99) + 1e-8
    spans = []
    for tokstr, v in zip(t["tokens"], s):
        x = float(np.clip(v / scale, -1, 1))
        color = f"rgba(214,39,40,{x:.2f})" if x > 0 else f"rgba(31,119,180,{-x:.2f})"
        text = html.escape(tokstr.replace("Ġ", " ").replace("▁", " ").replace("Ċ", "\n"))
        spans.append(f'<span title="{v:+.3f}" style="background:{color}">{text}</span>')
    page = (f"<!doctype html><meta charset=utf-8><title>{html.escape(args.emotion)} trace</title>"
            f"<body style='font:13px/1.5 monospace;white-space:pre-wrap;max-width:1000px;margin:2em auto'>"
            f"<h3>{html.escape(args.emotion)} | task={r.get('task')} | label={r.get('label')} | "
            f"direction={r.get('direction')} strength={r.get('strength')}</h3>" + "".join(spans))
    Path(args.out).write_text(page)
    print(f"wrote {args.out}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["rates", "correlate", "trace-html"])
    ap.add_argument("--inp", required=True)
    ap.add_argument("--field", default="hack")
    ap.add_argument("--positive", nargs="*", help="label values counted as positive (default: truthiness)")
    ap.add_argument("--by", nargs="*", help="extra grouping fields, e.g. task")
    ap.add_argument("--index", type=int, default=0)
    ap.add_argument("--emotion", default="desperate")
    ap.add_argument("--out")
    args = ap.parse_args()
    res = {"rates": cmd_rates, "correlate": cmd_correlate, "trace-html": cmd_trace_html}[args.cmd](args)
    if args.out and args.cmd != "trace-html":
        Path(args.out).write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
