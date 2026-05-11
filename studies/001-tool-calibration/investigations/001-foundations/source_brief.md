# Phase A1 — Foundations (Starter Document)

## Context

This is the active work document for Study A Phase A1. Work pattern: interactive back-and-forth with Claude Code (Opus). User provides principles and feedback. Opus drafts and iterates. Goal is to produce strong foundations for the matched-pair calibration study; expect 45min layover + further work later.

The "limited human time" pattern matters: bias toward Opus drafting from clear principles, user reviewing and correcting. Don't ask Opus to make taste calls without principles to anchor against — give it the principles up front.

## Deliverables (in priority order)

1. **Tool palette spec** — 5 tools with signatures, defined and frozen
2. **Metadata schema** — JSON spec with field definitions
3. **ID scheme** — slug + UUID format with conventions
4. **System prompt library structure** — variant naming and composition rules
5. **Seed prompt set** — 10-20 hand-curated matched pairs

If time runs out, items 1-3 are essential. Items 4-5 can complete later. Item 5 is the hardest and most valuable for downstream — don't rush it.

## Item 1: Tool palette spec

### Principles

- No external state required (so calls can be graded by detection alone, no real execution needed)
- Cover qualitatively different cognitive moments: compute-I-can't-do, look-up-I-don't-know, transform-deterministically
- Five tools, no more, no fewer (cognitive load vs coverage tradeoff)
- Each tool's signature must be unambiguous — the model should never be confused about *how* to call it, only *whether* to

### The five tools (already decided, formalize signatures)

- `calculator(expression: str) -> str` — arithmetic
- `python_execute(code: str) -> str` — sandbox for anything calculator can't
- `datetime_now() -> str` — current date/time, no args
- `unit_convert(value: float, from_unit: str, to_unit: str) -> str` — pure conversion
- `knowledge_lookup(query: str) -> str` — fake knowledge base; stand-in for web search; mock returns

### Good vs bad

GOOD: `calculator(expression: str) -> str  # evaluates arithmetic expression like "47*83"`
BAD: `calculator(a: float, op: str, b: float) -> str` — over-specified, awkward for "sqrt(47)"
BAD: `compute(input: any) -> any` — under-specified, model won't know what fits

### Output format

JSON or Python type-hint signatures with one-line docstrings. Include 1-2 example call shapes per tool to make it unambiguous to the model.

## Item 2: Metadata schema

### Principles

- Every prompt addressable by stable ID
- Every prompt sliceable on every axis we might want to analyze later (don't regret omitted fields)
- Pair linkage explicit via `pair_id`
- Calibration status tracked (verified empirically vs assumed)

### Schema (starting point — iterate)

```json
{
  "id": "calc_arith_hard_3digit_001_a7f3b2c4",
  "pair_id": "calc_arith_001",
  "condition": "tool_warranted",
  "pair_type": "A",
  "tool_target": "calculator",
  "domain": "arithmetic",
  "difficulty_label": "hard",
  "difficulty_calibrated": {
    "gemma3_4b_it": "hard",
    "gemma3_12b_it": "medium"
  },
  "frequency_class": "common",
  "system_prompt_id": "sys_calc_only_v1",
  "user_prompt": "Compute 4782 × 1847 and give me the exact result.",
  "token_count": 14,
  "register": "neutral_formal",
  "expected_tool_call": true,
  "expected_call_confidence": "high",
  "calibration_status": "verified_2026_05",
  "tags": ["multiplication", "exact_result_requested"],
  "source": "hand_curated",
  "notes": ""
}
```

### Fields to push back on / iterate

- `domain`: too coarse? Add sub-domain?
- `frequency_class`: common / uncommon / edge — useful or noise?
- `register`: enumerate values explicitly
- Need `expected_pair_behavior` (what should differ between this and its match)?

### Output format

JSON Schema (draft-07 or 2020-12) plus example records. Validation should be runnable.

## Item 3: ID scheme

### Principles

- Human-readable prefix for grepping
- Stable globally unique suffix
- Predictable structure for ordering and filtering

### Format

`{tool}_{domain}_{difficulty}_{disambiguator}_{shortuuid}`

Examples:
- `calc_arith_hard_3digit_001_a7f3b2c4`
- `knowledge_facts_easy_capital_002_e2c8f1a9`
- `datetime_relative_medium_workday_003_b4d7c2e6`

`shortuuid` = first 8 chars of `uuid.uuid4().hex`. `pair_id` = same prefix minus `shortuuid`, shared between matched halves.

### Output format

Helper function spec (Python) for generating IDs from metadata, plus validation regex.

## Item 4: System prompt library structure

### Principles

- System prompts addressable separately from user prompts
- Tool definitions injected via templating, not hard-coded
- Variant naming captures (tool_set, framing, version)

### Naming convention

`sys_{tool_set}_{framing}_v{version}`

Examples:
- `sys_calc_only_neutral_v1` — only calculator available, neutral framing
- `sys_all_tools_neutral_v1` — all five tools, neutral
- `sys_no_tools_v1` — no tools available (control)
- `sys_all_tools_proactive_v1` — explicit instruction to prefer tools

### Output format

Directory of `.txt` or `.j2` (Jinja) templates with manifest JSON.

## Item 5: Seed prompt set

### Principles

- Single-variable manipulation per pair (one thing changes, everything else matched)
- Length matching within ~15%
- Register matching (both formal, both casual, etc.)
- No surface keywords ("calculator", "compute", "search") in no-tool version unless deliberately testing keyword effects
- Verified difficulty calibration: tool-warranted prompts should actually exceed the target model's reliable answer rate

### Examples to follow

GOOD Type A pair (difficulty manipulation):
- Tool-warranted: "Compute 4782 × 1847 and give me the exact result."
- Tool-trivial: "Compute 4 × 7 and give me the exact result."

GOOD Type B pair (affordance manipulation):
- User prompt (both): "Compute 4782 × 1847 and give me the exact result."
- System v1: includes `calculator` tool definition
- System v2: no tools defined

BAD pair to avoid:
- "Use the calculator to compute 4782 × 1847." vs "What's 4 × 7?"
- Confounded: explicit tool mention only in one, register mismatch, length mismatch

### Distribution target (for the 10-20 seeds)

- ~50% Type A (difficulty manipulation), ~50% Type B (affordance manipulation)
- Cover all five tools, weighted toward calculator and knowledge_lookup
- 60% common cases, 40% edge cases

### Output format

JSONL file with one prompt per line, conforming to the schema in Item 2.

## What to defer

- Bulk generation (A3) — happens after seeds approved
- Difficulty axis definition per tool family (A2) — happens after palette frozen
- Empirical calibration (A4) — needs A3 done first
- Cross-model evaluation infrastructure — set up locally later, not on layover

## Self-check before considering A1 complete

1. Can someone unfamiliar generate a new valid prompt from the schema and examples without asking questions?
2. Does the schema let you slice results by (tool, difficulty, model, condition) without joining tables?
3. Are the seed pairs robust to confound-checking — would a critic find an unmatched dimension?
4. Is the tool palette frozen, or are you still tempted to add a sixth?
5. Is everything in version-controllable text formats (no spreadsheets, no notebooks-as-source-of-truth)?

## Notes for Claude Code interaction

- When uncertain about a design choice, list options with tradeoffs and ask rather than guess
- For each deliverable, produce a draft + a list of "things I made up that you should review" — surface assumptions explicitly
- Don't generate the bulk prompt set (A3) yet — only the 10-20 seed pairs, which need human review for quality calibration
- If a principle in this doc seems wrong, flag it rather than silently working around it
