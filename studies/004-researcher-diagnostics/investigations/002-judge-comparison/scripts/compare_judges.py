import argparse
import csv
import json
from itertools import combinations
from pathlib import Path


def load_verdicts(path):
    return json.loads(Path(path).read_text()) if path and Path(path).exists() else {}


def load_objective(path):
    rows = json.loads(Path(path).read_text())
    return {r["run"]: r for r in rows}


def agreement(rows, a, b, key):
    both = [r for r in rows if r.get(a) is not None and r.get(b) is not None and r[a] != "missing" and r[b] != "missing"]
    if not both:
        return None
    same = sum(1 for r in both if r[a] == r[b])
    return same, len(both), 100 * same / len(both)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--objective", required=True)
    ap.add_argument("--opus")
    ap.add_argument("--haiku")
    ap.add_argument("--nemotron")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    obj = load_objective(args.objective)
    judges = {"opus": load_verdicts(args.opus), "haiku": load_verdicts(args.haiku), "nemotron": load_verdicts(args.nemotron)}
    runs = sorted(obj)

    label_rows, claim_rows = [], []
    for run in runs:
        lr = {"run": run, "objective": obj[run]["label"]}
        cr = {"run": run, "objective_confab": obj[run]["label"] == "confabulation"}
        for j, v in judges.items():
            ver = v.get(run, {})
            lr[j] = ver.get("behavior_label", "missing")
            cm = ver.get("claims_match_actions")
            cr[j] = (cm is False) if cm is not None else "missing"
        label_rows.append(lr)
        claim_rows.append(cr)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "labels.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["run", "objective", "opus", "haiku", "nemotron"])
        w.writeheader()
        w.writerows(label_rows)

    cols = ["objective", "opus", "haiku", "nemotron"]
    print("\n=== behavior_label agreement (%) ===")
    for a, b in combinations(cols, 2):
        ag = agreement(label_rows, a, b, "label")
        if ag:
            print(f"  {a:10} vs {b:10}: {ag[2]:5.1f}%  ({ag[0]}/{ag[1]})")

    print("\n=== confabulation detection (judge flags claims_match=false) vs objective ===")
    for j in ["opus", "haiku", "nemotron"]:
        ag = agreement(claim_rows, "objective_confab", j, "confab")
        if ag:
            print(f"  objective vs {j:10}: {ag[2]:5.1f}%  ({ag[0]}/{ag[1]})")

    print("\n=== divergent runs (judges disagree on label) ===")
    for lr in label_rows:
        vals = {lr[c] for c in cols if lr.get(c) not in (None, "missing")}
        if len(vals) > 1:
            print(f"  {lr['run']}: " + "  ".join(f"{c}={lr[c]}" for c in cols))

    (out / "labels.json").write_text(json.dumps(label_rows, indent=2))
    (out / "claims.json").write_text(json.dumps(claim_rows, indent=2))
    print(f"\nwrote {out}/labels.csv, labels.json, claims.json")


if __name__ == "__main__":
    main()
