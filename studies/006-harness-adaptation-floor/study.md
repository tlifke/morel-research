---
id: studies/006-harness-adaptation-floor
title: Harness adaptation floor
status: planned
parents: []
children: []
related:
  - studies/005-harness-rescue
  - studies/004-researcher-diagnostics
axes:
  llm_capability: medium
  human_capability: high
tags:
  - harness
  - small-models
  - replication
  - feasibility
  - gemma-4
created: 2026-07-25
updated: 2026-07-25
---

# Study 6 — Harness adaptation floor

## Question

_Placeholder — the human writes this._

Working framing from the 2026-07-25 planning conversation, to be confirmed
or rewritten: **how far down the model-size ladder does automated harness
adaptation keep working, and what fails first when it stops?**
[Yang et al. 2026](https://arxiv.org/abs/2607.08938) show that a meta-agent
can automatically discover harness adaptations that let small models recover
~90% of frontier performance at ~4% of cost, and report that *more capable*
small models benefit *more*. They stop at 3.8B active / 26B total. This study
extends that curve downward.

The first unit of work is narrower than the study question and is
deliberately a **feasibility test**, not a result: reproduce their process
end-to-end at one smaller Gemma 4 size, on one task, at their stated $20
optimization budget, and find out whether the process runs at all.

## Why this study

_To be populated by the human._

Working notes from the planning conversation (replace or refine):

- Study 005 asked whether a rich harness could substitute for training at 4B
  and produced mostly negative results. Yang et al. asked a closely related
  question at larger scale with a working method and a positive result. The
  most useful next move is not to re-litigate 005's question but to attach to
  their published baseline and extend it where they stopped.
- The Gemma 4 family provides a clean, single-family, open-weight ladder
  (§ Model ladder below), which removes the cross-family confound that made
  study 003's model comparisons hard to interpret.
- This study is scoped to be *checkable*. Success criteria are programmatic
  (see § Why grading matters), which deliberately keeps LLM-judge reliability
  off the critical path — a direct response to studies 004/005, where judge
  validation consumed effort without resolving.

## Investigations

_Populated as investigations are added._

Planned first unit (not yet scaffolded):

- `001-feasibility-single-task` — the **`budget-approval`** task, reusing the
  authors' replication package, at their $20 optimization budget. Reproduce
  their published cell first (`gemma-4-26b-a4b`, the only configuration with a
  number to check against), then descend the Gemma 4 ladder. Deliverable is a
  yes/no on whether the process runs, a cost and wall-clock accounting, and a
  list of every place the method or package is under-specified. **Explicitly
  not** a result about the floor.

## Reference points

- **Anchor paper:** Yang, Zhao, Wu, Kästner, *Better Harnesses, Smaller Models*,
  [arXiv 2607.08938](https://arxiv.org/abs/2607.08938) (2026-07-09).
- **Replication package:**
  [github.com/malusamayo/migration-analysis](https://github.com/malusamayo/migration-analysis)
  (task data committed; large artifacts on
  [figshare](https://figshare.com/s/520e6259e3cc730c358d); uses `uv`).
- **Harness runtime:** OpenHands Software Agent SDK,
  [arXiv 2511.03690](https://arxiv.org/html/2511.03690v1) ·
  [repo](https://github.com/OpenHands/software-agent-sdk) (MIT).
- **Optimizer:** GEPA, [arXiv 2507.19457](https://arxiv.org/abs/2507.19457).
- **Model ladder:** Gemma 4 (Apache 2.0, 2026-04-02) —
  E2B 2.3B eff · E4B 4.5B eff · 12B dense · 26B MoE @3.8B active · 31B dense.
  [Technical report](https://arxiv.org/html/2607.02770v1).
  **Hardware ceiling (confirmed 2026-07-25):** 12B runs on the RTX 3080 (12 GB);
  the 26B MoE does not — MoE cuts compute, not resident weights. The descent
  ladder (12B → E4B → E2B) is fully local; the anchor cell
  (`gemma-4-26b-a4b`, the only one with a published number) needs Modal or a
  hosted API.
- **Target line on `budget-approval`:** frontier 97.3% @ $0.22/query;
  unadapted SLM 75.0%; optimized SLM 98.3%.
- **Full planning record:** `planning-record-2026-07-25.md` — the anchor paper
  read in detail, the methodological lessons, and the decisions behind this
  scope.

## Repository policy

Default applies, plus (proposed, confirm):

- Task instances and their ground-truth checkers check in — they are the
  substrate and must be reproducible.
- Model output trajectories are gitignored; per-run summaries and the
  discovered harness artifacts (system prompts, tool lists, hook scripts)
  check in, since the harness *is* the finding.
- Meta-agent API spend is logged per run in a checked-in ledger. Cost is a
  headline variable in this study, not an implementation detail.

## Forward-looking

_To be populated._

## Open questions

- Which of the seven tasks? See § Task selection.
- Is the meta-agent's own model a variable, or held fixed at frontier?
- Does the floor, if found, sit at total parameters or active parameters?
  See § Model ladder.
