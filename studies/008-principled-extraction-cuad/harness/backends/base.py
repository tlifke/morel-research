from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

StructuredOutputMechanism = Literal["json_schema", "json_object", "prompt_only"]
TokenCountMethod = Literal["exact", "heuristic"]

HEURISTIC_CHARS_PER_TOKEN = 4.0


class BackendError(RuntimeError):
    pass


class BackendUnavailable(BackendError):
    pass


@dataclass
class SamplingResult:
    text: str
    raw: dict[str, Any]
    n_prompt_tokens: Optional[int]
    n_completion_tokens: Optional[int]
    latency_ms: int
    finish_reason: Optional[str] = None
    request_params: Optional[dict[str, Any]] = None


class Backend(ABC):
    model_id: str
    context_limit: int
    structured_output: StructuredOutputMechanism
    token_count_method: TokenCountMethod = "heuristic"
    accepts_seed_param: bool = True
    seed_honored: bool = True
    tokenizer_id: Optional[str] = None
    notes: dict[str, Any] = field(default_factory=dict)

    def load_tokenizer(self, tokenizer_id: Optional[str]) -> None:
        self.tokenizer_id = tokenizer_id
        self._tokenizer = None
        if tokenizer_id is None:
            self.token_count_method = "heuristic"
            return
        try:
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise BackendError(
                f"tokenizer_id={tokenizer_id!r} was requested but transformers is not "
                f"installed; refusing to fall back to a character heuristic silently"
            ) from exc
        self._tokenizer = AutoTokenizer.from_pretrained(tokenizer_id)
        self.token_count_method = "exact"

    def count_tokens(self, text: str) -> int:
        tokenizer = getattr(self, "_tokenizer", None)
        if tokenizer is not None:
            return len(tokenizer.encode(text, add_special_tokens=False))
        return int(math.ceil(len(text) / HEURISTIC_CHARS_PER_TOKEN))

    @abstractmethod
    def sample(
        self,
        messages: list[dict[str, str]],
        json_schema: Optional[dict[str, Any]],
        temperature: float,
        seed: int,
        max_tokens: int,
    ) -> SamplingResult:
        ...

    def describe(self) -> dict[str, Any]:
        described = {
            "model": self.model_id,
            "context_limit": self.context_limit,
            "structured_output": self.structured_output,
            "token_count_method": self.token_count_method,
            "tokenizer_id": self.tokenizer_id,
            "seed_honored": self.seed_honored,
        }
        separate_reasoning = getattr(self, "separate_reasoning", None)
        if separate_reasoning is not None:
            described["separate_reasoning"] = separate_reasoning
        return described
