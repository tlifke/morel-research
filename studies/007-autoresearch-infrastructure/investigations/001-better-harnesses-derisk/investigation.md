---
id: studies/007-autoresearch-infrastructure/investigations/001-better-harnesses-derisk
title: Better Harnesses derisk
status: in-progress
parents:
  - studies/007-autoresearch-infrastructure
children: []
related:
  - studies/005-harness-rescue
axes:
  llm_capability: medium
  human_capability: high
tags: [reproduction, derisk, ticketing, paper-card]
created: 2026-07-26
updated: 2026-07-26
---

# Investigation 1 — Better Harnesses derisk

## Scope

Walkthrough-driven derisk of replicating "Better Harnesses, Smaller Models"
(arXiv 2607.08938) on a 3080 + $20 budget; produces the paper card, the
end-to-end system walkthrough, the ticket-system spec, and one leaf task
executed by an agent through the ticket files.

## Methods

_To be populated._

## Decisions

_Populate as work proceeds. Format:_

> **Decision N — short title** (date)
> What was chosen, alternatives considered, why this won.

> **Decision 1 — blind decomposition rounds as experiments** (2026-07-27)
> PoC ticket decomposition ran as three blind Haiku rounds, each against
> an evolved drafting contract (v0 rules-poor → v1 rules → v1.1 primary
> sources), contracts preserved verbatim in `tickets/rounds/`. Chosen
> over iterating one ticket set in place so the contract's effect is
> measurable and publishable (blogpost planned).

> **Decision 2 — 006 meta-agent choice is review-layer territory**
> (2026-07-27, Tyler)
> Round-3 ticket 006 chose a flash-lite meta-agent for budget reasons;
> the reviewer note initially called it a failure. Reclassified: the
> ticket is good, the choice is legitimate but misaligned with the
> replication (paper Lesson 1 + $0 subscription option). Such choices
> should be surfaced by a reviewer layer, not forced by overtuned
> drafting prompts; approve/reject rationales accumulate into a
> principles corpus (backlog 6).

## Results

_To be populated._

## Forward-looking

_To be populated._

## Things to flag

_Surface assumptions explicitly here when drafting._

## Limitations

_To be populated._
