"""Self-prediction runner.

For each (record, model) pair: build the meta-prompt that embeds the
task's system_prompt + user_prompt, ask the target model to predict its
own behavior, parse the JSON response, write one row per trial to a
JSONL.

n=1 per (record, model) — we are measuring whether a single sample
correlates with the empirical mode, not the stochasticity of the
prediction itself.

Idempotent: re-runs skip records that already have a row for that model
on that day's results file.

Run from repo root (example):
  uv run studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline/runner.py \\
    --model gemma3:4b-it-qat --backend ollama

Outputs land at:
  results/<model_safe>/self_predict_v1_<date>.jsonl
relative to this investigation directory (gitignored — re-runnable).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
INVESTIGATION_ROOT = HERE
STUDY_ROOT = HERE.parents[1]
STUDIES_ROOT = HERE.parents[2]
STUDY_001_ROOT = STUDIES_ROOT / "001-tool-calibration"
PROMPT_PATH = HERE / "prompts" / "self_predict_v1.txt"
RESULTS_ROOT = HERE / "results"

sys.path.insert(0, str(STUDY_001_ROOT))
from harness.inference import get_backend  # noqa: E402
from harness.prompt_format import (  # noqa: E402
    load_system_prompt_body,
    load_system_prompt_manifest,
)


def _safe(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _load_records(seeds_path: Path) -> list[dict]:
    return [json.loads(l) for l in seeds_path.read_text().splitlines() if l]


def _build_meta_prompt(template: str, system_body: str, user_prompt: str) -> str:
    """Fill the meta-prompt template + wrap in Gemma chat tokens."""
    body = template.format(system_prompt=system_body, user_prompt=user_prompt)
    return (
        "<bos><start_of_turn>user\n"
        f"{body}<end_of_turn>\n"
        "<start_of_turn>model\n"
    )


_JSON_OBJECT_RE = re.compile(r"\{(?:[^{}]|\{[^{}]*\})*\}", re.DOTALL)


def parse_self_prediction(output: str) -> tuple[dict | None, str | None]:
    """Best-effort JSON extraction. Returns (parsed_dict, error_msg)."""
    text = output.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass
    m = _JSON_OBJECT_RE.search(text)
    if not m:
        return None, "no_json_object"
    try:
        return json.loads(m.group(0)), None
    except json.JSONDecodeError as e:
        return None, f"json_decode_error: {e}"


def _validate(parsed: dict, available_tools: list[str]) -> str | None:
    """Light schema validation. Returns error key or None."""
    if not isinstance(parsed, dict):
        return "not_object"
    if parsed.get("predicted_behavior") not in {"call_tool", "answer_directly"}:
        return "bad_predicted_behavior"
    if parsed.get("confidence") not in {"low", "medium", "high"}:
        return "bad_confidence"
    if not isinstance(parsed.get("predicted_success"), bool):
        return "bad_predicted_success"
    tool = parsed.get("predicted_tool")
    if parsed["predicted_behavior"] == "call_tool":
        if not isinstance(tool, str) or tool == "":
            return "missing_tool_for_call"
        if available_tools and tool not in available_tools:
            return "predicted_tool_not_available"
    else:
        if tool not in (None, "", "null"):
            return "tool_set_without_call"
    if not isinstance(parsed.get("reasoning"), str):
        return "bad_reasoning"
    return None


def main() -> int:
    p = argparse.ArgumentParser(description="Run the self-prediction baseline trial loop.")
    p.add_argument("--model", required=True, help="Target model id, e.g. gemma3:4b-it-qat")
    p.add_argument("--backend", default="ollama")
    p.add_argument("--seeds", default=str(STUDY_001_ROOT / "bulk_seeds.jsonl"),
                   help="JSONL of records to run. Default: study 001's bulk corpus.")
    p.add_argument("--limit", type=int, default=None, help="Cap on number of records (for smoke tests).")
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--top-p", type=float, default=0.95)
    p.add_argument("--results-tag", default="self_predict_v1")
    p.add_argument("--max-tokens", type=int, default=600)
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    template = PROMPT_PATH.read_text()
    manifest = load_system_prompt_manifest(STUDY_001_ROOT / "system_prompts" / "manifest.json")
    seeds_path = Path(args.seeds).resolve()
    records = _load_records(seeds_path)
    if args.limit:
        records = records[: args.limit]

    out_dir = RESULTS_ROOT / _safe(args.model)
    out_dir.mkdir(parents=True, exist_ok=True)
    date = dt.date.today().isoformat()
    out_path = out_dir / f"{args.results_tag}_{date}.jsonl"

    done_ids: set[str] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line:
                done_ids.add(json.loads(line)["record_id"])

    backend = get_backend(args.backend)
    run_id = uuid.uuid4().hex[:8]

    n_todo = sum(1 for r in records if r["id"] not in done_ids)
    print(f"runner: model={args.model} seeds={seeds_path.name} todo={n_todo} done={len(done_ids)} out={out_path}")

    if args.dry_run:
        for r in records[:5]:
            me = manifest[r["system_prompt_id"]]
            sys_body = load_system_prompt_body(me, STUDY_001_ROOT / "system_prompts")
            prompt = _build_meta_prompt(template, sys_body, r["user_prompt"])
            print(f"  [dry] {r['id']}: {prompt[:160].replace(chr(10), ' ')}…")
        return 0

    n_done = 0
    n_parse_fail = 0
    n_validate_fail = 0
    t0 = time.time()
    with out_path.open("a") as f:
        for r in records:
            if r["id"] in done_ids:
                continue
            me = manifest.get(r["system_prompt_id"])
            if me is None:
                print(f"  warn: no manifest entry for {r['system_prompt_id']} (record {r['id']}) — skipping")
                continue
            sys_body = load_system_prompt_body(me, STUDY_001_ROOT / "system_prompts")
            available_tools = me.get("tool_set", [])
            prompt = _build_meta_prompt(template, sys_body, r["user_prompt"])
            result = backend.generate(
                prompt,
                model=args.model,
                temperature=args.temperature,
                top_p=args.top_p,
                max_tokens=args.max_tokens,
            )
            parsed, parse_err = parse_self_prediction(result.output)
            validate_err = None
            if parsed is not None:
                validate_err = _validate(parsed, available_tools)
                if validate_err:
                    n_validate_fail += 1
            else:
                n_parse_fail += 1
            row = {
                "run_id": run_id,
                "record_id": r["id"],
                "model": args.model,
                "tool_target": r["tool_target"],
                "expected_tool_call": r["expected_tool_call"],
                "system_prompt_id": r["system_prompt_id"],
                "available_tools": available_tools,
                "temperature": args.temperature,
                "top_p": args.top_p,
                "prompt_template": "self_predict_v1",
                "output": result.output,
                "parsed": parsed,
                "parse_error": parse_err,
                "validate_error": validate_err,
                "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            f.write(json.dumps(row) + "\n")
            f.flush()
            n_done += 1
            if n_done % 20 == 0:
                elapsed = time.time() - t0
                rate = n_done / elapsed if elapsed else 0
                eta = (n_todo - n_done) / rate if rate else float("nan")
                print(f"  progress: {n_done}/{n_todo} ({rate:.2f}/s, eta ~{eta/60:.1f} min)  "
                      f"parse_fail={n_parse_fail} validate_fail={n_validate_fail}")

    elapsed = time.time() - t0
    print(f"runner: done run_id={run_id} n={n_done} elapsed={elapsed:.1f}s "
          f"parse_fail={n_parse_fail} validate_fail={n_validate_fail} → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
