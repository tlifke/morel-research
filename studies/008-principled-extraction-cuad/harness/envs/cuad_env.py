from __future__ import annotations

import csv
import json
import logging
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

import yaml
from pydantic import BaseModel, Field

from .. import metrics
from ..env import ComplianceChecker, Environment
from ..models import (
    AnswerScore,
    DecisionRecord,
    GoldAnnotations,
    GoldSpan,
    GoldTarget,
    Instance,
    PrincipleSet,
    TaskDefinition,
    TaskOutput,
)

log = logging.getLogger(__name__)

STUDY_ROOT = Path(__file__).resolve().parents[2]
if str(STUDY_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDY_ROOT))

from scripts.cuad_dataset import CuadDataset  # noqa: E402

INSTANCE_SCOPE_KEY = "__instance__"

SEALED_SPLITS = ("test",)

CATEGORY_SUBSET_CONFIG = STUDY_ROOT / "scripts" / "config" / "category_subset.yaml"
CATEGORY_DESCRIPTIONS = STUDY_ROOT / "data" / "raw" / "category_descriptions.csv"

ATTRIBUTION = (
    "Category definitions are quoted from CUAD v1 (The Atticus Project), "
    "released under CC BY 4.0."
)

FRAMING = (
    "You are given the full text of a commercial contract. For each target "
    "category below, make exactly one decision: either extract every verbatim "
    "span of the contract that the category covers, or claim that the category "
    "is absent from this contract. Every category must receive exactly one "
    "decision, never both and never none."
)

APPLICABILITY_UNAVAILABLE_NOTE = (
    "No applicability source is loaded. gold_applicable is empty for every "
    "decision, so C3 citation precision/recall/F1 and the Level-C cross-tab are "
    "NOT measurements and must be discarded. Everything else scores normally."
)

COMPLIANCE_UNAVAILABLE_NOTE = (
    "No compliance checkers were injected. compliance.pass_rate is reported as "
    "None (unavailable), never as 0."
)


class ApplicabilitySource(BaseModel):
    """Precomputed, frozen per-decision principle applicability (D-24).

    Contract of the on-disk file (JSON):

        {
          "version": "app-2026-08-16",
          "principle_set_version": "round2-v1",
          "labeler": {"model": "...", "prompt_version": "...", "kind": "llm|human|programmatic"},
          "spot_check": {"n": 40, "agreement": 0.9},
          "instances": {
            "<contract_id>": {
              "__instance__": ["p04"],
              "Governing Law": ["p01", "p07"],
              "Minimum Commitment": []
            }
          }
        }

    Keys under an instance are the 12 subset category names plus the reserved
    `__instance__` key for instance-scoped principles. A missing contract or a
    missing category means "no principle applies", not "unknown".
    """

    version: str
    principle_set_version: str = "unset"
    labeler: dict[str, Any] = Field(default_factory=dict)
    spot_check: dict[str, Any] = Field(default_factory=dict)
    instances: dict[str, dict[str, list[str]]] = Field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | str) -> "ApplicabilitySource":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(payload)

    def for_instance(self, contract_id: str) -> dict[str, list[str]]:
        return {k: list(v) for k, v in self.instances.get(contract_id, {}).items()}

    def describe(self) -> dict[str, Any]:
        return {
            "available": True,
            "version": self.version,
            "principle_set_version": self.principle_set_version,
            "labeler": self.labeler,
            "spot_check": self.spot_check,
            "n_instances": len(self.instances),
        }


def load_category_subset(path: Path | str = CATEGORY_SUBSET_CONFIG) -> list[str]:
    config = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [entry["name"] for entry in config["categories"]]


CSV_ARTIFACT_FOLD = {
    " ": " ",
    "‘": "'",
    "’": "'",
    "‚": "'",
    "“": '"',
    "”": '"',
    "„": '"',
}


def normalize_csv_text(text: str) -> str:
    """Strip raw-CSV artifacts before the text reaches the model.

    Non-breaking spaces and curly quotes/apostrophes come from the CUAD
    spreadsheet, carry no meaning, and tokenize badly. Nothing else is touched.
    """
    for bad, good in CSV_ARTIFACT_FOLD.items():
        text = text.replace(bad, good)
    return " ".join(text.split())


def load_category_definitions(
    path: Path | str = CATEGORY_DESCRIPTIONS,
) -> dict[str, str]:
    """One-line category definitions, Description column only.

    The CSV's `Answer Format` column is deliberately NOT appended. It described
    what a human types into an answer field ("Yes/No" for nine of the twelve
    subset targets) while this task asks for spans scored against sentence-level
    gold, so it told the model to answer in a shape the scorer does not accept.
    Nothing replaces it: answer granularity is business logic and belongs to a
    principle (w01), not to the task definition. The task definition stays
    neutral on granularity so w01 has something real to do.
    """
    out: dict[str, str] = {}
    with open(path, encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            name = row["Category (incl. context and answer)"].split(": ", 1)[1].strip()
            description = row["Description"].split(": ", 1)[1].strip()
            out[normalize_csv_text(name).lower()] = normalize_csv_text(description)
    return out


class CuadEnvironment(Environment):
    name = "cuad"

    def __init__(
        self,
        principle_set: PrincipleSet,
        dataset: Optional[CuadDataset] = None,
        applicability: Optional[ApplicabilitySource] = None,
        compliance_checkers: Optional[Mapping[str, ComplianceChecker]] = None,
        categories: Optional[Iterable[str]] = None,
        category_definitions: Optional[Mapping[str, str]] = None,
        allow_test: bool = False,
    ) -> None:
        self.targets = list(categories) if categories else load_category_subset()
        self._dataset = dataset or CuadDataset(categories=self.targets)
        self._principles = principle_set
        self._applicability = applicability
        self._checkers: dict[str, ComplianceChecker] = dict(compliance_checkers or {})
        self._allow_test = allow_test

        definitions = (
            dict(category_definitions)
            if category_definitions is not None
            else load_category_definitions()
        )
        self._definitions = {
            target: definitions.get(normalize_csv_text(target).lower(), "")
            for target in self.targets
        }
        missing = [t for t, d in self._definitions.items() if not d]
        if missing:
            raise ValueError(
                f"no one-line definition found for target(s): {', '.join(missing)}"
            )

        if self._applicability is None:
            log.warning("cuad env: %s", APPLICABILITY_UNAVAILABLE_NOTE)
        else:
            unknown_targets = {
                key
                for per_instance in self._applicability.instances.values()
                for key in per_instance
                if key != INSTANCE_SCOPE_KEY and key not in set(self.targets)
            }
            if unknown_targets:
                raise ValueError(
                    "applicability source names targets outside the subset: "
                    + ", ".join(sorted(unknown_targets))
                )
        if not self._checkers:
            log.warning("cuad env: %s", COMPLIANCE_UNAVAILABLE_NOTE)

    @property
    def applicability_available(self) -> bool:
        return self._applicability is not None

    @property
    def compliance_available(self) -> bool:
        return bool(self._checkers)

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "targets": list(self.targets),
            "attribution": ATTRIBUTION,
            "principle_set_version": self._principles.version,
            "n_principles": len(self._principles.principles),
            "applicability": (
                self._applicability.describe()
                if self._applicability is not None
                else {"available": False, "note": APPLICABILITY_UNAVAILABLE_NOTE}
            ),
            "compliance": {
                "available": self.compliance_available,
                "principle_ids": sorted(self._checkers),
                "note": None if self._checkers else COMPLIANCE_UNAVAILABLE_NOTE,
            },
            "allow_test": self._allow_test,
        }

    def assert_ready(self, conditions: Iterable[str]) -> None:
        conditions = list(conditions)
        if "C3" in conditions and not self.applicability_available:
            raise RuntimeError(
                "condition C3 was requested but no applicability source is loaded; "
                "citation scoring would compare against an empty gold set and read "
                "as precision 0.0 rather than as unavailable. Pass an "
                "ApplicabilitySource, or construct the run knowing the citation "
                "block is not a measurement."
            )

    def load_instances(self, split: str) -> list[Instance]:
        if split in SEALED_SPLITS and not self._allow_test:
            raise PermissionError(
                f"split {split!r} is sealed until gate G4 (plans/splits.md standing "
                f"rule 1); pass allow_test=True only with an explicit decision"
            )
        if split in SEALED_SPLITS:
            log.warning(
                "SEALED SPLIT LOADED: %r was read with allow_test=True. This is a "
                "gate-G4 action and must be recorded in the decision log.",
                split,
            )
        return [
            self._to_instance(contract_id)
            for contract_id in self._dataset.contract_ids(split)
        ]

    def _to_instance(self, contract_id: str) -> Instance:
        record = self._dataset.record(contract_id)
        if record is None:
            raise KeyError(f"unknown contract_id {contract_id!r}")
        text = self._dataset.texts[contract_id]
        targets: dict[str, GoldTarget] = {}
        for target in self.targets:
            entry = record["gold"][target]
            targets[target] = GoldTarget(
                target=target,
                is_impossible=entry["is_impossible"],
                spans=[
                    GoldSpan(text=text[start:end], start=start, end=end)
                    for start, end in entry["spans"]
                ],
            )
        applicability = (
            self._applicability.for_instance(contract_id)
            if self._applicability is not None
            else {}
        )
        return Instance(
            contract_id=contract_id,
            title=record["title"],
            text=text,
            n_tokens=record["n_tokens"],
            split=record["split"],
            gold=GoldAnnotations(targets=targets, applicability=applicability),
        )

    def task_definition(self) -> TaskDefinition:
        return TaskDefinition(
            name="cuad-clause-extraction",
            framing=FRAMING,
            decision_kinds=["extraction", "absence"],
            targets=list(self.targets),
            target_definitions=dict(self._definitions),
            attribution=ATTRIBUTION,
        )

    def principle_set(self) -> PrincipleSet:
        return self._principles

    def applicable_principles(self, instance: Instance) -> list[str]:
        seen: list[str] = []
        for pids in instance.gold.applicability.values():
            for pid in pids:
                if pid not in seen:
                    seen.append(pid)
        return seen

    def gold_applicable_for_decision(
        self, instance: Instance, decision: DecisionRecord
    ) -> list[str]:
        if decision.target is None:
            return []
        return list(instance.gold.applicability.get(decision.target, []))

    def gold_for_decision(
        self, instance: Instance, decision: DecisionRecord
    ) -> dict[str, Any]:
        if decision.target is None:
            return {"spans": [], "is_impossible": None}
        gold = instance.gold.targets.get(decision.target)
        if gold is None:
            return {"spans": [], "is_impossible": None}
        return {
            "spans": [span.text for span in gold.spans],
            "is_impossible": gold.is_impossible,
        }

    def score_decision(
        self, instance: Instance, decision: DecisionRecord
    ) -> dict[str, Any]:
        gold = instance.gold.targets.get(decision.target) if decision.target else None
        if gold is None:
            return {"cell": None, "correct_kind": False, "span_f1": None}
        gold_present = not gold.is_impossible
        predicted_present = decision.kind == "extraction"
        cell = metrics.confusion_cell(predicted_present, gold_present)
        score: dict[str, Any] = {
            "cell": cell,
            "correct_kind": cell in ("TP", "TN"),
            "span_f1": None,
        }
        if predicted_present:
            spans = (decision.predicted or {}).get("spans", [])
            report = metrics.span_report(
                spans, [g.text for g in gold.spans], instance.text
            )
            if cell == "TP":
                score.update(report)
            else:
                score.update(
                    {
                        "span_f1": None,
                        "soft": None,
                        "exact_match_rate": None,
                        "verbatim_fidelity": report["verbatim_fidelity"],
                        "multi_span_recovery": report["multi_span_recovery"],
                        "span_positions": report["span_positions"],
                    }
                )
        return score

    def score_answer(self, instance: Instance, output: BaseModel) -> AnswerScore:
        assert isinstance(output, TaskOutput)
        extracted = {item.category: list(item.spans) for item in output.extractions}
        absent = {item.category for item in output.absent}

        per_category_counts: dict[str, dict[str, int]] = {}
        per_category_cells: dict[str, str] = {}
        per_category: dict[str, dict[str, Any]] = {}

        for target in self.targets:
            gold = instance.gold.targets.get(target)
            if gold is None:
                continue
            gold_present = not gold.is_impossible
            predicted_present = target in extracted
            cell = metrics.confusion_cell(predicted_present, gold_present)
            per_category_cells[target] = cell
            counts = metrics.empty_counts()
            counts[cell] = 1
            per_category_counts[target] = counts
            per_category[target] = {
                "cell": cell,
                "gold_present": gold_present,
                "predicted_present": predicted_present,
                "kind": "extraction" if predicted_present else "absence",
                "declared_absent": target in absent,
                "n_gold_spans": len(gold.spans),
                "n_predicted_spans": len(extracted.get(target, [])),
            }

        level_a = metrics.aggregate_level_a(per_category_counts)
        level_a["per_category_cells"] = per_category_cells

        return AnswerScore(level_a=level_a, level_b={}, per_category=per_category)

    def compliance_checkers(self) -> dict[str, ComplianceChecker]:
        return dict(self._checkers)

    def output_model(self) -> type[BaseModel]:
        return TaskOutput

    def validate_output(self, instance: Instance, output: BaseModel) -> list[str]:
        assert isinstance(output, TaskOutput)
        extracted = [item.category for item in output.extractions]
        absent = [item.category for item in output.absent]
        decided = extracted + absent
        violations: list[str] = []

        unknown = sorted({c for c in decided if c not in set(self.targets)})
        if unknown:
            violations.append(f"unknown target(s): {', '.join(unknown)}")

        duplicated = sorted({c for c in decided if decided.count(c) > 1})
        if duplicated:
            violations.append(
                f"target(s) decided more than once: {', '.join(duplicated)}"
            )

        missing = [t for t in self.targets if t not in decided]
        if missing:
            violations.append(f"target(s) with no decision: {', '.join(missing)}")

        return violations

    def iter_decisions(self, output: BaseModel) -> list[DecisionRecord]:
        assert isinstance(output, TaskOutput)
        extractions = {item.category: item for item in output.extractions}
        absences = {item.category: item for item in output.absent}
        records: list[DecisionRecord] = []
        for idx, target in enumerate(self.targets):
            if target in extractions:
                item = extractions[target]
                records.append(
                    DecisionRecord(
                        idx=idx,
                        kind="extraction",
                        target=target,
                        principles_cited=item.principles_cited,
                        explanation=item.explanation,
                        predicted={"spans": list(item.spans)},
                    )
                )
            elif target in absences:
                item = absences[target]
                records.append(
                    DecisionRecord(
                        idx=idx,
                        kind="absence",
                        target=target,
                        principles_cited=item.principles_cited,
                        explanation=item.explanation,
                        predicted=None,
                    )
                )
            else:
                records.append(
                    DecisionRecord(
                        idx=idx,
                        kind=None,
                        target=target,
                        principles_cited=None,
                        predicted=None,
                    )
                )
        return records

    def unrealized_decisions(self, instance: Instance) -> list[DecisionRecord]:
        return [
            DecisionRecord(
                idx=idx,
                kind=None,
                target=target,
                principles_cited=None,
                predicted=None,
            )
            for idx, target in enumerate(self.targets)
        ]
