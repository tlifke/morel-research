from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STUDY_ROOT = Path(__file__).resolve().parents[2]
if str(STUDY_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDY_ROOT))

from harness.backends.tinker_backend import TinkerBackend
from harness.envs.cuad_env import CuadEnvironment
from harness.principles_io import load_principle_set
from harness.runner import RunConfig, new_run_id, run_grid
from harness.store import ResultsStore
from harness.trace_store import TraceReader

PRINCIPLES = STUDY_ROOT / "principles" / "pilot" / "candidates_round2.yaml"
OUT_ROOT = STUDY_ROOT / "data" / "traces" / "smoke"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen3.5-9B")
    parser.add_argument("--split", default="excluded")
    parser.add_argument("--n-contracts", type=int, default=2)
    parser.add_argument("--conditions", default="C1,C2,C3")
    parser.add_argument("--schema-variant", default="field_present")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-output-tokens", type=int, default=16384)
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args()

    conditions = args.conditions.split(",")
    principle_set = load_principle_set(PRINCIPLES, version="pilot-round2-all23")
    env = CuadEnvironment(principle_set=principle_set)

    try:
        env.assert_ready(conditions)
        citation_note = "applicability loaded; citation metrics are measurements"
    except RuntimeError as exc:
        citation_note = f"CITATION METRICS ARE NOT MEASUREMENTS: {exc}"
        print("!! " + citation_note, file=sys.stderr)

    instances = sorted(env.load_instances(args.split), key=lambda i: i.n_tokens)
    instances = instances[: args.n_contracts]

    backend = TinkerBackend(model=args.model)
    run_id = args.run_id or new_run_id("smoke")
    store = ResultsStore(OUT_ROOT / run_id)
    config = RunConfig(
        run_id=run_id,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
        principle_set_version=principle_set.version,
        trace_root=OUT_ROOT / "traces",
        compress_traces=False,
    )

    print(json.dumps({"run_id": run_id, "env": env.describe()}, indent=2)[:2000])
    print(
        json.dumps(
            {
                "contracts": [
                    {"id": i.contract_id, "n_tokens": i.n_tokens} for i in instances
                ],
                "conditions": conditions,
                "citation_note": citation_note,
                "out": str(OUT_ROOT / run_id),
            },
            indent=2,
        )
    )

    results = run_grid(
        env=env,
        backend=backend,
        instances=instances,
        conditions=conditions,
        seeds=[args.seed],
        schema_variants=[args.schema_variant],
        principle_set=principle_set,
        config=config,
        store=store,
        skip_existing=True,
    )

    for result in results:
        row = result.trial
        answer = row.answer or {}
        level_a = (answer.get("level_a") or {}).get("micro", {})
        level_b = answer.get("level_b") or {}
        citation = row.citation or {}
        print(
            json.dumps(
                {
                    "contract": row.contract_id[:40],
                    "condition": row.condition,
                    "outcome": row.outcome,
                    "failure_stage": (row.failure_detail or {}).get("stage"),
                    "n_completion_tokens": row.n_completion_tokens,
                    "latency_ms": row.latency_ms,
                    "truncated": row.completion_truncated,
                    "counts": level_a.get("counts"),
                    "span_f1": level_b.get("span_f1"),
                    "verbatim_exact_rate": level_b.get("verbatim_exact_rate"),
                    "verbatim_not_found_rate": level_b.get("verbatim_not_found_rate"),
                    "compliance_pass_rate": (row.compliance or {}).get("pass_rate"),
                    "n_decisions_with_citations": (row.leakage or {}).get(
                        "n_decisions_with_nonempty_cited"
                    ),
                    "citation_f1": citation.get("f1"),
                    "n_decision_rows": len(result.decisions),
                }
            )
        )

    verify = TraceReader(config.trace_root).verify_against_trials(
        run_id, store.read_trials()
    )
    print(json.dumps({"trace_verify": verify}, indent=2))


if __name__ == "__main__":
    main()
