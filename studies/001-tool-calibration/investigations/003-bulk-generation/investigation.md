---
id: studies/001-tool-calibration/investigations/003-bulk-generation
title: Bulk corpus generation (Phase A3)
status: planned
parents:
  - studies/001-tool-calibration
children: []
related:
  - studies/001-tool-calibration/investigations/001-foundations
  - studies/001-tool-calibration/investigations/002-difficulty-axes
axes:
  llm_capability: high
  human_capability: low
tags:
  - bulk-generation
  - corpus
  - axes
aliases:
  - A3
  - phase-a3
created: 2026-05-11
updated: 2026-05-11
---

# Investigation 3 — Bulk corpus generation (Phase A3)

## Scope

Given the difficulty axes frozen in A2 (Decision 1 in
`../002-difficulty-axes/investigation.md`), generate a larger corpus
of matched-pair prompts at *known* difficulty coordinates. The A1
seed set is 18 hand-curated pairs; A3 expands to a target size of
~200–500 pairs covering the tool × axis-value grid more densely.

Goals:

1. For each (tool, axis-value combination), produce N matched pairs
   that hit the predicted difficulty bucket.
2. Maintain matched-pair integrity (single-variable manipulation per
   pair) automatically.
3. Validate every generated record against the schema and the
   canonical_domains convention.
4. Reach distribution targets — Type A:B ≈ 50:50, common:edge per
   tool, all 5 difficulty bands populated.

A1 design substrate (palette, schema, KBs, ID scheme, system prompts)
is reused as-is. A3 only adds the generation pipeline + the corpus.

## Methods (planned)

1. **Axis-to-prompt-template mapping.** For each tool, build a tiny
   library of prompt templates parameterized by axis values. E.g.
   calculator: `"Compute {a} {op} {b}{precision_clause}"` with
   `{a}, {b}` drawn from digit-count buckets and `{op}` drawn from
   the operation axis.

2. **Generator + validator loop.** For each (tool, target difficulty,
   target axis values), generate N candidate pairs; validate each
   against the schema; re-roll on failure. LLM-led drafting with
   programmatic validation.

3. **Spot review.** Sample ~5% of generated pairs for human review
   (versus 100% for A1 seeds). Track override rate per tool — high
   override rate means the axes or templates need adjustment.

4. **Difficulty hypothesis recording.** Each generated record gets
   `difficulty_label` per the axis prediction; `human_review` left
   null pending Phase A4 empirical calibration.

## Decisions

_Populate as work proceeds._

## Results

_To be populated._

## Forward-looking

- Phase A4 — empirical calibration runs against target models to
  populate `difficulty_calibrated`. The bulk corpus is the substrate
  for A4.
- Sibling investigation testing axes performativity (study.md
  Forward-looking) — runs on the A3 corpus once A4 produces enough
  signal.

## Things to flag

- Generated prompts risk being too template-formulaic; matched-pair
  curation specifically wanted *natural* prompts that probe natural
  cognitive moments. May need diversification via paraphrase.
- Axis interactions: if axes don't factorize cleanly, bulk
  generation by axis-value combination over-counts or
  under-represents certain regions of difficulty space.
- Anti-leakage: avoid surface keywords ("calculator", "search",
  "compute") in user_prompts that bias models toward calling vs.
  not calling. A1 source brief flagged this as a hard constraint.

## Limitations

- Heavy LLM authorship invites the same fact-grounding /
  arithmetic-error failure modes the curator hit in A1 (Decisions 16,
  17). Mitigations: every quantitative claim in generated prompts
  goes through python first; every general-knowledge prompt resolves
  to an entry in `general_knowledge_real.json` (Decision 19).
