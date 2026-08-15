---
id: studies/008-principled-extraction-cuad/investigations/003-applicability-ground-truth
title: Principle applicability ground truth (WS3)
status: planned
parents:
  - studies/008-principled-extraction-cuad
children: []
related: []
axes:
  llm_capability: low
  human_capability: high
tags: [ground-truth, labeling, checkers]
created: 2026-08-15
updated: 2026-08-15
---

# Investigation 3 — Principle applicability ground truth (WS3)

## Scope

Give every scored principle a `gold_applicability` label over dev and holdout
instances, with documented reliability — the ground truth citation quality
(C3) and compliance (all conditions) are scored against.

## Methods

1. **Implement checkers** from inv 002's sketches:
   `(instance, gold_annotations) -> bool`, per decision point where the
   principle is decision-scoped.
2. **Classify each checker** as fully-programmatic / heuristic-needs-spot-check
   / manual.
3. **Manual residual**: a minimal labeling flow — contract excerpt + principle
   + yes/no per decision point — over dev + holdout instances.
4. **Reliability**: measure spot-check agreement on a sample of the
   programmatic checkers. A checker that disagrees with human judgment is a
   defect in the principle, not just in the code — route it back to inv 002.

This is the human-intensive workstream and the one most likely to reshape the
principle set. Budget for the set shrinking.

## Acceptance

- Every scored principle has applicability labels over dev + holdout.
- Checker classification recorded per principle.
- Spot-check agreement measured and documented.

## Decisions

_Populate as work proceeds._

## Results

_To be populated._

## Forward-looking

_To be populated._

## Things to flag

_Surface assumptions explicitly here when drafting._

## Limitations

_To be populated._
