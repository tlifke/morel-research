from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Literal, Optional

from pydantic import BaseModel

from .models import (
    AnswerScore,
    DecisionRecord,
    GoldAnnotations,
    Instance,
    PrincipleSet,
    TaskDefinition,
)

ComplianceScope = Literal["instance", "decision"]


@dataclass(frozen=True)
class ComplianceContext:
    instance: Instance
    gold: GoldAnnotations
    output: Optional[BaseModel]
    decision: Optional[DecisionRecord] = None


@dataclass(frozen=True)
class ComplianceChecker:
    principle_id: str
    scope: ComplianceScope
    check: Callable[[ComplianceContext], bool]


class Environment(ABC):
    name: str

    @property
    def applicability_available(self) -> bool:
        """Whether `gold_applicable_for_decision` is a measurement.

        When this is False an empty gold-applicable list means "unknown", not
        "no principle applies", and citation precision/recall/F1 must be
        reported as unavailable rather than as a number.
        """
        return True

    @abstractmethod
    def load_instances(self, split: str) -> list[Instance]:
        ...

    @abstractmethod
    def task_definition(self) -> TaskDefinition:
        ...

    @abstractmethod
    def principle_set(self) -> PrincipleSet:
        ...

    @abstractmethod
    def applicable_principles(self, instance: Instance) -> list[str]:
        ...

    @abstractmethod
    def gold_applicable_for_decision(
        self, instance: Instance, decision: DecisionRecord
    ) -> list[str]:
        ...

    @abstractmethod
    def score_answer(self, instance: Instance, output: BaseModel) -> AnswerScore:
        ...

    @abstractmethod
    def score_decision(
        self, instance: Instance, decision: DecisionRecord
    ) -> dict[str, object]:
        ...

    @abstractmethod
    def gold_for_decision(
        self, instance: Instance, decision: DecisionRecord
    ) -> dict[str, object]:
        ...

    @abstractmethod
    def compliance_checkers(self) -> dict[str, ComplianceChecker]:
        ...

    @abstractmethod
    def output_model(self) -> type[BaseModel]:
        ...

    @abstractmethod
    def validate_output(self, instance: Instance, output: BaseModel) -> list[str]:
        ...

    @abstractmethod
    def iter_decisions(self, output: BaseModel) -> list[DecisionRecord]:
        ...

    @abstractmethod
    def unrealized_decisions(self, instance: Instance) -> list[DecisionRecord]:
        ...
