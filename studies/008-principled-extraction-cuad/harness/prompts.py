from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from pydantic import BaseModel

from .models import Instance, PrincipleSet, TaskDefinition
from .output_schema import SchemaVariant, json_schema_for

PROMPT_TEMPLATE_VERSION = "v1"

Condition = Literal["C1", "C2", "C3"]


@dataclass(frozen=True)
class ConditionSpec:
    id: str
    task_definition: bool
    principles: bool
    citation_required: bool


CONDITIONS: dict[str, ConditionSpec] = {
    "C1": ConditionSpec("C1", task_definition=True, principles=False, citation_required=False),
    "C2": ConditionSpec("C2", task_definition=True, principles=True, citation_required=False),
    "C3": ConditionSpec("C3", task_definition=True, principles=True, citation_required=True),
}

SYSTEM_BLOCK = (
    "You are a careful analyst. You read a document and produce a single JSON "
    "object that answers the task exactly as specified. You never add commentary "
    "outside the JSON object."
)

CITATION_BLOCK = (
    "CITATION REQUIREMENT\n"
    "For every decision you make (each extraction and each absence claim), list "
    "in `principles_cited` the ids of the principles above that governed that "
    "specific decision. Cite only principles that actually bore on the decision. "
    "Use the exact ids as given (for example \"p03\"). An empty list means no "
    "principle applied."
)

NO_CITATION_BLOCK = (
    "The `principles_cited` field must be left as an empty list for every "
    "decision. Do not populate it."
)

OUTPUT_BLOCK_HEADER = (
    "OUTPUT FORMAT\n"
    "Reply with one JSON object and nothing else. It must validate against this "
    "JSON Schema:"
)


@dataclass(frozen=True)
class PromptBundle:
    system: str
    user: str
    json_schema: dict[str, Any]
    condition: str
    schema_variant: str
    template_version: str = PROMPT_TEMPLATE_VERSION
    blocks: dict[str, str] = field(default_factory=dict)

    def as_messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.user},
        ]

    def full_text(self) -> str:
        return self.system + "\n\n" + self.user


def render_task_definition(task: TaskDefinition) -> str:
    lines = ["TASK DEFINITION", task.framing, ""]
    lines.append("Decision kinds: " + ", ".join(task.decision_kinds))
    if task.targets:
        lines.append("")
        lines.append("Targets (you must make exactly one decision per target):")
        for t in task.targets:
            definition = task.target_definitions.get(t, "")
            lines.append(f"- {t}: {definition}")
    if task.attribution:
        lines.append("")
        lines.append(task.attribution)
    return "\n".join(lines)


def render_principles(principle_set: PrincipleSet) -> str:
    lines = [
        "PRINCIPLES",
        "The following principles govern how the decisions above must be made.",
        "",
    ]
    for p in principle_set.principles:
        scope = "all targets" if not p.scope else ", ".join(p.scope)
        lines.append(f"[{p.id}] ({p.type}; applies to: {scope})")
        lines.append(f"  Rule: {p.statement}")
        lines.append(f"  When to consider it: {p.trigger_guidance}")
    return "\n".join(lines)


def render_instance(instance: Instance) -> str:
    return (
        "DOCUMENT\n"
        f"Title: {instance.title}\n"
        f"Id: {instance.contract_id}\n"
        "---\n"
        f"{instance.text}\n"
        "---"
    )


def build_prompt(
    task: TaskDefinition,
    principle_set: Optional[PrincipleSet],
    condition: str,
    schema_variant: SchemaVariant,
    instance: Instance,
    output_model: type[BaseModel],
) -> PromptBundle:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")
    spec = CONDITIONS[condition]
    if spec.principles and principle_set is None:
        raise ValueError(f"condition {condition} requires a principle set")

    schema = json_schema_for(output_model, schema_variant)

    blocks: dict[str, str] = {}
    blocks["task_definition"] = render_task_definition(task)
    if spec.principles:
        blocks["principles"] = render_principles(principle_set)
    if spec.citation_required:
        blocks["citation"] = CITATION_BLOCK
    elif schema_variant == "field_present":
        blocks["citation"] = NO_CITATION_BLOCK
    blocks["output_format"] = (
        OUTPUT_BLOCK_HEADER + "\n" + json.dumps(schema, indent=2, sort_keys=True)
    )
    blocks["instance"] = render_instance(instance)

    order = ["task_definition", "principles", "citation", "output_format", "instance"]
    user = "\n\n".join(blocks[k] for k in order if k in blocks)

    return PromptBundle(
        system=SYSTEM_BLOCK,
        user=user,
        json_schema=schema,
        condition=condition,
        schema_variant=schema_variant,
        blocks=blocks,
    )
