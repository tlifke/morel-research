from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness.backends.base import BackendError, BackendUnavailable
from harness.backends.tinker_backend import (
    DEFAULT_MODEL,
    TINKER_MODEL_FACTS,
    TinkerBackend,
)

SCHEMA = {
    "type": "object",
    "properties": {"capital": {"type": "string"}},
    "required": ["capital"],
    "additionalProperties": False,
}


def availability(backend: TinkerBackend) -> dict:
    try:
        result = backend.sample(
            messages=[{"role": "user", "content": 'Reply with {"capital": "Paris"} only.'}],
            json_schema=SCHEMA,
            temperature=0.0,
            seed=0,
            max_tokens=600,
        )
    except BackendError as exc:
        return {"status": "failed", "error": str(exc)}
    return {
        "status": "ok",
        "content": result.text[:160],
        "finish_reason": result.finish_reason,
        "n_reasoning_chars": result.raw.get("n_reasoning_chars"),
        "n_completion_tokens": result.n_completion_tokens,
        "latency_ms": result.latency_ms,
    }


def measure_context(backend: TinkerBackend, lo: int, hi: int, steps: int) -> dict:
    def accepts(n_words: int) -> tuple[bool, str]:
        try:
            backend.sample(
                messages=[{"role": "user", "content": "word " * n_words}],
                json_schema=None,
                temperature=0.0,
                seed=0,
                max_tokens=4,
            )
            return True, ""
        except BackendError as exc:
            return False, str(exc)

    ok_hi, detail_hi = accepts(hi)
    if ok_hi:
        return {"status": "no_upper_bound_found", "accepted_at": hi}
    trace = [{"n": hi, "accepted": False, "error": detail_hi[:300]}]
    for _ in range(steps):
        mid = (lo + hi) // 2
        ok, detail = accepts(mid)
        trace.append({"n": mid, "accepted": ok, "error": detail[:200] if not ok else None})
        if ok:
            lo = mid
        else:
            hi = mid
    return {"status": "bisected", "last_accepted": lo, "first_rejected": hi, "trace": trace}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--measure-context", action="store_true")
    parser.add_argument("--lo", type=int, default=1000)
    parser.add_argument("--hi", type=int, default=300000)
    parser.add_argument("--steps", type=int, default=6)
    args = parser.parse_args()

    models = list(TINKER_MODEL_FACTS) if args.all else [args.model]
    report = {}
    for model in models:
        try:
            backend = TinkerBackend(model=model)
        except BackendUnavailable as exc:
            print(f"UNAVAILABLE: {exc}")
            return 2
        except BackendError as exc:
            report[model] = {"status": "refused", "error": str(exc)}
            continue
        entry = {"describe": backend.describe(), "notes": backend.notes}
        entry["availability"] = availability(backend)
        if args.measure_context:
            entry["context"] = measure_context(backend, args.lo, args.hi, args.steps)
        report[model] = entry

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
