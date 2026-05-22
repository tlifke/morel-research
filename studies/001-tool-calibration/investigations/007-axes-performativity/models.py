from typing import List
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


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


class AuditableResponse(BaseModel):
    response: str = Field(
        description="The agent's answer to the task, as it should be returned to the user.",
    )
    cited_principles: List[AuditablePrinciple] = Field(
        description=(
            "The principles the agent relied on to produce this response. "
            "Include every principle that materially shaped the answer; omit "
            "principles that were considered but not load-bearing."
        ),
    )
    reasoning: str = Field(
        description=(
            "Explanation of how the cited principles led to this specific "
            "response. Should reference the principles by slug or name and "
            "make the chain of reasoning auditable."
        ),
    )
