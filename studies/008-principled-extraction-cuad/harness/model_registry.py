from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

REFERENCE_TOKENIZER_ID = "Qwen/Qwen3-8B"


@dataclass(frozen=True)
class ModelSpec:
    id: str
    family: str
    tokenizer_id: Optional[str]
    served_as: dict[str, str] = field(default_factory=dict)
    emits_reasoning_content: bool = False


MODEL_SPECS: dict[str, ModelSpec] = {
    "Qwen/Qwen3.5-4B": ModelSpec(
        id="Qwen/Qwen3.5-4B",
        family="qwen3.5",
        tokenizer_id="Qwen/Qwen3.5-4B",
        served_as={"tinker": "Qwen/Qwen3.5-4B", "ollama": "qwen3.5:4b"},
        emits_reasoning_content=True,
    ),
    "Qwen/Qwen3.5-9B": ModelSpec(
        id="Qwen/Qwen3.5-9B",
        family="qwen3.5",
        tokenizer_id="Qwen/Qwen3.5-9B",
        served_as={"tinker": "Qwen/Qwen3.5-9B", "ollama": "qwen3.5:9b"},
        emits_reasoning_content=True,
    ),
    "thinkingmachines/Inkling-Small": ModelSpec(
        id="thinkingmachines/Inkling-Small",
        family="inkling",
        tokenizer_id=None,
        served_as={"tinker": "thinkingmachines/Inkling-Small"},
        emits_reasoning_content=True,
    ),
}


def spec_for(model_id: str) -> Optional[ModelSpec]:
    return MODEL_SPECS.get(model_id)


def served_name(model_id: str, substrate: str) -> str:
    spec = MODEL_SPECS.get(model_id)
    if spec is None:
        return model_id
    return spec.served_as.get(substrate, model_id)
