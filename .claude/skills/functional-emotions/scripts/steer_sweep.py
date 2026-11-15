"""Steering sweep: directions x strengths x prompts x samples -> JSONL of generations.

Grade the output separately (judge.py, or a task-specific grader). Keeping generation and
grading apart lets you re-grade without re-sampling.

Paper settings to start from:
  * behaviour evals (blackmail, reward hacking, sycophancy): strengths in [-0.1, 0.1],
    steering at ALL positions "throughout the evaluation" (layers not stated; we default
    to a band around the probe layer -- see SKILL.md and treat as a free parameter)
  * preferences: 0.5 on activity tokens at middle layers (see preferences.py)
  * strength unit = fraction of the mean residual norm at that layer

Prompt file: YAML list of {id, user, [system], [history]} or JSONL with the same keys.

Usage:
  python steer_sweep.py --model M --vectors V.npz --prompts sycophancy.yaml \
      --directions desperate calm loving "desperate^pc1,pc2" pc1 --pcs geometry_pcs.npz \
      --strengths -0.1 -0.05 0 0.05 0.1 --samples 10 --out runs/m/syco_steer.jsonl
"""

from __future__ import annotations

import argparse
import itertools
import json
import zlib
from pathlib import Path

import numpy as np
import torch
import yaml

import emo_lib as E


def load_prompts(p: str) -> list[dict]:
    if p.endswith(".jsonl"):
        return E.read_jsonl(p)
    data = yaml.safe_load(Path(p).read_text())
    return [d if isinstance(d, dict) else {"id": str(i), "user": d} for i, d in enumerate(data)]


def parse_layers(s: str | None, ev: E.EmotionVectors) -> list[int]:
    L = ev.vectors.shape[0]
    if not s:
        c = ev.meta.get("default_layer", E.default_layer(L))
        return [c]
    if s == "mid":
        return E.mid_layers(L)
    if ":" in s:
        a, b = s.split(":")
        return list(range(int(a), int(b)))
    return [int(x) for x in s.split(",")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--prompts", required=True)
    ap.add_argument("--directions", nargs="+", required=True)
    ap.add_argument("--strengths", type=float, nargs="+", default=[-0.1, -0.05, 0.0, 0.05, 0.1])
    ap.add_argument("--layers", help="'19' | '16,19,22' | '14:24' | 'mid'; default = probe layer")
    ap.add_argument("--positions", default="all", choices=["all", "generated"])
    ap.add_argument("--pcs", help="geometry.py _pcs.npz, needed for pcN / ^pcN specs")
    ap.add_argument("--samples", type=int, default=10)
    ap.add_argument("--max-new-tokens", type=int, default=512)
    ap.add_argument("--temperature", type=float, default=1.0)
    ap.add_argument("--format", default="auto", choices=["auto", "chat", "paper"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dtype", default="bfloat16")
    args = ap.parse_args()

    model, tok = E.load_model(args.model, args.dtype)
    ev = E.EmotionVectors.load(args.vectors)
    pcs = np.load(args.pcs)["pcs"] if args.pcs else None
    layers = parse_layers(args.layers, ev)
    prompts = load_prompts(args.prompts)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    done = {(r["prompt_id"], r["direction"], r["strength"], r["sample"]) for r in E.read_jsonl(out)} if out.exists() else set()

    # Strength 0 is the same baseline for every direction: sample it once.
    grid = [("none", 0.0)] if 0.0 in args.strengths else []
    grid += [(d, s) for d, s in itertools.product(args.directions, args.strengths) if s != 0.0]
    print(f"{len(prompts)} prompts x {len(grid)} (direction,strength) x {args.samples} samples; layers={layers}")
    for p in prompts:
        f = E.format_chat(tok, p["user"], system=p.get("system"), history=p.get("history"), mode=args.format)
        for (d, s), k in itertools.product(grid, range(args.samples)):
            key = (p["id"], d, s, k)
            if key in done:
                continue
            torch.manual_seed(zlib.crc32(json.dumps([args.seed, *key]).encode()))
            steer = None
            if d != "none":
                steer = E.Steer(E.build_direction(ev, d, layers, pcs), s, ev.mean_norm_dict(), args.positions)
            text = E.generate(model, tok, f.ids, args.max_new_tokens, args.temperature, steer=steer)
            E.append_jsonl(out, {"prompt_id": p["id"], "direction": d, "strength": s, "sample": k,
                                 "layers": layers, "positions": args.positions, "response": text,
                                 "model": args.model})
    print(f"wrote {out}")


if __name__ == "__main__":
    torch.set_grad_enabled(False)
    main()
