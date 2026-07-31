---
id: studies/007-autoresearch-infrastructure/investigations/003-model-complexity-floor
title: Model x complexity floor through the OpenCode drain
status: in-progress
parents:
  - studies/007-autoresearch-infrastructure
children: []
related:
  - studies/007-autoresearch-infrastructure/investigations/002-distributed-hello-world
  - studies/006-harness-adaptation-floor
axes:
  llm_capability: medium
  human_capability: medium
tags: [drain, opencode, complexity-ladder, delegation, capability-map]
created: 2026-07-31
updated: 2026-07-31
---

# Investigation 3 — Model × complexity floor through the OpenCode drain

## Scope

Part 3 of the drain program: empirically map which models, running as
OpenCode agents through the drain, clear which complexity of coding task.
The instrument is a five-tier ticket ladder run identically per model; the
verdicts come from the drain's machine checks, never from self-report.

## Complexity ladder

| Tier | Ticket | What it adds over the tier below |
|---|---|---|
| c1 | 001-c1-exact-output | single file, byte-exact stdout |
| c2 | 002-c2-module-with-test | two coordinated files (module + its own unittest) |
| c3 | 003-c3-bugfix-median | read + modify seeded code against seeded failing tests |
| c4 | 004-c4-feature-flag | extend seeded CLI, preserving old behavior |
| c5 | 005-c5-implement-from-tests | implement a class from a failing test spec alone |

Seeded fixtures (buggy `stats.py`, `counter.py`, `test_todo.py`) live on the
drain-sandbox repo's `main`. c3/c5 include a `git diff --quiet main` check so
test-tampering counts as failure.

## Methods

- Tickets carry `complexity` but no `route`; each sweep uses a per-model
  drain config (defaultRoute + distinct `branchPrefix`, e.g. `p3-9b/`) so
  branches never collide across models.
- Sweeps run with `--no-write-back`: tickets stay `ready` for every model;
  the dataset is the per-run `result.json` records
  (`morel-primordia/projects/drain/runs/`), joined by
  `projects/drain/scripts/matrix.ts` (latest result per model × task).
- First sweep models: gemini-3.1-flash-lite (API), qwen35-9b-32k and
  qwen35-4b-32k (desktop 3080, serialized, 32k-context derived models per
  investigation 002 Decision 4).
- One attempt per model × task, no retries; timeout 300s counts as its own
  outcome.

## Results

**Sweep 1 — 2026-07-31, N=1 per cell** (runs `2026-07-31T04-37-37-742Z`
flash, `…04-38-11-820Z` 9b, `…04-40-39-892Z` 4b):

| Task | gemini-3.1-flash-lite | qwen35-9b-32k | qwen35-4b-32k |
|---|---|---|---|
| 001-c1-exact-output | ✅ 7s | ✅ 9s | ✅ 12s |
| 002-c2-module-with-test | ✅ 12s | ✅ 34s | ❌ 7s |
| 003-c3-bugfix-median | ✅ 8s | ✅ 14s | ❌ 6s |
| 004-c4-feature-flag | ✅ 14s | ✅ 55s | ❌ 18s |
| 005-c5-implement-from-tests | ✅ 12s | ❌ 29s | ✅ 20s |

Totals: flash-lite 5/5 (53s, $0.0073) · 9b 4/5 (141s, $0) · 4b 2/5 (63s, $0).

Reading the failures from the event traces:

- **flash-lite clears the whole ladder**, including c5
  (implement-from-tests), at roughly 2–4× the local models' speed.
- **qwen35-9b-32k's floor is capability-shaped**: it worked every tier the
  expected way and genuinely failed only c5 — it edited, ran tests, and
  still couldn't satisfy the six-test spec in one attempt.
- **qwen35-4b-32k's floor is harness-shaped, not coding-shaped**: its c2–c4
  failures are all premature turn-termination — one or two tool calls
  (`mkdir -p py`; read both files) and then it ends its turn without doing
  the work. Its c5 pass shows the coding ability exists when it stays in
  the loop. This rhymes with the study-005/006 finding that small-model
  pathologies are substantially harness artifacts.
- The c5-pass/c2-fail inversion at 4B is exactly the "adjacent tiers
  invert" case pre-registered below; with temperature 1.0 (inherited from
  the desktop sampling recipe) and N=1, repetition is required before
  reading anything directional from single cells.

Follow-ups this sweep earns: N≥3 repetition per 4B cell; a
continuation-nudge experiment (does a "keep going until checks pass"
system line rescue the 4B?); temperature 0.2–0.6 for coding sweeps; and
adding nemotron-3-nano:4b / gemma4:12b columns once their tool support is
smoke-tested.

## Things made up that you should review

- The five-tier ladder and its difficulty ordering are asserted, not
  measured; if two adjacent tiers invert empirically, reorder the ladder
  rather than the data.
- N=1 per cell in the first sweep; treat single-cell surprises as prompts
  for repetition, not conclusions.
- The `part3-approval` gate was marked approved by tyler on the basis of the
  explicit "begin part 3" request in conversation.
