---
id: studies/001-tool-calibration
title: Tool calibration (matched-pair)
status: in-progress
parents: []
children:
  - studies/001-tool-calibration/investigations/001-foundations
related: []
axes:
  llm_capability: medium
  human_capability: high
tags:
  - tool-use
  - calibration
  - matched-pair
created: 2026-05-11
updated: 2026-05-11
---

# Study 1 — Tool calibration (matched-pair)

## Question

When do LLMs reach for tools, and when *should* they? We want to probe the
gap between an LLM's tool-call behavior and the behavior a calibrated agent
would exhibit, using matched-pair prompts that vary one factor at a time
(difficulty, affordance) so that we can attribute behavior changes cleanly.

## Why matched-pair

A pair holds everything fixed except the dimension under test. A Type A
pair varies *task difficulty* while the tool affordance stays constant; a
Type B pair varies the *available tools* while the task stays constant.
Single-variable manipulation lets us avoid confounds like length, register,
or keyword leakage.

## Investigations

- `001-foundations` — define the tool palette, metadata schema, ID scheme,
  system-prompt structure, and a seed prompt set of 10–20 hand-curated
  matched pairs. In-progress.

Planned follow-ons (not yet investigations):

- `002-difficulty-axes` — define per-tool difficulty axes that produce
  reliable model failures at the "hard" end and reliable successes at the
  "easy" end (corresponds to Phase A2 in the source plan).
- `003-bulk-generation` — generate a larger prompt corpus from the seed set
  and verified axes (Phase A3).
- `004-empirical-calibration` — run the corpus through target models, log
  call/no-call decisions, fit calibration curves (Phase A4).
- `005-cross-model-eval` — sweep across model families and harness
  variations.

## Repository policy

- Prompt corpora live under `data/` and are checked in until size becomes
  an issue. Model output logs (likely large) will be gitignored and
  archived externally; only summaries and aggregates check in.
- Figures regenerate from scripts in `scripts/` and check in alongside.
- Per-investigation seed/spec files (palette, schema, seed prompts) check
  in.

## Forward-looking

This study is the substrate for several downstream questions:

- How does tool calibration shift with model size, RLHF generation, and
  prompting style?
- Does providing more tools improve or degrade calibration?
- Is there a "tool-use temperature" — a single parameter that captures an
  agent's eagerness to delegate?

## Open questions

- How aggressively should the seed set cover edge cases vs. mainline?
  Phase A1 targets 60/40 common/edge; revisit after seeing model behavior.
- Should we publish the schema externally so other research can reuse it?
  Probably yes once stable.
