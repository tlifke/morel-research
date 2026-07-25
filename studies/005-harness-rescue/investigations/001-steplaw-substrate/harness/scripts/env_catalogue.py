"""Generate the environment catalogue for inv 001's investigation.md.

Everything printed here is derived from the vendored StepLaw CSV, so the
catalogue section can be regenerated if the data is ever revendored:

    python3 scripts/env_catalogue.py            # markdown, to stdout
    python3 scripts/env_catalogue.py --check    # verify the derived invariants

Stdlib only (no pandas) so it runs without `uv`.
"""

import argparse
import collections
import csv
import statistics
from pathlib import Path

CSV = Path(__file__).resolve().parents[2] / "data" / "dense_lr_bs_loss.csv"
METRIC = "smooth loss"

# Our labels for the three envs swept in the baseline. StepLaw names no
# environments; A/B/C are local to this repo.
LABELS = {
    (214663680, 100000000000): "A",
    (536872960, 50000000000): "B",
    (1073741824, 56900000000): "C",
}


def load():
    with CSV.open() as fh:
        rows = list(csv.DictReader(fh))
    envs = collections.defaultdict(list)
    for r in rows:
        envs[(int(r["N"]), int(r["D"]))].append(r)
    return rows, dict(sorted(envs.items()))


def stats(group):
    losses = sorted(float(r[METRIC]) for r in group)
    opt = losses[0]
    best = min(group, key=lambda r: float(r[METRIC]))
    lrs = sorted({float(r["lr"]) for r in group})
    bss = sorted({int(r["bs"]) for r in group})
    within = lambda t: sum(1 for x in losses if x - opt <= t) / len(losses)
    return {
        "cells": len(group), "lrs": lrs, "bss": bss,
        "full": len(lrs) * len(bss),
        "opt": opt, "lr_star": float(best["lr"]), "bs_star": int(best["bs"]),
        "median_gap": statistics.median(losses) - opt,
        "spread": losses[-1] - opt,
        "w005": within(0.005), "w02": within(0.02),
    }


def arch(group):
    shapes = {(int(r["h"]), int(r["ffnh"]), int(r["numh"]), int(r["numl"])) for r in group}
    assert len(shapes) == 1, f"expected one architecture per env, got {shapes}"
    return shapes.pop()


def seq_len(group):
    """Implied sequence length: D == bs * train_iters * seq_len.

    Lands within 0.4% of 2048 for every env. The four envs whose D is rounded
    to 3 s.f. (11.4B, 14.2B, 22.7B, 28.4B) carry the whole residual — `ti`
    reflects the true budget, the D column doesn't.
    """
    lens = [int(r["D"]) / (int(r["bs"]) * int(r["ti"])) for r in group]
    return statistics.mean(lens)


def catalogue(envs):
    out = ["| label | N (non-emb) | D | D/N | cells | grid | lr* | bs* | optimum | med−opt | <.005 | <.02 |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for (N, D), g in envs.items():
        s = stats(g)
        label = LABELS.get((N, D), "")
        cells = f"{s['cells']}/{s['full']}"
        row = (f"| {'**' + label + '**' if label else '—'} | {N / 1e6:.1f}M | {D / 1e9:.1f}B | {D / N:.1f} "
               f"| {cells} | {len(s['lrs'])}×{len(s['bss'])} | {s['lr_star']:.3g} | {s['bs_star']} "
               f"| {s['opt']:.4f} | {s['median_gap']:.3f} | {s['w005'] * 100:.0f}% | {s['w02'] * 100:.0f}% |")
        out.append(row)
    return "\n".join(out)


def architectures(envs):
    seen = {}
    for (N, _), g in envs.items():
        seen.setdefault(N, arch(g))
    out = ["| N (non-emb) | d_model | ffn hidden | heads | layers | recomputed |",
           "|---|---|---|---|---|---|"]
    for N, (h, ffnh, numh, numl) in sorted(seen.items()):
        calc = numl * (4 * h * h + 3 * h * ffnh)
        out.append(f"| {N:,} | {h} | {ffnh} | {numh} | {numl} | {calc:,}{'' if calc == N else ' ✗'} |")
    return "\n".join(out)


def windows(envs):
    out = ["| N | D | lr window (12 unless noted) | bs values |", "|---|---|---|---|"]
    for (N, D), g in envs.items():
        s = stats(g)
        n = "" if len(s["lrs"]) == 12 else f" ({len(s['lrs'])} values)"
        out.append(f"| {N / 1e6:.1f}M | {D / 1e9:.1f}B | {s['lrs'][0]:.3g} … {s['lrs'][-1]:.3g}{n} "
                   f"| {', '.join(str(b) for b in s['bss'])} |")
    return "\n".join(out)


def holes(envs):
    out = []
    for (N, D), g in envs.items():
        s = stats(g)
        have = {(float(r["lr"]), int(r["bs"])) for r in g}
        miss = [(lr, bs) for lr in s["lrs"] for bs in s["bss"] if (lr, bs) not in have]
        if miss:
            out.append(f"- {N / 1e6:.1f}M/{D / 1e9:.1f}B — {len(miss)} hole(s): "
                       + ", ".join(f"({lr:.3g}, {bs})" for lr, bs in miss[:6])
                       + (" …" if len(miss) > 6 else ""))
    return "\n".join(out)


def ladder(rows):
    physical = sorted({float(f"{float(r['lr']):.3g}") for r in rows})
    strings = {r["lr"] for r in rows}
    ratios = [physical[i + 1] / physical[i] for i in range(len(physical) - 1)]
    return physical, strings, ratios


def check(rows, envs):
    """Assert the invariants the prose relies on. Exits non-zero on failure."""
    ok = True

    def want(cond, msg):
        nonlocal ok
        print(("  ok   " if cond else "  FAIL ") + msg)
        ok = ok and cond

    print("invariants:")
    want(len(rows) == 1911, f"1911 data rows (got {len(rows)})")
    want(len(envs) == 17, f"17 (N,D) row-groups (got {len(envs)})")
    keys = collections.Counter((r["N"], r["D"], r["lr"], r["bs"]) for r in rows)
    want(max(keys.values()) == 1, "no duplicate (N,D,lr,bs) keys")
    for (N, D), g in envs.items():
        h, ffnh, numh, numl = arch(g)
        want(numl * (4 * h * h + 3 * h * ffnh) == N, f"N={N:,} == non-embedding params of its shape")
        want(abs(seq_len(g) / 2048 - 1) < 0.01, f"{N / 1e6:.0f}M/{D / 1e9:.0f}B implies seq_len 2048 (±1%)")
    physical, strings, ratios = ladder(rows)
    want(len(physical) == 14, f"14 physical lr values (got {len(physical)})")
    want(len(strings) == 26, f"26 distinct lr strings — the precision artifact (got {len(strings)})")
    want(all(abs(r - 2 ** 0.5) < 0.02 for r in ratios), "lr ladder is √2-spaced")
    complete = [k for k, g in envs.items() if stats(g)["cells"] == stats(g)["full"]]
    want(len(complete) == 4, f"4 complete grids (got {len(complete)})")
    want(stats(envs[(214663680, 100000000000)])["cells"] == 120, "Env A is a complete 12×10")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify invariants instead of printing markdown")
    a = ap.parse_args()
    rows, envs = load()
    if a.check:
        raise SystemExit(0 if check(rows, envs) else 1)
    physical, strings, _ = ladder(rows)
    print("### All 17 environments\n")
    print(catalogue(envs))
    print("\n### Architectures (one per N)\n")
    print(architectures(envs))
    print("\n### Per-env axis windows\n")
    print(windows(envs))
    print("\n### Unmeasured cells\n")
    print(holes(envs))
    print(f"\nlr ladder: {len(physical)} physical values, {physical[0]:.3g} … {physical[-1]:.3g}, "
          f"√2-spaced; {len(strings)} distinct strings in the CSV (precision artifact).")


if __name__ == "__main__":
    main()
