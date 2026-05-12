"""Calibration trial runner.

Driver for running the A1 seed corpus (default 18 pairs / 36 records)
against a target model and writing per-(record, model) results.

Usage:
    uv run harness/runner.py --model gemma3:4b-it-qat --backend ollama --n 20

For each record, runs `n` trials (default 20 per
`calibration_methodology.md`), scores each via parser.scored_success,
and appends to `results/{model_id_safe}/{date}.jsonl`. Idempotent —
re-runs skip records that already have n trials for that model on
that date.

Skeleton only. Wired up after the user authorizes target-model
selection and confirms the desktop/Ollama or API path is live.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
SEEDS_PATH = STUDY_ROOT / "seeds.jsonl"
SYSTEM_PROMPTS_DIR = STUDY_ROOT / "system_prompts"
SYSTEM_PROMPTS_MANIFEST = SYSTEM_PROMPTS_DIR / "manifest.json"
RESULTS_ROOT = STUDY_ROOT / "results"

sys.path.insert(0, str(STUDY_ROOT))
from harness.inference import get_backend  # noqa: E402
from harness.parser import classify_trial  # noqa: E402
from harness.prompt_format import (  # noqa: E402
    build_prompt,
    load_system_prompt_body,
    load_system_prompt_manifest,
)


def _safe_model_id(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _load_records(path: Path | None = None) -> list[dict]:
    p = path or SEEDS_PATH
    return [json.loads(line) for line in p.read_text().splitlines() if line]


def main() -> int:
    p = argparse.ArgumentParser(description="Run the calibration trial loop.")
    p.add_argument("--model", required=True,
                   help="Target model id, e.g. gemma3:4b-it-qat (Ollama) "
                        "or gemma-3-4b-it (Gemini API).")
    p.add_argument("--backend", default="ollama",
                   choices=["ollama", "gemini"],
                   help="Inference backend; see harness/inference.py.")
    p.add_argument("--n", type=int, default=20,
                   help="Trials per record (default 20 per calibration_methodology.md).")
    p.add_argument("--limit", type=int, default=None,
                   help="Optional cap on record count for quick smoke tests.")
    p.add_argument("--dry-run", action="store_true",
                   help="Build prompts and identify the dispatch but don't call the model.")
    p.add_argument("--temperature", type=float, default=None,
                   help="Override sampling temperature (default: backend default, currently 1.0).")
    p.add_argument("--top-p", type=float, default=None,
                   help="Override sampling top_p (default: backend default, currently 0.95).")
    p.add_argument("--prompt-set", default="neutral", choices=["neutral", "directive"],
                   help="When 'directive', remaps each record's `*_neutral_v1` system_prompt_id "
                        "to its `*_directive_v1` sibling (see system_prompts/manifest.json). "
                        "Used for the 006 temperature × prompt 2x2.")
    p.add_argument("--results-tag", default=None,
                   help="Optional filename prefix for the results file. Without this, "
                        "results land at results/<model>/<date>.jsonl. With --results-tag X, "
                        "the file becomes results/<model>/<X>_<date>.jsonl.")
    p.add_argument("--seeds", default=None,
                   help="Path to the seed corpus JSONL. Defaults to "
                        "studies/001-tool-calibration/seeds.jsonl (the A1 hand-curated set). "
                        "Pass `../../bulk_seeds.jsonl` (or any other JSONL conforming to "
                        "the metadata schema) to grade an alternate corpus.")
    args = p.parse_args()

    backend = get_backend(args.backend)
    manifest = load_system_prompt_manifest(SYSTEM_PROMPTS_MANIFEST)
    seeds_path = Path(args.seeds).resolve() if args.seeds else None
    records = _load_records(seeds_path)
    if args.limit is not None:
        records = records[: args.limit]

    today = dt.date.today().isoformat()
    run_id = uuid.uuid4().hex[:8]
    out_dir = RESULTS_ROOT / _safe_model_id(args.model)
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = f"{args.results_tag}_{today}.jsonl" if args.results_tag else f"{today}.jsonl"
    out_path = out_dir / fname

    print(f"runner: {len(records)} records × n={args.n} trials → {out_path}")
    print(f"run_id={run_id} backend={args.backend} model={args.model} "
          f"dry_run={args.dry_run}")

    for rec in records:
        sys_id = rec["system_prompt_id"]
        if args.prompt_set == "directive":
            directive_id = sys_id.replace("_neutral_v1", "_directive_v1")
            if directive_id in manifest:
                sys_id = directive_id
            # If there's no directive variant (e.g. sys_no_tools_v1),
            # fall through to the original prompt unchanged.
        manifest_entry = manifest[sys_id]
        sys_body = load_system_prompt_body(manifest_entry, SYSTEM_PROMPTS_DIR)
        prompt = build_prompt(rec, system_body=sys_body)

        if args.dry_run:
            preview = prompt.replace("\n", " ")[:80]
            print(f"  [dry] {rec['id']}: {preview}…")
            continue

        successes = 0
        over_calls = 0
        under_calls = 0
        gen_kwargs = {}
        if args.temperature is not None:
            gen_kwargs["temperature"] = args.temperature
        if args.top_p is not None:
            gen_kwargs["top_p"] = args.top_p
        for trial_idx in range(args.n):
            result = backend.generate(prompt, model=args.model, **gen_kwargs)
            ok, err = classify_trial(rec, result.output)
            successes += int(ok)
            if err == "over_call":
                over_calls += 1
            elif err == "under_call":
                under_calls += 1
            raw = result.raw if isinstance(result.raw, dict) else {}
            # Ollama duration fields are nanoseconds; convert to ms.
            def _ns_to_ms(v):
                return None if v is None else round(v / 1e6, 3)
            with out_path.open("a") as f:
                f.write(json.dumps({
                    "run_id": run_id,
                    "record_id": rec["id"],
                    "pair_id": rec["pair_id"],
                    "tool_target": rec["tool_target"],
                    "expected_tool_call": rec["expected_tool_call"],
                    "trial_idx": trial_idx,
                    "model": args.model,
                    "backend": args.backend,
                    "prompt_set": args.prompt_set,
                    "resolved_system_prompt_id": sys_id,
                    "temperature": args.temperature,
                    "top_p": args.top_p,
                    "success": ok,
                    "error_type": err,
                    "output": result.output,
                    "date": today,
                    # Timing + token telemetry from Ollama. Other
                    # backends may populate a subset; missing fields
                    # are None.
                    "prompt_tokens": raw.get("prompt_eval_count"),
                    "output_tokens": raw.get("eval_count"),
                    "total_ms": _ns_to_ms(raw.get("total_duration")),
                    "load_ms": _ns_to_ms(raw.get("load_duration")),
                    "prompt_eval_ms": _ns_to_ms(raw.get("prompt_eval_duration")),
                    "eval_ms": _ns_to_ms(raw.get("eval_duration")),
                }) + "\n")
        sr = successes / args.n if args.n else 0.0
        err_str = ""
        if over_calls or under_calls:
            err_str = f"  [over={over_calls} under={under_calls}]"
        print(f"  {rec['id']}  → {successes}/{args.n}  "
              f"(success_rate={sr:.2f}){err_str}")

    print(f"runner: done run_id={run_id} → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
