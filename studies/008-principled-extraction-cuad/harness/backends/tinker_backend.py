from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Optional

from ..model_registry import served_name, spec_for
from .base import Backend, BackendError, BackendUnavailable, SamplingResult

DEFAULT_BASE_URL = "https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1"
DEFAULT_MODEL = "thinkingmachines/Inkling-Small"

SUBSTRATE = "tinker"

_USER_AGENT = "curl/8.7.1"

DEFAULT_SAFETY_MARGIN = 512


@dataclass(frozen=True)
class TinkerModelFacts:
    advertised_context: int
    structured_output: str
    safety_margin: int = DEFAULT_SAFETY_MARGIN
    note: str = ""


TINKER_MODEL_FACTS: dict[str, TinkerModelFacts] = {
    "thinkingmachines/Inkling-Small": TinkerModelFacts(
        advertised_context=262144,
        structured_output="json_object",
        note="measured 2026-08-15: 150k accepted, 300k rejected with an explicit limit",
    ),
    "Qwen/Qwen3.5-4B": TinkerModelFacts(
        advertised_context=65536,
        structured_output="prompt_only",
        note=(
            "measured 2026-08-15: endpoint states 65536; response_format is accepted "
            "but neither json_object nor json_schema constrains the decode"
        ),
    ),
    "Qwen/Qwen3.5-9B": TinkerModelFacts(
        advertised_context=65536,
        structured_output="prompt_only",
        safety_margin=1024,
        note=(
            "measured 2026-08-15: endpoint states 65536, but a 65530-token prompt "
            "fails inside the server with 'Input length exceeds the maximum allowed "
            "length (65530 tokens)'; last accepted probe was 65357, hence the wider "
            "safety margin"
        ),
    ),
}


class TinkerBackend(Backend):
    structured_output = "json_object"
    token_count_method = "heuristic"

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        context_limit: Optional[int] = None,
        base_url: str = DEFAULT_BASE_URL,
        api_key_env: str = "TINKER_API_KEY",
        timeout: int = 900,
        tokenizer_id: Optional[str] = None,
        safety_margin: Optional[int] = None,
    ) -> None:
        self.model_id = model
        self.served_model = served_name(model, SUBSTRATE)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.api_key = os.environ.get(api_key_env)
        if not self.api_key:
            raise BackendUnavailable(
                f"{api_key_env} is not set; Tinker backend cannot authenticate"
            )

        facts = TINKER_MODEL_FACTS.get(model)
        if facts is None and context_limit is None:
            raise BackendError(
                f"no measured context window for {model!r} on Tinker and none supplied; "
                f"measure it with probe_tinker.py rather than guessing"
            )
        margin = safety_margin if safety_margin is not None else (
            facts.safety_margin if facts else DEFAULT_SAFETY_MARGIN
        )
        advertised = context_limit if context_limit is not None else facts.advertised_context
        self.advertised_context_limit = advertised
        self.safety_margin = margin
        self.context_limit = advertised - margin
        if facts is not None:
            self.structured_output = facts.structured_output

        spec = spec_for(model)
        if tokenizer_id is None and spec is not None:
            tokenizer_id = None
        self.load_tokenizer(tokenizer_id)

        self.notes: dict[str, Any] = {
            "served_model": self.served_model,
            "advertised_context_limit": advertised,
            "safety_margin": margin,
            "effective_context_limit": self.context_limit,
            "context_measurement": facts.note if facts else "supplied by caller",
            "structured_output": self.structured_output,
            "emits_reasoning_content": bool(spec and spec.emits_reasoning_content),
        }

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        req = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": _USER_AGENT,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            body = exc.read().decode()[:400]
            raise BackendError(f"tinker HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BackendUnavailable(f"tinker unreachable: {exc}") from exc

    def sample(
        self,
        messages: list[dict[str, str]],
        json_schema: Optional[dict[str, Any]],
        temperature: float,
        seed: int,
        max_tokens: int,
    ) -> SamplingResult:
        payload: dict[str, Any] = {
            "model": self.served_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "seed": seed,
        }
        if json_schema is not None:
            payload["response_format"] = {"type": "json_object"}

        t0 = time.time()
        data = self._post("/chat/completions", payload)
        latency_ms = int((time.time() - t0) * 1000)

        choice = (data.get("choices") or [{}])[0]
        message = choice.get("message") or {}
        usage = data.get("usage") or {}
        reasoning = message.get("reasoning_content") or ""

        return SamplingResult(
            text=message.get("content") or "",
            raw={**data, "n_reasoning_chars": len(reasoning)},
            n_prompt_tokens=usage.get("prompt_tokens"),
            n_completion_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason"),
        )
