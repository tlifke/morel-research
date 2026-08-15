---
id: studies/008-principled-extraction-cuad/investigations/002-principle-derivation
title: Principle derivation (WS2)
status: planned
parents:
  - studies/008-principled-extraction-cuad
children: []
related: []
axes:
  llm_capability: medium
  human_capability: high
tags: [principles, cuad, curation]
created: 2026-08-15
updated: 2026-08-15
---

# Investigation 2 — Principle derivation (WS2)

## Scope

Produce 15–25 candidate `Principle` records governing the hard calls in CUAD
clause extraction, each with provenance and a feasible gold-applicability
checker sketch, for Tyler to curate into the locked scored set.

## Methods

**Sources, in priority order.**

1. **Atticus annotation guidelines PDF** (from the Atticus Project site — *not*
   in the repo; `category_descriptions.csv` has one-liners only). The
   guidelines carry the distinguishing notes and edge cases that principles are
   made of.
2. **Literature confusions.** Savelka 2023's confusable trio (Minimum
   Commitment / Volume Restriction / Revenue-Profit Sharing) → 2–3
   disambiguation principles.
3. **Contrastive data mining.** Find similar language with different gold
   labels in the train split and read off the implicit convention.
   Model-assisted, under the protocol below.

## Model-assisted proposal protocol

This is a methods-section artifact. Every number and name here gets reported.

**Pair mining (deterministic, no model).** Over the **FT-train remainder
only** — never dev, never holdout — retrieve span pairs with high surface
similarity and different gold category labels (or present-vs-absent
disagreement). Similarity metric, threshold, and the number of pairs surfaced
are recorded in `principles/mining_config.yaml` and are part of the reported
method. Dev stays clean because P0 and Phase-1 iteration run on it; holdout is
sealed under G4.

**Proposer.** Claude Opus 5, model id `claude-opus-5`, temperature 1.0,
one prompt version pinned in `principles/prompts/proposer_vN.md`. Exact model
id, prompt version, and pair-batch composition are stamped into every
candidate record. If the model id changes mid-workstream, that is a new
proposer version and the affected candidates are re-stamped, not silently
carried.

Input per call: a batch of contrastive pairs + the `Principle` schema + the
category definitions. Output: candidate principles in schema form, each with a
mandatory `evidence` field listing the pair ids it was read off, and a
mandatory `checker_sketch`. **A proposal with no evidence pointer or no checker
sketch is discarded before Tyler ever sees it** — that filter is mechanical,
not editorial.

The proposer never sees the guidelines-derived principles. Sources stay
independent so overlap between them is a real signal about whether the
conventions are recoverable from data.

**Review (Tyler).** Every candidate, from every source, lands in
`principles/candidates.yaml` with a `review` block Tyler fills in:

```yaml
- id: p14
  statement: A role designator naming no entity still counts as a party.
  provenance: data_mined            # atticus_guidelines | savelka_confusion
                                    # | data_mined | authored
  proposer:
    model: claude-opus-5
    prompt_version: proposer_v1
    batch_id: cm-003
  evidence: [pair-0412, pair-0455]
  checker_sketch: "gold parties list non-empty AND matched span has no
                   named entity → applicable"
  review:
    decision: accept | edit | reject | defer
    reviewer: tyler
    date: 2026-08-__
    rationale: "one line — why, in your words"
    edited_from: "verbatim prior statement, present only when decision: edit"
```

Rules: `rationale` is required on every decision including `accept` — a bare
accept tells the writeup nothing. `edit` preserves the original text so the
human-vs-model delta is measurable. `reject` records the reason; rejected
candidates stay in the file rather than being deleted, because the rejection
set is itself a finding about what the model gets wrong.

**Locking.** Accepted + edited candidates are written to
`principles/locked-YYYY-MM-DD.yaml`, which is what the harness loads and what
`principle_set_version` in the results store names. Claude proposes; Claude
does not lock. Changing the locked set after inv 003 has labeled against it
means re-labeling — treat the lock as expensive.

**Reportable from this file, no extra bookkeeping**: acceptance rate by
provenance, edit rate, how many model proposals survived to the scored set,
and how much of the guidelines-derived set the data-mining independently
recovered.

**Output.** 15–25 candidate `Principle` records (schema in
`plans/component-contracts.md`), including **3–5 deliberately rare ones** —
rare principles are what make the citation-confusion structure of H4
informative rather than dominated by a few high-frequency rules.

**Hard constraint.** No feasible checker or labeling plan → not in the scored
set. Sketch the checker at proposal time, not afterwards.

**Portability constraint.** Nothing CUAD-specific enters the `Principle` model
itself. The set must generalize as a framework to domains without categories
(AbstentionBench's single answer-or-abstain decision is the test case).

**Curation gate (G2).** Tyler curates before anything is locked. Claude
proposes; Claude does not lock the set.

## Acceptance

- 15–25 candidates, each with `id`, `statement`, `trigger_guidance`, `type`,
  `scope`, `provenance`, and a checker sketch.
- 3–5 deliberately rare principles present.
- Provenance traceable to a source for every record; model-proposed records
  additionally carry proposer model id, prompt version, and evidence pairs.
- Every candidate has a filled `review` block with a rationale.
- Tyler's curated subset written to `principles/locked-YYYY-MM-DD.yaml`.

## Decisions

_Populate as work proceeds._

## Results

_To be populated._

## Forward-looking

_To be populated._

## Things to flag

Licensing: CUAD is CC BY 4.0, so verbatim reuse of definitions in prompts is
permitted with attribution — no paraphrase fallback needed. Confirm the
annotation-guidelines PDF ships under that same release before quoting it;
attribute The Atticus Project wherever guideline text or derived principle
statements are checked in.

_Surface further assumptions explicitly here when drafting._

## Limitations

_To be populated._
