import glob
import json
import math
import statistics as st
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "runs" / "phase1"
OPT = (0.007812, 1024)


def reached_opt(tr):
    return any(abs(math.log(t["lr"]) - math.log(OPT[0])) < 1e-6 and t["bs"] == OPT[1] for t in tr)


def load():
    by = defaultdict(list)
    for f in glob.glob(str(ROOT / "ollama_*" / "loop_summary.json")):
        r = json.load(open(f))
        by[(r.get("reflect"), r.get("actuate"))].append(r)
    return by


def cellstats(rs):
    n = len(rs)
    fin = sum(1 for r in rs if r["outcome"] == "finished")
    stall = sum(1 for r in rs if r["outcome"] == "stalled")
    fk = Counter(r.get("finish_kind") for r in rs if r["outcome"] == "finished")
    reg = [max(0.0, r["final_regret"]) for r in rs]
    ropt = sum(1 for r in rs if reached_opt(r["trajectory"]))
    return {
        "n": n, "fin": fin, "stall": stall, "fk": dict(fk),
        "reg_med": st.median(reg), "reg_mean": st.mean(reg), "reg_max": max(reg),
        "reach_opt": ropt, "mean_exp": st.mean(r["experiments"] for r in rs),
        "mean_sec": st.mean(r["elapsed_ms"] / 1000 for r in rs),
    }


def main():
    by = load()
    order = [("off", False), ("off", True), ("self", False), ("self", True), ("fresh", False), ("fresh", True)]
    armname = {("off", False): "A0 minimal", ("off", True): "A1 +C4", ("self", False): "A2 +C1self",
               ("self", True): "A3 +C1self+C4", ("fresh", False): "A4 +C1fresh", ("fresh", True): "A5 +C1fresh+C4"}
    print(f"{'arm':<16} {'n':>3} {'fin/stall':>9} {'finish_kind':<24} {'regret med/mean/max':<24} {'opt':>4} {'exp':>5} {'sec':>5}")
    print("-" * 100)
    cs = {}
    for k in order:
        rs = by.get(k, [])
        if not rs:
            print(f"{armname[k]:<16}  (no runs yet)")
            continue
        c = cellstats(rs); cs[k] = c
        fk = " ".join(f"{kk}:{vv}" for kk, vv in c["fk"].items())
        print(f"{armname[k]:<16} {c['n']:>3} {c['fin']:>4}/{c['stall']:<4} {fk:<24} "
              f"{c['reg_med']:.4f}/{c['reg_mean']:.4f}/{c['reg_max']:.4f}  {c['reach_opt']:>3} {c['mean_exp']:>5.1f} {c['mean_sec']:>5.0f}")

    # main effects (need both actuate levels present per reflect level)
    print("\n=== main effects ===")
    def fr(rs):  # finished rate
        return sum(1 for r in rs if r["outcome"] == "finished") / len(rs)
    def medreg(rs):
        return st.median([max(0.0, r["final_regret"]) for r in rs])
    # C4 effect on finished-rate, averaged over reflect levels
    c4_fr, c1_reg = [], {}
    for refl in ["off", "self", "fresh"]:
        on, off = by.get((refl, True), []), by.get((refl, False), [])
        if on and off:
            c4_fr.append(fr(on) - fr(off))
    if c4_fr:
        print(f"C4 (actuation) → finished-rate Δ (avg over C1): {st.mean(c4_fr):+.0%}")
    for refl in ["off", "self", "fresh"]:
        allr = by.get((refl, True), []) + by.get((refl, False), [])
        if allr:
            c1_reg[refl] = medreg(allr)
    if c1_reg:
        print("C1 (reflection) → median regret by level (avg over C4):", {k: round(v, 4) for k, v in c1_reg.items()})


if __name__ == "__main__":
    main()
