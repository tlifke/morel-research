---
id: studies/004-researcher-diagnostics
title: Researcher diagnostics
status: in-progress
parents: []
children:
  - studies/004-researcher-diagnostics/investigations/001-mock-substrate-harness
  - studies/004-researcher-diagnostics/investigations/002-judge-comparison
related:
  - studies/003-automated-w2s-replication
  - studies/001-tool-calibration
axes:
  llm_capability: medium
  human_capability: high
tags:
  - harness
  - diagnostics
  - tool-use
  - pi
created: 2026-06-03
updated: 2026-06-03
---

# Study 4 — Researcher diagnostics

## Question

> _Draft, derived from Tyler's framing — confirm or rewrite; the question is the human's call._

Where precisely does a small-model autonomous researcher break down —
**reasoning**, **tool-calling**, **recording**, or **long-horizon
coherence** — and can a substrate-free harness localize each failure
mode independently of the others?

The motivating observation: in study 003's overnight runs (inv 006) the
failures are already mixed-shape. Some are reasoning failures (bad ideas,
misread results); many are tool-call/contract failures (`Glob:
Non-relative patterns unsupported`, no `evaluate_predictions` emitted,
shim dropping tool results); some are recording failures (`learnings: []`
in every handoff); and we cannot currently tell them apart. This study
builds the instrument that separates them.

## Why this study

_To be populated by the human._

## Investigations

- `investigations/001-mock-substrate-harness` (in-progress) — a clean
  "researcher CLI" on Pi (`pi-agent-core` SDK) with a
  `SUBSTRATE = mock | desktop` switch: trivial to test against scripted
  fixtures, then run unchanged against the real desktop with an
  identical researcher response path. Carries the move-taxonomy OTel
  tracing (→ Phoenix) and the T1–T8 capability test cases.

Planned siblings (not yet scaffolded):
- **Judge comparison** — does a cheap local judge (nemotron on the
  desktop) grade the T1–T8 traces the same way a strong reader (Claude)
  does? Its own investigation: run nemotron-as-judge over the trace
  corpus, compare to the human/Claude read, inspect divergences after
  the fact, then decide whether to test other judge models. This is the
  scoring layer (#3) turned into an experiment rather than an assumption.
- **Human-as-researcher console** — same I/O contract, human drives,
  every action logged to the same trace for side-by-side comparison.
  Parked for now (half-baked; revisit once the loop exists).
- **Trace observability + action taxonomy** — largely delivered inside
  inv 001 (move-tagged reports + Phoenix); promote to its own write-up
  if it grows.

## Repository policy

Default applies, with two deviations:

- This study introduces a **TypeScript** subtree (the Pi SDK researcher
  CLI) inside an otherwise Python repo. `node_modules/` is gitignored;
  `package.json` / `package-lock.json` / source `.ts` are checked in.
- **Test fixtures** are derived from study 003 inv 006 run archives
  (iteration yamls, JSONL traces). We check in the small derived fixture
  files, not full run dirs. The desktop substrate is never invoked from
  tests — only the mock backend.

## Forward-looking

Direction set 2026-06-03 (Tyler):

- **Memory design (handoff vs full-context):** compare the study-003
  handoff-reset against keeping the whole history in nemotron's 256K
  window. Do it as a **fast simulation** (mock substrate) to get a
  directional answer — does the handoff machinery actually buy anything
  for this model? — before paying for real desktop runs. This doubles as
  the T8 (coherence) experiment.
- **Scoring is an experiment, not an assumption:** the human/Claude read
  of traces is the reference; test **nemotron-as-judge on the desktop**
  against it (new investigation), look at divergences after the fact,
  then consider other judge models.
- **Test ladder:** T1 done (mock + real desktop); T7 next; T4/T5/T6/T8
  follow once the multi-iteration loop exists.

## Open questions

- nemotron-3-nano:4b has a **256K context window**. The handoff/reset
  machinery in study 003 was motivated by a 4B model blowing out a much
  smaller context. How much of that machinery is still necessary? (Bears
  on test case T8.)
- How much scaffolding does a 4B model need added back on top of Pi's
  deliberately frontier-model-minimal contract before the loop works?
  That delta is itself a measurement.
