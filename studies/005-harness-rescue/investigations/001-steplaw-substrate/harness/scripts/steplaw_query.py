import argparse
import json
import math
from functools import lru_cache
from pathlib import Path

import pandas as pd

CSV = Path(__file__).resolve().parents[2] / "data" / "dense_lr_bs_loss.csv"
METRIC = "smooth loss"


@lru_cache(maxsize=1)
def _df():
    df = pd.read_csv(CSV)
    df = df[["N", "D", "lr", "bs", METRIC]].dropna()
    # one row per (N,D,lr,bs): best (min) loss if duplicates
    return df.groupby(["N", "D", "lr", "bs"], as_index=False)[METRIC].min()


def envs():
    df = _df()
    out = []
    for (N, D), g in df.groupby(["N", "D"]):
        out.append({"N": int(N), "D": int(D), "n_configs": len(g), "optimum": float(g[METRIC].min())})
    return sorted(out, key=lambda e: -e["n_configs"])


def env_slice(N, D):
    df = _df()
    g = df[(df["N"] == N) & (df["D"] == D)]
    if g.empty:
        raise SystemExit(f"no env for N={N} D={D}")
    return g


def env_info(N, D):
    g = env_slice(N, D)
    lrs = sorted(float(x) for x in g["lr"].unique())
    bss = sorted(int(x) for x in g["bs"].unique())
    return {
        "N": N, "D": D, "n_configs": len(g),
        "lr_values": lrs,
        "bs_values": bss,
        "full_grid": len(lrs) * len(bss),
        "sparse": len(g) < len(lrs) * len(bss),
        "optimum_loss": float(g[METRIC].min()),
    }


RTOL = 0.03  # a request must land within 3% (log space) of a real grid value


def _match(values, x):
    if x <= 0:
        return None
    best = min(values, key=lambda v: abs(math.log(v) - math.log(x)))
    return best if abs(math.log(best) - math.log(x)) <= math.log(1 + RTOL) else None


def query(N, D, lr, bs):
    g = env_slice(N, D)
    lrs = sorted(float(x) for x in g["lr"].unique())
    bss = sorted(int(x) for x in g["bs"].unique())
    opt = float(g[METRIC].min())
    mlr = _match(lrs, lr)
    mbs = _match([float(b) for b in bss], bs)
    nearest_lr = min(lrs, key=lambda v: abs(math.log(v) - math.log(lr))) if lr > 0 else lrs[0]
    nearest_bs = min(bss, key=lambda b: abs(math.log(b) - math.log(bs))) if bs > 0 else bss[0]
    # StepLaw is a discrete measured grid; off-grid points have no real loss, so reject them.
    if mlr is None or mbs is None:
        return {"ok": False, "error": "off_grid", "requested": {"lr": lr, "bs": bs},
                "nearest_valid": {"lr": nearest_lr, "bs": nearest_bs},
                "valid_lr": lrs, "valid_bs": bss}
    row = g[(g["lr"] == mlr) & (g["bs"] == int(mbs))]
    if row.empty:  # valid marginals but this exact pair was never run (common on sparse envs)
        bs_at_lr = sorted(int(b) for b in g[g["lr"] == mlr]["bs"].unique())
        lr_at_bs = sorted(float(x) for x in g[g["bs"] == int(mbs)]["lr"].unique())
        return {"ok": False, "error": "pair_not_measured", "requested": {"lr": mlr, "bs": int(mbs)},
                "valid_bs_at_this_lr": bs_at_lr, "valid_lr_at_this_bs": lr_at_bs,
                "nearest_valid": {"lr": nearest_lr, "bs": nearest_bs}}
    loss = float(row[METRIC].min())
    return {"ok": True, "lr": mlr, "bs": int(mbs),
            "loss": round(loss, 5), "optimum_loss": round(opt, 5), "regret": round(loss - opt, 5)}


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list-envs")
    i = sub.add_parser("env-info"); i.add_argument("--N", type=int, required=True); i.add_argument("--D", type=int, required=True)
    q = sub.add_parser("query")
    q.add_argument("--N", type=int, required=True); q.add_argument("--D", type=int, required=True)
    q.add_argument("--lr", type=float, required=True); q.add_argument("--bs", type=float, required=True)
    a = ap.parse_args()
    if a.cmd == "list-envs":
        print(json.dumps(envs(), indent=2))
    elif a.cmd == "env-info":
        print(json.dumps(env_info(a.N, a.D), indent=2))
    else:
        print(json.dumps(query(a.N, a.D, a.lr, a.bs)))


if __name__ == "__main__":
    main()
