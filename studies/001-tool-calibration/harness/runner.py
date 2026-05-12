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
from pathlib import Path

HERE = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
SEEDS_PATH = STUDY_ROOT / "seeds.jsonl"
SYSTEM_PROMPTS_DIR = STUDY_ROOT / "system_prompts"
SYSTEM_PROMPTS_MANIFEST = SYSTEM_PROMPTS_DIR / "manifest.json"
RESULTS_ROOT = STUDY_ROOT / "results"

sys.path.insert(0, str(STUDY_ROOT))
from harness.inference import get_backend  # noqa: E402
from harness.parser import scored_success  # noqa: E402
from harness.prompt_format import (  # noqa: E402
    build_prompt,
    load_system_prompt_body,
    load_system_prompt_manifest,
)


def _safe_model_id(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _load_records() -> list[dict]:
    return [json.loads(line) for line in SEEDS_PATH.read_text().splitlines() if line]


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
    args = p.parse_args()

    backend = get_backend(args.backend)
    manifest = load_system_prompt_manifest(SYSTEM_PROMPTS_MANIFEST)
    records = _load_records()
    if args.limit is not None:
        records = records[: args.limit]

    today = dt.date.today().isoformat()
    out_dir = RESULTS_ROOT / _safe_model_id(args.model)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today}.jsonl"

    print(f"runner: {len(records)} records × n={args.n} trials → {out_path}")
    print(f"backend={args.backend} model={args.model} dry_run={args.dry_run}")

    for rec in records:
        sys_id = rec["system_prompt_id"]
        manifest_entry = manifest[sys_id]
        sys_body = load_system_prompt_body(manifest_entry, SYSTEM_PROMPTS_DIR)
        prompt = build_prompt(rec, system_body=sys_body)

        if args.dry_run:
            # Just verify dispatch — print the record id and the
            # first 60 chars of the prompt.
            preview = prompt.replace("\n", " ")[:80]
            print(f"  [dry] {rec['id']}: {preview}…")
            continue

        successes = 0
        for trial_idx in range(args.n):
            result = backend.generate(prompt, model=args.model)
            ok = scored_success(rec, result.output)
            successes += int(ok)
            with out_path.open("a") as f:
                f.write(json.dumps({
                    "record_id": rec["id"],
                    "pair_id": rec["pair_id"],
                    "tool_target": rec["tool_target"],
                    "trial_idx": trial_idx,
                    "model": args.model,
                    "backend": args.backend,
                    "success": ok,
                    "output_preview": result.output[:400],
                    "date": today,
                }) + "\n")
        sr = successes / args.n if args.n else 0.0
        print(f"  {rec['id']}  → {successes}/{args.n}  (success_rate={sr:.2f})")

    print(f"runner: done → {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
