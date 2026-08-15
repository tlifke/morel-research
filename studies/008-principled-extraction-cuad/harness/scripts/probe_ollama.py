from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.backends.base import BackendError, BackendUnavailable
from harness.backends.ollama_backend import DEFAULT_HOST, OllamaBackend

NEEDLE = "The verification passphrase is CRIMSON-FERRET-4417."


def build_haystack(target_tokens: int) -> str:
    filler = "This paragraph is filler for a context-window probe. " * 8
    body = []
    approx = 0
    while approx < target_tokens * 4:
        body.append(filler)
        approx += len(filler)
    return NEEDLE + "\n\n" + "".join(body)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="qwen3.5:8b")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--num-ctx", type=int, default=32768)
    parser.add_argument("--probe-tokens", type=int, default=0)
    parser.add_argument("--tokenizer-id", default=None)
    args = parser.parse_args()

    try:
        backend = OllamaBackend(
            model=args.model,
            num_ctx=args.num_ctx,
            host=args.host,
            verify=True,
            tokenizer_id=args.tokenizer_id,
        )
    except BackendUnavailable as exc:
        print(f"UNREACHABLE: {exc}")
        return 2
    except BackendError as exc:
        print(f"REFUSED: {exc}")
        return 3

    report = {
        "model": backend.model_id,
        "host": backend.host,
        "requested_num_ctx": backend.requested_num_ctx,
        "model_max_context": backend.model_max_context,
        "modelfile_num_ctx": backend.modelfile_num_ctx,
        "effective_context_limit": backend.context_limit,
        "token_count_method": backend.token_count_method,
    }

    probe_tokens = args.probe_tokens or max(1024, int(backend.context_limit * 0.75))
    haystack = build_haystack(probe_tokens)
    messages = [
        {
            "role": "user",
            "content": haystack
            + "\n\nRepeat the verification passphrase that appeared at the very "
            "top of this message, and nothing else.",
        }
    ]
    try:
        result = backend.sample(
            messages=messages,
            json_schema=None,
            temperature=0.0,
            seed=0,
            max_tokens=64,
        )
    except BackendError as exc:
        report["needle_probe"] = {"status": "failed", "error": str(exc)}
        print(json.dumps(report, indent=2))
        return 4

    recovered = "CRIMSON-FERRET-4417" in result.text
    report["needle_probe"] = {
        "status": "recovered" if recovered else "TRUNCATED_OR_LOST",
        "probe_tokens_requested": probe_tokens,
        "prompt_eval_count": result.n_prompt_tokens,
        "prompt_tokens_estimate": backend.count_tokens(messages[0]["content"]),
        "response": result.text[:200],
    }
    print(json.dumps(report, indent=2))
    return 0 if recovered else 5


if __name__ == "__main__":
    raise SystemExit(main())
