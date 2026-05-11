---
id: studies/001-tool-calibration/investigations/002-difficulty-axes
title: Per-tool difficulty axes (Phase A2)
status: in-progress
parents:
  - studies/001-tool-calibration
children: []
related:
  - studies/001-tool-calibration/investigations/001-foundations
axes:
  llm_capability: medium
  human_capability: high
tags:
  - difficulty-axes
  - calibration
  - tooling
aliases:
  - A2
  - phase-a2
created: 2026-05-11
updated: 2026-05-11
---

# Investigation 2 — Per-tool difficulty axes (Phase A2)

## Scope

Define, per tool, the **dimensions along which difficulty varies**, so
that A1's hand-curated seeds and A3's bulk-generated prompts can sit at
*known* difficulty bands rather than at hypothesized ones. Concretely:

1. For each of the six palette tools, identify the small set of
   structural axes that drive prompt difficulty (e.g. for calculator:
   digit count + operation type + precision).
2. Bind each axis to concrete value ranges that map onto the existing
   5-level `difficulty_label.value` enum (trivial | easy | medium |
   hard | extreme).
3. Implement the tool **execution layer** so prompts can actually be
   run end-to-end (Decision 18 fixed-return for `datetime_now`;
   Decision 19 verified KB for general/user lookups; calculator,
   python_execute, unit_convert wired up properly).
4. Define the **calibration methodology** for translating per-model
   empirical `success_rate` into one of the 5 difficulty buckets, so
   downstream `difficulty_calibrated` reports are interpretable
   (Decision 13 deferred this to "A4 thresholds" — landed here as
   part of A2 because it gates everything downstream).

## Methods

_Populate as we go. Pre-A2 sketch:_

1. **Per-tool axis drafting** (LLM-led, human-reviewed). For each
   tool, propose 2–4 structural axes and the value ranges that anchor
   each difficulty band. Surface assumptions explicitly. Frozen
   per-tool by a Decision-block sign-off from the human.

2. **Tool execution layer** (LLM-led, runnable). Replace the
   `NotImplementedError`-only Python stubs with KB-backed / actual
   implementations:
   - `calculator(expression)` — `safe_eval` over an arithmetic AST.
   - `python_execute(code)` — sandboxed subprocess returning stdout.
   - `datetime_now()` — returns a **fixed** value pinned to the
     corpus runtime anchor (2026-05-11T12:00:00Z; see Decision 18).
   - `unit_convert(value, from_unit, to_unit)` — actual conversion
     via a small unit table.
   - `general_knowledge_lookup(query)` — BM25-lite over
     `general_knowledge_real.json` (Decision 19 makes this the
     canonical source).
   - `user_knowledge_lookup(query)` — BM25-lite over
     `user_knowledge.json`.

3. **Calibration methodology** ("A4 thresholds"). Define
   `success_rate → difficulty bucket` thresholds, the trial count `n`,
   pass/fail semantics per tool, and how `calibration_status:
   contested` is computed.

4. **Pipeline dry run**. With the tool execution layer wired up, run
   each of the 34 A1 seed records through the harness *without*
   calling any target model — confirms the prompt-to-tool plumbing
   works end-to-end. Actual model trials are deferred to Phase A4
   when the user authorizes target-model API access.

## Decisions

_Populate as work proceeds. Format:_

> **Decision N — short title** (date)
> What was chosen, alternatives considered, why this won.

## Results

_To be populated._

## Forward-looking

_To be populated. Likely:_

- `003-bulk-generation` (Phase A3) — once axes are frozen, generate
  the larger corpus.
- Phase A4 — empirical calibration runs against target models;
  populate `difficulty_calibrated`.

## Things to flag

_Surface assumptions explicitly as drafting proceeds. Particularly:_

- Whether per-tool axes are independent vs. interacting (the difficulty
  manifold may not factorize cleanly).
- Whether bucket thresholds should be tool-agnostic or per-tool.
- How `expected_call_confidence: medium` records (e.g. pair 8,
  pair 10) should be graded — they sit deliberately on the calibration
  boundary.

## Limitations

_To be populated._
