from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union


@dataclass
class TextBlock:
    text: str


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: Dict[str, Any]


@dataclass
class ThinkingBlock:
    text: str
    source: str = "block"


@dataclass
class ToolResultBlock:
    tool_use_id: str
    content: Any
    is_error: bool = False


@dataclass
class AssistantMessage:
    content: List[Union[TextBlock, ToolUseBlock, ThinkingBlock]]
    model: Optional[str] = None


@dataclass
class UserMessage:
    content: List[Union[TextBlock, ToolResultBlock]]


@dataclass
class ResultMessage:
    result: Optional[str] = None
    stop_reason: Optional[str] = None


@dataclass
class ClaudeAgentOptions:
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    allowed_tools: List[str] = field(default_factory=list)
    mcp_servers: Dict[str, Any] = field(default_factory=dict)
    permission_mode: Optional[str] = None
    cwd: Optional[str] = None
    setting_sources: Optional[List[str]] = None
    betas: Optional[List[str]] = None
    cli_path: Optional[str] = None
    max_tokens: int = 8192
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    tool_invocation_hint: Optional[str] = None
    bash_cwd: Optional[str] = None
    bash_env: Optional[Dict[str, str]] = None
    model_family: Optional[str] = None
    thinking_mode: Optional[str] = None
    model_notes: Optional[str] = None

    def __post_init__(self) -> None:
        from .model_registry import get_model_entry

        if not self.model:
            return
        entry = get_model_entry(self.model)
        if entry is None:
            return
        if self.model_family is None:
            self.model_family = entry.family
        if self.thinking_mode is None:
            self.thinking_mode = entry.thinking_mode
        if self.model_notes is None:
            self.model_notes = entry.notes

    @classmethod
    def from_registry(cls, name: str, **overrides: Any) -> "ClaudeAgentOptions":
        from .model_registry import get_model_entry

        entry = get_model_entry(name)
        if entry is None:
            raise KeyError(f"unknown model registry key: {name}")
        defaults: Dict[str, Any] = {
            "model": entry.ollama_tag,
            "max_tokens": entry.max_tokens_default,
            "tool_invocation_hint": entry.recommended_hint,
            "model_family": entry.family,
            "thinking_mode": entry.thinking_mode,
            "model_notes": entry.notes,
        }
        defaults.update(overrides)
        return cls(**defaults)
