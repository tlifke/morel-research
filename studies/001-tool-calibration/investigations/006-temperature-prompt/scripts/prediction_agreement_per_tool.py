"""Per-tool precision/recall for the Opus 'trivial-task detector' framing.

Companion to `prediction_agreement_stats.py`. The corpus-wide summary
reduced Opus's predictions to a trivial-task detector and showed it
works for 12B but not 4B. This script asks: does that detector behave
differently across tool families?

For each tool_target (calculator, python_execute, datetime_now,
unit_convert, general_knowledge_lookup, user_knowledge_lookup) and each
target model (Gemma 3 4B IT, 12B IT) compute the 3x3 contingency
(predicted tertiary × empirical tertiary) and the trivial-endpoint
statistics: precision, baseline rate, lift, recall.

The hypothesis from investigation 007 (F5 dot plot) is that gkl / ukl
records cluster at the empirical-trivial top of the corpus regardless
of curator label, while python_execute records spread vertically. If
that surface pattern is real, the trivial detector should be
high-baseline / harder-to-add-lift for gkl + ukl, and lower-baseline /
more room to lift for python_execute.

Run from repo root with:
  CORPUS=a3_bulk uv run \
    studies/001-tool-calibration/investigations/006-temperature-prompt/scripts/prediction_agreement_per_tool.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

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


def _table(seeds: list[dict], sr_map: dict[str, float], model: str) -> dict:
    by_tool: dict[str, dict] = {}
    for s in seeds:
        rid = s["id"]
        if rid not in sr_map:
            continue
        tool = s["tool_target"] or "none"
        d = by_tool.setdefault(tool, {
            "n": 0,
            "counts": {p: {e: 0 for e in TERTIARY} for p in TERTIARY},
            "emp_marg": {e: 0 for e in TERTIARY},
        })
        pred = _to_tertiary(s["difficulty_label"]["value"])
        emp = _to_tertiary(_bucket_of(sr_map[rid]))
        d["counts"][pred][emp] += 1
        d["emp_marg"][emp] += 1
        d["n"] += 1
    rows = []
    for tool in sorted(by_tool):
        d = by_tool[tool]
        n = d["n"]
        triv_pred_total = sum(d["counts"]["trivial"][e] for e in TERTIARY)
        triv_correct = d["counts"]["trivial"]["trivial"]
        prec_triv = triv_correct / triv_pred_total if triv_pred_total else None
        base_triv = d["emp_marg"]["trivial"] / n
        lift = (prec_triv - base_triv) if prec_triv is not None else None
        rec_triv = (triv_correct / d["emp_marg"]["trivial"]) if d["emp_marg"]["trivial"] else None
        rows.append({
            "tool": tool,
            "n": n,
            "pred_trivial_n": triv_pred_total,
            "emp_trivial_n": d["emp_marg"]["trivial"],
            "precision_trivial": prec_triv,
            "baseline_trivial": base_triv,
            "lift_pp": (lift * 100) if lift is not None else None,
            "recall_trivial": rec_triv,
        })
    return {"model": model, "rows": rows, "by_tool_counts": by_tool}


def _print(report: dict) -> None:
    print(f"\n=== {report['model']} ===")
    print(f"{'tool':<28} {'n':>4} {'pred_T':>7} {'emp_T':>6} {'prec':>6} {'base':>6} {'lift_pp':>8} {'recall':>7}")
    for r in report["rows"]:
        prec = f"{r['precision_trivial']:.3f}" if r["precision_trivial"] is not None else "  —  "
        base = f"{r['baseline_trivial']:.3f}"
        lift = f"{r['lift_pp']:+.1f}" if r["lift_pp"] is not None else "  —  "
        rec = f"{r['recall_trivial']:.3f}" if r["recall_trivial"] is not None else "  —  "
        print(f"{r['tool']:<28} {r['n']:>4} {r['pred_trivial_n']:>7} {r['emp_trivial_n']:>6} "
              f"{prec:>6} {base:>6} {lift:>8} {rec:>7}")


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    out = {"corpus": CORPUS.name, "date": DATE, "per_model": {}}
    for m in MODELS:
        sr_map = _sr_per_record(m)
        rep = _table(seeds, sr_map, m)
        _print(rep)
        out["per_model"][m] = {"rows": rep["rows"]}
    out_path = INVESTIGATION_ROOT / "results-analysis" / f"prediction_agreement_per_tool_{CORPUS.name}_{DATE}.json"
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
