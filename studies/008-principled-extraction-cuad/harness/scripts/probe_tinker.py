from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.backends.base import BackendError, BackendUnavailable
from harness.backends.tinker_backend import DEFAULT_MODEL, TinkerBackend


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--confirm-context", action="store_true")
    args = parser.parse_args()

    try:
        backend = TinkerBackend(model=args.model)
    except BackendUnavailable as exc:
        print(f"UNAVAILABLE: {exc}")
        return 2

    report = {"describe": backend.describe(), "notes": backend.notes}

    try:
        result = backend.sample(
            messages=[
                {"role": "system", "content": "Reply with JSON only."},
                {"role": "user", "content": 'Reply with {"ok": true} and nothing else.'},
            ],
            json_schema={"type": "object"},
            temperature=0.0,
            seed=0,
            max_tokens=64,
        )
    except BackendError as exc:
        report["smoke"] = {"status": "failed", "error": str(exc)}
        print(json.dumps(report, indent=2))
        return 3

    report["smoke"] = {
        "status": "ok",
        "text": result.text[:200],
        "n_prompt_tokens": result.n_prompt_tokens,
        "latency_ms": result.latency_ms,
    }

    if args.confirm_context:
        over = backend.context_limit + 1000
        padding = "word " * over
        try:
            backend.sample(
                messages=[{"role": "user", "content": padding}],
                json_schema=None,
                temperature=0.0,
                seed=0,
                max_tokens=4,
            )
            report["context_probe"] = {
                "status": "UNEXPECTED_ACCEPT",
                "sent_tokens_approx": over,
            }
        except BackendError as exc:
            report["context_probe"] = {"status": "rejected_as_expected", "error": str(exc)}

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
