from __future__ import annotations

from typing import Annotated, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints

SpanText = Annotated[str, StringConstraints(min_length=1)]

DecisionKind = Literal["extraction", "absence"]


class LoopDecision(BaseModel):
    category: str
    kind: DecisionKind
    spans: list[SpanText] = Field(default_factory=list)
    explanation: Optional[str] = None
    principles_cited: list[str] = Field(default_factory=list)

    @property
    def predicted_present(self) -> bool:
        return self.kind == "extraction" and len(self.spans) > 0

    @property
    def is_inconsistent(self) -> bool:
        return (self.kind == "extraction") != (len(self.spans) > 0)


class LoopOutput(BaseModel):
    decisions: list[LoopDecision] = Field(default_factory=list)

    def by_category(self) -> dict[str, LoopDecision]:
        out: dict[str, LoopDecision] = {}
        for d in self.decisions:
            out.setdefault(d.category, d)
        return out

    def conformance(self, expected: list[str]) -> dict[str, object]:
        seen = [d.category for d in self.decisions]
        unique = set(seen)
        return {
            "n_decisions": len(seen),
            "n_unique_categories": len(unique),
            "n_expected": len(expected),
            "missing": sorted(set(expected) - unique),
            "unknown": sorted(unique - set(expected)),
            "n_duplicate": len(seen) - len(unique),
            "n_kind_span_inconsistent": sum(1 for d in self.decisions if d.is_inconsistent),
        }
