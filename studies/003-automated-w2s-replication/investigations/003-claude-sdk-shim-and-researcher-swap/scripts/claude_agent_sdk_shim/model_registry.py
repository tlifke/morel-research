from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ModelEntry:
    ollama_tag: str
    family: str
    max_tokens_default: int = 8192
    thinking_mode: str = "none"
    recommended_hint: Optional[str] = None
    notes: str = ""
    extras: Dict[str, Any] = field(default_factory=dict)


_QWEN35_4B_HINT = (
    "you MUST invoke the corresponding tool (Bash, Read, Write, Edit, Glob, Grep) "
    "via a real tool call; do not write shell commands in markdown code blocks or prose."
)


MODEL_REGISTRY: Dict[str, ModelEntry] = {
    "qwen3.5:4b": ModelEntry(
        ollama_tag="qwen3.5:4b",
        family="qwen3.5",
        max_tokens_default=8192,
        thinking_mode="block",
        recommended_hint=_QWEN35_4B_HINT,
        notes=(
            "Default researcher model for inv 003. Native Anthropic-compat tool_use; "
            "emits explicit thinking blocks through Ollama Anthropic-compat. Thinking "
            "is load-bearing for tool selection (disabling collapses tool calls)."
        ),
    ),
    "qwen3:4b": ModelEntry(
        ollama_tag="qwen3:4b",
        family="qwen3",
        max_tokens_default=8192,
        thinking_mode="block",
        recommended_hint=None,
        notes=(
            "Narrates tool calls as markdown / fenced JSON regardless of hint; "
            "kept as a known-failing contrast point."
        ),
    ),
    "nemotron-3-nano:4b": ModelEntry(
        ollama_tag="nemotron-3-nano:4b",
        family="nemotron",
        max_tokens_default=8192,
        thinking_mode="sidecar",
        recommended_hint=None,
        notes=(
            "Mamba-2 hybrid. Native Anthropic tool_use; reasoning surfaced as a "
            "sidecar 'thinking' field on the assistant message in the Ollama raw API. "
            "Smaller on-disk than qwen3.5:4b (~2.8 GB)."
        ),
    ),
    "gemma4:e4b": ModelEntry(
        ollama_tag="gemma4:e4b",
        family="gemma4",
        max_tokens_default=8192,
        thinking_mode="block",
        recommended_hint=None,
        notes=(
            "Emits explicit 'thinking' blocks in the response content array. "
            "9.6 GB on disk; meaningful VRAM pressure on 12 GB cards once KV cache grows."
        ),
    ),
}


def get_model_entry(name: str) -> Optional[ModelEntry]:
    return MODEL_REGISTRY.get(name)


def list_models() -> list:
    return sorted(MODEL_REGISTRY.keys())
