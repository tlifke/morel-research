from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from harness import metrics
from harness.backends.base import Backend, BackendUnavailable
from harness.envs.fake_env import FakeEnvironment
from harness.runner import DEFAULT_MAX_OUTPUT_TOKENS, RunConfig, new_run_id, run_grid
from harness.store import ResultsStore


def make_backend(
    name: str, model: str, num_ctx: int, context_limit: int, tokenizer_id: str | None
) -> Backend:
    if name == "ollama":
        from harness.backends.ollama_backend import OllamaBackend

        return OllamaBackend(model=model, num_ctx=num_ctx, tokenizer_id=tokenizer_id)
    if name == "tinker":
        from harness.backends.tinker_backend import TinkerBackend

        return TinkerBackend(model=model, context_limit=context_limit, tokenizer_id=tokenizer_id)
    if name == "fake":
        from harness.backends.fake_backend import FakeBackend

        payload = {
            "extractions": [
                {
                    "category": "Governing Law",
                    "spans": [
                        "This Agreement shall be governed by the laws of the State of Delaware."
                    ],
                    "principles_cited": ["p01"],
                }
            ],
            "absent": [
                {"category": "Agreement Date", "principles_cited": ["p02"]},
                {"category": "Minimum Commitment", "principles_cited": ["p02"]},
                {"category": "Volume Restriction", "principles_cited": ["p02"]},
            ],
        }
        return FakeBackend(
            lambda messages, idx: json.dumps(payload),
            model="fake-model",
            context_limit=context_limit,
        )
    raise SystemExit(f"unknown backend {name!r}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="fake", choices=["fake", "ollama", "tinker"])
    parser.add_argument("--model", default="qwen3.5:8b")
    parser.add_argument("--num-ctx", type=int, default=32768)
    parser.add_argument("--context-limit", type=int, default=262144)
    parser.add_argument("--out", default=None)
    parser.add_argument("--conditions", default="C1,C2,C3")
    parser.add_argument("--variants", default="field_present,field_absent")
    parser.add_argument("--seeds", default="0")
    parser.add_argument("--split", default="harness_val")
    parser.add_argument("--max-output-tokens", type=int, default=DEFAULT_MAX_OUTPUT_TOKENS)
    parser.add_argument("--max-instances", type=int, default=0)
    parser.add_argument("--tokenizer-id", default=None)
    args = parser.parse_args()

    env = FakeEnvironment()
    try:
        backend = make_backend(
            args.backend, args.model, args.num_ctx, args.context_limit, args.tokenizer_id
        )
    except BackendUnavailable as exc:
        print(f"UNAVAILABLE: {exc}")
        return 2

    out = Path(args.out) if args.out else Path(__file__).resolve().parents[2] / "data" / "fake_e2e"
    store = ResultsStore(out, strict=False)
    config = RunConfig(
        run_id=new_run_id("fake-e2e"),
        temperature=0.7,
        max_output_tokens=args.max_output_tokens,
        principle_set_version=env.principle_set().version,
        trace_root=out / "traces",
    )

    instances = env.load_instances(args.split)
    if args.max_instances:
        instances = instances[: args.max_instances]

    results = run_grid(
        env=env,
        backend=backend,
        instances=instances,
        conditions=args.conditions.split(","),
        seeds=[int(s) for s in args.seeds.split(",")],
        schema_variants=args.variants.split(","),
        principle_set=env.principle_set(),
        config=config,
        store=store,
    )

    rows = [r.trial.model_dump() for r in results]
    print(
        json.dumps(
            {
                "backend": backend.describe(),
                "n_trials": len(rows),
                "run_id": config.run_id,
                "max_output_tokens": config.max_output_tokens,
                "trace_dir": str(out / "traces" / config.run_id),
            },
            indent=2,
        )
    )
    print(json.dumps(metrics.stratified_summary(rows), indent=2, default=str))
    print(json.dumps(metrics.corpus_level_a(rows, "final"), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
