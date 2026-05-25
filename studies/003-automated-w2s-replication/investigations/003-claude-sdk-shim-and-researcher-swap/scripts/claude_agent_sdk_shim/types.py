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
class ToolResultBlock:
    tool_use_id: str
    content: Any
    is_error: bool = False


@dataclass
class AssistantMessage:
    content: List[Union[TextBlock, ToolUseBlock]]
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
