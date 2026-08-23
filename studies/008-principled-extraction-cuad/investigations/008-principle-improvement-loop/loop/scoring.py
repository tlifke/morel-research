from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from harness.comparison_metrics import (
    GroundTruth,
    MatchRecord,
    ModelOutput,
    PredSpan,
    Span,
    aggregate,
    score,
)

from loop.models import LoopOutput

STUDY = Path(__file__).resolve().parents[3]
INSTANCES = STUDY / "data/processed/instances.jsonl"
RAW = STUDY / "data/raw/CUADv1.json"

FAILURE_CLASSES = ("false_absent", "false_present", "boundary_miss", "no_failure")


def gold_for(contract_ids: list[str], categories: list[str]) -> dict[tuple[str, str], GroundTruth]:
    wanted = set(contract_ids)
    raw = json.loads(RAW.read_text())
    texts = {d["title"]: d["paragraphs"][0]["context"] for d in raw["data"] if d["title"] in wanted}

    out: dict[tuple[str, str], GroundTruth] = {}
    for line in INSTANCES.read_text().splitlines():
        row = json.loads(line)
        cid = row["contract_id"]
        if cid not in wanted:
            continue
        text = texts[cid]
        for category in categories:
            g = row["gold"].get(category, {"is_impossible": True, "spans": []})
            spans = tuple(
                Span(text=text[s[0] : s[1]], start=s[0])
                for s in g.get("spans", [])
                if not g.get("is_impossible", True)
            )
            out[(cid, category)] = GroundTruth(contract_id=cid, category=category, gt_spans=spans)
    return out


@dataclass
class Failure:
    contract_id: str
    category: str
    failure_class: str
    n_gold: int
    n_pred: int
    best_jaccard: Optional[float]
    gold_sample: Optional[str]
    pred_sample: Optional[str]

    def to_json(self) -> dict[str, Any]:
        return self.__dict__


def classify(record: MatchRecord, gt: GroundTruth, out: ModelOutput) -> Failure:
    if record.detection_cell == "fn":
        cls = "false_absent"
    elif record.detection_cell == "fp":
        cls = "false_present"
    elif record.detection_cell == "tp" and (record.fn > 0 or record.fp > 0):
        cls = "boundary_miss"
    else:
        cls = "no_failure"
    return Failure(
        contract_id=record.contract_id,
        category=record.category,
        failure_class=cls,
        n_gold=record.n_gt,
        n_pred=record.n_pred,
        best_jaccard=max(record.matched_jaccards) if record.matched_jaccards else None,
        gold_sample=gt.gt_spans[0].text[:300] if gt.gt_spans else None,
        pred_sample=out.pred_spans[0].text[:300] if out.pred_spans else None,
    )


def score_trial(
    trial: dict[str, Any],
    gold: dict[tuple[str, str], GroundTruth],
    categories: list[str],
    system: str,
) -> tuple[list[MatchRecord], list[Failure]]:
    key = trial["key"]
    cid = key["contract_id"]
    parsed = LoopOutput(**trial["output"]) if trial.get("output") else LoopOutput()
    by_cat = parsed.by_category()

    records: list[MatchRecord] = []
    failures: list[Failure] = []
    for category in categories:
        decision = by_cat.get(category)
        spans = ()
        cited = None
        if decision is not None and decision.predicted_present:
            spans = tuple(PredSpan(text=s) for s in decision.spans)
        if decision is not None:
            cited = tuple(decision.principles_cited) or None
        out = ModelOutput(
            contract_id=cid,
            category=category,
            system=system,
            condition=key["arm"],
            run_id=trial["run_id"],
            pred_spans=spans,
            abstain_principles=cited if not spans else None,
        )
        gt = gold[(cid, category)]
        rec = score(gt, out)
        records.append(rec)
        f = classify(rec, gt, out)
        if f.failure_class != "no_failure":
            failures.append(f)
    return records, failures


def summarize(records: list[MatchRecord]) -> dict[str, Any]:
    return aggregate(records)
