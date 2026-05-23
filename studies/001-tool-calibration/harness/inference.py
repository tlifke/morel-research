"""Inference backend abstractions for the calibration harness.

Two backends planned:

- `OllamaBackend` — POSTs to a remote Ollama HTTP server (default
  `http://100.97.4.17:11434` over Tailscale to the desktop). Supports
  any model Ollama has pulled, including Gemma 3 4B/12B IT QAT.
- `GeminiBackend` — Google AI Studio API. Uses `GEMINI_API_KEY` env.
  Serves both Gemini and Gemma 3 models under the same key.

Both expose a single `generate(prompt, *, model, stop=None,
max_tokens=512, temperature=0.0)` method returning the raw model
output as a string. The harness does its own tool-call parsing on the
output (see `parser.py`); backends don't try to interpret tool calls
themselves.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import urllib.request
import urllib.error


@dataclass
class GenerationResult:
    output: str
    model: str
    raw: dict


class InferenceBackend:
    """Interface marker. Subclasses implement `generate`."""

    name: str = "abstract"

    def generate(
        self,
        prompt: str,
        *,
        model: str,
        stop: list[str] | None = None,
        max_tokens: int = 512,
        temperature: float = 1.0,
        top_p: float = 0.95,
    ) -> GenerationResult:
        raise NotImplementedError


class OllamaBackend(InferenceBackend):
    """HTTP client for an Ollama server.

    Default host targets the desktop over Tailscale. Set
    `OLLAMA_HOST` env to override (e.g. `http://127.0.0.1:11434` for
    a laptop-local Ollama).
    """

    name = "ollama"

    def __init__(self, host: str | None = None, timeout: float | None = None) -> None:
        self.host = host or os.environ.get("OLLAMA_HOST", "http://100.97.4.17:11434")
        if timeout is None:
            timeout = float(os.environ.get("OLLAMA_TIMEOUT", "300"))
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        *,
        model: str,
        stop: list[str] | None = None,
        max_tokens: int = 512,
        temperature: float = 1.0,
        top_p: float = 0.95,
    ) -> GenerationResult:
        # Defaults (temperature=1.0, top_p=0.95) follow current
        # recommended sampling for production-typical behavior on
        # modern instruction-tuned models. temperature=0 is a legacy
        # convention that doesn't cleanly probe how models actually
        # behave in deployment.
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": top_p,
                "num_predict": max_tokens,
            },
        }
        if stop:
            payload["options"]["stop"] = stop
        req = urllib.request.Request(
            f"{self.host.rstrip('/')}/api/generate",
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = json.loads(r.read().decode())
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Ollama backend unreachable at {self.host}. "
                f"Confirm OLLAMA_HOST=0.0.0.0:11434 on the desktop and "
                f"Tailscale connectivity. Underlying error: {e}"
            ) from e
        return GenerationResult(output=body.get("response", ""), model=model, raw=body)


class GeminiBackend(InferenceBackend):
    """Google AI Studio REST client.

    Reads `GEMINI_API_KEY` from environment. Same key serves Gemini
    and Gemma 3 model families on Google's API.

    NOTE: skeleton only — Google AI Studio's exact endpoint for Gemma
    3 4B IT / 12B IT under the standard generateContent path needs
    confirmation before this is wired up. Particularly: whether the
    model id is `gemma-3-4b-it` (Vertex) or `models/gemma-3-4b-it`
    (Studio v1beta), and whether system instructions / tool
    declarations use the same shape as Gemini calls.
    """

    name = "gemini"

    def __init__(self, api_key: str | None = None, timeout: float = 120.0) -> None:
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "GEMINI_API_KEY not set. Source from "
                "morel-primordia/.env.local or set explicitly."
            )
        self.timeout = timeout

    def generate(
        self,
        prompt: str,
        *,
        model: str,
        stop: list[str] | None = None,
        max_tokens: int = 512,
        temperature: float = 0.0,
    ) -> GenerationResult:
        # TODO: confirm endpoint shape for Gemma 3 on Google AI Studio
        # vs. Vertex AI. Stub keeps the harness from being
        # tightly coupled to the wrong endpoint before verification.
        raise NotImplementedError(
            "GeminiBackend.generate is a skeleton — wire up after "
            "confirming the Gemma 3 endpoint for the active "
            "GEMINI_API_KEY (AI Studio vs Vertex AI vs OpenRouter)."
        )


_BACKENDS: dict[str, type[InferenceBackend]] = {
    "ollama": OllamaBackend,
    "gemini": GeminiBackend,
}


def get_backend(name: str, **kwargs) -> InferenceBackend:
    cls = _BACKENDS.get(name)
    if cls is None:
        raise ValueError(f"unknown backend {name!r}; available: {list(_BACKENDS)}")
    return cls(**kwargs)
