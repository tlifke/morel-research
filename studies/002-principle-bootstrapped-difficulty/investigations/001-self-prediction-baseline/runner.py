"""Self-prediction runner — four-question ladder.

Each question is asked independently (no shared conversation context):

  Q1 — Could you answer correctly with NO tools?           (capability_no_tools)
  Q2 — If you USED the appropriate tool, would the         (capability_with_tools)
        final answer be correct?
  Q3 — Would you reach for a tool on this task?            (behavior)
  Q4 — Which tool would you reach for?                     (tool_selection)

The runner takes --question and runs that question over the corpus on
one model. Independent calls per (record, trial). Idempotent: re-runs
skip (record_id, trial_index) pairs already in the day's output file.

Outputs land at:
  results/<model_safe>/<question>_<n>_<date>.jsonl
relative to this investigation directory.

Run from repo root (example):
  uv run studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline/runner.py \\
    --model gemma3:4b-it-qat --question q1 --n 5 --limit 20
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
INVESTIGATION_ROOT = HERE
STUDIES_ROOT = HERE.parents[2]
STUDY_001_ROOT = STUDIES_ROOT / "001-tool-calibration"
RESULTS_ROOT = HERE / "results"

sys.path.insert(0, str(STUDY_001_ROOT))
from harness.inference import get_backend  # noqa: E402
from harness.prompt_format import (  # noqa: E402
    load_system_prompt_body,
    load_system_prompt_manifest,
)

QUESTIONS = {
    "q1": {
        "template": HERE / "prompts" / "q1_capability_no_tools.txt",
        "needs_system_prompt": False,
        "needs_tool_list": False,
        "validator": "_validate_q1",
    },
    "q2": {
        "template": HERE / "prompts" / "q2_capability_with_tools.txt",
        "needs_system_prompt": False,
        "needs_tool_list": True,
        "validator": "_validate_q2",
    },
    "q3": {
        "template": HERE / "prompts" / "q3_behavior.txt",
        "needs_system_prompt": True,
        "needs_tool_list": True,
        "validator": "_validate_q3",
    },
    "q4": {
        "template": HERE / "prompts" / "q4_tool_selection.txt",
        "needs_system_prompt": True,
        "needs_tool_list": True,
        "validator": "_validate_q4",
    },
}


def _safe(model: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _load_records(seeds_path: Path) -> list[dict]:
    return [json.loads(l) for l in seeds_path.read_text().splitlines() if l]


def _format_tool_list(available_tools: list[str]) -> str:
    if not available_tools:
        return "  (no tools available)"
    return "\n".join(f"  - {t}" for t in available_tools)


def _build_meta_prompt(
    question: str,
    template: str,
    *,
    system_body: str | None,
    user_prompt: str,
    available_tools: list[str],
) -> str:
    qspec = QUESTIONS[question]
    fmt_kwargs: dict[str, str] = {"user_prompt": user_prompt}
    if qspec["needs_system_prompt"]:
        fmt_kwargs["system_prompt"] = system_body or ""
    if qspec["needs_tool_list"]:
        fmt_kwargs["tool_list"] = _format_tool_list(available_tools)
    body = template.format(**fmt_kwargs)
    return (
        "<bos><start_of_turn>user\n"
        f"{body}<end_of_turn>\n"
        "<start_of_turn>model\n"
    )


_JSON_OBJECT_RE = re.compile(r"\{(?:[^{}]|\{[^{}]*\})*\}", re.DOTALL)


def parse_json_output(output: str) -> tuple[dict | None, str | None]:
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


_CONFIDENCE_VALS = {"low", "medium", "high"}


def _check_basic(parsed: dict) -> str | None:
    if not isinstance(parsed, dict):
        return "not_object"
    if parsed.get("confidence") not in _CONFIDENCE_VALS:
        return "bad_confidence"
    if not isinstance(parsed.get("reasoning"), str):
        return "bad_reasoning"
    return None


def _validate_q1(parsed: dict, available_tools: list[str]) -> str | None:
    err = _check_basic(parsed)
    if err:
        return err
    if parsed.get("verdict") not in {"yes", "no", "i_cannot_know"}:
        return "bad_verdict"
    return None


def _validate_q2(parsed: dict, available_tools: list[str]) -> str | None:
    err = _check_basic(parsed)
    if err:
        return err
    if parsed.get("verdict") not in {"yes", "no"}:
        return "bad_verdict"
    return None


def _validate_q3(parsed: dict, available_tools: list[str]) -> str | None:
    err = _check_basic(parsed)
    if err:
        return err
    if parsed.get("predicted_behavior") not in {"call_tool", "answer_directly"}:
        return "bad_predicted_behavior"
    return None


def _validate_q4(parsed: dict, available_tools: list[str]) -> str | None:
    err = _check_basic(parsed)
    if err:
        return err
    tool = parsed.get("predicted_tool")
    if not isinstance(tool, str) or not tool:
        return "missing_predicted_tool"
    if available_tools and tool not in available_tools:
        return "predicted_tool_not_available"
    return None


_VALIDATORS = {
    "q1": _validate_q1, "q2": _validate_q2, "q3": _validate_q3, "q4": _validate_q4,
}


def main() -> int:
    p = argparse.ArgumentParser(description="Self-prediction runner — four-question ladder.")
    p.add_argument("--model", required=True)
    p.add_argument("--backend", default="ollama")
    p.add_argument("--question", required=True, choices=list(QUESTIONS))
    p.add_argument("--n", type=int, default=1, help="Trials per (record, question). n=1 is the default.")
    p.add_argument("--seeds", default=str(STUDY_001_ROOT / "bulk_seeds.jsonl"))
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--temperature", type=float, default=1.0)
    p.add_argument("--top-p", type=float, default=0.95)
    p.add_argument("--results-tag", default=None,
                   help="Override the output filename tag. Default: <question>_n<n>.")
    p.add_argument("--max-tokens", type=int, default=400)
    p.add_argument("--concurrency", type=int, default=1,
                   help="Number of concurrent in-flight HTTP requests. "
                        "Ollama must have OLLAMA_NUM_PARALLEL set to at least "
                        "this value (default 'auto' usually handles 4+).")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    template = QUESTIONS[args.question]["template"].read_text()
    manifest = load_system_prompt_manifest(STUDY_001_ROOT / "system_prompts" / "manifest.json")
    seeds_path = Path(args.seeds).resolve()
    records = _load_records(seeds_path)
    if args.limit:
        records = records[: args.limit]

    out_dir = RESULTS_ROOT / _safe(args.model)
    out_dir.mkdir(parents=True, exist_ok=True)
    date = dt.date.today().isoformat()
    tag = args.results_tag or f"{args.question}_n{args.n}"
    out_path = out_dir / f"{tag}_{date}.jsonl"

    done: set[tuple[str, int]] = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line:
                row = json.loads(line)
                done.add((row["record_id"], row["trial_index"]))

    validator = _VALIDATORS[args.question]
    backend = get_backend(args.backend)
    run_id = uuid.uuid4().hex[:8]

    todo = [(r, i) for r in records for i in range(args.n) if (r["id"], i) not in done]
    print(f"runner: model={args.model} question={args.question} n={args.n} "
          f"todo={len(todo)} done={len(done)} out={out_path}")

    if args.dry_run:
        for r in records[:3]:
            me = manifest[r["system_prompt_id"]]
            sys_body = load_system_prompt_body(me, STUDY_001_ROOT / "system_prompts")
            available_tools = me.get("tool_set", [])
            prompt = _build_meta_prompt(args.question, template,
                system_body=sys_body, user_prompt=r["user_prompt"],
                available_tools=available_tools)
            print(f"  [dry] {r['id']}: {prompt[:160].replace(chr(10), ' ')}…")
        return 0

    n_parse_fail = 0
    n_validate_fail = 0
    t0 = time.time()
    n_done = 0

    def _do_one(r: dict, trial_idx: int) -> dict | None:
        me = manifest.get(r["system_prompt_id"])
        if me is None:
            return None
        sys_body = load_system_prompt_body(me, STUDY_001_ROOT / "system_prompts")
        available_tools = me.get("tool_set", [])
        prompt = _build_meta_prompt(args.question, template,
            system_body=sys_body, user_prompt=r["user_prompt"],
            available_tools=available_tools)
        result = backend.generate(
            prompt, model=args.model,
            temperature=args.temperature, top_p=args.top_p,
            max_tokens=args.max_tokens,
        )
        parsed, parse_err = parse_json_output(result.output)
        validate_err = None
        if parsed is not None:
            validate_err = validator(parsed, available_tools)
        return {
            "row": {
                "run_id": run_id,
                "record_id": r["id"],
                "trial_index": trial_idx,
                "model": args.model,
                "question": args.question,
                "tool_target": r["tool_target"],
                "expected_tool_call": r["expected_tool_call"],
                "system_prompt_id": r["system_prompt_id"],
                "available_tools": available_tools,
                "temperature": args.temperature,
                "top_p": args.top_p,
                "prompt_template": QUESTIONS[args.question]["template"].name,
                "output": result.output,
                "parsed": parsed,
                "parse_error": parse_err,
                "validate_error": validate_err,
                "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            },
            "parse_err": parse_err,
            "validate_err": validate_err,
        }

    write_lock = threading.Lock()
    with out_path.open("a") as f:
        if args.concurrency <= 1:
            iterator = (_do_one(r, i) for r, i in todo)
            for outcome in iterator:
                if outcome is None:
                    continue
                if outcome["parse_err"]:
                    n_parse_fail += 1
                if outcome["validate_err"]:
                    n_validate_fail += 1
                f.write(json.dumps(outcome["row"]) + "\n")
                f.flush()
                n_done += 1
                if n_done % 20 == 0:
                    elapsed = time.time() - t0
                    rate = n_done / elapsed if elapsed else 0
                    eta = (len(todo) - n_done) / rate if rate else float("nan")
                    print(f"  progress: {n_done}/{len(todo)} ({rate:.2f}/s, eta ~{eta/60:.1f} min)  "
                          f"parse_fail={n_parse_fail} validate_fail={n_validate_fail}")
        else:
            with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
                futures = [ex.submit(_do_one, r, i) for r, i in todo]
                for fut in as_completed(futures):
                    outcome = fut.result()
                    if outcome is None:
                        continue
                    with write_lock:
                        if outcome["parse_err"]:
                            n_parse_fail += 1
                        if outcome["validate_err"]:
                            n_validate_fail += 1
                        f.write(json.dumps(outcome["row"]) + "\n")
                        f.flush()
                        n_done += 1
                        if n_done % 20 == 0:
                            elapsed = time.time() - t0
                            rate = n_done / elapsed if elapsed else 0
                            eta = (len(todo) - n_done) / rate if rate else float("nan")
                            print(f"  progress: {n_done}/{len(todo)} ({rate:.2f}/s, eta ~{eta/60:.1f} min)  "
                                  f"concurrency={args.concurrency}  "
                                  f"parse_fail={n_parse_fail} validate_fail={n_validate_fail}")

    elapsed = time.time() - t0
    print(f"runner: done run_id={run_id} n={n_done} elapsed={elapsed:.1f}s "
          f"parse_fail={n_parse_fail} validate_fail={n_validate_fail} → {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
