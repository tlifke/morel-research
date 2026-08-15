from __future__ import annotations

from typing import Any, Callable, Optional, Sequence

from .base import Backend, BackendError, SamplingResult


class FakeBackend(Backend):
    structured_output = "json_schema"
    token_count_method = "heuristic"

    def __init__(
        self,
        responses: Sequence[str] | Callable[[list[dict[str, str]], int], str],
        model: str = "fake-model",
        context_limit: int = 8192,
        raise_on_call: Optional[Exception] = None,
    ) -> None:
        self.model_id = model
        self.context_limit = context_limit
        self._responses = responses
        self._raise = raise_on_call
        self.calls: list[dict[str, Any]] = []

    def sample(
        self,
        messages: list[dict[str, str]],
        json_schema: Optional[dict[str, Any]],
        temperature: float,
        seed: int,
        max_tokens: int,
    ) -> SamplingResult:
        if self._raise is not None:
            raise self._raise
        idx = len(self.calls)
        self.calls.append(
            {
                "messages": messages,
                "json_schema": json_schema,
                "temperature": temperature,
                "seed": seed,
                "max_tokens": max_tokens,
            }
        )
        if callable(self._responses):
            text = self._responses(messages, idx)
        elif idx < len(self._responses):
            text = self._responses[idx]
        else:
            text = self._responses[-1] if self._responses else ""
        return SamplingResult(
            text=text,
            raw={"fake": True, "call_index": idx},
            n_prompt_tokens=self.count_tokens(
                "".join(m.get("content", "") for m in messages)
            ),
            n_completion_tokens=self.count_tokens(text),
            latency_ms=1,
            finish_reason="stop",
        )
