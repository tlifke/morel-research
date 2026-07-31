---
id: studies/007-autoresearch-infrastructure
title: Autoresearch Infrastructure
status: planned
parents: []
children:
  - studies/007-autoresearch-infrastructure/investigations/001-better-harnesses-derisk
  - studies/007-autoresearch-infrastructure/investigations/002-distributed-hello-world
related:
  - studies/003-automated-w2s-replication
  - studies/005-harness-rescue
  - studies/006-harness-adaptation-floor
axes:
  llm_capability: medium
  human_capability: high
tags: [autoresearch, infrastructure, reproduction, ticketing, delegation]
created: 2026-07-26
updated: 2026-07-26
---

# Study 7 — Autoresearch Infrastructure

## Question

How do we build autoresearchers that effectively confirm existing knowledge,
discover new insights, and report those insights so humans can understand
them and agents can use them — and what infrastructure lets us scale with
autoresearchers, enabling them and having them enable us in turn? Concretely:
which parts of the research process can be delegated to which level of model,
measured by grounding the system in paper reproduction (starting with
"Better Harnesses, Smaller Models", arXiv 2607.08938, under a 3080 + $20
constraint)?

## Why this study

_To be populated by the human._

## Approach

The system is built walkthrough-first: components earn design depth only
when the Better Harnesses replication story demands them. Seven components
are named (ticketing/agent-drain, literature grounding via paper cards,
reproducibility assessment, gated phasing, agent/human artifacts,
frontend, knowledge graph); the ticket system is mandatory and gets the
deep plan, the rest get contract-level docs. No app in the first pass —
data structures used locally, file-based.

Research artifacts (schemas, plans, tickets, evaluation code, data) live
in this public repo; deployment plumbing (frontend app, keys, Vercel)
lives in morel-primordia, consuming this repo's contracts one-way.

The harness surface itself — Claude Code skills, CLAUDE.md rules, and
memory entries — is part of the infrastructure under study: versioned,
revisable, and edits made on behalf of this study are recorded as
interventions. Existing repo rules are up for debate through the same door.

Phasing gates: Derisk → Pilot → Scale → Report, each gated by the human.

Plans: `plans/walkthrough.md` (overarching, gates marked),
`plans/ticket-system.md` (deep spec), `plans/component-contracts.md`
(contract-level). First paper card:
`literature/2607.08938-better-harnesses-smaller-models.md`.

## Investigations

- `investigations/001-better-harnesses-derisk` — planned. Walkthrough-driven
  derisk of the Better Harnesses, Smaller Models replication; forcing
  function for the component plans and the first live slice of the ticket
  system.

## Repository policy

Default applies, plus: ticket files, paper cards, schemas, and component
plan docs are checked in — they are the research record. Large run outputs
(model generations, logs) are gitignored per-investigation with summaries
checked in; revisit per investigation.

## Forward-looking

_To be populated._

## Open questions

_To be populated._
