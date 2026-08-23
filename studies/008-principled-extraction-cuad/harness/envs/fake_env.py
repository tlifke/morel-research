from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel

from .. import metrics
from ..env import ComplianceChecker, ComplianceContext, Environment
from ..models import (
    AnswerScore,
    DecisionRecord,
    GoldAnnotations,
    GoldSpan,
    GoldTarget,
    Instance,
    Principle,
    PrincipleSet,
    TaskDefinition,
    TaskOutput,
)

INSTANCE_SCOPE_KEY = "__instance__"

TARGETS = [
    "Governing Law",
    "Agreement Date",
    "Minimum Commitment",
    "Volume Restriction",
]

TARGET_DEFINITIONS = {
    "Governing Law": "The state or country whose law governs the interpretation of the contract.",
    "Agreement Date": "The date of the contract as stated on its face.",
    "Minimum Commitment": "A clause imposing a floor on the quantity or value the buyer must purchase.",
    "Volume Restriction": "A clause imposing a ceiling on the quantity the buyer may purchase or the seller must supply.",
}

CLAUSE_TEXT = {
    "Governing Law": "This Agreement shall be governed by the laws of the State of Delaware.",
    "Agreement Date": "This Agreement is entered into as of March 3, 2019.",
    "Minimum Commitment": "Buyer shall purchase at least 10,000 units per calendar year.",
    "Volume Restriction": "Buyer shall order no more than 50,000 units in any calendar quarter.",
}

NEAR_DUPLICATE_CLAUSE = {
    "Governing Law": (
        "This Agreement shall be governed by the laws of the State of Delaware, "
        "without regard to its conflict of laws principles."
    )
}

FILLER = (
    "The parties acknowledge that the recitals set forth above are incorporated "
    "herein by reference and made a part hereof for all purposes. "
)

PRINCIPLES = PrincipleSet(
    version="fake-v1",
    principles=[
        Principle(
            id="p01",
            statement="Quote every extracted span verbatim from the document; never paraphrase or normalize it.",
            trigger_guidance="Whenever you emit an extraction.",
            type="constraint",
            scope=[],
            provenance="authored",
        ),
        Principle(
            id="p02",
            statement="If no clause matches the target definition, claim absence explicitly rather than extracting a near miss.",
            trigger_guidance="Whenever the document contains nothing that satisfies the target definition.",
            type="absence",
            scope=[],
            provenance="authored",
        ),
        Principle(
            id="p03",
            statement="A floor on purchase quantity is a Minimum Commitment; a ceiling is a Volume Restriction.",
            trigger_guidance="Whenever a quantity obligation appears and the two categories could be confused.",
            type="disambiguation",
            scope=["Minimum Commitment", "Volume Restriction"],
            provenance="savelka_confusion",
        ),
        Principle(
            id="p04",
            statement="Within one extraction, list each distinct span once; do not repeat an identical span.",
            trigger_guidance="Whenever an extraction carries more than one span.",
            type="procedure",
            scope=[],
            provenance="authored",
        ),
    ],
)


def _build_instance(
    contract_id: str,
    title: str,
    present: list[str],
    filler_repeats: int,
    split: str,
    repeated: tuple[str, ...] = (),
) -> Instance:
    body_parts = [f"{title.upper()}\n"]
    for target in TARGETS:
        body_parts.append(FILLER * filler_repeats)
        if target in present:
            body_parts.append(CLAUSE_TEXT[target] + "\n")
            if target in repeated:
                body_parts.append(FILLER * filler_repeats)
                body_parts.append(NEAR_DUPLICATE_CLAUSE[target] + "\n")
    text = "\n".join(body_parts)

    targets: dict[str, GoldTarget] = {}
    applicability: dict[str, list[str]] = {INSTANCE_SCOPE_KEY: ["p04"]}
    for target in TARGETS:
        if target in present:
            span_texts = [CLAUSE_TEXT[target]]
            if target in repeated:
                span_texts.append(NEAR_DUPLICATE_CLAUSE[target])
            targets[target] = GoldTarget(
                target=target,
                spans=[
                    GoldSpan(
                        text=span_text,
                        start=text.find(span_text),
                        end=text.find(span_text) + len(span_text),
                    )
                    for span_text in span_texts
                ],
                is_impossible=False,
            )
            applicable = ["p01"]
            if target in ("Minimum Commitment", "Volume Restriction"):
                applicable.append("p03")
        else:
            targets[target] = GoldTarget(target=target, spans=[], is_impossible=True)
            applicable = ["p02"]
        applicability[target] = applicable

    n_tokens = metrics_token_estimate(text)
    return Instance(
        contract_id=contract_id,
        title=title,
        text=text,
        n_tokens=n_tokens,
        split=split,
        gold=GoldAnnotations(targets=targets, applicability=applicability),
    )


def metrics_token_estimate(text: str) -> int:
    return max(1, len(text) // 4)


class FakeEnvironment(Environment):
    name = "fake-contracts"

    def __init__(
        self,
        principle_set: Optional[PrincipleSet] = None,
        applicability_available: bool = True,
    ) -> None:
        self._principles = principle_set or PRINCIPLES
        self._applicability_available = applicability_available

    @property
    def applicability_available(self) -> bool:
        return self._applicability_available

    def load_instances(self, split: str) -> list[Instance]:
        specs = [
            ("FAKE_0001", "Alpha Supply Agreement", TARGETS, 4, "harness_val", ("Governing Law",)),
            ("FAKE_0002", "Beta Distribution Agreement", ["Governing Law"], 40, "harness_val", ()),
            (
                "FAKE_0003",
                "Gamma Master Services Agreement",
                ["Agreement Date", "Volume Restriction"],
                400,
                "harness_val",
                (),
            ),
            ("FAKE_0004", "Delta Reseller Agreement", [], 4000, "test", ()),
        ]
        return [
            _build_instance(cid, title, present, filler, isplit, repeated)
            for cid, title, present, filler, isplit, repeated in specs
            if isplit == split
        ]

    def task_definition(self) -> TaskDefinition:
        return TaskDefinition(
            name="fake-clause-extraction",
            framing=(
                "Read the document below and, for each target category, either "
                "extract the verbatim span that satisfies it or declare it absent."
            ),
            decision_kinds=["extraction", "absence"],
            targets=list(TARGETS),
            target_definitions=dict(TARGET_DEFINITIONS),
            attribution="Synthetic documents; no third-party content.",
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
        if decision.target is None or not self._applicability_available:
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
            "spans": [s.text for s in gold.spans],
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

        for target in TARGETS:
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
            entry: dict[str, Any] = {
                "cell": cell,
                "gold_present": gold_present,
                "predicted_present": predicted_present,
                "kind": "extraction" if predicted_present else "absence",
                "declared_absent": target in absent,
            }
            if cell == "TP":
                entry["span_f1"] = metrics.decision_span_f1(
                    extracted[target], [g.text for g in gold.spans]
                )
            per_category[target] = entry

        level_a = metrics.aggregate_level_a(per_category_counts)
        level_a["per_category_cells"] = per_category_cells

        return AnswerScore(level_a=level_a, level_b={}, per_category=per_category)

    def compliance_checkers(self) -> dict[str, ComplianceChecker]:
        return {
            "p01": ComplianceChecker("p01", "decision", _check_verbatim),
            "p02": ComplianceChecker("p02", "decision", _check_absence_claimed),
            "p03": ComplianceChecker("p03", "decision", _check_quantity_direction),
            "p04": ComplianceChecker("p04", "instance", _check_no_duplicate_spans),
        }

    def output_model(self) -> type[BaseModel]:
        return TaskOutput

    def validate_output(self, instance: Instance, output: BaseModel) -> list[str]:
        assert isinstance(output, TaskOutput)
        extracted = [item.category for item in output.extractions]
        absent = [item.category for item in output.absent]
        decided = extracted + absent
        violations: list[str] = []

        unknown = sorted({c for c in decided if c not in TARGETS})
        if unknown:
            violations.append(f"unknown target(s): {', '.join(unknown)}")

        duplicated = sorted({c for c in decided if decided.count(c) > 1})
        if duplicated:
            violations.append(f"target(s) decided more than once: {', '.join(duplicated)}")

        missing = [t for t in TARGETS if t not in decided]
        if missing:
            violations.append(f"target(s) with no decision: {', '.join(missing)}")

        return violations

    def iter_decisions(self, output: BaseModel) -> list[DecisionRecord]:
        assert isinstance(output, TaskOutput)
        extractions = {item.category: item for item in output.extractions}
        absences = {item.category: item for item in output.absent}
        records: list[DecisionRecord] = []
        for idx, target in enumerate(TARGETS):
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
                    DecisionRecord(idx=idx, kind=None, target=target, predicted=None)
                )
        return records

    def unrealized_decisions(self, instance: Instance) -> list[DecisionRecord]:
        return [
            DecisionRecord(idx=idx, kind=None, target=target, principles_cited=[], predicted=None)
            for idx, target in enumerate(TARGETS)
        ]


def _check_verbatim(ctx: ComplianceContext) -> bool:
    decision = ctx.decision
    if decision is None or decision.kind != "extraction":
        return True
    spans = (decision.predicted or {}).get("spans", [])
    return bool(spans) and all(span in ctx.instance.text for span in spans)


def _check_absence_claimed(ctx: ComplianceContext) -> bool:
    decision = ctx.decision
    if decision is None:
        return True
    return decision.kind == "absence"


def _check_quantity_direction(ctx: ComplianceContext) -> bool:
    decision = ctx.decision
    if decision is None or decision.kind != "extraction":
        return True
    spans = [s.lower() for s in (decision.predicted or {}).get("spans", [])]
    if decision.target == "Minimum Commitment":
        return all("at least" in s for s in spans)
    if decision.target == "Volume Restriction":
        return all("no more than" in s for s in spans)
    return True


def _check_no_duplicate_spans(ctx: ComplianceContext) -> bool:
    output = ctx.output
    if not isinstance(output, TaskOutput):
        return False
    return all(len(set(e.spans)) == len(e.spans) for e in output.extractions)
