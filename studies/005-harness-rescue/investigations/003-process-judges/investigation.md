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

_To be populated. Plan: per-agent rubrics → hand-score a small held-out reference
sample → measure each panel model's agreement with the reference → audit
divergences → iterate rubric → only then trust scores at scale. Probe small
([[feedback_small_scale_first]]) before scaling._

## Decisions

_Populate as work proceeds._

## Results

_To be populated._

## Things to flag

_Surface assumptions here._

## Limitations

_To be populated._
