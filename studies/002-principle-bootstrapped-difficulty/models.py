from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class PrincipleStatus(str, Enum):
    PROPOSED = "proposed"
    UNDER_TEST = "under_test"
    VALIDATED = "validated"
    REGRESSED = "regressed"
    RETIRED = "retired"


class PrincipleProvenance(BaseModel):
    parent_uuid: Optional[UUID] = Field(
        default=None,
        description=(
            "The principle this one refines or replaces. None for a root "
            "principle proposed without a predecessor."
        ),
    )
    authoring_agent: str = Field(
        description=(
            "Identifier of who/what authored this principle, e.g. "
            "'opus-4.7', 'gemini-3-pro', 'human:tlifke'."
        ),
    )
    source_incident: Optional[str] = Field(
        default=None,
        description=(
            "Compact reference to the empirical observation that "
            "motivated this principle: <record_id>@<model_id> or a "
            "comma-separated list. Empty for principles not derived from "
            "a specific failure."
        ),
    )
    created: datetime = Field(default_factory=datetime.utcnow)


class PrincipleEffect(BaseModel):
    record_id: str = Field(
        description="The record on which the ablation was run.",
    )
    model_id: str = Field(
        description="The target model whose behavior was measured.",
    )
    n_trials: int = Field(
        description="Trials per condition (with-principle, without).",
    )
    delta_success_rate: float = Field(
        description=(
            "Empirical success rate WITH the principle minus success rate "
            "WITHOUT. Positive = principle helps."
        ),
    )
    delta_matched_pair_gap: Optional[float] = Field(
        default=None,
        description=(
            "Change in (success_rate[hard half] - success_rate[trivial half]) "
            "after adding the principle. The matched-pair design cares about "
            "this gap, not absolute success rate. None for non-paired records."
        ),
    )
    experiment_id: str = Field(
        description=(
            "Pointer to the experiment that produced this measurement, "
            "e.g. 'exp_017'."
        ),
    )


class AuditablePrinciple(BaseModel):
    uuid: UUID = Field(
        default_factory=uuid4,
        description="Stable unique identifier for this principle across runs.",
    )
    slug: str = Field(
        description=(
            "Short human-readable code for the principle, formatted as a "
            "three-letter category prefix followed by a zero-padded number "
            "(e.g. 'DIF00001'). Used for compact citation."
        ),
    )
    name: str = Field(
        description=(
            "Brief title summarizing what the principle says, in a few words "
            "(e.g. 'Post-cutoff knowledge increases difficulty')."
        ),
    )
    text: str = Field(
        description=(
            "Full statement of the principle in one or two sentences, "
            "phrased so it can be applied as a rule when judging a task."
        ),
    )

    scope: List[str] = Field(
        default_factory=list,
        description=(
            "Tool families or task categories this principle applies to, "
            "e.g. ['general_knowledge_lookup'] or ['*'] for universal. "
            "Filtered at experiment-config time to keep prompts focused."
        ),
    )
    status: PrincipleStatus = Field(
        default=PrincipleStatus.PROPOSED,
        description="Lifecycle state.",
    )
    applicability_conditions: Optional[str] = Field(
        default=None,
        description=(
            "Optional structured condition for when this principle fires. "
            "Often phrased inside text; this field is for cases where the "
            "experiment runner needs a programmatic check."
        ),
    )

    provenance: PrincipleProvenance = Field(
        description="Who authored this and why."
    )
    tested_on: List[PrincipleEffect] = Field(
        default_factory=list,
        description=(
            "Empirical effect-size measurements across (record, model) "
            "pairs. Append-only as ablation experiments accumulate."
        ),
    )


class PredictedOutcome(str, Enum):
    SUCCESS = "success"
    OVER_CALL = "over_call"
    UNDER_CALL = "under_call"
    WRONG_TOOL = "wrong_tool"


class PredictionConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SelfPredictionResponse(BaseModel):
    predicted_outcome: PredictedOutcome = Field(
        description=(
            "The model's prediction of which outcome class it would produce "
            "on a single trial at temperature 1.0 against the supplied "
            "(system_prompt, user_prompt) pair."
        ),
    )
    confidence: PredictionConfidence = Field(
        description="Subjective certainty about the prediction.",
    )
    reasoning: str = Field(
        description=(
            "One to three sentences naming the features of the situation "
            "that drive the prediction. Source material for principle "
            "extraction (see investigations/001-self-prediction-baseline)."
        ),
    )


class AuditableResponse(BaseModel):
    response: str = Field(
        description="The agent's answer to the task, as it should be returned to the user.",
    )
    cited_principles: List[UUID] = Field(
        description=(
            "UUIDs of principles from the active library that the agent "
            "claims materially shaped this response. Cited by uuid, not "
            "inlined — the registry is the source of truth for principle "
            "text. Omit principles that were considered but not "
            "load-bearing."
        ),
    )
    reasoning: str = Field(
        description=(
            "Explanation of how the cited principles led to this specific "
            "response. Should reference the principles by slug and make "
            "the chain of reasoning auditable. This is the agent's *claim* "
            "about its reasoning; faithfulness to the actual computation "
            "is itself a research question (see study.md)."
        ),
    )
