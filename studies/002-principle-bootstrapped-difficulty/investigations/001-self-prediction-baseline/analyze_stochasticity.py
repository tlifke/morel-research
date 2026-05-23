"""Analyze stochasticity of self-prediction across n trials per question.

Reads the four `stoch_q{1,2,3,4}_<date>.jsonl` files (24 records × 5
trials each = 120 rows per file). For each (record, question) cell,
computes the entropy of the model's structured-output answer across the
5 trials. If most cells are zero-entropy (all 5 trials agree), n=1 is
defensible. If many cells show split predictions, we need higher n on
the full corpus.

Run from repo root:
  uv run studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline/analyze_stochasticity.py
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_ROOT = HERE / "results"
MODEL_SAFE = "gemma3_4b-it-qat"

# Per-question, which fields constitute "the answer" for stochasticity purposes.
ANSWER_KEYS = {
    "q1": ("verdict",),
    "q2": ("verdict",),
    "q3": ("predicted_behavior",),
    "q4": ("predicted_tool",),
}


def _entropy(values: list[str]) -> float:
    n = len(values)
    if n == 0:
        return 0.0
    counts = Counter(values)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _load_latest(question: str) -> list[dict]:
    pattern = f"stoch_{question}_*.jsonl"
    candidates = sorted((RESULTS_ROOT / MODEL_SAFE).glob(pattern))
    if not candidates:
        return []
    return [json.loads(l) for l in candidates[-1].read_text().splitlines() if l]


def main() -> None:
    print(f"{'question':<6} {'cells':>6} {'parse_fail':>11} {'agree_5/5':>10} "
          f"{'agree_4/5':>10} {'agree_3/5':>10} {'mean_H':>8}")
    overall = []
    for q in ("q1", "q2", "q3", "q4"):
        rows = _load_latest(q)
        if not rows:
            print(f"  {q}: no data found")
            continue
        by_record: dict[str, list[str | None]] = defaultdict(list)
        for r in rows:
            parsed = r.get("parsed")
            if not parsed or r.get("validate_error"):
                by_record[r["record_id"]].append(None)
                continue
            key = "|".join(str(parsed.get(k)) for k in ANSWER_KEYS[q])
            by_record[r["record_id"]].append(key)

        cells = 0
        parse_fail_cells = 0
        bucket = Counter()
        entropies = []
        for rid, vals in by_record.items():
            cells += 1
            valid = [v for v in vals if v is not None]
            if len(valid) < len(vals):
                parse_fail_cells += 1
            if not valid:
                continue
            counts = Counter(valid)
            modal = max(counts.values())
            if modal == 5:
                bucket["5/5"] += 1
            elif modal == 4:
                bucket["4/5"] += 1
            elif modal == 3:
                bucket["3/5"] += 1
            else:
                bucket["≤2/5"] += 1
            entropies.append(_entropy(valid))
        mean_H = sum(entropies) / len(entropies) if entropies else 0.0
        overall.append((q, mean_H))
        print(f"{q:<6} {cells:>6} {parse_fail_cells:>11} {bucket['5/5']:>10} "
              f"{bucket['4/5']:>10} {bucket['3/5']:>10} {mean_H:>8.3f}")

    print()
    print("Interpretation:")
    print("  Mean entropy ~0.0  → predictions are deterministic; n=1 fine on full corpus.")
    print("  Mean entropy ~0.5  → modest disagreement; n=1 produces noisy data.")
    print("  Mean entropy >1.0  → high disagreement; need higher n or smaller corpus.")


if __name__ == "__main__":
    main()
