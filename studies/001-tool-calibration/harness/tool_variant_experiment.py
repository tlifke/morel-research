"""A/B experiment: vary the user_knowledge_lookup tool definition
only (not the rest of the system prompt) and see which variants get
4B IT to actually invoke the tool on the three user_knowledge_lookup
hard-half records.

Phase A4 pilot showed 4B IT failing 0/20 on these records — model
correctly defers ("I don't have access to your personal profile")
without realizing it has a tool that would *give* it access. This
experiment probes whether the failure is a tool-description / naming
issue or something deeper.

Variants are defined inline below. Each replaces the
`user_knowledge_lookup` line in `sys_all_tools_neutral_v1.txt`. Tool
name may also be renamed.

Usage:
    uv run tool_variant_experiment.py --n 5
    uv run tool_variant_experiment.py --n 10 --variants v1 v3

Output: per-variant success rate (across the 3 hard records × n
trials), plus full per-trial outputs written to
`results/tool_variant_experiment/<run_id>.jsonl`.
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
RESULTS_ROOT = STUDY_ROOT / "results" / "tool_variant_experiment"

sys.path.insert(0, str(STUDY_ROOT))
from harness.inference import OllamaBackend  # noqa: E402
from harness.parser import parse_tool_calls  # noqa: E402
from harness.prompt_format import _TOOL_BLOCK_INSTRUCTIONS  # noqa: E402

# ---------- variant definitions ----------
# `line_pattern` matches the line in the base system prompt that
# should be replaced. `replacement` is the new line content.
# `tool_name` is the name we'll watch for in tool_code blocks when
# scoring.

VARIANTS: dict[str, dict] = {
    "v0_baseline": {
        "tool_name": "user_knowledge_lookup",
        "replacement": (
            "- user_knowledge_lookup(query: str) — search the current "
            "user's private profile (identity, family, calendar, "
            "preferences); same shape as general_knowledge_lookup"
        ),
        "description": "Original A1 wording — control.",
    },
    "v1_directive": {
        "tool_name": "user_knowledge_lookup",
        "replacement": (
            "- user_knowledge_lookup(query: str) — REQUIRED whenever the "
            "user asks about themselves (their family, schedule, history, "
            "preferences, or anything they personally know). Returns the "
            "user's private profile data as ranked results"
        ),
        "description": "Same name, directive language about when to use.",
    },
    "v2_renamed": {
        "tool_name": "lookup_user_info",
        "replacement": (
            "- lookup_user_info(query: str) — returns information about "
            "the current user (identity, family, calendar, preferences). "
            "Same shape as general_knowledge_lookup"
        ),
        "description": "Renamed tool; baseline description.",
    },
    "v3_epistemic": {
        "tool_name": "user_knowledge_lookup",
        "replacement": (
            "- user_knowledge_lookup(query: str) — returns the current "
            "user's personal information that you would otherwise not "
            "have access to. Use whenever the user asks about themselves "
            "('I', 'my', 'me'); the tool DOES give you access to this "
            "information even though you cannot know it directly"
        ),
        "description": (
            "Same name; epistemic framing that directly addresses the "
            "'I don't have access' refusal pattern."
        ),
    },
    "v4_combined": {
        "tool_name": "lookup_user_info",
        "replacement": (
            "- lookup_user_info(query: str) — REQUIRED for any question "
            "about the current user themselves (family, calendar, "
            "preferences, history). Returns the user's private profile. "
            "Use even if you'd otherwise say 'I don't have access to "
            "personal information' — this tool gives you that access"
        ),
        "description": "Rename + directive + epistemic framing combined.",
    },
}

UKL_LINE_RE = re.compile(
    r"^- user_knowledge_lookup\([^\n]*\n", re.MULTILINE
)


def build_system_prompt(variant_key: str) -> tuple[str, str]:
    """Returns (system_body, tool_name) for the variant."""
    base = (SYSTEM_PROMPTS_DIR / "all_tools_neutral_v1.txt").read_text()
    variant = VARIANTS[variant_key]
    body = UKL_LINE_RE.sub(variant["replacement"] + "\n", base, count=1)
    return body, variant["tool_name"]


def build_prompt(record: dict, system_body: str) -> str:
    system_text = system_body + "\n\n" + _TOOL_BLOCK_INSTRUCTIONS
    return (
        "<bos><start_of_turn>user\n"
        f"{system_text}\n\n{record['user_prompt']}<end_of_turn>\n"
        "<start_of_turn>model\n"
    )


def _load_target_records() -> list[dict]:
    rows = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    # Three user_knowledge_lookup hard halves only.
    return [
        r for r in rows
        if r["tool_target"] == "user_knowledge_lookup"
        and r["expected_tool_call"] is True
    ]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--n", type=int, default=5,
                   help="Trials per (variant, record). Default 5 for quick A/B.")
    p.add_argument("--variants", nargs="+", default=list(VARIANTS),
                   help="Subset of variant keys to run. Default: all.")
    p.add_argument("--model", default="gemma3:4b-it-qat")
    args = p.parse_args()

    records = _load_target_records()
    assert len(records) == 3, f"expected 3 ukl hard records; got {len(records)}"
    print(f"target records: {[r['id'] for r in records]}")

    backend = OllamaBackend()
    run_id = uuid.uuid4().hex[:8]
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_ROOT / f"{run_id}.jsonl"
    print(f"run_id={run_id} model={args.model} n={args.n} -> {out_path}")
    print(f"variants: {args.variants}")
    print()

    summary: dict[str, dict] = {}
    for vkey in args.variants:
        sys_body, tool_name = build_system_prompt(vkey)
        print(f"=== {vkey} (target tool: {tool_name}) ===")
        print(f"    {VARIANTS[vkey]['description']}")
        per_record = {}
        for rec in records:
            prompt = build_prompt(rec, sys_body)
            calls_target = 0
            calls_other = 0
            no_call = 0
            for trial in range(args.n):
                r = backend.generate(prompt, model=args.model)
                tool_calls = parse_tool_calls(r.output)
                names = [c.name for c in tool_calls]
                if tool_name in names:
                    calls_target += 1
                elif tool_calls:
                    calls_other += 1
                else:
                    no_call += 1
                with out_path.open("a") as f:
                    f.write(json.dumps({
                        "run_id": run_id,
                        "variant": vkey,
                        "tool_name": tool_name,
                        "record_id": rec["id"],
                        "user_prompt": rec["user_prompt"],
                        "trial_idx": trial,
                        "model": args.model,
                        "output": r.output,
                        "tool_names_invoked": names,
                        "called_target": tool_name in names,
                    }) + "\n")
            sr = calls_target / args.n if args.n else 0.0
            per_record[rec["id"]] = {
                "called_target": calls_target,
                "called_other": calls_other,
                "no_call": no_call,
                "success_rate": sr,
            }
            print(f"    {rec['user_prompt'][:55]:<58} → {calls_target}/{args.n} "
                  f"(target={calls_target}, other={calls_other}, none={no_call})")
        overall = sum(s["called_target"] for s in per_record.values()) / (
            args.n * len(records))
        summary[vkey] = {"overall_success_rate": overall, "per_record": per_record}
        print(f"    OVERALL: {overall:.2%}")
        print()

    # Final ranked summary
    print("=" * 60)
    print("RANKED:")
    for vkey, s in sorted(summary.items(),
                          key=lambda kv: -kv[1]["overall_success_rate"]):
        print(f"  {vkey:18s}  {s['overall_success_rate']:.2%}  "
              f"({VARIANTS[vkey]['description']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
