"""Pydantic schemas — API request/response contracts (SPEC 3.4)."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    study: str
    condition: str
    model: str
    spec: str | None
    tag: str | None
    run_dir: str
    workspace_dir: str
    session_file: str | None
    tokens_input: int
    tokens_output: int
    tokens_reasoning: int
    tokens_cache_read: int
    tokens_cache_write: int
    estimated_cost_usd: float | None
    pricing_source: str | None
    audit_clean: bool
    audit_violations: Any | None
    imported_at: datetime


class QuestionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1)
    description: str | None = None
    answered_by: Literal["agent", "human", "both"]
    value_type: Literal["bool", "int_1_5", "text"]
    active: bool = True
    sort_order: int = 0


class QuestionUpdate(BaseModel):
    text: str | None = None
    description: str | None = None
    answered_by: Literal["agent", "human", "both"] | None = None
    value_type: Literal["bool", "int_1_5", "text"] | None = None
    active: bool | None = None
    sort_order: int | None = None


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    text: str
    description: str | None
    answered_by: str
    value_type: str
    active: bool
    sort_order: int
    created_at: datetime


class AnswerCreate(BaseModel):
    question_id: int
    judge: Literal["agent", "human"]
    value: Any = None
    evidence: str | None = None
    judge_model: str | None = None
    notes: str | None = None


class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str
    question_id: int
    judge: str
    value: Any
    evidence: str | None
    judge_model: str | None
    notes: str | None
    created_at: datetime


class ComparisonCreate(BaseModel):
    run_a_id: str
    run_b_id: str
    better: Literal["a", "b", "tie"]
    dimensions: dict[str, Any] | None = None
    notes: str | None = None

    @field_validator("run_b_id")
    @classmethod
    def runs_differ(cls, v: str, info):
        if info.data.get("run_a_id") == v:
            raise ValueError("run_a_id and run_b_id must differ")
        return v


class ComparisonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_a_id: str
    run_b_id: str
    better: str
    dimensions: dict | None
    notes: str | None
    created_at: datetime


class WrittenFeedbackCreate(BaseModel):
    run_id: str | None = None
    anchor_type: Literal["run", "file", "tool_call"]
    anchor_ref: dict[str, Any] | None = None
    text: str = Field(min_length=1)


class WrittenFeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    run_id: str | None
    anchor_type: str
    anchor_ref: dict | None
    text: str
    created_at: datetime


class ImportResult(BaseModel):
    runs_found: int
    runs_upserted: int
    runs_skipped: list[str]
    questions_seeded: list[str]


# ---- exports (SPEC 7) ----


class ExportSFTExample(BaseModel):
    run_id: str
    messages: list[dict[str, Any]]


class ExportSFT(BaseModel):
    format: Literal["sft"]
    renderer: Literal["tml_v0"]
    effort: float
    examples: list[ExportSFTExample]


class ExportDPOPair(BaseModel):
    run_a: str
    run_b: str
    better: str
    prompt: list[dict[str, Any]]
    chosen: list[dict[str, Any]]
    rejected: list[dict[str, Any]]


class ExportRewardScore(BaseModel):
    run_id: str
    answers: dict[str, Any]
    score: float
    trace_ref: str
