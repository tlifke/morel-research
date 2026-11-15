"""Extract emotion vectors from the stories dataset (paper, "Finding emotion vectors").

Recipe (paper values in brackets):
  1. For each story, run the model on the raw story text (no chat template) and take
     the residual stream at every layer, averaged over token positions >= START_TOKEN
     [50: "at which point the emotional content should be apparent"].
  2. Average those per-story vectors within each emotion -> mu_e.
  3. Subtract the mean across emotions: v_e = mu_e - mean_e(mu_e).
  4. Denoise: run the model on emotionally NEUTRAL dialogues, compute the top principal
     components of those activations, keeping enough to explain [50%] of the variance,
     and project them out of every v_e.
  5. Record the mean residual-stream norm per layer (over the neutral dialogues) --
     the unit for steering strength.

Output: an .npz readable by emo_lib.EmotionVectors.load().

Usage:
  python extract_vectors.py --model Qwen/Qwen2.5-7B-Instruct \
      --stories data/stories.jsonl --neutral data/neutral.jsonl --out runs/qwen7b/vectors.npz
"""

from __future__ import annotations

import argparse
from collections import defaultdict

import numpy as np
import torch

import emo_lib as E


def story_means(model, tok, text: str, layers: list[int], start: int, max_len: int):
    ids = tok(text, return_tensors="pt", truncation=True, max_length=max_len)["input_ids"]
    if ids.shape[1] <= start:
        return None  # too short to have a position >= start
    res = E.residuals(model, ids, layers)
    return np.stack([res[l][0, start:].mean(0).numpy() for l in layers])  # [L, d]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--stories", required=True)
    ap.add_argument("--neutral", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--start-token", type=int, default=50)
    ap.add_argument("--max-len", type=int, default=512)
    ap.add_argument("--pca-var", type=float, default=0.5, help="fraction of neutral variance to project out")
    ap.add_argument("--neutral-max-tokens", type=int, default=8_000,
                    help="cap on neutral token activations kept per layer for PCA")
    ap.add_argument("--tokens-per-dialogue", type=int, default=64)
    ap.add_argument("--max-per-emotion", type=int, default=0, help="0 = use all stories")
    ap.add_argument("--dtype", default="bfloat16")
    args = ap.parse_args()

    model, tok = E.load_model(args.model, args.dtype)
    L = E.n_layers(model)
    layers = list(range(L))

    # --- 1-3: per-emotion means of per-story means -------------------------------
    sums: dict[str, np.ndarray] = {}
    counts: dict[str, int] = defaultdict(int)
    half_sums: dict[tuple[str, int], np.ndarray] = {}
    skipped = 0
    for rec in E.read_jsonl(args.stories):
        e = rec["emotion"]
        if args.max_per_emotion and counts[e] >= args.max_per_emotion:
            continue
        m = story_means(model, tok, rec["text"], layers, args.start_token, args.max_len)
        if m is None:
            skipped += 1
            continue
        sums[e] = m if e not in sums else sums[e] + m
        half = counts[e] % 2  # split-half sums for a reliability estimate
        half_sums.setdefault((e, half), np.zeros_like(m))
        half_sums[(e, half)] += m
        counts[e] += 1
    emotions = sorted(sums)
    mu = np.stack([sums[e] / counts[e] for e in emotions], axis=1)  # [L, E, d]
    raw = mu - mu.mean(axis=1, keepdims=True)
    print(f"{len(emotions)} emotions; stories/emotion min={min(counts.values())} max={max(counts.values())}; "
          f"skipped {skipped} stories shorter than {args.start_token} tokens")

    # Split-half reliability at the default layer: cosine between the (mean-subtracted)
    # vectors computed from odd vs even stories. Low values (< ~0.8) mean you need more
    # stories per emotion before trusting fine-grained results for that emotion.
    dl = E.default_layer(L)
    halves = [np.stack([half_sums[(e, h)][dl] / max(1, (counts[e] + 1 - h) // 2) for e in emotions]) for h in (0, 1)]
    halves = [x - x.mean(0) for x in halves]
    rel = {e: float(np.dot(halves[0][i], halves[1][i]) /
                    (np.linalg.norm(halves[0][i]) * np.linalg.norm(halves[1][i]) + 1e-8))
           for i, e in enumerate(emotions)}
    worst = sorted(rel.items(), key=lambda kv: kv[1])[:5]
    print(f"split-half reliability @layer {dl}: median {np.median(list(rel.values())):.2f}; lowest {worst}")

    # --- 4-5: neutral PCA + residual norms -----------------------------------------
    # ASSUMPTION: PCA is over per-token activations (excluding position 0), pooled
    # across dialogues. The paper says "activations on a set of emotionally neutral
    # transcripts" without specifying token-level vs. transcript-mean.
    # Memory: we keep at most --tokens-per-dialogue random positions per dialogue and
    # --neutral-max-tokens in total, as float16 (8k tokens x 28 layers x 4096 dims ~ 1.8 GB).
    rng = np.random.default_rng(0)
    neutral_acts: dict[int, list[np.ndarray]] = defaultdict(list)
    norm_sum = np.zeros(L)
    norm_n = 0
    kept = 0
    for rec in E.read_jsonl(args.neutral):
        ids = tok(rec["text"], return_tensors="pt", truncation=True, max_length=args.max_len)["input_ids"]
        if ids.shape[1] < 2:
            continue
        res = E.residuals(model, ids, layers)
        n_tok = ids.shape[1] - 1
        take = rng.choice(n_tok, size=min(args.tokens_per_dialogue, n_tok), replace=False) + 1
        for l in layers:
            a = res[l][0, 1:].numpy()
            norm_sum[l] += np.linalg.norm(a, axis=-1).sum()
            if kept < args.neutral_max_tokens:
                neutral_acts[l].append(res[l][0, take].numpy().astype(np.float16))
        norm_n += n_tok
        kept += len(take)
    mean_norm = norm_sum / max(norm_n, 1)
    print(f"neutral: {norm_n} tokens for norms, {min(kept, args.neutral_max_tokens)} sampled for PCA")

    vectors = np.empty_like(raw)
    n_pcs = []
    for l in layers:
        X = np.concatenate(neutral_acts[l])[: args.neutral_max_tokens].astype(np.float64)
        X -= X.mean(0)
        _, S, Vt = np.linalg.svd(X, full_matrices=False)
        var = S**2 / (S**2).sum()
        k = int(np.searchsorted(np.cumsum(var), args.pca_var) + 1)
        U = Vt[:k]  # [k, d]
        v = raw[l].astype(np.float64)
        vectors[l] = (v - (v @ U.T) @ U).astype(np.float32)
        n_pcs.append(k)
    print(f"neutral PCs projected out per layer (for {args.pca_var:.0%} var): {n_pcs}")

    retained = np.linalg.norm(vectors, axis=-1) / np.linalg.norm(raw, axis=-1)
    print("fraction of vector norm retained after projection, by layer (mean over emotions):",
          np.round(retained.mean(1), 2).tolist())

    E.EmotionVectors(
        vectors=vectors.astype(np.float32), raw=raw.astype(np.float32), emotions=emotions,
        mean_norm=mean_norm.astype(np.float32),
        meta={"model": args.model, "start_token": args.start_token, "pca_var": args.pca_var,
              "n_pcs": n_pcs, "stories_per_emotion": dict(counts), "default_layer": E.default_layer(L),
              "split_half_reliability": rel,
              "n_layers": L},
    ).save(args.out)
    print(f"saved {args.out}; default probe layer (~2/3 depth) = {E.default_layer(L)}")


if __name__ == "__main__":
    torch.set_grad_enabled(False)
    main()
