---
id: studies/005-harness-rescue
title: Harness rescue (context engineering vs training)
status: in-progress
parents: []
children:
  - studies/005-harness-rescue/investigations/001-steplaw-substrate
  - studies/005-harness-rescue/investigations/002-rich-harness
  - studies/005-harness-rescue/investigations/003-process-judges
related:
  - studies/003-automated-w2s-replication
  - studies/004-researcher-diagnostics
axes:
  llm_capability: medium
  human_capability: high
tags:
  - harness
  - context-engineering
  - long-horizon
  - rl-environment
created: 2026-06-05
updated: 2026-06-05
---

# Study 5 — Harness rescue (context engineering vs training)

## Question

> _Draft, from Tyler's framing — confirm or rewrite; the question is the human's call._

Can a **rich harness** (context engineering — structured handoff-with-state,
a results-playbook, bounded episodes, timeout/recovery scaffolding)
**substitute for training** to make a small *prompted* model
(nemotron-3-nano:4b) a competent **long-horizon** research agent? Develop
and validate it cheaply in a simulated config-tuning environment (the
StepLaw lr/bs loss landscape), then transfer the winning harness to the
real weak-to-strong task on the desktop GPU over 24h+.

This stakes a **third corner** in the design space:

| | minimal harness | rich harness |
|---|---|---|
| **strong model** | automated-w2s paper (Opus → human-level) | — |
| **weak model** | study 004 (fails: long-horizon) | **this study** |
| **weak model + training** | — | AutoLLMResearch (beats frontier) |

i.e. between the [automated-w2s paper](https://alignment.anthropic.com/2026/automated-w2s-researcher/)
(strong model + minimal harness) and AutoLLMResearch ([2605.11518](https://arxiv.org/html/2605.11518),
weak model + *training*), we test **weak model + harness instead of training**.

## Why this study

_To be populated by the human._

## Investigations

- `investigations/001-steplaw-substrate` (in-progress) — vendor the
  StepLaw `dense_lr_bs_loss.csv` (1911 rows · 17 (N,D) environments ·
  ~118 lr/bs configs each · known per-env optimum), build a lookup
  substrate behind Pi (`SUBSTRATE=steplaw`), establish the
  **minimal-harness baseline** with nemotron, and compute **regret +
  coverage**. Goal: confirm whether the long-horizon coherence failure
  reproduces in a *rich, real-data* space — disentangling it from the
  env-exhaustion confound of study 004's toy 12-config landscape.

Planned siblings:
- **inv 002 — rich-harness build + ablation** (handoff-with-state +
  results-playbook + bounded episodes + timeout/recovery) in the StepLaw
  env; measure how much of the gap the harness closes vs minimal.
- **inv 003 — real-W2S desktop transfer** — port the winning harness to
  the real weak-to-strong task, 24h+, vs the human baseline (~0.23 PGR).

## Repository policy

Default applies, plus:
- The StepLaw landscape CSV (`dense_lr_bs_loss.csv`, ~344 KB, from
  `github.com/step-law/steplaw`, CC-licensed) is vendored into inv 001's
  `data/` — it's the figure/experiment data and small enough to check in.
- The Pi harness is a TypeScript subtree (same as study 004);
  `node_modules/` and `runs/` gitignored, rendered artifacts in `assets/`.

## Forward-looking

_To be populated._

## Open questions

- Does the coherence failure even reproduce in a rich space, or was it
  substantially a study-004 toy-env artifact? (inv 001 answers this.)
- Can a *prompted* weak model + harness approach the *trained* small-agent
  result of AutoLLMResearch without any weight updates?
- The sim tests coherence/exploration; the real-W2S run tests actuation
  too. How much does sim success predict real success?
