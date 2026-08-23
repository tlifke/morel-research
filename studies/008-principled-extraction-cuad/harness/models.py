from __future__ import annotations

from typing import Annotated, Any, Literal, Optional

from pydantic import BaseModel, Field, StringConstraints, field_validator

CategoryId = str

PrincipleId = Annotated[str, StringConstraints(pattern=r"^[pw]\d{2}$")]

SpanText = Annotated[str, StringConstraints(min_length=1, strip_whitespace=False)]

ExplanationText = Annotated[str, StringConstraints(min_length=1)]

PrincipleType = Literal[
    "constraint", "procedure", "preference", "disambiguation", "absence", "other"
]

Provenance = Literal[
    "atticus_guidelines", "data_mined", "authored", "other"
]


class Principle(BaseModel):
    """A portable principle record.

    `provenance` is a LIST because a merged record genuinely has more than one
    source arm: w02 in the working set arrived independently from the Atticus
    guidelines and from contrastive data mining, and collapsing that to a single
    value would destroy the study's clearest cross-source corroboration. A bare
    string is accepted on input and normalised to a one-element list.
    """

    id: str
    statement: str
    trigger_guidance: str
    type: PrincipleType
    scope: list[str] = Field(default_factory=list)
    provenance: list[Provenance] = Field(min_length=1)

    @field_validator("provenance", mode="before")
    @classmethod
    def _as_list(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [value]
        return value

    @property
    def provenance_label(self) -> str:
        return " + ".join(self.provenance)


class PrincipleSet(BaseModel):
    version: str
    principles: list[Principle] = Field(default_factory=list)

    @property
    def ids(self) -> list[str]:
        return [p.id for p in self.principles]

    def by_id(self, pid: str) -> Principle:
        for p in self.principles:
            if p.id == pid:
                return p
        raise KeyError(pid)

    def in_scope_for(self, target: Optional[str]) -> list[Principle]:
        out = []
        for p in self.principles:
            if not p.scope:
                out.append(p)
            elif target is not None and target in p.scope:
                out.append(p)
        return out

    def subset(self, ids: list[str], version: Optional[str] = None) -> "PrincipleSet":
        keep = [p for p in self.principles if p.id in set(ids)]
        return PrincipleSet(version=version or f"{self.version}+subset", principles=keep)


class TaskDefinition(BaseModel):
    name: str
    framing: str
    decision_kinds: list[str]
    targets: list[str] = Field(default_factory=list)
    target_definitions: dict[str, str] = Field(default_factory=dict)
    attribution: Optional[str] = None


class GoldSpan(BaseModel):
    text: str
    start: Optional[int] = None
    end: Optional[int] = None


class GoldTarget(BaseModel):
    target: str
    spans: list[GoldSpan] = Field(default_factory=list)
    is_impossible: bool = True


class GoldAnnotations(BaseModel):
    targets: dict[str, GoldTarget] = Field(default_factory=dict)
    applicability: dict[str, list[str]] = Field(default_factory=dict)

    def positive_targets(self) -> list[str]:
        return [t for t, g in self.targets.items() if not g.is_impossible]


class Instance(BaseModel):
    contract_id: str
    title: str
    text: str
    n_tokens: int
    split: str
    gold: GoldAnnotations


class Decision(BaseModel):
    category: CategoryId
    explanation: Optional[ExplanationText] = None
    principles_cited: Optional[list[PrincipleId]] = None


class Extraction(Decision):
    kind: Literal["extraction"] = "extraction"
    spans: list[SpanText] = Field(min_length=1)


class AbsenceClaim(Decision):
    kind: Literal["absence"] = "absence"


class TaskOutput(BaseModel):
    schema_version: Literal[2] = 2
    extractions: list[Extraction] = Field(default_factory=list)
    absent: list[AbsenceClaim] = Field(default_factory=list)


class DecisionRecord(BaseModel):
    idx: int
    kind: Optional[str]
    target: Optional[str]
    explanation: Optional[str] = None
    principles_cited: Optional[list[str]] = None
    predicted: Optional[dict[str, Any]] = None


class AnswerScore(BaseModel):
    level_a: dict[str, Any] = Field(default_factory=dict)
    level_b: dict[str, Any] = Field(default_factory=dict)
    per_category: dict[str, dict[str, Any]] = Field(default_factory=dict)
