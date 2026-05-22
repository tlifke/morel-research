"""Per-tool precision/recall/lift for the Opus 'trivial-task detector' framing.

Companion to `prediction_agreement_stats.py`. The corpus-wide summary
reduced Opus's predictions to a trivial-task detector and showed it
works for 12B but not 4B. This script asks: does that detector behave
differently across tool families?

For each tool_target (calculator, python_execute, datetime_now,
unit_convert, general_knowledge_lookup, user_knowledge_lookup) and each
target model (Gemma 3 4B IT, 12B IT) compute the 3x3 contingency
(predicted tertiary x empirical tertiary) and the trivial-endpoint
statistics: precision, baseline rate, lift, recall — with 95% percentile
bootstrap CIs resampled within tool, and paired (12B - 4B) deltas.

Run from repo root with:
  CORPUS=a3_bulk uv run \\
    studies/001-tool-calibration/investigations/006-temperature-prompt/scripts/prediction_agreement_per_tool.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
INVESTIGATION_ROOT = HERE.parent
STUDY_ROOT = INVESTIGATION_ROOT.parent.parent
RESULTS_ROOT = STUDY_ROOT / "results"

sys.path.insert(0, str(STUDY_ROOT))
sys.path.insert(0, str(INVESTIGATION_ROOT / "figures"))
from harness.parser import classify_trial  # noqa: E402
from corpus_config import select_corpus  # noqa: E402

CORPUS = select_corpus()
SEEDS_PATH = STUDY_ROOT / CORPUS.seeds_filename
DATE = "2026-05-12"
MODELS = ["gemma3:4b-it-qat", "gemma3:12b-it-qat"]
TERTIARY = ["trivial", "middle", "impossible"]
N_BOOT = 10_000
RNG = np.random.default_rng(20260522)


def _safe(m: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", m)


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


def _sr_per_record(model: str) -> dict[str, float]:
    path = RESULTS_ROOT / _safe(model) / CORPUS.results_filename_fmt.format(date=DATE)
    rows = [json.loads(l) for l in path.read_text().splitlines() if l]
    by = defaultdict(list)
    for r in rows:
        ok, _ = classify_trial(
            {"tool_target": r["tool_target"], "expected_tool_call": r["expected_tool_call"]},
            r.get("output") or r.get("output_preview", ""),
        )
        by[r["record_id"]].append(ok)
    return {k: sum(v) / len(v) for k, v in by.items()}


def _per_tool_arrays(seeds: list[dict], sr_map: dict[str, float]) -> dict[str, dict]:
    """Per-tool arrays of (pred_is_trivial, emp_is_trivial). Aligned, one row per record."""
    by_tool: dict[str, dict] = {}
    for s in seeds:
        rid = s["id"]
        if rid not in sr_map:
            continue
        tool = s["tool_target"] or "none"
        d = by_tool.setdefault(tool, {"pred_T": [], "emp_T": []})
        pred_T = 1 if _to_tertiary(s["difficulty_label"]["value"]) == "trivial" else 0
        emp_T = 1 if _to_tertiary(_bucket_of(sr_map[rid])) == "trivial" else 0
        d["pred_T"].append(pred_T)
        d["emp_T"].append(emp_T)
    for tool, d in by_tool.items():
        d["pred_T"] = np.array(d["pred_T"], dtype=int)
        d["emp_T"] = np.array(d["emp_T"], dtype=int)
    return by_tool


def _stats(pred_T: np.ndarray, emp_T: np.ndarray) -> dict:
    n = len(pred_T)
    pred_trivial_n = int(pred_T.sum())
    emp_trivial_n = int(emp_T.sum())
    if pred_trivial_n == 0:
        prec = float("nan")
    else:
        prec = float((pred_T & emp_T).sum() / pred_trivial_n)
    base = float(emp_trivial_n / n) if n else float("nan")
    lift = prec - base if not (np.isnan(prec) or np.isnan(base)) else float("nan")
    if emp_trivial_n == 0:
        recall = float("nan")
    else:
        recall = float((pred_T & emp_T).sum() / emp_trivial_n)
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
        return {"lo": None, "hi": None, "n_finite": 0}
    return {
        "lo": float(np.percentile(finite, 2.5)),
        "hi": float(np.percentile(finite, 97.5)),
        "n_finite": int(len(finite)),
    }


def _bootstrap_per_tool(by_tool_4b: dict, by_tool_12b: dict) -> dict:
    """For each tool, do a single paired bootstrap (records resampled the same
    way for 4B and 12B since the predictions are shared). Returns per-tool
    point estimates + CIs + paired diff CIs."""
    out: dict[str, dict] = {}
    tools = sorted(set(by_tool_4b) & set(by_tool_12b))
    for tool in tools:
        d4 = by_tool_4b[tool]
        d12 = by_tool_12b[tool]
        pred = d4["pred_T"]
        emp4 = d4["emp_T"]
        emp12 = d12["emp_T"]
        n = len(pred)
        point_4b = _stats(pred, emp4)
        point_12b = _stats(pred, emp12)
        keys = ["precision", "baseline", "lift", "recall"]
        boot_4b = {k: np.empty(N_BOOT) for k in keys}
        boot_12b = {k: np.empty(N_BOOT) for k in keys}
        boot_diff = {k: np.empty(N_BOOT) for k in keys}
        idx_all = np.arange(n)
        for b in range(N_BOOT):
            idx = RNG.choice(idx_all, size=n, replace=True)
            s4 = _stats(pred[idx], emp4[idx])
            s12 = _stats(pred[idx], emp12[idx])
            for k in keys:
                boot_4b[k][b] = s4[k]
                boot_12b[k][b] = s12[k]
                boot_diff[k][b] = s12[k] - s4[k]
        diff_stat = {}
        for k in keys:
            ci = _ci(boot_diff[k])
            finite = boot_diff[k][np.isfinite(boot_diff[k])]
            if len(finite):
                # two-sided p that diff is zero (proportion of resamples on the wrong side of zero)
                point = point_12b[k] - point_4b[k]
                if np.isnan(point):
                    p = None
                else:
                    centered = finite - point
                    p = float(min(1.0, 2 * min(
                        (centered >= point).mean(),
                        (centered <= point).mean(),
                    )))
            else:
                p = None
            diff_stat[k] = {
                "point": (point_12b[k] - point_4b[k]) if not (np.isnan(point_12b[k]) or np.isnan(point_4b[k])) else None,
                "ci": ci,
                "p_two_sided": p,
            }
        out[tool] = {
            "n": n,
            "point": {"gemma3:4b-it-qat": point_4b, "gemma3:12b-it-qat": point_12b},
            "ci_4b": {k: _ci(boot_4b[k]) for k in keys},
            "ci_12b": {k: _ci(boot_12b[k]) for k in keys},
            "paired_diff_12b_minus_4b": diff_stat,
        }
    return out


def _print(per_tool: dict, model: str) -> None:
    print(f"\n=== {model} ===")
    print(f"{'tool':<28} {'n':>4} {'prec':>6} {'CI':>22} {'base':>6} {'lift_pp':>10} {'CI_lift':>22} {'recall':>7}")
    for tool in sorted(per_tool):
        d = per_tool[tool]
        p = d["point"][model]
        ci_p = d["ci_4b" if "4b" in model else "ci_12b"]
        prec = f"{p['precision']:.3f}" if not np.isnan(p['precision']) else "  —  "
        base = f"{p['baseline']:.3f}"
        lift_pp = f"{p['lift']*100:+.1f}"
        ci_prec = ci_p["precision"]
        ci_prec_s = f"[{ci_prec['lo']:.3f},{ci_prec['hi']:.3f}]" if ci_prec["lo"] is not None else "[—]"
        ci_lift = ci_p["lift"]
        ci_lift_s = f"[{ci_lift['lo']*100:+.1f},{ci_lift['hi']*100:+.1f}]" if ci_lift["lo"] is not None else "[—]"
        rec = f"{p['recall']:.3f}" if not np.isnan(p['recall']) else "  —  "
        print(f"{tool:<28} {d['n']:>4} {prec:>6} {ci_prec_s:>22} {base:>6} {lift_pp:>10} {ci_lift_s:>22} {rec:>7}")


def _print_paired(per_tool: dict) -> None:
    print(f"\n=== paired delta (12B - 4B) ===")
    print(f"{'tool':<28} {'Δprec':>10} {'CI':>22} {'p':>6} {'Δlift_pp':>10} {'CI':>22} {'p':>6}")
    for tool in sorted(per_tool):
        d = per_tool[tool]["paired_diff_12b_minus_4b"]
        dp = d["precision"]
        dl = d["lift"]
        dp_s = f"{dp['point']:+.3f}" if dp["point"] is not None else "  —  "
        ci_p = dp["ci"]
        ci_p_s = f"[{ci_p['lo']:+.3f},{ci_p['hi']:+.3f}]" if ci_p["lo"] is not None else "[—]"
        p_p = f"{dp['p_two_sided']:.3f}" if dp["p_two_sided"] is not None else "  —  "
        dl_s = f"{dl['point']*100:+.1f}" if dl["point"] is not None else "  —  "
        ci_l = dl["ci"]
        ci_l_s = f"[{ci_l['lo']*100:+.1f},{ci_l['hi']*100:+.1f}]" if ci_l["lo"] is not None else "[—]"
        p_l = f"{dl['p_two_sided']:.3f}" if dl["p_two_sided"] is not None else "  —  "
        print(f"{tool:<28} {dp_s:>10} {ci_p_s:>22} {p_p:>6} {dl_s:>10} {ci_l_s:>22} {p_l:>6}")


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    sr_4b = _sr_per_record("gemma3:4b-it-qat")
    sr_12b = _sr_per_record("gemma3:12b-it-qat")
    by_tool_4b = _per_tool_arrays(seeds, sr_4b)
    by_tool_12b = _per_tool_arrays(seeds, sr_12b)

    per_tool = _bootstrap_per_tool(by_tool_4b, by_tool_12b)
    _print(per_tool, "gemma3:4b-it-qat")
    _print(per_tool, "gemma3:12b-it-qat")
    _print_paired(per_tool)

    out = {
        "corpus": CORPUS.name,
        "date": DATE,
        "n_bootstrap": N_BOOT,
        "per_tool": per_tool,
    }
    out_path = INVESTIGATION_ROOT / "results-analysis" / f"prediction_agreement_per_tool_{CORPUS.name}_{DATE}.json"
    out_path.write_text(json.dumps(out, indent=2, default=lambda x: None if (isinstance(x, float) and np.isnan(x)) else x))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
