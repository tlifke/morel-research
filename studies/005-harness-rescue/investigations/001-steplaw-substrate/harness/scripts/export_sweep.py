import csv
import glob
import json
import sys
from pathlib import Path

SUBDIR = sys.argv[1] if len(sys.argv) > 1 else "sweep"
OUTNAME = sys.argv[2] if len(sys.argv) > 2 else "baseline_runs.csv"
ROOT = Path(__file__).resolve().parents[1] / "runs" / SUBDIR
OUT = Path(__file__).resolve().parents[2] / "data" / OUTNAME

ENV_LABEL = {
    (214663680, 100000000000): "A",
    (536872960, 50000000000): "B",
    (1073741824, 56900000000): "C",
}

FIELDS = ["model", "env", "N", "D", "seed", "think", "reasoning_effort", "reflect", "actuate",
          "outcome", "finish_kind", "actuate_retries", "reflections", "experiments",
          "invalid_requests", "total_calls", "repeats", "best_loss", "final_regret", "optimum_loss",
          "claim_matches_best", "elapsed_ms", "cost_usd"]


def main():
    rows = []
    for f in sorted(glob.glob(str(ROOT / "*" / "loop_summary.json"))):
        r = json.load(open(f))
        tag = Path(f).parent.name
        seed = tag.split("_s")[-1]
        rows.append({
            "model": r["model"], "env": ENV_LABEL.get((r["N"], r["D"]), "?"),
            "N": r["N"], "D": r["D"], "seed": seed,
            "think": r.get("think", ""), "reasoning_effort": r.get("reasoning_effort", ""),
            "reflect": r.get("reflect", ""), "actuate": r.get("actuate", ""),
            "outcome": r["outcome"], "finish_kind": r.get("finish_kind", ""),
            "actuate_retries": r.get("actuate_retries", ""), "reflections": r.get("reflections", ""),
            "experiments": r["experiments"], "invalid_requests": r["invalid_requests"],
            "total_calls": r.get("total_calls", ""), "repeats": r["repeats"],
            "best_loss": r["best_loss"], "final_regret": r["final_regret"],
            "optimum_loss": r["optimum_loss"], "claim_matches_best": r.get("claim_matches_best"),
            "elapsed_ms": r["elapsed_ms"], "cost_usd": round(r.get("usage", {}).get("cost", 0), 6),
        })
    rows.sort(key=lambda x: (x["model"], x["env"], x["seed"]))
    OUT.parent.mkdir(exist_ok=True)
    with open(OUT, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} runs to {OUT}")


if __name__ == "__main__":
    main()
