---
id: studies/005-harness-rescue/investigations/003-process-judges
title: Process judges (per-step LLM judging of the researcher's reasoning)
status: planned
parents:
  - studies/005-harness-rescue
children: []
related:
  - studies/005-harness-rescue/investigations/002-rich-harness
  - studies/004-researcher-diagnostics/investigations/002-judge-comparison
axes:
  llm_capability: medium
  human_capability: high
tags:
  - judges
  - credit-assignment
  - evaluation
  - mdp
created: 2026-06-14
updated: 2026-06-14
---

# Inv 003 — Process judges

## Scope

Build and **validate** the LLM judging agents that score each step of the
researcher's reasoning (Orienter, Hypothesizer, Designer, Analyst, …) defined in
[[002-rich-harness]]'s `agent-mdp-design.md`. One judge rubric per process-agent;
qualitative assessment **always**, quantitative anchor where a ground truth
exists; **never** naive string-match/keyword proxies. First-pass panel: **Opus 4.8
+ Haiku 4.5 + gemini-3.1-flash-lite + nemotron-3-nano:4b**.

This is split out from inv 002 because the judging layer is substantial and
reusable — **but it is tightly coupled to 002 and significant overlap is
expected** (the judges exist to score 002's agents; they co-evolve). Treat the
boundary as porous.

## Why a separate investigation

- The judges are a **measurement instrument** in their own right: they must be
  validated (judge↔reference agreement, divergence audits) before their scores
  are load-bearing — the methodology from
  `studies/004-.../investigations/002-judge-comparison`.
- They carry their own open question — **credit assignment**: when only a final
  outcome (regret) is observed, can per-step LLM judges correctly attribute
  success/failure to individual reasoning steps? (Literature pull in progress;
  the "Reasoning→Agentic credit-assignment" survey is the anchor.)

## Methods

Judge design is literature-grounded (see `002-rich-harness/agent-mdp-design.md`
refs). The blueprint follows **CriticSearch** ([2511.12159](https://arxiv.org/abs/2511.12159))
and the credit-assignment survey ([2604.09459](https://arxiv.org/abs/2604.09459)):

- **Retrospective + privileged:** judges run *after* a trajectory, seeing the full
  trajectory + outcome (regret, distance to known optimum) — access the actor lacked.
- **Coarse, hard-to-game verdicts** (`strong|adequate|weak` or binary), **aggregated
  bottleneck/min-form, never summed** (sum-form is reward-hackable).
- **Decision-error vs information-gap:** rubric must credit each step relative to
  *what was knowable then* — the survey's named open problem; the central rubric risk.
- **Bifurcation-point focus:** weight pivotal decisions, don't grade every step uniformly.
- **Frozen** off-the-shelf judges; no judge↔actor co-training.

**Validation protocol** (the gate before scores are load-bearing): hand-score a
**~20-trajectory** reference sample per step type → measure each panel model's
(Opus 4.8 / Haiku 4.5 / gemini-3.1-flash-lite / nemotron-4b) agreement with the
reference → target **~80%** → audit divergences → iterate the rubric. Probe small
([[feedback_small_scale_first]]) before scaling.

## Decisions

_Populate as work proceeds._

## Results

_To be populated._

## Things to flag

_Surface assumptions here._

## Limitations

_To be populated._
