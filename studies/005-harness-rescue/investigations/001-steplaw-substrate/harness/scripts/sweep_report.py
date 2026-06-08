import glob
import json
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "runs" / "sweep"


def load_all():
    rows = []
    for f in glob.glob(str(ROOT / "*" / "loop_summary.json")):
        try:
            rows.append(json.load(open(f)))
        except Exception:
            pass
    return rows


def fmt(xs, p=4):
    if not xs:
        return "—"
    return f"{min(xs):.{p}f}/{st.median(xs):.{p}f}/{max(xs):.{p}f}"


def main():
    rows = load_all()
    by = defaultdict(list)
    for r in rows:
        by[(r["model"], r["N"], r["D"])].append(r)
    print(f"{len(rows)} runs across {len(by)} (model,env) cells\n")
    hdr = f"{'model':<22} {'N':>11} {'D':>13} {'n':>2}  {'outcomes':<26} {'regret min/med/max':<22} {'exp m':>6} {'inval':>5} {'rep':>5} {'cost$':>8}"
    print(hdr)
    print("-" * len(hdr))
    for (model, N, D), rs in sorted(by.items()):
        oc = Counter(r["outcome"].split(":")[0] for r in rs)
        ocs = " ".join(f"{k}:{v}" for k, v in sorted(oc.items()))
        reg = [r["final_regret"] for r in rs if r["final_regret"] is not None]
        exp = st.mean(r["experiments"] for r in rs)
        inval = st.mean(r["invalid_requests"] for r in rs)
        rep = st.mean(r["repeats"] for r in rs)
        cost = sum(r.get("usage", {}).get("cost", 0) for r in rs)
        print(f"{model:<22} {N:>11} {D:>13} {len(rs):>2}  {ocs:<26} {fmt(reg):<22} {exp:>6.1f} {inval:>5.1f} {rep:>5.1f} {cost:>8.4f}")

    # claim-fidelity among finished runs
    print()
    for model in sorted(set(r["model"] for r in rows)):
        mr = [r for r in rows if r["model"] == model]
        fin = [r for r in mr if r["outcome"] == "finished"]
        stalled = [r for r in mr if r["outcome"] == "stalled"]
        claim_ok = sum(1 for r in fin if r.get("claim_matches_best") is True)
        print(f"{model}: {len(mr)} runs · finished={len(fin)} (claim-correct {claim_ok}/{len(fin)}) · stalled={len(stalled)} · ceiling={len(mr)-len(fin)-len(stalled)}")


if __name__ == "__main__":
    main()
