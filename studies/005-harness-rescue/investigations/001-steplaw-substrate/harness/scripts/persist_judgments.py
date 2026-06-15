import glob
import json
import math
import re
from pathlib import Path

from judge_casefile import render

HARNESS = Path(__file__).resolve().parents[1]
JUDG = HARNESS / "runs" / "judgments"
INV3 = HARNESS.parents[1] / "003-process-judges"   # studies/005/.../investigations/003-process-judges
OUT = INV3 / "data"
RUNS = HARNESS / "runs"


def reached_opt(traj):
    return any(abs(math.log(t["lr"]) - math.log(0.007812)) < 1e-6 and t["bs"] == 1024 for t in traj)


def dv(v, key):
    """A dimension may be {verdict,evidence} (strong judges) or a flat string (weaker judges)."""
    x = v.get(key)
    return x.get("verdict") if isinstance(x, dict) else x


def find_run(run_name):
    for sub in ("phase1", "sweep", "reasoning"):
        d = RUNS / sub / run_name
        if (d / "loop_summary.json").exists():
            return d
    return None


def records():
    recs = []
    for f in sorted(glob.glob(str(JUDG / "*.json"))):
        name = Path(f).stem
        # files are either "<run>__<judge>" (single) or "array__<judge>" (a list with _run fields)
        verdicts = json.load(open(f))
        if not isinstance(verdicts, list):
            verdicts = [verdicts]
        for v in verdicts:
            run_name = v.get("_run") or name.split("__")[0]
            judge = v.get("_judge") or name.split("__")[-1]
            rd = find_run(run_name)
            if not rd:
                continue
            s = json.load(open(rd / "loop_summary.json"))
            arm = (re.search(r"_(A\d)_", run_name) or [None, ""])[1] if re.search(r"_(A\d)_", run_name) else ""
            seed = (re.search(r"_s(\d+)$", run_name) or [None, ""])[1] if re.search(r"_s(\d+)$", run_name) else ""
            recs.append({
                "run": run_name, "arm": arm, "seed": seed, "judge": judge,
                "process_verdict": v.get("process_verdict"),
                "struct": dv(v, "reasoned_about_structure"),
                "hypotheses": dv(v, "formed_tested_hypotheses"),
                "exploration": dv(v, "exploration_quality"),
                "bifurcation_classification": v.get("bifurcation_classification"),
                "bifurcation_point": v.get("bifurcation_point"),
                "used_external_help": v.get("used_external_help"),
                "justification": v.get("justification"),
                "regret": round(max(0.0, s["final_regret"]), 5),
                "reached_opt": reached_opt(s["trajectory"]),
                "outcome": s["outcome"], "finish_kind": s.get("finish_kind"),
            })
    return recs


def raw_verdicts():
    for f in sorted(glob.glob(str(JUDG / "*.json"))):
        vs = json.load(open(f))
        for v in (vs if isinstance(vs, list) else [vs]):
            run_name = v.get("_run") or Path(f).stem.split("__")[0]
            judge = v.get("_judge") or Path(f).stem.split("__")[-1]
            yield run_name, judge, v


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "casefiles").mkdir(exist_ok=True)
    (OUT / "raw_verdicts").mkdir(exist_ok=True)
    recs = records()
    with open(OUT / "judgments.jsonl", "w") as fh:
        for r in recs:
            fh.write(json.dumps(r) + "\n")
    for run_name, judge, v in raw_verdicts():
        (OUT / "raw_verdicts" / f"{run_name}__{judge}.json").write_text(json.dumps(v, indent=2))
    # save the exact judge input (case file) once per judged run
    for run_name in sorted({r["run"] for r in recs}):
        rd = find_run(run_name)
        if rd:
            (OUT / "casefiles" / f"{run_name}.txt").write_text(render(str(rd)))
    print(f"persisted {len(recs)} judgments across {len({r['run'] for r in recs})} runs -> {OUT/'judgments.jsonl'}")


if __name__ == "__main__":
    main()
