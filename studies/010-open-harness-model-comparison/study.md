---
id: studies/010-open-harness-model-comparison
title: Open harness model comparison
status: in-progress
parents: []
children: []
related:
  - studies/008-principled-extraction-cuad
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - harness
  - model-comparison
  - cuad
created: 2026-09-03
updated: 2026-09-03
---

# Study 10 — Open harness model comparison

## Question

How much does the pi system prompt (the harness's default coding-assistant
prompt, including its hardcoded guidelines such as "Be concise in your
responses") change agent behavior, compared to a minimal harness with an
effectively empty system prompt? Measured across two models (Inkling-Small
vs GLM-5.3-Flash) on a fixed task: building an application that renders a
CUAD contract with its ground-truth category highlights. [DRAFTED FROM
DISCUSSION 2026-09-03 — REVIEW BEFORE RELYING ON IT.]

## Why this study

The pi harness injects a substantial default system prompt (role framing,
tool usage guidance, tone instructions like "Be concise in your responses")
that is not parameterized and cannot be removed per-run except by full
replacement. Before drawing conclusions from agent experiments run under
pi, we need to know how much this prompt shapes outcomes. The task —
building a contract-visualization app from a written specification — is
complex enough to expose behavioral differences (planning, tool use,
verbosity, self-verification) while remaining objectively judgeable.

## Design

- **2×2**: {Inkling-Small, GLM-5.3-Flash} × {pi-clean (empty system
  prompt), pi (default system prompt, no project context)}.
- **Conditions differ only in system prompt**: same tools, no project
  context files, no skills/extensions in either condition.
- **Task**: given `task-spec.md` (sent as the initial prompt) and a
  per-run workspace containing `contract_text/` (510 CUAD contracts) and
  `contract_ground_truth` (JSONL: categories, is_impossible, spans), the
  agent builds a rendering application.
- **Judgment**: human judgment of task success first; LLM-judge design
  follows only after human judgments exist.
- **Isolation**: each run gets its own workspace subfolder; agents run
  without knowledge of each other. pi has no filesystem sandbox, so
  isolation is behavioral — verified post-hoc by auditing tool calls in
  the session JSONL for paths outside the run's workspace.

## Investigations

_Populated as investigations are added._

## Repository policy

- `data/contract_text/` (510 files, ~27MB) and `data/contract_ground_truth`
  are checked in — they are the experimental instrument and are derived
  deterministically from study 009's data via `scripts/build_dataset.py`.
- Per-run outputs (workspaces, session JSONL, audit results) land under
  `data/runs/`; check in judgments and analyses, prune bulky workspace
  copies when a run's verdict is recorded.

## Forward-looking

After human judgments: design an LLM judge against them; consider more
models, more tasks, and interaction effects with thinking level.

## Open questions

- Exact GLM-5.3-Flash serving route via HuggingFace (confirm model id in
  pi's registry).
- Number of repeats per cell.
