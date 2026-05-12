"""A/B experiments: vary specific tool definitions (not the rest of
the system prompt) and measure correct-invocation rates.

Five experiments are defined inline below. Pick one with
`--experiment <name>`. Each defines:
  - which tool's line(s) get replaced in the base system prompt
  - which seed records to test (filter on the seed corpus)
  - per-variant: replacement text and a tool-name remap
    (some variants rename tools; the scorer uses the remap)
  - whether success means "invoked the renamed tool" (for
    expected_tool_call=true records) or "did NOT invoke" (for
    expected_tool_call=false records)

Usage:
    uv run tool_variant_experiment.py --experiment ukl_followup --n 5
    uv run tool_variant_experiment.py --experiment python_boundary --n 5
    uv run tool_variant_experiment.py --experiment gkl_temporal --n 5
    uv run tool_variant_experiment.py --experiment trivial_skip --n 5
    uv run tool_variant_experiment.py --experiment ukl_original --n 5
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

# ---------------------------------------------------------------------
# Regex helpers: build a line-matcher for a tool definition.
# Tool descriptions in the system prompt all start with "- <name>(..."
# so we match the line that begins with that prefix.

def _line_re(tool_name: str) -> re.Pattern:
    return re.compile(rf"^- {re.escape(tool_name)}\([^\n]*\n", re.MULTILINE)


# ---------------------------------------------------------------------
# Experiment configs.
#
# Each experiment is a dict with:
#   description: prose for run logs
#   record_ids: explicit list of seed record_ids to run (so we can
#               control exactly which probes hit which variants)
#   variants: dict[variant_key, dict]:
#     replacements: list of (original_tool_name, new_line_text, new_tool_name)
#                   tuples. new_tool_name is the name the scorer looks
#                   for in tool_code blocks.
#     description: prose

EXPERIMENTS: dict[str, dict] = {

    # ---- ukl_original ----
    # Replays the original v0-v4 experiment for parity. Kept for
    # reproducibility — running --experiment ukl_original re-creates
    # the n=5 sweep from the prior session.
    "ukl_original": {
        "description": "Original ukl variant sweep (v0-v4).",
        "record_ids": [
            "user_knowledge_lookup-personal-medium-anniversary-001-69f72239",
            "user_knowledge_lookup-personal-medium-daughter_school_affordance-001-d3f3a623",
            "user_knowledge_lookup-personal-medium-aunt_nina-001-9a276851",
        ],
        "variants": {
            "v0_baseline": {
                "description": "Original A1 wording (control).",
                "replacements": [(
                    "user_knowledge_lookup",
                    "- user_knowledge_lookup(query: str) — search the current "
                    "user's private profile (identity, family, calendar, "
                    "preferences); same shape as general_knowledge_lookup\n",
                    "user_knowledge_lookup",
                )],
            },
            "v1_directive": {
                "description": "REQUIRED whenever directive language.",
                "replacements": [(
                    "user_knowledge_lookup",
                    "- user_knowledge_lookup(query: str) — REQUIRED whenever "
                    "the user asks about themselves (their family, schedule, "
                    "history, preferences, or anything they personally know). "
                    "Returns the user's private profile data as ranked results\n",
                    "user_knowledge_lookup",
                )],
            },
        },
    },

    # ---- ukl_followup ----
    # Off the v1 branch: localize what's load-bearing in the
    # prescriptive wording.
    "ukl_followup": {
        "description": "Variants off the v1_directive branch.",
        "record_ids": [
            "user_knowledge_lookup-personal-medium-anniversary-001-69f72239",
            "user_knowledge_lookup-personal-medium-daughter_school_affordance-001-d3f3a623",
            "user_knowledge_lookup-personal-medium-aunt_nina-001-9a276851",
        ],
        "variants": {
            "v1_directive": {
                "description": "Baseline winner from previous run.",
                "replacements": [(
                    "user_knowledge_lookup",
                    "- user_knowledge_lookup(query: str) — REQUIRED whenever "
                    "the user asks about themselves (their family, schedule, "
                    "history, preferences, or anything they personally know). "
                    "Returns the user's private profile data as ranked results\n",
                    "user_knowledge_lookup",
                )],
            },
            "v1a_antirefusal": {
                "description": "v1 + explicit anti-refusal instruction.",
                "replacements": [(
                    "user_knowledge_lookup",
                    "- user_knowledge_lookup(query: str) — REQUIRED whenever "
                    "the user asks about themselves. Do NOT respond with 'I "
                    "don't have access to personal information' — use this "
                    "tool to get the access. Returns the user's private "
                    "profile data as ranked results\n",
                    "user_knowledge_lookup",
                )],
            },
            "v1b_softer": {
                "description": "Softer imperative ('Use whenever' vs 'REQUIRED whenever').",
                "replacements": [(
                    "user_knowledge_lookup",
                    "- user_knowledge_lookup(query: str) — Use whenever the "
                    "user asks about themselves (their family, schedule, "
                    "history, preferences, or anything they personally know). "
                    "Returns the user's private profile data as ranked results\n",
                    "user_knowledge_lookup",
                )],
            },
            "v1c_no_examples": {
                "description": "v1 with the enumerated examples dropped.",
                "replacements": [(
                    "user_knowledge_lookup",
                    "- user_knowledge_lookup(query: str) — REQUIRED whenever "
                    "the user asks about themselves. Returns the user's "
                    "private profile data as ranked results\n",
                    "user_knowledge_lookup",
                )],
            },
        },
    },

    # ---- python_boundary ----
    # Probes the calculator/python_execute boundary. Pilot showed
    # 4B IT invoking calculator with python-style expressions on
    # SHA-256 and sum-of-primes. Variant tightens the boundary by
    # describing calculator AS arithmetic-only and python AS
    # everything-else.
    "python_boundary": {
        "description": (
            "Boundary-clarification between calculator and "
            "python_execute. Modifies both tools' descriptions."
        ),
        "record_ids": [
            # python_execute hard halves (currently wrong_tool fails):
            "python_execute-text-hard-sha256_hash-001-926e664c",
            "python_execute-math-hard-prime_sum-001-68c18da3",
        ],
        "variants": {
            "vP0_baseline": {
                "description": "Original A1 wording (control).",
                "replacements": [
                    (
                        "calculator",
                        "- calculator(expression: str) — evaluate an "
                        "arithmetic expression and return the exact result\n",
                        "calculator",
                    ),
                    (
                        "python_execute",
                        "- python_execute(code: str) — run a snippet of "
                        "Python and return its stdout\n",
                        "python_execute",
                    ),
                ],
            },
            "vP1_boundary": {
                "description": "Tightened boundary: calc IS arithmetic-only.",
                "replacements": [
                    (
                        "calculator",
                        "- calculator(expression: str) — evaluate a plain "
                        "arithmetic expression (e.g. '47 * 83', 'sqrt(2)'). "
                        "Use ONLY for arithmetic — NOT for hashing, list/"
                        "string operations, iteration, library calls, or "
                        "anything involving lambda/filter/sum constructs\n",
                        "calculator",
                    ),
                    (
                        "python_execute",
                        "- python_execute(code: str) — REQUIRED for any "
                        "computation that calculator cannot do: hashing, "
                        "list/string manipulation, iteration, library "
                        "calls, multi-step logic, lambda expressions. "
                        "Returns the stdout of the executed snippet\n",
                        "python_execute",
                    ),
                ],
            },
        },
    },

    # ---- gkl_temporal ----
    # Probes the general_knowledge_lookup confab + over-call combo.
    # NLA paper got confabulated (under-call); Transformer decade
    # got over-called. Variant tries to encode temporal-position
    # and specificity cues into the description.
    "gkl_temporal": {
        "description": "Temporal-anchored + specificity framing for gkl.",
        "record_ids": [
            # The hard half (post-cutoff fact — currently confabulated):
            "general_knowledge_lookup-ai_tech-hard-nla_paper-001-607ad48e",
            # The trivial half (over-called on broad historical fact):
            "general_knowledge_lookup-ai_tech-hard-nla_paper-001-a3ca466e",
        ],
        "variants": {
            "vG0_baseline": {
                "description": "Original A1 wording (control).",
                "replacements": [(
                    "general_knowledge_lookup",
                    "- general_knowledge_lookup(query: str) — search an "
                    "external knowledge base of time-anchored world facts; "
                    "returns ranked results (empty list if nothing matches)\n",
                    "general_knowledge_lookup",
                )],
            },
            "vG1_temporal": {
                "description": (
                    "REQUIRED for specific values / post-cutoff facts; "
                    "skip for broad historical knowledge."
                ),
                "replacements": [(
                    "general_knowledge_lookup",
                    "- general_knowledge_lookup(query: str) — REQUIRED for "
                    "any specific factual value (date, price, score, name) "
                    "or any fact about events after early 2025 — your "
                    "training data may not cover these. Returns ranked "
                    "results from a time-anchored knowledge base. Do NOT "
                    "call for broad historical knowledge you can answer "
                    "directly (e.g. decade-level questions, pre-2020 "
                    "well-known facts)\n",
                    "general_knowledge_lookup",
                )],
            },
        },
    },

    # ---- trivial_skip ----
    # Three over-call records on different tools. One variant adds
    # a 'skip trivial' clause to all three tool descriptions
    # simultaneously and tests whether trivial cases get answered
    # directly instead of via tool.
    "trivial_skip": {
        "description": (
            "Skip-trivial framing applied across calc, dt, "
            "unit_convert. Tests whether over-call on trivial "
            "cases yields to direct guidance."
        ),
        "record_ids": [
            # calc over-call: "Compute 4 × 7" (trivial half of pair 1)
            "calculator-math-hard-mult4digit-001-2f9febf9",
            # dt over-call: "If today is 2025-01-01..." (trivial half of pair 8)
            "datetime_now-time-medium-current_date-001-2e9c96ed",
            # unit_convert over-call: "5 m to cm" (trivial half of pair 10)
            "unit_convert-units-medium-cross_system-001-a1bce5d5",
        ],
        "variants": {
            "vT0_baseline": {
                "description": "Original A1 wording (control).",
                "replacements": [
                    (
                        "calculator",
                        "- calculator(expression: str) — evaluate an "
                        "arithmetic expression and return the exact result\n",
                        "calculator",
                    ),
                    (
                        "datetime_now",
                        "- datetime_now() — return the current date and "
                        "time as an ISO-8601 string (no arguments)\n",
                        "datetime_now",
                    ),
                    (
                        "unit_convert",
                        "- unit_convert(value: float, from_unit: str, "
                        "to_unit: str) — convert a numeric quantity "
                        "between units\n",
                        "unit_convert",
                    ),
                ],
            },
            "vT1_skip_trivial": {
                "description": "All three tools gain 'skip for trivial cases' guidance.",
                "replacements": [
                    (
                        "calculator",
                        "- calculator(expression: str) — evaluate an "
                        "arithmetic expression. Skip for single-digit "
                        "arithmetic and other trivially mental cases — "
                        "answer those directly\n",
                        "calculator",
                    ),
                    (
                        "datetime_now",
                        "- datetime_now() — return the current date and "
                        "time as ISO-8601. Skip if the date is already in "
                        "the user's prompt or otherwise unambiguous from "
                        "context — answer directly in those cases\n",
                        "datetime_now",
                    ),
                    (
                        "unit_convert",
                        "- unit_convert(value, from_unit, to_unit) — "
                        "convert between units. Skip for power-of-10 "
                        "same-system conversions (e.g. m to cm, kg to g) "
                        "and other trivially mental cases — answer those "
                        "directly\n",
                        "unit_convert",
                    ),
                ],
            },
        },
    },
}


def build_system_prompt(
    variant_cfg: dict, base_template_path: Path
) -> tuple[str, dict[str, str]]:
    """Apply variant replacements to the base system prompt.

    Returns (system_body, tool_name_remap) where tool_name_remap is
    {original_target_in_seed: name_to_match_in_output}.
    """
    body = base_template_path.read_text()
    remap: dict[str, str] = {}
    for orig, new_line, new_name in variant_cfg["replacements"]:
        body = _line_re(orig).sub(new_line, body, count=1)
        remap[orig] = new_name
    return body, remap


def build_prompt(record: dict, system_body: str) -> str:
    system_text = system_body + "\n\n" + _TOOL_BLOCK_INSTRUCTIONS
    return (
        "<bos><start_of_turn>user\n"
        f"{system_text}\n\n{record['user_prompt']}<end_of_turn>\n"
        "<start_of_turn>model\n"
    )


def _load_records(ids: list[str]) -> list[dict]:
    by_id = {
        json.loads(line)["id"]: json.loads(line)
        for line in SEEDS_PATH.read_text().splitlines()
        if line
    }
    out = [by_id[rid] for rid in ids if rid in by_id]
    missing = [rid for rid in ids if rid not in by_id]
    if missing:
        raise SystemExit(f"missing seed records: {missing}")
    return out


def score(record: dict, output: str, remap: dict[str, str]) -> tuple[bool, str]:
    """Returns (success, outcome_label) where outcome_label is one of
    'target', 'wrong_tool', 'no_call' (under) or 'over_call', 'no_call' (clean).
    Uses the variant's remap to identify the renamed target tool, if any.
    """
    calls = parse_tool_calls(output)
    names = [c.name for c in calls]
    target_remapped = remap.get(record["tool_target"], record["tool_target"])
    invoked_target = target_remapped in names
    any_call = len(calls) > 0

    if record["expected_tool_call"]:
        if invoked_target:
            return (True, "target")
        if any_call:
            return (False, "wrong_tool")
        return (False, "no_call")
    # expected_tool_call is False
    if invoked_target:
        return (False, "over_call_target")
    if any_call:
        return (False, "over_call_other")
    return (True, "no_call")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--experiment", required=True, choices=list(EXPERIMENTS))
    p.add_argument("--variants", nargs="+", default=None,
                   help="Subset of variant keys. Defaults to all in the experiment.")
    p.add_argument("--n", type=int, default=5)
    p.add_argument("--model", default="gemma3:4b-it-qat")
    p.add_argument("--base-template",
                   default="all_tools_neutral_v1.txt",
                   help="System prompt file to modify.")
    args = p.parse_args()

    cfg = EXPERIMENTS[args.experiment]
    records = _load_records(cfg["record_ids"])
    base_template_path = SYSTEM_PROMPTS_DIR / args.base_template
    variant_keys = args.variants or list(cfg["variants"])
    print(f"=== experiment: {args.experiment} ===")
    print(f"    {cfg['description']}")
    print(f"records ({len(records)}):")
    for r in records:
        print(f"  - {r['id']}  (expect_call={r['expected_tool_call']})")
    print()

    backend = OllamaBackend()
    run_id = uuid.uuid4().hex[:8]
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    out_path = RESULTS_ROOT / f"{run_id}.jsonl"
    print(f"run_id={run_id} model={args.model} n={args.n} -> {out_path}")
    print(f"variants: {variant_keys}")
    print()

    summary: dict[str, dict] = {}
    for vkey in variant_keys:
        variant_cfg = cfg["variants"][vkey]
        sys_body, remap = build_system_prompt(variant_cfg, base_template_path)
        print(f"--- {vkey} ---  {variant_cfg['description']}")
        per_record = {}
        total_success = 0
        total_trials = 0
        for rec in records:
            prompt = build_prompt(rec, sys_body)
            outcomes: dict[str, int] = {}
            successes = 0
            for trial in range(args.n):
                r = backend.generate(prompt, model=args.model)
                ok, outcome = score(rec, r.output, remap)
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
                successes += int(ok)
                with out_path.open("a") as f:
                    f.write(json.dumps({
                        "experiment": args.experiment,
                        "variant": vkey,
                        "run_id": run_id,
                        "record_id": rec["id"],
                        "user_prompt": rec["user_prompt"],
                        "trial_idx": trial,
                        "model": args.model,
                        "output": r.output,
                        "outcome": outcome,
                        "success": ok,
                    }) + "\n")
            sr = successes / args.n
            per_record[rec["id"]] = {"success_rate": sr, "outcomes": outcomes}
            total_success += successes
            total_trials += args.n
            tail = ", ".join(f"{k}={v}" for k, v in outcomes.items())
            print(f"    {rec['user_prompt'][:55]:<58} → {successes}/{args.n}  ({tail})")
        overall = total_success / total_trials if total_trials else 0.0
        summary[vkey] = {"overall": overall, "per_record": per_record}
        print(f"    OVERALL: {overall:.2%}")
        print()

    print("=" * 60)
    print(f"RANKED ({args.experiment}):")
    for vkey, s in sorted(summary.items(), key=lambda kv: -kv[1]["overall"]):
        print(f"  {vkey:24s}  {s['overall']:.2%}  "
              f"({cfg['variants'][vkey]['description']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
