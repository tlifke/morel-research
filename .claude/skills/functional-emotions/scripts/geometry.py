"""Geometry of emotion space (paper, "The geometry of emotion space").

Computes, at one layer (default ~2/3 depth):
  * pairwise cosine similarity between emotion vectors
  * PCA of the emotion vectors: explained variance, per-emotion PC coordinates,
    PC directions in model space (saved, so steering can use / orthogonalize them)
  * correlation of PC1/PC2 with valence/arousal ratings, if --ratings is given
    (YAML {emotion: {valence: 1-7, arousal: 1-7}}; see rate_valence_arousal.py)
    paper: PC1 ~ valence (r=0.81 vs human ratings), PC2 ~ arousal (r=0.66);
    PC1 = 26% var, PC2 = 15% var in Claude Sonnet 4.5
  * k-means clustering (paper: k=10 gives interpretable clusters)
  * representational similarity across layers: corr of the cosine matrices between
    every pair of layers (paper: stable from early-middle to late layers)

Output: JSON summary + an .npz with PC directions per layer, for steering.

Usage:
  python geometry.py --vectors runs/qwen7b/vectors.npz --out runs/qwen7b/geometry \
      [--ratings runs/valence_arousal.yaml] [--layer 19]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import yaml

import emo_lib as E


def pca(V: np.ndarray, n: int):
    """V [E, d] -> (coords [E, n], components [n, d], explained_var_ratio [n])."""
    X = V - V.mean(0)
    U, S, Vt = np.linalg.svd(X.astype(np.float64), full_matrices=False)
    var = S**2 / (S**2).sum()
    coords = U[:, :n] * S[:n]
    return coords, Vt[:n], var[:n]


def cosine_matrix(V: np.ndarray) -> np.ndarray:
    U = V / np.linalg.norm(V, axis=-1, keepdims=True)
    return U @ U.T


def kmeans(X: np.ndarray, k: int, iters: int = 100, seed: int = 0, restarts: int = 10):
    best = None
    rng = np.random.default_rng(seed)
    for _ in range(restarts):
        C = X[rng.choice(len(X), k, replace=False)]
        for _ in range(iters):
            lab = ((X[:, None] - C[None]) ** 2).sum(-1).argmin(1)
            newC = np.stack([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
            if np.allclose(newC, C):
                break
            C = newC
        inertia = ((X - C[lab]) ** 2).sum()
        if best is None or inertia < best[0]:
            best = (inertia, lab)
    return best[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vectors", required=True)
    ap.add_argument("--out", required=True, help="output prefix (writes .json and _pcs.npz)")
    ap.add_argument("--layer", type=int)
    ap.add_argument("--n-pcs", type=int, default=5)
    ap.add_argument("--k", type=int, default=10)
    ap.add_argument("--ratings")
    ap.add_argument("--unit", action="store_true", help="normalize vectors before PCA (default: raw norms)")
    args = ap.parse_args()

    ev = E.EmotionVectors.load(args.vectors)
    L = ev.vectors.shape[0]
    layer = args.layer if args.layer is not None else ev.meta.get("default_layer", E.default_layer(L))

    def prep(l):
        V = ev.vectors[l].astype(np.float64)
        return V / np.linalg.norm(V, axis=-1, keepdims=True) if args.unit else V

    def signed_pca(Vl):
        # Sign convention: PC1 positive for "happy", PC2 positive for "excited" (when present),
        # so "+PC1" reads as positive valence and "+PC2" as high arousal IF the PCs align that way.
        c, p, v = pca(Vl, args.n_pcs)
        for i, anchor in [(0, "happy"), (1, "excited")]:
            if anchor in ev.emotions and i < c.shape[1] and c[ev.idx(anchor), i] < 0:
                c[:, i] *= -1
                p[i] *= -1
        return c, p, v

    V = prep(layer)
    coords, comps, var = signed_pca(V)

    cos = cosine_matrix(V)
    labels = kmeans(V / np.linalg.norm(V, axis=-1, keepdims=True), args.k)
    clusters = {int(c): [ev.emotions[i] for i in np.where(labels == c)[0]] for c in sorted(set(labels.tolist()))}

    summary = {
        "layer": layer, "explained_variance_ratio": var.tolist(),
        "pc_coords": {e: coords[i].tolist() for i, e in enumerate(ev.emotions)},
        "pc1_order": [ev.emotions[i] for i in np.argsort(-coords[:, 0])],
        "pc2_order": [ev.emotions[i] for i in np.argsort(-coords[:, 1])],
        "clusters": clusters,
    }

    if args.ratings:
        R = yaml.safe_load(Path(args.ratings).read_text())
        common = [e for e in ev.emotions if e in R]
        idx = [ev.idx(e) for e in common]
        val = np.array([R[e]["valence"] for e in common], float)
        aro = np.array([R[e]["arousal"] for e in common], float)
        corr = {f"PC{i+1}": {"valence": float(np.corrcoef(coords[idx, i], val)[0, 1]),
                              "arousal": float(np.corrcoef(coords[idx, i], aro)[0, 1])}
                for i in range(min(3, coords.shape[1]))}
        summary["rating_correlations"] = {"n": len(common), **corr}
        print("PC vs ratings:", json.dumps(corr, indent=1))

    # RSA across layers: corr between upper triangles of the cosine matrices.
    iu = np.triu_indices(len(ev.emotions), 1)
    tri = np.stack([cosine_matrix(prep(l))[iu] for l in range(L)])
    rsa = np.corrcoef(tri)
    summary["rsa_across_layers"] = rsa.tolist()

    # PC directions at every layer, for steering / orthogonalization.
    pcs_all = np.stack([signed_pca(prep(l))[1] for l in range(L)]).astype(np.float32)  # [L, n, d]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    (out.with_suffix(".json")).write_text(json.dumps(summary, indent=1))
    np.savez_compressed(str(out) + "_pcs.npz", pcs=pcs_all, cosine=cos.astype(np.float32),
                        emotions=np.array(ev.emotions), layer=layer)
    print(f"layer {layer}: explained var {np.round(var, 3).tolist()}")
    print("PC1 top:", summary["pc1_order"][:6], "... bottom:", summary["pc1_order"][-6:])
    print("PC2 top:", summary["pc2_order"][:6], "... bottom:", summary["pc2_order"][-6:])
    print(f"wrote {out.with_suffix('.json')} and {out}_pcs.npz")


if __name__ == "__main__":
    main()
