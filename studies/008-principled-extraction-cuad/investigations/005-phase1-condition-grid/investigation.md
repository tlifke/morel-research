---
id: studies/008-principled-extraction-cuad/investigations/005-phase1-condition-grid
title: Phase 1 condition grid
status: planned
parents:
  - studies/008-principled-extraction-cuad
children: []
related: []
axes:
  llm_capability: medium
  human_capability: high
tags: [phase1, grid, h1, h3, h4, h5]
created: 2026-08-15
updated: 2026-08-15
---

# Investigation 5 — Phase 1 condition grid

## Scope

Run C1 / C2 / C3 across the model axis on the official CUAD test split and
report the answer → compliance → citation chain, length-stratified. This is the
investigation that answers H1, and supplies the H3/H4/H5 evidence.

## Design

- **Conditions**: C1 baseline / C2 principles / C3 cite (see
  `plans/component-contracts.md`).
- **Models**: ~8B open, ~32B open, one frontier API model. Exact picks open.
- **Instances**: official test split, 102 contracts, full text, no filtering
  or chunking.
- **Seeds**: ≥3 sampled runs per instance at temp ~0.7; report CIs.
- **Schema variant**: whatever G3 decided in inv 004.

## Measurement chain

1. **Task success** — programmatic; primary. Token-level span F1 + exact
   category match + absence accuracy, per-category and length-stratified.
2. **Behavioral compliance** — did the output obey each applicable principle,
   checked independently of citation. Measured in **all** conditions; this is
   the mediation variable.
3. **Citation quality (C3)** — per-decision precision / recall / F1 against
   the scope-relevant gold applicability slice, plus a confusion matrix over
   principle ids (H4).

Causal chain to report: principles → compliance → success; citation
requirement → Δcompliance beyond provision → Δsuccess.

## Standing constraints

- Holdout is untouched until gate G4. All iteration happens on dev.
- `infeasible_at_length` is a reported outcome, not a dropped row (H5).
- Length-stratified reporting is mandatory for every primary metric.
- Contamination caveat travels with every table.

## Acceptance

- Every cell populated or explicitly marked infeasible, with counts.
- CIs reported; ≥30–50 instances per cell where feasible.
- One figure that carries the message (Plotly, Morel branding), plus the
  per-length-bucket tables.

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
