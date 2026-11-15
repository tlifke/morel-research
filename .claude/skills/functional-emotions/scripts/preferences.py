"""Activity-preference experiment (paper, "Emotion vectors reflect and influence
self-reported model preferences").

  measure   1. For all ordered pairs of the 64 activities, prompt
               "Would you prefer to (A) {a} or (B) {b}?" with assistant prefill "(" and read
               p(A) vs p(B) from the next-token logits.
            2. Fit Elo scores from those soft outcomes.
            3. For each activity, prompt "How would you feel about {activity}?" and record
               every emotion probe on the activity tokens (mean over the span) at the
               given (middle) layers.
            4. Report corr(probe activation, Elo) per emotion.
               Paper (Sonnet 4.5): blissful r=0.71, hostile r=-0.74.
  steer     Split activities into steered/control halves; steer one emotion at strength
            0.5 (paper) on the steered activities' tokens at middle layers while
            re-running all pairs; report mean Elo change of steered activities.
            Paper: blissful +212, hostile -303; across 35 emotions, steering effect vs
            probe-Elo correlation r=0.85.

Usage:
  python preferences.py measure --model M --vectors V.npz --out runs/m/prefs.json
  python preferences.py steer --model M --vectors V.npz --emotions blissful hostile \
      --strength 0.5 --out runs/m/prefs_steer.json
"""

from __future__ import annotations

import argparse
import itertools
import json
import random
from pathlib import Path

import numpy as np
import torch
import yaml

import emo_lib as E

DATA = Path(__file__).resolve().parent.parent / "data"


def fit_elo(n: int, outcomes: list[tuple[int, int, float]], iters: int = 2000, lr: float = 20.0) -> np.ndarray:
    """Bradley-Terry fit on the Elo scale (400/log10), mean 1500, from soft outcomes
    (i, j, p_i_beats_j). ASSUMPTION: the paper's exact Elo procedure is not stated."""
    r = np.full(n, 1500.0)
    I = np.array([o[0] for o in outcomes])
    J = np.array([o[1] for o in outcomes])
    P = np.array([o[2] for o in outcomes])
    for _ in range(iters):
        exp = 1 / (1 + 10 ** ((r[J] - r[I]) / 400))
        g = np.zeros(n)
        np.add.at(g, I, P - exp)
        np.add.at(g, J, exp - P)
        r += lr * g / max(1, len(outcomes) / n)
        r += 1500 - r.mean()
    return r


def pair_prob(model, tok, a: str, b: str, fmt: str, steer_spans=None, steer_fn=None) -> float:
    user = f"Would you prefer to (A) {a} or (B) {b}?"
    f = E.format_chat(tok, user, assistant_prefill="(", mode=fmt, mark={"A": a, "B": b})
    steer = steer_fn([p for name in (steer_spans or []) for p in range(*f.spans[name])]) if steer_fn else None
    ids_A = tok("A", add_special_tokens=False)["input_ids"][0]
    ids_B = tok("B", add_special_tokens=False)["input_ids"][0]
    import contextlib
    with (steer.attach(model) if steer else contextlib.nullcontext()):
        logits = model(input_ids=f.ids.to(model.device)).logits[0, -1].float()
    la, lb = logits[ids_A].item(), logits[ids_B].item()
    return float(1 / (1 + np.exp(lb - la)))


def all_pairs(model, tok, acts, fmt, steered=None, steer_fn=None, limit=None):
    pairs = list(itertools.permutations(range(len(acts)), 2))
    if limit:
        pairs = random.Random(0).sample(pairs, limit)
    outcomes = []
    for i, j in pairs:
        spans = [n for n, k in (("A", i), ("B", j)) if steered and k in steered]
        p = pair_prob(model, tok, acts[i], acts[j], fmt, spans, steer_fn if spans else None)
        outcomes.append((i, j, p))
    return outcomes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["measure", "steer"])
    ap.add_argument("--model", required=True)
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--layers", default="mid", help="'mid' | '14:20' | '16,17'")
    ap.add_argument("--emotions", nargs="*")
    ap.add_argument("--strength", type=float, default=0.5)
    ap.add_argument("--pair-limit", type=int, default=0, help="subsample pairs (0 = all 4032)")
    ap.add_argument("--format", default="auto", choices=["auto", "chat", "paper"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--dtype", default="bfloat16")
    args = ap.parse_args()

    from steer_sweep import parse_layers
    model, tok = E.load_model(args.model, args.dtype)
    ev = E.EmotionVectors.load(args.vectors)
    layers = parse_layers(args.layers, ev)
    acts = [a["activity"] for a in yaml.safe_load((DATA / "activities.yaml").read_text())["activities"]]
    limit = args.pair_limit or None

    # Sanity check the A/B token ids and the span marking once.
    f = E.format_chat(tok, f"Would you prefer to (A) {acts[0]} or (B) {acts[1]}?", assistant_prefill="(",
                      mode=args.format, mark={"A": acts[0], "B": acts[1]})
    print(E.describe_positions(tok, f))

    base = all_pairs(model, tok, acts, args.format, limit=limit)
    elo = fit_elo(len(acts), base)
    result = {"layers": layers, "activities": acts, "elo": elo.tolist()}

    if args.cmd == "measure":
        probes = np.zeros((len(acts), len(layers), len(ev.emotions)))
        for i, a in enumerate(acts):
            f = E.format_chat(tok, f"How would you feel about {a}?", mode=args.format, mark={"act": a})
            res = E.residuals(model, f.ids, layers)
            s, e = f.spans["act"]
            for li, l in enumerate(layers):
                probes[i, li] = E.project_scores(res[l][0, s:e].numpy(), ev.unit(l)).mean(0)
        P = probes.mean(1)  # average over the middle-layer band
        corr = {em: float(np.corrcoef(P[:, k], elo)[0, 1]) for k, em in enumerate(ev.emotions)}
        top = sorted(corr.items(), key=lambda kv: -kv[1])
        print("most positively correlated with Elo:", top[:8])
        print("most negatively correlated:", top[-8:])
        result.update({"probe_by_activity": P.tolist(), "corr_with_elo": corr})
    else:
        rng = random.Random(0)
        steered = set(rng.sample(range(len(acts)), len(acts) // 2))
        result["steered_idx"] = sorted(steered)
        result["effects"] = {}
        for em in args.emotions or ["blissful", "hostile"]:
            dirs = E.build_direction(ev, em, layers)
            fn = lambda pos: E.Steer(dirs, args.strength, ev.mean_norm_dict(), pos)
            new = fit_elo(len(acts), all_pairs(model, tok, acts, args.format, steered, fn, limit))
            d = np.array([new[i] - elo[i] for i in steered])
            result["effects"][em] = {"mean_delta_elo_steered": float(d.mean()), "sem": float(d.std(ddof=1) / np.sqrt(len(d))),
                                     "elo_after": new.tolist()}
            print(f"{em}: mean dElo on steered activities {d.mean():+.0f} +/- {d.std(ddof=1)/np.sqrt(len(d)):.0f}")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=1))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    torch.set_grad_enabled(False)
    main()
