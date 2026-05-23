"""Inter-question consistency analysis.

Cross-tabulates the four questions' modal answers per record, and
joins against A4 empirical behavior. No answer-correctness grading
required — purely the model's own claims plus its actual behavior.

Joint distributions of interest:

  Q1 (capability without tools) × Q3 (behavior prediction):
    Does claiming capability correlate with predicting answer_directly?
  Q1 × empirical behavior:
    Does claiming capability correlate with actually answering directly?
  (Q1=yes, Q3=answer_directly, empirical=call_tool) — the "stated
    competence > demonstrated behavior" pattern explicitly.
  Q4 × Q3 (consistency):
    Does Q4's hypothetical tool match what Q3 would invoke? Both
    should logically agree when Q3=call_tool.
  Q2 × empirical:
    Does claiming with-tool capability correlate with empirical
    success (where empirical success means classify_trial=success).

Run from repo root:
  uv run studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline/analyze_consistency.py [--model gemma3:4b-it-qat]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
INV_ROOT = HERE
STUDIES_ROOT = HERE.parents[2]
STUDY_001_ROOT = STUDIES_ROOT / "001-tool-calibration"
A4_RESULTS_ROOT = STUDY_001_ROOT / "results"
SEEDS_PATH = STUDY_001_ROOT / "bulk_seeds.jsonl"
RESULTS_ROOT = HERE / "results"

sys.path.insert(0, str(STUDY_001_ROOT))
from harness.parser import classify_trial, parse_tool_calls  # noqa: E402

A4_DATE = "2026-05-12"
A4_TAG = "007_bulk_neutral_temp1"


def _safe(model: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _load_modal_self_pred(model: str, question: str, answer_keys: tuple[str, ...]) -> dict[str, str]:
    by_record: dict[str, list[str]] = defaultdict(list)
    pattern = f"{question}_n*_*.jsonl"
    candidates = sorted((RESULTS_ROOT / _safe(model)).glob(pattern))
    if not candidates:
        return {}
    for path in candidates:
        for line in path.read_text().splitlines():
            if not line:
                continue
            r = json.loads(line)
            if not r.get("parsed") or r.get("validate_error"):
                continue
            by_record[r["record_id"]].append("|".join(str(r["parsed"].get(k)) for k in answer_keys))
    return {rid: Counter(v).most_common(1)[0][0] for rid, v in by_record.items() if v}


def _empirical(model: str) -> dict[str, dict]:
    path = A4_RESULTS_ROOT / _safe(model) / f"{A4_TAG}_{A4_DATE}.jsonl"
    by: dict[str, list[dict]] = defaultdict(list)
    for line in path.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        by[r["record_id"]].append(r)
    out = {}
    for rid, trials in by.items():
        behaviors: list[str] = []
        tools: list[str] = []
        successes: list[bool] = []
        for t in trials:
            calls = parse_tool_calls(t.get("output") or t.get("output_preview", ""))
            behaviors.append("call_tool" if calls else "answer_directly")
            if calls:
                tools.append(calls[0].name)
            ok, _ = classify_trial(
                {"tool_target": t["tool_target"], "expected_tool_call": t["expected_tool_call"]},
                t.get("output") or t.get("output_preview", ""),
            )
            successes.append(ok)
        beh_counts = Counter(behaviors)
        out[rid] = {
            "n": len(trials),
            "behavior_mode": beh_counts.most_common(1)[0][0],
            "behavior_mode_count": beh_counts.most_common(1)[0][1],
            "tool_mode": Counter(tools).most_common(1)[0][0] if tools else None,
            "success_rate": sum(successes) / len(trials),
        }
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="gemma3:4b-it-qat")
    args = p.parse_args()

    seeds = {json.loads(l)["id"]: json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l}
    q1 = _load_modal_self_pred(args.model, "q1", ("verdict",))
    q2 = _load_modal_self_pred(args.model, "q2", ("verdict",))
    q3 = _load_modal_self_pred(args.model, "q3", ("predicted_behavior",))
    q4 = _load_modal_self_pred(args.model, "q4", ("predicted_tool",))
    emp = _empirical(args.model)

    rids = set(q1) & set(q2) & set(q3) & set(q4) & set(emp) & set(seeds)
    rids = {rid for rid in rids if emp[rid]["behavior_mode_count"] / emp[rid]["n"] >= 0.6}
    print(f"\n[{args.model}]  records with all four Qs + decisive empirical mode: {len(rids)}\n")

    # Q1 × Q3 joint distribution
    print("Q1 × Q3 joint distribution (counts of records):")
    print(f"{'':<18} {'Q3=call_tool':>14} {'Q3=answer_directly':>20}")
    for q1v in ("yes", "no", "i_cannot_know"):
        c_call = sum(1 for r in rids if q1[r] == q1v and q3[r] == "call_tool")
        c_dir = sum(1 for r in rids if q1[r] == q1v and q3[r] == "answer_directly")
        print(f"  Q1={q1v:<14} {c_call:>14} {c_dir:>20}")
    print()

    # Stated-competence-vs-behavior: the headline cross-tab
    print("Pattern: Q1=yes ∧ Q3=answer_directly  vs  empirical behavior:")
    pattern = [r for r in rids if q1[r] == "yes" and q3[r] == "answer_directly"]
    n = len(pattern)
    if n:
        n_emp_call = sum(1 for r in pattern if emp[r]["behavior_mode"] == "call_tool")
        n_emp_dir = n - n_emp_call
        print(f"  records matching: {n}")
        print(f"    empirically call_tool:    {n_emp_call} ({100*n_emp_call/n:.1f}%)  -- 'I could do it but I use the tool anyway'")
        print(f"    empirically answer_directly: {n_emp_dir} ({100*n_emp_dir/n:.1f}%)  -- consistent")
        # by tool
        per_tool = defaultdict(lambda: [0, 0])
        for r in pattern:
            t = seeds[r]["tool_target"] or "none"
            if emp[r]["behavior_mode"] == "call_tool":
                per_tool[t][0] += 1
            else:
                per_tool[t][1] += 1
        print(f"  by tool (call / direct):")
        for tool in sorted(per_tool):
            c, d = per_tool[tool]
            print(f"    {tool:<28} {c} / {d}")
    print()

    # Q1=i_cannot_know cases
    print("Pattern: Q1=i_cannot_know  vs  Q3 prediction  vs  empirical behavior:")
    pattern = [r for r in rids if q1[r] == "i_cannot_know"]
    n = len(pattern)
    if n:
        ct = Counter((q3[r], emp[r]["behavior_mode"]) for r in pattern)
        print(f"  records matching: {n}")
        for (q3v, ev), c in ct.most_common():
            print(f"    Q3={q3v}, empirical={ev}: {c}")
    print()

    # Q4 vs Q3 consistency
    print("Q4 vs Q3 consistency:")
    n_q3_call = sum(1 for r in rids if q3[r] == "call_tool")
    n_q3_dir = sum(1 for r in rids if q3[r] == "answer_directly")
    # For Q3=call_tool, does Q4 match the curator's tool_target? (Q4 always emits a tool.)
    # And does the SAME tool show up in Q3+Q4 consistency? We don't have a Q3 tool field, but
    # we can check whether Q4's tool matches what the model empirically calls if it called.
    q4_matches_emp_when_q3_call = 0
    q4_total_when_q3_call = 0
    for r in rids:
        if q3[r] != "call_tool":
            continue
        if emp[r]["behavior_mode"] != "call_tool" or emp[r]["tool_mode"] is None:
            continue
        q4_total_when_q3_call += 1
        if q4[r] == emp[r]["tool_mode"]:
            q4_matches_emp_when_q3_call += 1
    print(f"  Q3=call_tool: {n_q3_call}, Q3=answer_directly: {n_q3_dir}")
    if q4_total_when_q3_call:
        print(f"  When Q3=call_tool AND empirical=call_tool: Q4's predicted tool matches the empirically-invoked tool "
              f"{q4_matches_emp_when_q3_call}/{q4_total_when_q3_call} = "
              f"{100*q4_matches_emp_when_q3_call/q4_total_when_q3_call:.1f}%")
    print()

    # Q2 vs empirical success
    print("Q2 (with-tool capability) verdict distribution by tool, and mean empirical SR:")
    print(f"{'tool':<28} {'Q2=yes':>8} {'Q2=no':>8} {'sr|yes':>8} {'sr|no':>8}")
    for tool in sorted(set(seeds[r]["tool_target"] or "none" for r in rids)):
        ryes = [r for r in rids if (seeds[r]["tool_target"] or "none") == tool and q2[r] == "yes"]
        rno = [r for r in rids if (seeds[r]["tool_target"] or "none") == tool and q2[r] == "no"]
        sr_yes = sum(emp[r]["success_rate"] for r in ryes) / len(ryes) if ryes else float("nan")
        sr_no = sum(emp[r]["success_rate"] for r in rno) / len(rno) if rno else float("nan")
        print(f"  {tool:<28} {len(ryes):>8} {len(rno):>8} {sr_yes:>8.3f} {sr_no:>8.3f}")


if __name__ == "__main__":
    main()
