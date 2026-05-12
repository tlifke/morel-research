"""Exploratory analysis for investigation 007.

Goal: predict empirical success_rate per (record, model) from prompt-surface
features. Diagnose why curator difficulty axes under-predict.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
STUDY = REPO / "studies" / "001-tool-calibration"
sys.path.insert(0, str(STUDY))
from harness.parser import classify_trial  # noqa: E402

SEED_FILES = [STUDY / "seeds.jsonl", STUDY / "bulk_seeds.jsonl"]
RESULT_FILES = {
    ("4B", "neutral_A1"): STUDY / "results/gemma3_4b-it-qat/006_C_neutral_temp1_2026-05-12.jsonl",
    ("4B", "neutral_bulk"): STUDY / "results/gemma3_4b-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl",
    ("12B", "neutral_A1"): STUDY / "results/gemma3_12b-it-qat/006_C_neutral_temp1_2026-05-12.jsonl",
    ("12B", "neutral_bulk"): STUDY / "results/gemma3_12b-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl",
}


def load_jsonl(p):
    with open(p) as f:
        return [json.loads(l) for l in f if l.strip()]


def load_seeds():
    seeds = {}
    for f in SEED_FILES:
        for r in load_jsonl(f):
            seeds[r["id"]] = r
    return seeds


def rescore_records(seeds):
    """For each (model, corpus), aggregate success_rate per record by rescoring raw output."""
    out = {}
    for (model, corpus), path in RESULT_FILES.items():
        if not path.exists():
            continue
        counts = defaultdict(lambda: [0, 0])
        for trial in load_jsonl(path):
            rid = trial["record_id"]
            if rid not in seeds:
                continue
            success, _ = classify_trial(seeds[rid], trial.get("output", ""))
            counts[rid][0] += int(success)
            counts[rid][1] += 1
        out[(model, corpus)] = {rid: (s, n) for rid, (s, n) in counts.items()}
    return out


# ---- Feature engineering ----

TOOL_KEYWORDS = {
    "calculator": ["compute", "calculate", "calculator", "×", "x ", "*", "÷", "/", "what is "],
    "python_execute": ["python", "script", "code", "program"],
    "datetime_now": ["today", "now", "current date", "current time", "what date"],
    "unit_convert": ["convert", "in kilograms", "in meters", "to kg", "to lb", "to ft", "to °", "fahrenheit", "celsius"],
    "general_knowledge_lookup": ["who", "when did", "look up", "tell me", "what year"],
    "user_knowledge_lookup": ["my ", "i am ", "i'm ", "mine"],
}

TEMPORAL_RE = re.compile(r"\b(today|now|tomorrow|yesterday|currently|this (week|month|year))\b", re.I)
DATE_RE = re.compile(r"\b(20\d{2}|19\d{2})\b|\b(january|february|march|april|may|june|july|august|september|october|november|december)\b", re.I)
NUM_OP_RE = re.compile(r"[×÷*/+\-]\s*\d|\d\s*[×÷*/+\-]")
NUM_RE = re.compile(r"\d+")
FIRST_PERSON_RE = re.compile(r"\b(my|i am|i'm|me|mine|i\b)\b", re.I)
TOOL_NAME_RE = re.compile(r"\b(calculator|python|compute|search|look up|lookup|convert)\b", re.I)


def features(record):
    p = record["user_prompt"]
    pl = p.lower()
    f = {
        "tool_target": record["tool_target"],
        "pair_type": record["pair_type"],
        "condition": record["condition"],
        "frequency_class": record.get("frequency_class") or "unknown",
        "curator_difficulty": record["difficulty_label"]["value"],
        "human_feasibility": record.get("human_feasibility") or "unknown",
        "register_tone": record.get("register_tone") or "unknown",
        "register_form": record.get("register_form") or "unknown",
        "register_length": record.get("register_length") or "unknown",
        "expected_tool_call": int(bool(record["expected_tool_call"])),
        "prompt_length_words": len(p.split()),
        "prompt_length_chars": len(p),
        "has_first_person": int(bool(FIRST_PERSON_RE.search(p))),
        "has_temporal_word": int(bool(TEMPORAL_RE.search(pl))),
        "has_date_or_year": int(bool(DATE_RE.search(p))),
        "has_num_operator": int(bool(NUM_OP_RE.search(p))),
        "num_count": len(NUM_RE.findall(p)),
        "has_tool_name_keyword": int(bool(TOOL_NAME_RE.search(p))),
        "has_compute_verb": int("compute" in pl or "calculate" in pl),
        "has_convert_verb": int("convert" in pl),
        "has_today_now": int("today" in pl or " now" in pl or pl.startswith("now")),
        "has_question_mark": int("?" in p),
        "starts_with_imperative": int(record.get("register_form") == "imperative"),
    }
    # in-prompt answer heuristic: is there a substring "X is Y" or known field declarations,
    # *and* the question references that?
    f["has_declared_fact"] = int(bool(re.search(r"\b(is|are|=)\b\s+\w", p) and "?" in p))
    return f


def to_dict_records(seeds, scores):
    """Build flat per-(record, model) frame."""
    rows = []
    for (model, corpus), srmap in scores.items():
        for rid, (s, n) in srmap.items():
            if n == 0:
                continue
            sr = s / n
            rec = seeds[rid]
            row = {"record_id": rid, "model": model, "corpus": corpus,
                   "success_rate": sr, "n_trials": n}
            row.update(features(rec))
            rows.append(row)
    return rows


def spearman(xs, ys):
    """Spearman without scipy: rank both, compute Pearson on ranks."""
    n = len(xs)
    if n < 3:
        return None, n
    rx = _rank(xs)
    ry = _rank(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    dx = sum((a - mx) ** 2 for a in rx) ** 0.5
    dy = sum((b - my) ** 2 for b in ry) ** 0.5
    if dx == 0 or dy == 0:
        return 0.0, n
    return num / (dx * dy), n


def _rank(xs):
    # average rank for ties
    idx = sorted(range(len(xs)), key=lambda i: xs[i])
    ranks = [0.0] * len(xs)
    i = 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[idx[j + 1]] == xs[idx[i]]:
            j += 1
        avg = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[idx[k]] = avg
        i = j + 1
    return ranks


CURATOR_ORDER = {"trivial": 0, "easy": 1, "medium": 2, "hard": 3, "extreme": 4}
FREQ_ORDER = {"rare": 0, "uncommon": 1, "common": 2, "very_common": 3, "unknown": 1.5}
FEAS_ORDER = {"unaided": 0, "aided": 1, "infeasible": 2, "unknown": 1}
LEN_ORDER = {"terse": 0, "medium": 1, "verbose": 2, "unknown": 1}


def numerify(rows):
    """Replace categorical features with ordinals where ordering is natural; one-hot for tool_target."""
    tools = sorted({r["tool_target"] for r in rows})
    for r in rows:
        r["curator_difficulty_ord"] = CURATOR_ORDER.get(r["curator_difficulty"], 2)
        r["frequency_ord"] = FREQ_ORDER.get(r["frequency_class"], 1.5)
        r["feasibility_ord"] = FEAS_ORDER.get(r["human_feasibility"], 1)
        r["register_length_ord"] = LEN_ORDER.get(r["register_length"], 1)
        r["pair_type_A"] = int(r["pair_type"] == "A")
        for t in tools:
            r[f"tool_{t}"] = int(r["tool_target"] == t)
        r["cond_warranted"] = int(r["condition"] == "tool_warranted")
        r["cond_trivial"] = int(r["condition"] == "tool_trivial")
        r["cond_none"] = int(r["condition"] == "no_tools_available")
    return tools


NUMERIC_FEATURES = [
    "curator_difficulty_ord", "frequency_ord", "feasibility_ord",
    "register_length_ord", "pair_type_A", "expected_tool_call",
    "prompt_length_words", "prompt_length_chars",
    "has_first_person", "has_temporal_word", "has_date_or_year",
    "has_num_operator", "num_count",
    "has_tool_name_keyword", "has_compute_verb", "has_convert_verb",
    "has_today_now", "has_question_mark", "has_declared_fact",
    "cond_warranted", "cond_trivial", "cond_none",
]


def correlate_features(rows, model):
    sub = [r for r in rows if r["model"] == model]
    ys = [r["success_rate"] for r in sub]
    out = []
    for feat in NUMERIC_FEATURES:
        xs = [r[feat] for r in sub]
        rho, n = spearman(xs, ys)
        out.append((feat, rho, n))
    return out


def correlate_per_tool(rows, model):
    """Within-tool Spearman, since tool_target dominates."""
    sub = [r for r in rows if r["model"] == model]
    tools = sorted({r["tool_target"] for r in sub})
    out = {}
    for t in tools:
        sub_t = [r for r in sub if r["tool_target"] == t]
        ys = [r["success_rate"] for r in sub_t]
        rows_out = []
        for feat in NUMERIC_FEATURES:
            xs = [r[feat] for r in sub_t]
            rho, n = spearman(xs, ys)
            rows_out.append((feat, rho, n))
        out[t] = (len(sub_t), rows_out)
    return out


def main():
    seeds = load_seeds()
    scores = rescore_records(seeds)
    print("Aggregates:")
    for k, v in scores.items():
        print(f"  {k}: {len(v)} records, total trials={sum(n for _, n in v.values())}")
    rows = to_dict_records(seeds, scores)
    numerify(rows)

    out = {"per_cell_summary": {}, "global_corr": {}, "per_tool_corr": {}}
    for model in ["4B", "12B"]:
        msub = [r for r in rows if r["model"] == model]
        if not msub:
            continue
        out["per_cell_summary"][model] = {
            "n_records": len(msub),
            "mean_sr": sum(r["success_rate"] for r in msub) / len(msub),
            "by_corpus": {c: sum(1 for r in msub if r["corpus"] == c) for c in {r["corpus"] for r in msub}},
        }
        out["global_corr"][model] = correlate_features(rows, model)
        out["per_tool_corr"][model] = correlate_per_tool(rows, model)

    # Save raw rows for downstream use
    with open(Path(__file__).parent / "_rows.jsonl", "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    with open(Path(__file__).parent / "_corr.json", "w") as f:
        json.dump(out, f, indent=2, default=str)

    print("\nGlobal Spearman vs success_rate (sorted by |rho|):")
    for model in ["4B", "12B"]:
        if model not in out["global_corr"]:
            continue
        print(f"\n  Model {model} (n={out['per_cell_summary'][model]['n_records']}):")
        corrs = sorted(out["global_corr"][model], key=lambda x: -abs(x[1] or 0))
        for feat, rho, n in corrs:
            if rho is None:
                continue
            print(f"    {feat:30s} rho={rho:+.3f}  n={n}")


if __name__ == "__main__":
    main()
