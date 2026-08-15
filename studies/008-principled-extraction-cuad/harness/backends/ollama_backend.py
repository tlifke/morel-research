from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any, Optional

from .base import Backend, BackendError, BackendUnavailable, SamplingResult

DEFAULT_HOST = "http://100.97.4.17:11434"

_CONTEXT_KEY_SUFFIX = ".context_length"


def _post(host: str, path: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    req = urllib.request.Request(
        host.rstrip("/") + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "User-Agent": "morel-harness/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raise BackendError(f"ollama HTTP {exc.code}: {exc.read().decode()[:400]}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BackendUnavailable(f"ollama unreachable at {host}: {exc}") from exc


class OllamaBackend(Backend):
    structured_output = "json_schema"
    token_count_method = "heuristic"

    def __init__(
        self,
        model: str,
        num_ctx: int,
        host: str = DEFAULT_HOST,
        timeout: int = 900,
        verify: bool = True,
        truncation_guard_ratio: float = 0.8,
        tokenizer_id: Optional[str] = None,
    ) -> None:
        self.model_id = model
        self.host = host
        self.timeout = timeout
        self.requested_num_ctx = num_ctx
        self.truncation_guard_ratio = truncation_guard_ratio
        self.notes: dict[str, Any] = {}
        self.load_tokenizer(tokenizer_id)
        self.model_max_context: Optional[int] = None
        self.modelfile_num_ctx: Optional[int] = None
        if verify:
            self.verify_context_window()
            self.context_limit = min(num_ctx, self.model_max_context or num_ctx)
        else:
            self.context_limit = num_ctx

    def show(self) -> dict[str, Any]:
        return _post(self.host, "/api/show", {"model": self.model_id}, timeout=60)

    def verify_context_window(self) -> dict[str, Any]:
        info = self.show()
        model_info = info.get("model_info") or {}
        ctx_values = [
            v
            for k, v in model_info.items()
            if k.endswith(_CONTEXT_KEY_SUFFIX) and isinstance(v, int)
        ]
        if not ctx_values:
            raise BackendError(
                f"could not determine the trained context length of {self.model_id!r} "
                f"from /api/show; refusing to guess"
            )
        self.model_max_context = max(ctx_values)

        params = info.get("parameters") or ""
        for line in params.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[0] == "num_ctx":
                self.modelfile_num_ctx = int(parts[1])

        if self.requested_num_ctx > self.model_max_context:
            raise BackendError(
                f"requested num_ctx={self.requested_num_ctx} exceeds the trained "
                f"context length {self.model_max_context} of {self.model_id!r}; "
                f"ollama would silently truncate"
            )

        self.notes = {
            "model_max_context": self.model_max_context,
            "modelfile_num_ctx": self.modelfile_num_ctx,
            "requested_num_ctx": self.requested_num_ctx,
            "warning": (
                "OLLAMA_NUM_PARALLEL>1 on the server divides the context across "
                "concurrent slots; run this backend serialized"
            ),
        }
        return self.notes

    def sample(
        self,
        messages: list[dict[str, str]],
        json_schema: Optional[dict[str, Any]],
        temperature: float,
        seed: int,
        max_tokens: int,
    ) -> SamplingResult:
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": self.requested_num_ctx,
                "temperature": temperature,
                "seed": seed,
                "num_predict": max_tokens,
            },
        }
        if json_schema is not None:
            payload["format"] = json_schema

        t0 = time.time()
        data = _post(self.host, "/api/chat", payload, timeout=self.timeout)
        latency_ms = int((time.time() - t0) * 1000)

        text = (data.get("message") or {}).get("content", "")
        n_prompt = data.get("prompt_eval_count")
        n_completion = data.get("eval_count")

        estimate = self.count_tokens("".join(m.get("content", "") for m in messages))
        if (
            n_prompt is not None
            and estimate > 0
            and n_prompt < estimate * self.truncation_guard_ratio
        ):
            raise BackendError(
                f"ollama reported prompt_eval_count={n_prompt} against an estimate of "
                f"{estimate} tokens (num_ctx={self.requested_num_ctx}); the prompt was "
                f"probably silently truncated"
            )

        return SamplingResult(
            text=text,
            raw=data,
            request_params={k: v for k, v in payload.items() if k != "messages"},
            n_prompt_tokens=n_prompt,
            n_completion_tokens=n_completion,
            latency_ms=latency_ms,
            finish_reason=data.get("done_reason"),
        )
