"""Four-facet analysis of self-prediction baseline.

Ingests the four `<question>_n<n>_<date>.jsonl` result files for one
model and produces per-tool stats for each of the four facets:

  F1 (Q1: capability without tools): does the model know whether it
     could answer without tools? Scored against ANSWER_CORRECTNESS
     ground truth (programmatic grading; falls back to A4 modal-success
     if grading is unavailable).
  F2 (Q2: capability with tools): scored against answer correctness on
     A4 trials where the appropriate tool *was* invoked.
  F3 (Q3: behavior): does the model's predicted behavior match the
     A4 modal empirical behavior?
  F4 (Q4: tool selection): does the model's predicted tool match the
     A4 modally invoked tool (on trials where a tool was invoked)?

Per facet, per tool: precision, baseline, lift, recall with 95%
percentile bootstrap CIs. Optional paired comparison to Opus's external
predictions where applicable.

Writes JSON to `results-analysis/self_prediction_<date>.json`.

Run from repo root:
  uv run studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline/analyze.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
INVESTIGATION_ROOT = HERE
STUDIES_ROOT = HERE.parents[2]
STUDY_001_ROOT = STUDIES_ROOT / "001-tool-calibration"
A4_RESULTS_ROOT = STUDY_001_ROOT / "results"
SEEDS_PATH = STUDY_001_ROOT / "bulk_seeds.jsonl"
RESULTS_ROOT = HERE / "results"

sys.path.insert(0, str(STUDY_001_ROOT))
from harness.parser import classify_trial, parse_tool_calls  # noqa: E402

A4_DATE = "2026-05-12"
A4_TAG = "007_bulk_neutral_temp1"
N_BOOT = 10_000
RNG = np.random.default_rng(20260522)


def _safe(model: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _load_self_pred(model: str, question: str) -> dict[str, list[dict]]:
    """Group self-prediction trials by record_id."""
    pattern = f"{question}_n*_*.jsonl"
    candidates = sorted((RESULTS_ROOT / _safe(model)).glob(pattern))
    if not candidates:
        return {}
    out: dict[str, list[dict]] = defaultdict(list)
    for path in candidates:
        for line in path.read_text().splitlines():
            if not line:
                continue
            r = json.loads(line)
            out[r["record_id"]].append(r)
    return dict(out)


def _modal_self_pred(trials: list[dict], answer_keys: tuple[str, ...]) -> tuple[str | None, int, int]:
    """Modal answer across trials. Returns (modal, modal_count, total_valid)."""
    answers = []
    for t in trials:
        parsed = t.get("parsed")
        if not parsed or t.get("validate_error"):
            continue
        answers.append("|".join(str(parsed.get(k)) for k in answer_keys))
    if not answers:
        return None, 0, 0
    counts = Counter(answers)
    top = counts.most_common(1)[0]
    return top[0], top[1], len(answers)


def _empirical_per_record(model: str) -> dict[str, dict]:
    """For each record, summarize A4 trials: modal outcome, modal behavior, modal tool."""
    path = A4_RESULTS_ROOT / _safe(model) / f"{A4_TAG}_{A4_DATE}.jsonl"
    by_record: dict[str, list[dict]] = defaultdict(list)
    for line in path.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        by_record[r["record_id"]].append(r)
    out: dict[str, dict] = {}
    for rid, trials in by_record.items():
        outcomes: list[str] = []
        behaviors: list[str] = []
        tools_called: list[str] = []
        for t in trials:
            ok, err = classify_trial(
                {"tool_target": t["tool_target"], "expected_tool_call": t["expected_tool_call"]},
                t.get("output") or t.get("output_preview", ""),
            )
            outcomes.append("success" if ok else (err or "under_call"))
            calls = parse_tool_calls(t.get("output") or t.get("output_preview", ""))
            if calls:
                behaviors.append("call_tool")
                tools_called.append(calls[0].name)
            else:
                behaviors.append("answer_directly")
        outcome_counts = Counter(outcomes)
        behavior_counts = Counter(behaviors)
        tool_counts = Counter(tools_called) if tools_called else Counter()
        n = len(trials)
        out[rid] = {
            "n_trials": n,
            "outcome_mode": outcome_counts.most_common(1)[0][0],
            "outcome_mode_count": outcome_counts.most_common(1)[0][1],
            "outcome_dist": dict(outcome_counts),
            "behavior_mode": behavior_counts.most_common(1)[0][0],
            "behavior_mode_count": behavior_counts.most_common(1)[0][1],
            "tool_mode": (tool_counts.most_common(1)[0][0] if tool_counts else None),
            "success_rate": outcome_counts.get("success", 0) / n if n else float("nan"),
        }
    return out


# Facet score functions: each returns (pred_is_correct, has_ground_truth)
# where pred_is_correct is the boolean and has_ground_truth indicates
# whether we have a defensible comparison.


def score_f3_behavior(self_pred_modal: str | None, emp: dict, seed: dict) -> tuple[int | None, str | None]:
    """F3: did Q3's predicted behavior match A4 modal empirical behavior?"""
    if self_pred_modal is None:
        return None, "self_pred_missing"
    if emp["behavior_mode_count"] / emp["n_trials"] < 0.6:
        return None, "empirical_ambiguous"
    return (1 if self_pred_modal == emp["behavior_mode"] else 0), None


def f3_error_direction(self_pred_modal: str | None, emp: dict) -> str | None:
    """For F3, classify the error direction. Returns one of
    {'correct', 'under_predicted_tool_use', 'over_predicted_tool_use'} or None."""
    if self_pred_modal is None:
        return None
    if emp["behavior_mode_count"] / emp["n_trials"] < 0.6:
        return None
    emp_b = emp["behavior_mode"]
    if self_pred_modal == emp_b:
        return "correct"
    if self_pred_modal == "answer_directly" and emp_b == "call_tool":
        return "under_predicted_tool_use"
    if self_pred_modal == "call_tool" and emp_b == "answer_directly":
        return "over_predicted_tool_use"
    return None


def score_f4_tool(self_pred_modal: str | None, emp: dict, seed: dict) -> tuple[int | None, str | None]:
    """F4: did Q4's predicted tool match the A4 modally-invoked tool?
    Only defined when the empirical behavior was 'call_tool'."""
    if self_pred_modal is None:
        return None, "self_pred_missing"
    if emp["behavior_mode"] != "call_tool":
        return None, "empirical_no_tool_call"
    if emp["tool_mode"] is None:
        return None, "empirical_no_tool_mode"
    return (1 if self_pred_modal == emp["tool_mode"] else 0), None


def _bucket_of(sr: float) -> str:
    if sr < 0.05: return "extreme"
    if sr < 0.30: return "hard"
    if sr < 0.70: return "medium"
    if sr < 0.95: return "easy"
    return "trivial"


def _stats(scored: list[int]) -> dict:
    if not scored:
        return {"n": 0, "accuracy": float("nan")}
    arr = np.array(scored, dtype=int)
    return {"n": int(len(arr)), "accuracy": float(arr.mean())}


def _ci_accuracy(scored: list[int]) -> dict:
    if not scored:
        return {"lo": None, "hi": None}
    arr = np.array(scored, dtype=int)
    boot = np.empty(N_BOOT)
    for b in range(N_BOOT):
        boot[b] = arr[RNG.choice(len(arr), len(arr), replace=True)].mean()
    return {"lo": float(np.percentile(boot, 2.5)), "hi": float(np.percentile(boot, 97.5))}


def _per_tool_facet(rows: list[dict], facet_name: str) -> dict:
    by_tool: dict[str, list[int]] = defaultdict(list)
    overall: list[int] = []
    excluded_reasons: dict[str, int] = defaultdict(int)
    for row in rows:
        if row["score"] is None:
            excluded_reasons[row.get("exclude_reason", "unknown")] += 1
            continue
        by_tool[row["tool"]].append(row["score"])
        overall.append(row["score"])
    per_tool = {}
    for tool, scored in by_tool.items():
        s = _stats(scored)
        s["ci"] = _ci_accuracy(scored)
        per_tool[tool] = s
    return {
        "facet": facet_name,
        "per_tool": per_tool,
        "overall": {**_stats(overall), "ci": _ci_accuracy(overall)},
        "excluded": dict(excluded_reasons),
    }


def main(model: str = "gemma3:4b-it-qat") -> None:
    seeds = {s["id"]: s for s in (json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l)}

    self_preds = {
        "q1": _load_self_pred(model, "q1"),
        "q2": _load_self_pred(model, "q2"),
        "q3": _load_self_pred(model, "q3"),
        "q4": _load_self_pred(model, "q4"),
    }
    emp = _empirical_per_record(model)
    print(f"loaded: q1={len(self_preds['q1'])} q2={len(self_preds['q2'])} "
          f"q3={len(self_preds['q3'])} q4={len(self_preds['q4'])} A4_empirical={len(emp)}")

    out: dict = {"model": model, "n_records_with_a4": len(emp), "facets": {}}

    f3_rows = []
    for rid, trials in self_preds["q3"].items():
        if rid not in emp or rid not in seeds:
            continue
        modal, mcount, n = _modal_self_pred(trials, ("predicted_behavior",))
        score, reason = score_f3_behavior(modal, emp[rid], seeds[rid])
        direction = f3_error_direction(modal, emp[rid])
        f3_rows.append({
            "record_id": rid,
            "tool": seeds[rid]["tool_target"] or "none",
            "score": score,
            "exclude_reason": reason,
            "direction": direction,
            "self_pred_modal": modal,
            "self_pred_modal_count": mcount,
            "self_pred_total": n,
            "empirical_mode": emp[rid]["behavior_mode"],
        })
    out["facets"]["F3_behavior"] = _per_tool_facet(f3_rows, "F3_behavior")

    direction_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"correct": 0, "under_predicted_tool_use": 0, "over_predicted_tool_use": 0})
    overall_dir = {"correct": 0, "under_predicted_tool_use": 0, "over_predicted_tool_use": 0}
    for row in f3_rows:
        if row["direction"] is None:
            continue
        direction_counts[row["tool"]][row["direction"]] += 1
        overall_dir[row["direction"]] += 1
    out["facets"]["F3_behavior"]["direction_per_tool"] = dict(direction_counts)
    out["facets"]["F3_behavior"]["direction_overall"] = overall_dir

    f4_rows = []
    for rid, trials in self_preds["q4"].items():
        if rid not in emp or rid not in seeds:
            continue
        modal, mcount, n = _modal_self_pred(trials, ("predicted_tool",))
        score, reason = score_f4_tool(modal, emp[rid], seeds[rid])
        f4_rows.append({
            "record_id": rid,
            "tool": seeds[rid]["tool_target"] or "none",
            "score": score,
            "exclude_reason": reason,
            "self_pred_modal": modal,
            "empirical_tool_mode": emp[rid].get("tool_mode"),
        })
    out["facets"]["F4_tool_selection"] = _per_tool_facet(f4_rows, "F4_tool_selection")

    out["facets"]["F1_capability_no_tools"] = {
        "facet": "F1_capability_no_tools",
        "status": "deferred",
        "note": "F1 needs answer-correctness grading (programmatic or LLM-judge). "
                "Self-prediction trials are collected; scoring deferred until grading lands.",
    }
    out["facets"]["F2_capability_with_tools"] = {
        "facet": "F2_capability_with_tools",
        "status": "deferred",
        "note": "F2 needs answer-correctness grading on A4 trials where the appropriate "
                "tool was invoked. Self-prediction trials are collected; scoring deferred.",
    }

    print("\n=== F3 behavior ===")
    _print_facet(out["facets"]["F3_behavior"])
    print("\n=== F4 tool selection ===")
    _print_facet(out["facets"]["F4_tool_selection"])

    import datetime as dt
    out_dir = INVESTIGATION_ROOT / "results-analysis"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / f"self_prediction_{dt.date.today().isoformat()}.json"
    out_path.write_text(json.dumps(out, indent=2, default=lambda x: None if (isinstance(x, float) and np.isnan(x)) else x))
    print(f"\nwrote {out_path}")


def _print_facet(facet: dict) -> None:
    if facet.get("status") == "deferred":
        print(f"  deferred: {facet['note']}")
        return
    overall = facet["overall"]
    print(f"  overall: n={overall['n']} acc={overall['accuracy']:.3f} "
          f"CI=[{overall['ci']['lo']:.3f},{overall['ci']['hi']:.3f}]" if overall['n'] else "  overall: n=0")
    for tool, s in facet["per_tool"].items():
        ci = s["ci"]
        print(f"    {tool:<28} n={s['n']:>3} acc={s['accuracy']:.3f} "
              f"CI=[{ci['lo']:.3f},{ci['hi']:.3f}]")
    if facet["excluded"]:
        print(f"  excluded: {facet['excluded']}")
    if "direction_overall" in facet:
        d = facet["direction_overall"]
        total_err = d["under_predicted_tool_use"] + d["over_predicted_tool_use"]
        if total_err:
            pct_under = 100 * d["under_predicted_tool_use"] / total_err
            print(f"  error direction: under={d['under_predicted_tool_use']} "
                  f"over={d['over_predicted_tool_use']} ({pct_under:.1f}% under)")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="gemma3:4b-it-qat")
    args = p.parse_args()
    main(args.model)
