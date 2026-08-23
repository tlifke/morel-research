from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Optional, Sequence

STUDY = Path(__file__).resolve().parents[1]
RAW = STUDY / "data" / "raw"

_UPSTREAM = None


def upstream():
    global _UPSTREAM
    if _UPSTREAM is None:
        cwd = os.getcwd()
        os.chdir(RAW)
        try:
            spec = importlib.util.spec_from_file_location(
                "cuad_evaluate", RAW / "evaluate.py"
            )
            mod = importlib.util.module_from_spec(spec)
            sys.modules["cuad_evaluate"] = mod
            spec.loader.exec_module(mod)
        finally:
            os.chdir(cwd)
        _UPSTREAM = mod
    return _UPSTREAM


def jaccard(gold: str, pred: str) -> float:
    return upstream().get_jaccard(gold, pred)


def match_threshold() -> float:
    return upstream().IOU_THRESH


def is_match(gold: str, pred: str, category: str) -> bool:
    if jaccard(gold, pred) >= match_threshold():
        return True
    return category == "Parties" and gold in pred


@dataclass(frozen=True)
class Span:
    text: str
    start: Optional[int] = None


@dataclass(frozen=True)
class GroundTruth:
    contract_id: str
    category: str
    gt_spans: tuple[Span, ...] = ()

    @property
    def gold_present(self) -> bool:
        return len(self.gt_spans) > 0


@dataclass(frozen=True)
class PredSpan:
    text: str
    start: Optional[int] = None
    score: Optional[float] = None
    cited_principles: Optional[tuple[str, ...]] = None


@dataclass(frozen=True)
class ModelOutput:
    contract_id: str
    category: str
    system: str
    condition: str
    run_id: str
    pred_spans: tuple[PredSpan, ...] = ()
    abstain_principles: Optional[tuple[str, ...]] = None
    raw_response: Optional[str] = None

    @property
    def predicted_present(self) -> bool:
        return len(self.pred_spans) > 0


@dataclass
class MatchRecord:
    contract_id: str
    category: str
    system: str
    condition: str
    run_id: str
    n_gt: int
    n_pred: int
    pairs: list[dict[str, Any]] = field(default_factory=list)
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tp_oto: int = 0
    fp_oto: int = 0
    fn_oto: int = 0
    detection_cell: str = ""
    matched_jaccards: list[float] = field(default_factory=list)
    contracteval_correct: Optional[bool] = None

    @property
    def gold_present(self) -> bool:
        return self.n_gt > 0

    @property
    def predicted_present(self) -> bool:
        return self.n_pred > 0

    @property
    def in_tp_cell(self) -> bool:
        return self.detection_cell == "tp"


def detection_cell(predicted_present: bool, gold_present: bool) -> str:
    if gold_present and predicted_present:
        return "tp"
    if gold_present and not predicted_present:
        return "fn"
    if not gold_present and predicted_present:
        return "fp"
    return "tn"


def dedupe_spans(
    spans: Sequence[PredSpan], threshold: float = 0.8
) -> list[PredSpan]:
    kept: list[PredSpan] = []
    for s in spans:
        if not s.text:
            continue
        if all(jaccard(s.text, k.text) < threshold for k in kept):
            kept.append(s)
    return kept


def score(
    gt: GroundTruth,
    out: ModelOutput,
    dedupe: bool = True,
    dedupe_threshold: float = 0.8,
) -> MatchRecord:
    if gt.contract_id != out.contract_id or gt.category != out.category:
        raise ValueError(
            f"key mismatch: {gt.contract_id}/{gt.category} vs "
            f"{out.contract_id}/{out.category}"
        )

    preds = list(out.pred_spans)
    if dedupe:
        preds = dedupe_spans(preds, dedupe_threshold)
    else:
        preds = [p for p in preds if p.text]

    golds = [g for g in gt.gt_spans if g.text]
    cat = gt.category

    rec = MatchRecord(
        contract_id=gt.contract_id,
        category=cat,
        system=out.system,
        condition=out.condition,
        run_id=out.run_id,
        n_gt=len(golds),
        n_pred=len(preds),
    )
    rec.detection_cell = detection_cell(len(preds) > 0, len(golds) > 0)

    for gi, g in enumerate(golds):
        for pi, p in enumerate(preds):
            j = jaccard(g.text, p.text)
            m = is_match(g.text, p.text, cat)
            if m:
                rec.pairs.append(
                    {"gt_idx": gi, "pred_idx": pi, "jaccard": j, "match": True}
                )

    matched_golds = {p["gt_idx"] for p in rec.pairs}
    matched_preds = {p["pred_idx"] for p in rec.pairs}
    rec.tp = len(matched_golds)
    rec.fn = len(golds) - len(matched_golds)
    rec.fp = len(preds) - len(matched_preds)
    rec.matched_jaccards = [
        max(
            p["jaccard"]
            for p in rec.pairs
            if p["gt_idx"] == gi
        )
        for gi in sorted(matched_golds)
    ]

    used_g: set[int] = set()
    used_p: set[int] = set()
    for p in sorted(rec.pairs, key=lambda d: -d["jaccard"]):
        if p["gt_idx"] in used_g or p["pred_idx"] in used_p:
            continue
        used_g.add(p["gt_idx"])
        used_p.add(p["pred_idx"])
    rec.tp_oto = len(used_g)
    rec.fn_oto = len(golds) - len(used_g)
    rec.fp_oto = len(preds) - len(used_p)

    rec.contracteval_correct = contracteval_correct(gt, out)
    return rec


def contracteval_correct(gt: GroundTruth, out: ModelOutput) -> bool:
    resp = (out.raw_response or "").strip(" \n`")
    declined = "no related clause" in resp.lower()
    if not gt.gold_present:
        return declined
    if declined:
        return False
    return all(g.text.strip(" \n`") in resp for g in gt.gt_spans if g.text)


def prf(tp: float, fp: float, fn: float) -> dict[str, Optional[float]]:
    p = tp / (tp + fp) if (tp + fp) else None
    r = tp / (tp + fn) if (tp + fn) else None
    return {
        "precision": p,
        "recall": r,
        "f1": fbeta(p, r, 1.0),
        "f2": fbeta(p, r, 2.0),
        "tp": tp,
        "fp": fp,
        "fn": fn,
    }


def fbeta(p: Optional[float], r: Optional[float], beta: float) -> Optional[float]:
    if p is None or r is None:
        return None
    b2 = beta * beta
    denom = b2 * p + r
    if denom == 0:
        return 0.0
    return (1 + b2) * p * r / denom


def detection_metrics(records: Iterable[MatchRecord]) -> dict[str, Any]:
    cells = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for r in records:
        cells[r.detection_cell] += 1
    m = prf(cells["tp"], cells["fp"], cells["fn"])
    m["tn"] = cells["tn"]
    n_gold_pos = cells["tp"] + cells["fn"]
    m["false_empty_rate"] = cells["fn"] / n_gold_pos if n_gold_pos else None
    n = sum(cells.values())
    m["n_questions"] = n
    m["gold_positive_rate"] = n_gold_pos / n if n else None
    return m


def localization_metrics(records: Iterable[MatchRecord]) -> dict[str, Any]:
    rows = [r for r in records if r.in_tp_cell]
    tp = sum(r.tp for r in rows)
    fp = sum(r.fp for r in rows)
    fn = sum(r.fn for r in rows)
    m = prf(tp, fp, fn)
    js = [j for r in rows for j in r.matched_jaccards]
    m["mean_jaccard_on_matched"] = sum(js) / len(js) if js else None
    m["tp_cell_size"] = len(rows)
    m["n_gt_spans"] = sum(r.n_gt for r in rows)
    m["n_pred_spans"] = sum(r.n_pred for r in rows)
    oto = prf(
        sum(r.tp_oto for r in rows),
        sum(r.fp_oto for r in rows),
        sum(r.fn_oto for r in rows),
    )
    m["one_to_one_sensitivity"] = oto
    return m


def contracteval_metrics(records: Iterable[MatchRecord]) -> dict[str, Any]:
    tp = fp = fn = tn = 0
    for r in records:
        if r.contracteval_correct is None:
            continue
        if r.gold_present:
            if r.contracteval_correct:
                tp += 1
            else:
                fn += 1
        else:
            if r.contracteval_correct:
                tn += 1
            else:
                fp += 1
    m = prf(tp, fp, fn)
    m["tn"] = tn
    return m


def _macro(per_category: dict[str, dict[str, Any]], keys: Sequence[str]) -> dict:
    out = {}
    for k in keys:
        vals = [
            c[k]
            for c in per_category.values()
            if c.get(k) is not None
        ]
        out[k] = sum(vals) / len(vals) if vals else None
    return out


def aggregate(records: Sequence[MatchRecord]) -> dict[str, Any]:
    cats = sorted({r.category for r in records})
    per_cat = {}
    for c in cats:
        rs = [r for r in records if r.category == c]
        per_cat[c] = {
            "detection": detection_metrics(rs),
            "localization": localization_metrics(rs),
            "contracteval": contracteval_metrics(rs),
            "n_questions": len(rs),
        }
    keys = ("precision", "recall", "f1", "f2")
    return {
        "n_records": len(records),
        "n_categories": len(cats),
        "micro": {
            "detection": detection_metrics(records),
            "localization": localization_metrics(records),
            "contracteval": contracteval_metrics(records),
        },
        "macro": {
            "detection": _macro(
                {c: v["detection"] for c, v in per_cat.items()}, keys
            ),
            "localization": _macro(
                {c: v["localization"] for c, v in per_cat.items()}, keys
            ),
            "contracteval": _macro(
                {c: v["contracteval"] for c, v in per_cat.items()}, keys
            ),
        },
        "per_category": per_cat,
    }
