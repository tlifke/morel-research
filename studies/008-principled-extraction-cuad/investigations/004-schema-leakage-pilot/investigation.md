---
id: studies/008-principled-extraction-cuad/investigations/004-schema-leakage-pilot
title: Schema leakage pilot (P0)
status: planned
parents:
  - studies/008-principled-extraction-cuad
children: []
related: []
axes:
  llm_capability: high
  human_capability: medium
tags: [pilot, schema, confound]
created: 2026-08-15
updated: 2026-08-15
---

# Investigation 4 — Schema leakage pilot (P0)

## Scope

Decide, from data, whether C1/C2 share C3's output schema. Blocks the main
grid.

## The problem

Two competing risks, no free option:

- **(a) Contamination.** If C1/C2 share C3's schema with `principles_cited`
  present-but-instructed-empty, models may populate it anyway — C1/C2 stop
  being clean no-citation conditions.
- **(b) Confound.** If C1/C2 use a schema *without* the field, format burden
  differs across conditions, and any C3 effect is partly a schema effect.

## Design

2 schema variants (field-present / field-absent) × 2 conditions (C1, C2) ×
~12 dev contracts spanning the length range × 3 seeds. Pilot model:
**inkling-small** (confirm Tinker availability + context window first — it is
an open question in `plans/decisions.md`).

Principle input: inv 002's *candidate* set is sufficient. P0 tests schema
behavior, not principle quality.

## Measures

- **Leakage rate** — % of decisions with non-empty `principles_cited` in the
  field-present variant; **plus** a scan of all text fields in *both* variants
  for principle-id-like or rule-referencing content. Leakage can migrate to
  wherever the model can put it.
- **Answer-score delta** between schema variants, within each condition.

## Decision rule (written before the pilot runs — do not amend after seeing data)

- Leakage rare (**<~5% of decisions**) **and** score delta ≈ 0 →
  **field-present everywhere.** Schema constancy wins.
- Leakage common → **field-absent for C1/C2**, and the schema difference is
  documented as a known limitation of the main grid.
- Score delta large → schema burden is real → **field-present required**, and
  leakage is handled by post-hoc filtering, with **both raw and filtered
  numbers reported.**

Outcome is recorded as gate G3 in `plans/decisions.md`.

## Acceptance

- Leakage rates and score deltas reported by condition and length bucket.
- The schema decision made by the rule above, with the data attached.
- The harness ran the pilot end-to-end (this is also WS5's acceptance test).

## Decisions

_Populate as work proceeds._

## Results

_To be populated._

## Forward-looking

_To be populated._

## Things to flag

_Surface assumptions explicitly here when drafting._

## Limitations

- Single pilot model. A schema effect that is model-specific would not show up
  here; note it if the main grid's models differ materially in scale from
  inkling-small.
