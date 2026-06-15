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

### First validation (2026-06-15) — 6 traces × 3 cloud judges

Judge harness (in inv-001 `harness/`): `judges/process_judge.md` (shared rubric),
`scripts/judge_casefile.py` (privileged case-file renderer), `scripts/run_api_judge.py`
(gemini/nemotron). Anthropic judges run as **Agent subagents** (model override
opus/haiku); see [[feedback_multi_llm_judge_panel]]. Validation set = 6 Phase-1
traces spanning converged/close/far, with the manual subagent reads as reference.
**nemotron judge deferred — desktop GPU offline (last seen ~4d).**

- **Core verdict (strong/adequate/weak): 5/6 unanimous** across Opus+Haiku+Gemini;
  all three catch axis-freezing as `weak/decision_error` and joint-axis reasoning
  as `strong/sound`. The instrument works on its primary job.
- **The one split (A5 s8) is the advisor-handed win** — all three judges *downgrade*
  it (none says `strong`) because the advisor, not the agent, supplied the insight.
  The judges **corrected the manual reference** (which had called it a clean win):
  they score *process, not outcome*, as designed.
- **Disagreement concentrates on the advisor-involved cases** (s8, s18) — exactly
  where credit-assignment is genuinely hard (the literature's problem, manifest).
- **`outcome_vs_process` is the unreliable field**: Opus handles it; Gemini/Haiku
  confuse aligned/lucky/unlucky. **Action: tighten its definition or drop it.**
- **Open policy question:** does following good external advice earn *process*
  credit? (Gemini: no/`weak`; Opus/Haiku: partial/`adequate`.) Must be set by us —
  it is a credit-assignment decision, not a judge bug.

Clears the ~80% bar on core verdict; rubric needs the two fixes above before scaling.

## Things to flag

_Surface assumptions here._

## Limitations

_To be populated._
