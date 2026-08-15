from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Iterable, Optional, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+")

LENGTH_BUCKETS: list[tuple[int, float, str]] = [
    (0, 4096, "0-4k"),
    (4096, 8192, "4k-8k"),
    (8192, 16384, "8k-16k"),
    (16384, math.inf, ">16k"),
]

PRINCIPLE_REF_RE = re.compile(r"\bp\d{2,3}\b|\bprinciple\s*#?\s*\d+\b", re.IGNORECASE)


def length_bucket(n_tokens: int) -> str:
    for lo, hi, name in LENGTH_BUCKETS:
        if lo <= n_tokens < hi:
            return name
    return LENGTH_BUCKETS[-1][2]


def normalize_tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def token_f1(pred: str, gold: str) -> float:
    p_tokens = normalize_tokens(pred)
    g_tokens = normalize_tokens(gold)
    if not p_tokens and not g_tokens:
        return 1.0
    if not p_tokens or not g_tokens:
        return 0.0
    overlap = sum((Counter(p_tokens) & Counter(g_tokens)).values())
    if overlap == 0:
        return 0.0
    precision = overlap / len(p_tokens)
    recall = overlap / len(g_tokens)
    return 2 * precision * recall / (precision + recall)


def best_span_f1(pred: str, golds: Sequence[str]) -> float:
    if not golds:
        return 0.0
    return max(token_f1(pred, g) for g in golds)


def decision_span_f1(preds: Sequence[str], golds: Sequence[str]) -> float:
    """Span F1 aggregated WITHIN one target-level decision (D-14).

    Soft precision over the predicted span set, soft recall over the gold span
    set, harmonic mean. Each predicted span is credited by its best-matching
    gold span and vice versa, so a model that emits one copy of repeated
    boilerplate is not scored as if it had emitted none.
    """
    if not preds and not golds:
        return 1.0
    if not preds or not golds:
        return 0.0
    precision = sum(best_span_f1(p, golds) for p in preds) / len(preds)
    recall = sum(best_span_f1(g, preds) for g in golds) / len(golds)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


@dataclass
class CitationEval:
    tp: list[str] = field(default_factory=list)
    fp: list[str] = field(default_factory=list)
    fn: list[str] = field(default_factory=list)
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
        }


def citation_eval(cited: Iterable[str], gold_applicable: Iterable[str]) -> CitationEval:
    cited_set = set(cited)
    gold_set = set(gold_applicable)
    tp = sorted(cited_set & gold_set)
    fp = sorted(cited_set - gold_set)
    fn = sorted(gold_set - cited_set)
    precision = len(tp) / len(cited_set) if cited_set else (1.0 if not gold_set else 0.0)
    recall = len(tp) / len(gold_set) if gold_set else 1.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return CitationEval(tp=tp, fp=fp, fn=fn, precision=precision, recall=recall, f1=f1)


def micro_citation(decision_evals: Sequence[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(len(d["tp"]) for d in decision_evals)
    fp = sum(len(d["fp"]) for d in decision_evals)
    fn = sum(len(d["fn"]) for d in decision_evals)
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "micro_over_decisions": True,
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def confusion_pairs(decision_rows: Iterable[dict[str, Any]]) -> Counter:
    pairs: Counter = Counter()
    for row in decision_rows:
        ce = row.get("citation_eval")
        if not ce:
            continue
        for cited in ce.get("fp", []):
            for missed in ce.get("fn", []):
                pairs[(cited, missed)] += 1
    return pairs


def summarize_compliance(
    per_decision: Sequence[tuple[str, bool]],
    instance_level: Sequence[tuple[str, bool]] = (),
) -> dict[str, Any]:
    by_principle: dict[str, list[bool]] = {}
    for pid, passed in list(per_decision) + list(instance_level):
        by_principle.setdefault(pid, []).append(passed)
    per_principle = {pid: all(vals) for pid, vals in by_principle.items()}
    n_applicable = len(per_principle)
    n_passed = sum(1 for v in per_principle.values() if v)
    flat = [v for vals in by_principle.values() for v in vals]
    return {
        "n_applicable": n_applicable,
        "n_passed": n_passed,
        "pass_rate": (n_passed / n_applicable) if n_applicable else None,
        "n_applicable_pairs": len(flat),
        "n_passed_pairs": sum(1 for v in flat if v),
        "pass_rate_micro": (sum(1 for v in flat if v) / len(flat)) if flat else None,
        "per_principle": per_principle,
    }


def scan_text_fields_for_principle_refs(payload: Any) -> int:
    count = 0
    if isinstance(payload, dict):
        for k, v in payload.items():
            if k == "principles_cited":
                continue
            count += scan_text_fields_for_principle_refs(v)
    elif isinstance(payload, list):
        for v in payload:
            count += scan_text_fields_for_principle_refs(v)
    elif isinstance(payload, str):
        count += len(PRINCIPLE_REF_RE.findall(payload))
    return count


def mean_normal_approx_ci95(values: Sequence[float]) -> dict[str, Any]:
    """Mean with a NORMAL-APPROXIMATION 95% interval. This is NOT a bootstrap.

    It assumes the sampling distribution of the mean is normal, which is a poor
    assumption for bounded, skewed quantities like span F1 at small n, and it
    can return limits outside [0, 1]. Adequate for reading a run at the
    terminal; the one-pager will likely want bootstrap CIs instead, computed
    from the stored per-trial rows.
    """
    vals = [v for v in values if v is not None]
    n = len(vals)
    if n == 0:
        return {"n": 0, "mean": None, "ci95_normal_approx": None}
    mean = sum(vals) / n
    if n < 2:
        return {"n": n, "mean": mean, "ci95_normal_approx": None}
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    se = math.sqrt(var / n)
    return {"n": n, "mean": mean, "ci95_normal_approx": [mean - 1.96 * se, mean + 1.96 * se]}


_TRIAL_METRIC_PATHS: dict[str, tuple[str, ...]] = {
    "span_f1_macro": ("answer", "span_f1_macro"),
    "absence_accuracy": ("answer", "absence_accuracy"),
    "category_match_accuracy": ("answer", "category_match_accuracy"),
    "compliance_pass_rate": ("compliance", "pass_rate"),
    "citation_precision": ("citation", "precision"),
    "citation_recall": ("citation", "recall"),
    "citation_f1": ("citation", "f1"),
}


def _dig(row: dict[str, Any], path: tuple[str, ...]) -> Optional[float]:
    node: Any = row
    for key in path:
        if not isinstance(node, dict) or node.get(key) is None:
            return None
        node = node[key]
    return node


def summarize_trials(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    outcomes = Counter(r.get("outcome") for r in rows)
    block: dict[str, Any] = {
        "n_trials": n,
        "outcomes": dict(outcomes),
        "parse_failure_rate": outcomes.get("parse_failure", 0) / n if n else None,
        "infeasible_rate": outcomes.get("infeasible_at_length", 0) / n if n else None,
        "api_error_rate": outcomes.get("api_error", 0) / n if n else None,
    }
    ok_rows = [r for r in rows if r.get("outcome") == "ok"]
    for name, path in _TRIAL_METRIC_PATHS.items():
        block[name] = mean_normal_approx_ci95([_dig(r, path) for r in ok_rows])
    return block


def stratified_summary(
    rows: Sequence[dict[str, Any]],
    group_keys: Sequence[str] = ("condition", "model", "schema_variant"),
) -> dict[str, Any]:
    def group_of(row: dict[str, Any]) -> tuple:
        return tuple(row.get(k) for k in group_keys)

    groups: dict[tuple, list[dict[str, Any]]] = {}
    for row in rows:
        groups.setdefault(group_of(row), []).append(row)

    out: dict[str, Any] = {"group_keys": list(group_keys), "groups": []}
    for key, grouped in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        by_bucket: dict[str, Any] = {}
        for _, _, bucket in LENGTH_BUCKETS:
            bucket_rows = [r for r in grouped if r.get("length_bucket") == bucket]
            if bucket_rows:
                by_bucket[bucket] = summarize_trials(bucket_rows)
        out["groups"].append(
            {
                "key": dict(zip(group_keys, key)),
                "overall": summarize_trials(grouped),
                "by_length_bucket": by_bucket,
            }
        )
    return out
