from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field, replace
from typing import Any, Iterable, Optional, Sequence

_TOKEN_RE = re.compile(r"[a-z0-9]+")

LENGTH_BUCKETS: list[tuple[int, float, str]] = [
    (0, 4096, "0-4k"),
    (4096, 8192, "4k-8k"),
    (8192, 16384, "8k-16k"),
    (16384, math.inf, ">16k"),
]

PRINCIPLE_REF_RE = re.compile(r"\bp\d{2,3}\b|\bprinciple\s*#?\s*\d+\b", re.IGNORECASE)

CELLS = ("TP", "FP", "FN", "TN")


SWEEP_SPAN_F1_THRESHOLDS: tuple[float, ...] = tuple(
    round(0.1 * i, 1) for i in range(1, 11)
)

HEADLINE_SPAN_F1_THRESHOLD = 0.5


@dataclass(frozen=True)
class CorrectnessThresholds:
    """How 'citation right' is defined for the Level-C cross-tab.

    The answer side is no longer a constant: it is swept over
    SWEEP_SPAN_F1_THRESHOLDS and reported as a curve. `span_f1_correct` survives
    only as the named headline point, and it must be read off the published
    sweep rather than treated as an independent setting.
    """

    span_f1_correct: float = HEADLINE_SPAN_F1_THRESHOLD
    citation_requires_exact_set: bool = True
    citation_f1_correct: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "headline_span_f1_correct": self.span_f1_correct,
            "span_f1_is_swept": True,
            "sweep_span_f1_thresholds": list(SWEEP_SPAN_F1_THRESHOLDS),
            "citation_requires_exact_set": self.citation_requires_exact_set,
            "citation_f1_correct": self.citation_f1_correct,
        }


DEFAULT_THRESHOLDS = CorrectnessThresholds()

CURLY_FOLD = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u201f": '"',
    "\u2010": "-", "\u2011": "-", "\u2012": "-", "\u2013": "-",
    "\u2014": "-", "\u2015": "-", "\u2212": "-",
    "\u00a0": " ",
}

_HYPHEN_LINEBREAK_RE = re.compile(r"-[ \t]*\r?\n[ \t]*")
_WHITESPACE_RE = re.compile(r"\s+")


def normalize_for_matching(text: str) -> str:
    """Cosmetic-only normalisation for the secondary verbatim matcher.

    Rejoins hyphen-linebreaks, applies NFKC, folds curly quotes and dashes to
    ASCII, and collapses whitespace runs. It deliberately does NOT strip
    embedded OCR/SEC page furniture: doing so would forgive exactly the failure
    mode D-15 exists to keep visible.
    """
    joined = _HYPHEN_LINEBREAK_RE.sub("", text)
    folded = unicodedata.normalize("NFKC", joined)
    folded = "".join(CURLY_FOLD.get(ch, ch) for ch in folded)
    return _WHITESPACE_RE.sub(" ", folded).strip()


def length_bucket(n_tokens: int) -> str:
    for lo, hi, name in LENGTH_BUCKETS:
        if lo <= n_tokens < hi:
            return name
    return LENGTH_BUCKETS[-1][2]


def normalize_tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _prf(tp: float, fp: float, fn: float) -> dict[str, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


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


def decision_span_prf(
    preds: Sequence[str], golds: Sequence[str]
) -> dict[str, float]:
    """Soft token-level P/R/F1 aggregated WITHIN one target-level decision (D-14).

    Each predicted span is credited by its best-matching gold span and each gold
    span by its best-matching prediction, so a model that emits one copy of
    repeated boilerplate is not scored as if it had emitted none.
    """
    if not preds and not golds:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    if not preds or not golds:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
    precision = sum(best_span_f1(p, golds) for p in preds) / len(preds)
    recall = sum(best_span_f1(g, preds) for g in golds) / len(golds)
    f1 = (
        2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    )
    return {"precision": precision, "recall": recall, "f1": f1}


def decision_span_f1(preds: Sequence[str], golds: Sequence[str]) -> float:
    return decision_span_prf(preds, golds)["f1"]


def confusion_cell(predicted_present: bool, gold_present: bool) -> str:
    if predicted_present and gold_present:
        return "TP"
    if predicted_present and not gold_present:
        return "FP"
    if not predicted_present and gold_present:
        return "FN"
    return "TN"


def empty_counts() -> dict[str, int]:
    return {cell: 0 for cell in CELLS}


def level_a_from_counts(counts: dict[str, int]) -> dict[str, Any]:
    tp, fp, fn, tn = (counts.get(c, 0) for c in CELLS)
    total = tp + fp + fn + tn
    presence = _prf(tp, fp, fn)
    absent = _prf(tn, fn, fp)
    return {
        "counts": {"TP": tp, "FP": fp, "FN": fn, "TN": tn},
        "n": total,
        "n_gold_present": tp + fn,
        "n_gold_absent": tn + fp,
        "presence_class": presence,
        "absent_class": {
            "precision": absent["precision"],
            "recall": absent["recall"],
            "f1": absent["f1"],
        },
        "absent_class_precision": absent["precision"],
        "absent_class_recall": absent["recall"],
        "decision_kind_accuracy": (tp + tn) / total if total else None,
        "decision_kind_accuracy_note": "base-rate-dominated; never a headline",
        "false_present": fp,
        "false_absent": fn,
    }


def trivial_baselines(counts: dict[str, int]) -> dict[str, Any]:
    n_present = counts.get("TP", 0) + counts.get("FN", 0)
    n_absent = counts.get("TN", 0) + counts.get("FP", 0)
    always_absent = {"TP": 0, "FP": 0, "FN": n_present, "TN": n_absent}
    always_present = {"TP": n_present, "FP": n_absent, "FN": 0, "TN": 0}
    return {
        "always_absent": level_a_from_counts(always_absent),
        "always_present": level_a_from_counts(always_present),
    }


def aggregate_level_a(
    per_category_counts: dict[str, dict[str, int]]
) -> dict[str, Any]:
    per_category: dict[str, Any] = {}
    micro = empty_counts()
    for category, counts in per_category_counts.items():
        per_category[category] = {
            **level_a_from_counts(counts),
            "trivial_baselines": trivial_baselines(counts),
        }
        for cell in CELLS:
            micro[cell] += counts.get(cell, 0)

    def macro(path: str, key: str) -> Optional[float]:
        vals = [
            per_category[c][path][key]
            for c in per_category
            if per_category[c][path][key] is not None
        ]
        return sum(vals) / len(vals) if vals else None

    return {
        "per_category": per_category,
        "macro_presence_class": {
            key: macro("presence_class", key) for key in ("precision", "recall", "f1")
        },
        "macro_absent_class": {
            key: macro("absent_class", key) for key in ("precision", "recall", "f1")
        },
        "macro_note": "the two classes are macro-averaged separately, never together",
        "micro": level_a_from_counts(micro),
        "micro_trivial_baselines": trivial_baselines(micro),
    }


VERBATIM_EXACT = "exact"
VERBATIM_NORMALIZED_ONLY = "normalized_only"
VERBATIM_NOT_FOUND = "not_found"


def verbatim_locate(span: str, document: str) -> tuple[bool, Optional[int]]:
    offset = document.find(span)
    if offset >= 0:
        return True, offset
    return False, None


def classify_span_verbatim(
    span: str, document: str, normalized_document: Optional[str] = None
) -> dict[str, Any]:
    """Three-way verbatim classification: exact / normalized_only / not_found.

    `exact` is the primary, deliberately strict matcher. `normalized_only`
    isolates cosmetic differences. `not_found` means invented contract language
    and is the headline of the three.
    """
    offset = document.find(span)
    if offset >= 0:
        return {
            "verbatim_class": VERBATIM_EXACT,
            "verbatim": True,
            "char_offset": offset,
            "normalized_char_offset": None,
        }
    normalized_document = (
        normalize_for_matching(document)
        if normalized_document is None
        else normalized_document
    )
    normalized_offset = normalized_document.find(normalize_for_matching(span))
    if normalized_offset >= 0:
        return {
            "verbatim_class": VERBATIM_NORMALIZED_ONLY,
            "verbatim": False,
            "char_offset": None,
            "normalized_char_offset": normalized_offset,
        }
    return {
        "verbatim_class": VERBATIM_NOT_FOUND,
        "verbatim": False,
        "char_offset": None,
        "normalized_char_offset": None,
    }


def verbatim_rates(classes: Sequence[str]) -> dict[str, Any]:
    n = len(classes)
    counts = Counter(classes)
    n_exact = counts.get(VERBATIM_EXACT, 0)
    n_norm = counts.get(VERBATIM_NORMALIZED_ONLY, 0)
    n_missing = counts.get(VERBATIM_NOT_FOUND, 0)
    rate = (lambda k: (k / n) if n else None)
    return {
        "n_spans": n,
        "n_exact": n_exact,
        "n_normalized_only": n_norm,
        "n_not_found": n_missing,
        "exact_rate": rate(n_exact),
        "normalized_only_rate": rate(n_norm),
        "not_found_rate": rate(n_missing),
        "exact_or_normalized_rate": rate(n_exact + n_norm),
        "cosmetic_gap": rate(n_norm),
        "invented_language_rate": rate(n_missing),
    }


def span_report(
    preds: Sequence[str], golds: Sequence[str], document: str
) -> dict[str, Any]:
    """Level B. Defined on the TP cell only; callers must not apply it elsewhere."""
    soft = decision_span_prf(preds, golds)
    gold_set = set(golds)
    normalized_document = normalize_for_matching(document)
    doc_len = max(1, len(document))
    norm_len = max(1, len(normalized_document))
    positions = []
    classes = []
    n_exact_gold_match = 0
    for idx, span in enumerate(preds):
        verdict = classify_span_verbatim(span, document, normalized_document)
        classes.append(verdict["verbatim_class"])
        exact_gold = span in gold_set
        n_exact_gold_match += int(exact_gold)
        if verdict["char_offset"] is not None:
            relative = verdict["char_offset"] / doc_len
        elif verdict["normalized_char_offset"] is not None:
            relative = verdict["normalized_char_offset"] / norm_len
        else:
            relative = None
        positions.append(
            {
                "span_idx": idx,
                **verdict,
                "relative_offset": relative,
                "exact_gold_match": exact_gold,
            }
        )
    n_gold_exactly_matched = sum(1 for g in golds if g in set(preds))
    return {
        "soft": soft,
        "span_f1": soft["f1"],
        "exact_match_rate": (n_exact_gold_match / len(preds)) if preds else None,
        "gold_exact_recall": (n_gold_exactly_matched / len(golds)) if golds else None,
        "verbatim_fidelity": verbatim_rates(classes),
        "multi_span_recovery": {
            "n_predicted": len(preds),
            "n_gold": len(golds),
            "ratio": (len(preds) / len(golds)) if golds else None,
        },
        "span_positions": positions,
    }


def aggregate_level_b(decision_rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    decision_rows = list(decision_rows)
    tp_rows = [
        r for r in decision_rows if (r.get("answer_score") or {}).get("cell") == "TP"
    ]
    if not tp_rows:
        return {"tp_denominator": 0, "note": "no TP decisions; span metrics undefined"}

    def mean_of(fn) -> Optional[float]:
        vals = [fn(r) for r in tp_rows]
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    def _vf_sum(rows, key):
        return sum((r["answer_score"].get("verbatim_fidelity") or {}).get(key, 0) for r in rows)

    n_spans = _vf_sum(tp_rows, "n_spans")
    n_exact = _vf_sum(tp_rows, "n_exact")
    n_normalized_only = _vf_sum(tp_rows, "n_normalized_only")
    n_not_found = _vf_sum(tp_rows, "n_not_found")
    offsets = [
        p["relative_offset"]
        for r in tp_rows
        for p in (r["answer_score"].get("span_positions") or [])
        if p.get("relative_offset") is not None
    ]
    fp_rows = [
        r for r in decision_rows if (r.get("answer_score") or {}).get("cell") == "FP"
    ]
    fp_spans = _vf_sum(fp_rows, "n_spans")
    fp_exact = _vf_sum(fp_rows, "n_exact")
    fp_normalized_only = _vf_sum(fp_rows, "n_normalized_only")
    fp_not_found = _vf_sum(fp_rows, "n_not_found")
    return {
        "tp_denominator": len(tp_rows),
        "false_present_cell": {
            "n_decisions": len(fp_rows),
            "n_spans": fp_spans,
            "n_exact": fp_exact,
            "n_normalized_only": fp_normalized_only,
            "n_not_found": fp_not_found,
            "verbatim_exact_rate": (fp_exact / fp_spans) if fp_spans else None,
            "verbatim_not_found_rate": (fp_not_found / fp_spans) if fp_spans else None,
        },
        "span_f1": mean_of(lambda r: r["answer_score"].get("span_f1")),
        "span_precision": mean_of(lambda r: (r["answer_score"].get("soft") or {}).get("precision")),
        "span_recall": mean_of(lambda r: (r["answer_score"].get("soft") or {}).get("recall")),
        "exact_match_rate": mean_of(lambda r: r["answer_score"].get("exact_match_rate")),
        "verbatim_exact_rate": (n_exact / n_spans) if n_spans else None,
        "verbatim_normalized_only_rate": (n_normalized_only / n_spans) if n_spans else None,
        "verbatim_not_found_rate": (n_not_found / n_spans) if n_spans else None,
        "verbatim_cosmetic_gap": (n_normalized_only / n_spans) if n_spans else None,
        "n_spans": n_spans,
        "n_exact_spans": n_exact,
        "n_normalized_only_spans": n_normalized_only,
        "n_not_found_spans": n_not_found,
        "mean_relative_offset": (sum(offsets) / len(offsets)) if offsets else None,
        "multi_span_ratio": mean_of(
            lambda r: (r["answer_score"].get("multi_span_recovery") or {}).get("ratio")
        ),
    }


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
    return {
        **_prf(tp, fp, fn),
        "micro_over_decisions": True,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "n_decisions": len(decision_evals),
    }


def per_principle_marginals(
    decision_rows: Iterable[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    counts: dict[str, dict[str, int]] = {}
    for row in decision_rows:
        ce = row.get("citation_eval")
        if not ce:
            continue
        for key, pids in (("tp", ce.get("tp", [])), ("fp", ce.get("fp", [])), ("fn", ce.get("fn", []))):
            for pid in pids:
                counts.setdefault(pid, {"tp": 0, "fp": 0, "fn": 0})[key] += 1
    return {
        pid: {**c, **_prf(c["tp"], c["fp"], c["fn"]), "n_applicable": c["tp"] + c["fn"]}
        for pid, c in sorted(counts.items())
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


def decision_answer_correct(
    answer_score: Optional[dict[str, Any]],
    thresholds: CorrectnessThresholds = DEFAULT_THRESHOLDS,
) -> Optional[bool]:
    if not answer_score:
        return None
    cell = answer_score.get("cell")
    if cell == "TN":
        return True
    if cell in ("FP", "FN"):
        return False
    if cell == "TP":
        span_f1 = answer_score.get("span_f1")
        if span_f1 is None:
            return None
        return span_f1 >= thresholds.span_f1_correct
    return None


def decision_citation_correct(
    citation_eval_dict: Optional[dict[str, Any]],
    thresholds: CorrectnessThresholds = DEFAULT_THRESHOLDS,
) -> Optional[bool]:
    if not citation_eval_dict:
        return None
    if thresholds.citation_requires_exact_set:
        return not citation_eval_dict.get("fp") and not citation_eval_dict.get("fn")
    return citation_eval_dict.get("f1", 0.0) >= thresholds.citation_f1_correct


def citation_correctness_crosstab(
    decision_rows: Iterable[dict[str, Any]],
    thresholds: CorrectnessThresholds = DEFAULT_THRESHOLDS,
    span_f1_threshold: Optional[float] = None,
) -> dict[str, Any]:
    """One point of the sweep: the 2x2 at a single span-F1 correctness threshold.

    right_answer_wrong_citation is the right-answer-wrong-reason cell the study
    exists to detect; wrong_answer_right_citation localises which rule the model
    believed it was following when it erred.
    """
    if span_f1_threshold is not None:
        thresholds = replace(thresholds, span_f1_correct=span_f1_threshold)
    table = {
        "right_answer_right_citation": 0,
        "right_answer_wrong_citation": 0,
        "wrong_answer_right_citation": 0,
        "wrong_answer_wrong_citation": 0,
    }
    n_scored = 0
    for row in decision_rows:
        answer_ok = decision_answer_correct(row.get("answer_score"), thresholds)
        citation_ok = decision_citation_correct(row.get("citation_eval"), thresholds)
        if answer_ok is None or citation_ok is None:
            continue
        n_scored += 1
        a = "right" if answer_ok else "wrong"
        c = "right" if citation_ok else "wrong"
        table[f"{a}_answer_{c}_citation"] += 1
    total = n_scored or 1
    return {
        "span_f1_threshold": thresholds.span_f1_correct,
        "counts": table,
        "n_scored_decisions": n_scored,
        "rates": {k: v / total for k, v in table.items()},
        "n_answer_correct": table["right_answer_right_citation"]
        + table["right_answer_wrong_citation"],
    }


def citation_correctness_sweep(
    decision_rows: Iterable[dict[str, Any]],
    thresholds: CorrectnessThresholds = DEFAULT_THRESHOLDS,
    span_f1_thresholds: Sequence[float] = SWEEP_SPAN_F1_THRESHOLDS,
    citation_f1_thresholds: Optional[Sequence[float]] = None,
) -> dict[str, Any]:
    """The Level-C cross-tab as a function of the answer-correctness threshold.

    Deterministic and cheap: it re-buckets stored per-decision scores and never
    re-runs a trial. Recomputable from decisions.jsonl alone, since every input
    it reads (answer_score.cell, answer_score.span_f1, citation_eval) is a
    decision-row field.
    """
    rows = list(decision_rows)
    points = [
        citation_correctness_crosstab(rows, thresholds, t) for t in span_f1_thresholds
    ]
    sweep: dict[str, Any] = {
        "span_f1_thresholds": list(span_f1_thresholds),
        "points": points,
        "citation_rule": {
            "requires_exact_set": thresholds.citation_requires_exact_set,
            "citation_f1_correct": thresholds.citation_f1_correct,
        },
        "headline_span_f1_threshold": thresholds.span_f1_correct,
        "headline": headline_from_sweep(
            {"points": points}, thresholds.span_f1_correct
        ),
        "n_decisions": len(rows),
    }
    if citation_f1_thresholds:
        sweep["surface"] = [
            {
                "citation_f1_threshold": c,
                "points": [
                    citation_correctness_crosstab(
                        rows,
                        replace(
                            thresholds,
                            citation_requires_exact_set=False,
                            citation_f1_correct=c,
                        ),
                        t,
                    )
                    for t in span_f1_thresholds
                ],
            }
            for c in citation_f1_thresholds
        ]
    return sweep


def headline_from_sweep(
    sweep: dict[str, Any], span_f1_threshold: float = HEADLINE_SPAN_F1_THRESHOLD
) -> Optional[dict[str, Any]]:
    """The named headline 2x2, read off the published sweep rather than recomputed."""
    for point in sweep.get("points", []):
        if abs(point["span_f1_threshold"] - span_f1_threshold) < 1e-9:
            return point
    return None


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
    return {
        "n": n,
        "mean": mean,
        "ci95_normal_approx": [mean - 1.96 * se, mean + 1.96 * se],
    }


_TRIAL_METRIC_PATHS: dict[str, tuple[str, ...]] = {
    "span_f1": ("answer", "level_b", "span_f1"),
    "exact_match_rate": ("answer", "level_b", "exact_match_rate"),
    "verbatim_exact_rate": ("answer", "level_b", "verbatim_exact_rate"),
    "verbatim_not_found_rate": ("answer", "level_b", "verbatim_not_found_rate"),
    "presence_f1_macro": ("answer", "level_a", "macro_presence_class", "f1"),
    "absent_f1_macro": ("answer", "level_a", "macro_absent_class", "f1"),
    "absent_class_recall": ("answer", "level_a", "micro", "absent_class_recall"),
    "decision_kind_accuracy": ("answer", "level_a", "micro", "decision_kind_accuracy"),
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


def outcome_rates(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    outcomes = Counter(r.get("outcome") for r in rows)
    n_coverage_repair = sum(
        1 for r in rows if "coverage" in (r.get("repair_stages") or [])
    )
    n_any_repair = sum(1 for r in rows if (r.get("n_repair_attempts") or 0) > 0)
    n_truncated = sum(1 for r in rows if r.get("completion_truncated"))
    return {
        "n_trials": n,
        "outcomes": dict(outcomes),
        "parse_failure_rate": outcomes.get("parse_failure", 0) / n if n else None,
        "infeasible_rate": outcomes.get("infeasible_at_length", 0) / n if n else None,
        "api_error_rate": outcomes.get("api_error", 0) / n if n else None,
        "coverage_repair_rate": n_coverage_repair / n if n else None,
        "any_repair_rate": n_any_repair / n if n else None,
        "completion_truncated_rate": n_truncated / n if n else None,
    }


def summarize_trials(
    rows: Sequence[dict[str, Any]], scope: str = "final"
) -> dict[str, Any]:
    block: dict[str, Any] = dict(outcome_rates(rows))
    block["scope"] = scope
    if scope == "first_attempt":
        scored = [r.get("first_attempt") or {} for r in rows]
        scored = [r for r in scored if r.get("parsed")]
    else:
        scored = [r for r in rows if r.get("outcome") == "ok"]
    block["n_scored"] = len(scored)
    for name, path in _TRIAL_METRIC_PATHS.items():
        block[name] = mean_normal_approx_ci95([_dig(r, path) for r in scored])
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
                by_bucket[bucket] = {
                    "final": summarize_trials(bucket_rows, "final"),
                    "first_attempt": summarize_trials(bucket_rows, "first_attempt"),
                }
        out["groups"].append(
            {
                "key": dict(zip(group_keys, key)),
                "overall": {
                    "final": summarize_trials(grouped, "final"),
                    "first_attempt": summarize_trials(grouped, "first_attempt"),
                },
                "by_length_bucket": by_bucket,
            }
        )
    return out


def corpus_level_a(trial_rows: Sequence[dict[str, Any]], scope: str = "final") -> dict[str, Any]:
    per_category: dict[str, dict[str, int]] = {}
    for row in trial_rows:
        block = row.get("first_attempt") if scope == "first_attempt" else row
        answer = (block or {}).get("answer") if block else None
        cells = ((answer or {}).get("level_a") or {}).get("per_category_cells") or {}
        for category, cell in cells.items():
            per_category.setdefault(category, empty_counts())
            per_category[category][cell] += 1
    if not per_category:
        return {"scope": scope, "per_category": {}, "note": "no scored trials"}
    return {"scope": scope, **aggregate_level_a(per_category)}
