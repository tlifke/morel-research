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

SEPARATE_REASONING = True

NO_ENFORCEMENT_NOTE = (
    "structured output is NOT enforced by the endpoint for any model, established "
    "by controls 2026-08-15: 14 request shapes all returned HTTP 200 including "
    "deliberately invalid ones, while an unknown model 400s and temperature is "
    "honored, so the body is parsed and these keys are dropped; the cookbook proxy "
    "lists response_format in _UNSUPPORTED_OPENAI_KEYS. Conformance comes from the "
    "schema rendered into the prompt, not from constrained decode."
)


@dataclass(frozen=True)
class TinkerModelFacts:
    advertised_context: int
    structured_output: str
    safety_margin: int = DEFAULT_SAFETY_MARGIN
    note: str = ""


TINKER_MODEL_FACTS: dict[str, TinkerModelFacts] = {
    "thinkingmachines/Inkling-Small": TinkerModelFacts(
        advertised_context=262144,
        structured_output="prompt_only",
        note=(
            "context measured 2026-08-15: 150k accepted, 300k rejected with an "
            "explicit limit. The earlier json_object reading is FALSIFIED: with "
            "json_object set it emitted a markdown fence on 10/10 samples. "
            + NO_ENFORCEMENT_NOTE
        ),
    ),
    "Qwen/Qwen3.5-4B": TinkerModelFacts(
        advertised_context=65536,
        structured_output="prompt_only",
        note=(
            "context measured 2026-08-15: endpoint states 65536. " + NO_ENFORCEMENT_NOTE
        ),
    ),
    "Qwen/Qwen3.5-9B": TinkerModelFacts(
        advertised_context=65536,
        structured_output="prompt_only",
        safety_margin=1024,
        note=(
            "context measured 2026-08-15: endpoint states 65536, but a 65530-token "
            "prompt fails inside the server with 'Input length exceeds the maximum "
            "allowed length (65530 tokens)'; last accepted probe was 65357, hence "
            "the wider safety margin. " + NO_ENFORCEMENT_NOTE
        ),
    ),
}


class TinkerBackend(Backend):
    structured_output = "prompt_only"
    token_count_method = "heuristic"
    seed_honored = False

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        context_limit: Optional[int] = None,
        base_url: str = DEFAULT_BASE_URL,
        api_key_env: str = "TINKER_API_KEY",
        timeout: int = 900,
        tokenizer_id: Optional[str] = None,
        safety_margin: Optional[int] = None,
        separate_reasoning: bool = SEPARATE_REASONING,
    ) -> None:
        self.separate_reasoning = separate_reasoning
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
            "structured_output_enforcement": NO_ENFORCEMENT_NOTE,
            "emits_reasoning_content": bool(spec and spec.emits_reasoning_content),
            "separate_reasoning": self.separate_reasoning,
            "separate_reasoning_note": (
                "sent explicitly: the server default is true but it flipped from "
                "false in June 2026, and another flip would silently move reasoning "
                "text into content and corrupt every parse"
            ),
            "seed_honored": False,
            "seed_note": (
                "measured 2026-08-15: identical payloads at the same seed produced "
                "different outputs, so seed is a repetition LABEL, not a "
                "reproducibility handle; the trace store is the only record of what "
                "was actually sampled"
            ),
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
            "separate_reasoning": self.separate_reasoning,
        }

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
            request_params={k: v for k, v in payload.items() if k != "messages"},
            n_prompt_tokens=usage.get("prompt_tokens"),
            n_completion_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
            finish_reason=choice.get("finish_reason"),
        )
