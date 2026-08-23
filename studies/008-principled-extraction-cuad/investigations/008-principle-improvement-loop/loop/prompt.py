from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from harness.models import PrincipleSet
from harness.output_schema import json_schema_for

from loop.models import LoopOutput

INV = Path(__file__).resolve().parents[1]
TASK_DEFINITION = INV / "task_definition" / "v1.json"

QUESTIONS_HEADER = (
    "Answer every one of the following Questions about the Context above. "
    "Each Question is answered exactly once."
)

NO_PRINCIPLES_BLOCK = (
    "PRINCIPLES\n"
    "No principles are in force. Leave `principles_cited` as an empty list on "
    "every decision."
)

PRINCIPLES_HEADER = (
    "PRINCIPLES\n"
    "The following principles govern how this task is performed. Each carries "
    "guidance on when to consider it. On every decision, list in "
    "`principles_cited` the ids of the principles that actually bore on that "
    "specific decision; an empty list means none applied."
)

OUTPUT_HEADER = (
    "OUTPUT FORMAT\n"
    "Reply with one JSON object and nothing else. It must validate against this "
    "JSON Schema.\n"
    "`decisions` holds exactly one entry per Question above, in the same order — "
    "41 entries, no more and no fewer.\n"
    "Set `kind` to \"extraction\" and put the exact sentence(s) in `spans` when the "
    "Context contains relevant text. Set `kind` to \"absence\" and leave `spans` "
    "empty when it does not.\n"
    "This replaces the instruction to reply \"No related clause.\": express that "
    "same judgement as an \"absence\" decision. Never emit the phrase "
    "\"No related clause.\" as extracted text."
)


@dataclass(frozen=True)
class TaskDefinition:
    version: str
    content_sha256: str
    instruction_text: str
    questions: dict[str, str]

    @classmethod
    def load(cls, path: Path = TASK_DEFINITION) -> "TaskDefinition":
        d = json.loads(path.read_text())
        return cls(
            version=d["version"],
            content_sha256=d["content_sha256"],
            instruction_text=d["instruction_text"],
            questions=d["questions"],
        )

    @property
    def categories(self) -> list[str]:
        return list(self.questions)


@dataclass(frozen=True)
class Prompt:
    system: str
    user: str

    def messages(self) -> list[dict[str, str]]:
        return [
            {"role": "system", "content": self.system},
            {"role": "user", "content": self.user},
        ]


def render_questions(task: TaskDefinition) -> str:
    lines = [QUESTIONS_HEADER, ""]
    for category, question in task.questions.items():
        lines.append(f"[{category}] {question}")
    return "\n".join(lines)


def render_principles(principle_set: Optional[PrincipleSet]) -> str:
    if principle_set is None or not principle_set.principles:
        return NO_PRINCIPLES_BLOCK
    lines = [PRINCIPLES_HEADER, ""]
    for p in principle_set.principles:
        lines.append(f"{p.id}. {p.statement}")
        lines.append(f"    When to consider: {p.trigger_guidance}")
    return "\n".join(lines)


def build(
    task: TaskDefinition,
    contract_text: str,
    principle_set: Optional[PrincipleSet] = None,
) -> Prompt:
    schema = json_schema_for(LoopOutput, "field_present", categories=task.categories)
    user = "\n\n".join(
        [
            f"Context: \n```\n{contract_text}\n```",
            render_questions(task),
            render_principles(principle_set),
            OUTPUT_HEADER,
            json.dumps(schema, indent=2),
        ]
    )
    return Prompt(system=task.instruction_text, user=user)
