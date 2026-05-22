"""Analyze self-prediction baseline results.

For each (record, model) pair:
  1. Derive the predicted-outcome class from the model's structured
     output and the curator metadata.
  2. Compare to the empirical modal outcome from the A4 grading
     (results/<model_safe>/007_bulk_neutral_temp1_2026-05-12.jsonl
     under study 001).
  3. Compute per-tool precision/baseline/lift/recall on the trivial
     endpoint, with 95% percentile bootstrap CIs.
  4. Compute paired (12B − 4B) deltas using shared resampling indices.
  5. Optionally compare to Opus's external predictions (Q2 secondary
     analysis), pulled from the seed's `difficulty_label`.

Writes a JSON sibling next to this file under
`results-analysis/self_prediction_<date>.json`.

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

sys.path.insert(0, str(STUDY_001_ROOT))
from harness.parser import classify_trial  # noqa: E402

MODELS = ["gemma3:4b-it-qat", "gemma3:12b-it-qat"]
TERTIARY = ["trivial", "middle", "impossible"]
N_BOOT = 10_000
RNG = np.random.default_rng(20260522)
A4_DATE = "2026-05-12"
A4_TAG = "007_bulk_neutral_temp1"
SELF_PREDICT_TAG = "self_predict_v1"


def _safe(model: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _bucket_of(sr: float) -> str:
    if sr < 0.05: return "extreme"
    if sr < 0.30: return "hard"
    if sr < 0.70: return "medium"
    if sr < 0.95: return "easy"
    return "trivial"


def _to_tertiary(label: str) -> str:
    if label == "trivial": return "trivial"
    if label == "extreme": return "impossible"
    return "middle"


def _derive_predicted_outcome(parsed: dict, tool_target: str, expected_tool_call: bool) -> str | None:
    """Convert SelfPredictionResponse fields + curator metadata to one of
    {success, over_call, under_call, wrong_tool}, or None if malformed."""
    if not isinstance(parsed, dict):
        return None
    behavior = parsed.get("predicted_behavior")
    tool = parsed.get("predicted_tool")
    if behavior == "call_tool":
        if not expected_tool_call:
            return "over_call"
        if tool == tool_target:
            return "success"
        return "wrong_tool"
    elif behavior == "answer_directly":
        if expected_tool_call:
            return "under_call"
        return "success"
    return None


def _empirical_outcome(model: str, expected_by_id: dict[str, dict]) -> dict[str, str]:
    """For each record, the modal outcome across A4 trials. Records
    with a tied mode (e.g. 5/5 split) are marked 'ambiguous' and
    excluded from headline precision."""
    path = A4_RESULTS_ROOT / _safe(model) / f"{A4_TAG}_{A4_DATE}.jsonl"
    by = defaultdict(list)
    for line in path.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        rid = r["record_id"]
        ok, err = classify_trial(
            {"tool_target": r["tool_target"], "expected_tool_call": r["expected_tool_call"]},
            r.get("output") or r.get("output_preview", ""),
        )
        outcome = "success" if ok else (err or "under_call")
        by[rid].append(outcome)
    out = {}
    for rid, outcomes in by.items():
        counts = Counter(outcomes)
        modal_count = max(counts.values())
        modes = [o for o, c in counts.items() if c == modal_count]
        if len(modes) > 1:
            out[rid] = "ambiguous"
        else:
            out[rid] = modes[0]
    return out


def _load_self_predictions(model: str) -> dict[str, dict]:
    """Load most-recent self-prediction file for a model."""
    candidates = sorted((INVESTIGATION_ROOT / "results" / _safe(model)).glob(f"{SELF_PREDICT_TAG}_*.jsonl"))
    if not candidates:
        return {}
    rows = [json.loads(l) for l in candidates[-1].read_text().splitlines() if l]
    out = {}
    for r in rows:
        out[r["record_id"]] = r
    return out


def _stats(pred_T: np.ndarray, emp_T: np.ndarray) -> dict:
    n = len(pred_T)
    pred_trivial_n = int(pred_T.sum())
    emp_trivial_n = int(emp_T.sum())
    prec = float((pred_T & emp_T).sum() / pred_trivial_n) if pred_trivial_n else float("nan")
    base = float(emp_trivial_n / n) if n else float("nan")
    lift = prec - base if not (np.isnan(prec) or np.isnan(base)) else float("nan")
    recall = float((pred_T & emp_T).sum() / emp_trivial_n) if emp_trivial_n else float("nan")
    return {
        "n": n,
        "pred_trivial_n": pred_trivial_n,
        "emp_trivial_n": emp_trivial_n,
        "precision": prec,
        "baseline": base,
        "lift": lift,
        "recall": recall,
    }


def _ci(samples: np.ndarray) -> dict:
    finite = samples[np.isfinite(samples)]
    if len(finite) == 0:
        return {"lo": None, "hi": None}
    return {
        "lo": float(np.percentile(finite, 2.5)),
        "hi": float(np.percentile(finite, 97.5)),
    }


def _bootstrap(per_tool: dict) -> dict:
    out: dict[str, dict] = {}
    for tool, d in per_tool.items():
        pred = d["pred_T"]
        emp = d["emp_T"]
        n = len(pred)
        point = _stats(pred, emp)
        keys = ["precision", "baseline", "lift", "recall"]
        boot = {k: np.empty(N_BOOT) for k in keys}
        idx_all = np.arange(n)
        for b in range(N_BOOT):
            idx = RNG.choice(idx_all, size=n, replace=True)
            s = _stats(pred[idx], emp[idx])
            for k in keys:
                boot[k][b] = s[k]
        out[tool] = {
            "n": n,
            "point": point,
            "ci": {k: _ci(boot[k]) for k in keys},
        }
    return out


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    seeds_by_id = {s["id"]: s for s in seeds}

    report: dict = {"a4_date": A4_DATE, "models": {}}
    for model in MODELS:
        self_preds = _load_self_predictions(model)
        emp_modes = _empirical_outcome(model, seeds_by_id)

        per_tool: dict[str, dict] = {}
        n_ambiguous = 0
        n_parse_fail = 0
        for rid, pred_row in self_preds.items():
            if rid not in seeds_by_id or rid not in emp_modes:
                continue
            if emp_modes[rid] == "ambiguous":
                n_ambiguous += 1
                continue
            seed = seeds_by_id[rid]
            pred_outcome = _derive_predicted_outcome(
                pred_row.get("parsed"),
                seed["tool_target"],
                seed["expected_tool_call"],
            )
            if pred_outcome is None:
                n_parse_fail += 1
                continue
            tool = seed["tool_target"] or "none"
            d = per_tool.setdefault(tool, {"pred_T": [], "emp_T": []})
            d["pred_T"].append(1 if pred_outcome == "success" else 0)
            d["emp_T"].append(1 if emp_modes[rid] == "success" else 0)

        for tool, d in per_tool.items():
            d["pred_T"] = np.array(d["pred_T"], dtype=int)
            d["emp_T"] = np.array(d["emp_T"], dtype=int)

        per_tool_stats = _bootstrap(per_tool)
        report["models"][model] = {
            "n_self_predictions": len(self_preds),
            "n_ambiguous_empirical": n_ambiguous,
            "n_parse_fail": n_parse_fail,
            "per_tool": per_tool_stats,
        }

        print(f"\n=== {model} ===")
        print(f"  n_self_predictions={len(self_preds)}  n_ambiguous={n_ambiguous}  parse_fail={n_parse_fail}")
        print(f"  {'tool':<28} {'n':>4} {'prec':>6} {'base':>6} {'lift_pp':>10} {'recall':>7}")
        for tool, s in per_tool_stats.items():
            p = s["point"]
            prec = f"{p['precision']:.3f}" if not np.isnan(p['precision']) else "  —  "
            base = f"{p['baseline']:.3f}"
            lift = f"{p['lift']*100:+.1f}" if not np.isnan(p['lift']) else "  —  "
            rec = f"{p['recall']:.3f}" if not np.isnan(p['recall']) else "  —  "
            print(f"  {tool:<28} {s['n']:>4} {prec:>6} {base:>6} {lift:>10} {rec:>7}")

    out_dir = INVESTIGATION_ROOT / "results-analysis"
    out_dir.mkdir(exist_ok=True)
    import datetime as dt
    date = dt.date.today().isoformat()
    out_path = out_dir / f"self_prediction_{date}.json"
    out_path.write_text(json.dumps(
        report, indent=2,
        default=lambda x: None if (isinstance(x, float) and np.isnan(x)) else x,
    ))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
