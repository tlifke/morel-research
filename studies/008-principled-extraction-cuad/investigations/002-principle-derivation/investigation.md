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

## Pilot scope (2026-08-15)

The full set is **not** derived in one pass. The pipeline runs end-to-end on
**five categories** first, targeting ~5–8 curated principles:

- **Minimum Commitment, Volume Restriction, Revenue/Profit Sharing** — the
  Savelka confusable trio, where the boundary is a convention rather than a
  lexical cue.
- **Agreement Date, Governing Law** — structural, chosen so the pilot exercises
  principle *types* the trio cannot: Agreement Date is where absence rulings
  live, Governing Law forces a choice-of-law vs venue/jurisdiction
  disambiguation.
  **Correction (2026-08-15):** the pilot was scoped believing CUAD marks a
  contract gold-absent when the signing date is literally blank. **That was
  wrong** — see `reviews/agreement-date-check.md` and D-19. Gold follows the
  Handbook: a blanked date-shaped construct is *labelled*, with the blank as
  the span. Agreement Date remains a good pilot choice, but the absence-ruling
  principle it yields is about **what counts as a date-shaped construct**, not
  about blankness implying absence.

The pilot answers what would otherwise only surface at scale: what fraction of
model proposals survive curation, whether checker sketches are actually
implementable or whether half the set dies in WS3, whether the guidelines
contain the edge-case material the design assumes, and how long curation takes
per principle. The WS3 three-contract labeling-cost pilot runs alongside, since
labeling cost may argue for a smaller final set — much cheaper to learn at 6
principles than at 22.

Pilot artifacts live under `principles/pilot/`; the curated full set is written
later to `principles/locked-YYYY-MM-DD.yaml`.

**Human curation is a gate, not a source.** Every candidate from every source
passes through Tyler's accept / edit / reject / defer with a required
rationale. `authored` remains a valid provenance if he writes principles
neither source produced, but the default path is curation over proposals.

## Model-assisted proposal protocol

This is a methods-section artifact. Every number and name here gets reported.

**Pair mining (deterministic, no model).** Over the **FT-train remainder
only** — never dev, never holdout — retrieve span pairs with high surface
similarity and different gold category labels (or present-vs-absent
disagreement). Similarity metric, threshold, and the number of pairs surfaced
are recorded in `principles/mining_config.yaml` and are part of the reported
method. Dev stays clean because P0 and Phase-1 iteration run on it; holdout is
sealed under G4.

**Why `invocation` and `harness` are separate from `model`.** The same model
reached through an API call, a Claude Code subagent, an interactive session, or
a programmatic script is not the same experimental condition — temperature and
sampling controls differ, and in the subagent case may not be settable at all.
The pilot's data-mined arm ran as a subagent precisely because no API key was
available, and `temperature: 1.0` was consequently **not settable and no token
usage was captured**. That is a real deviation from the pinned method and it is
recorded on the records rather than in a footnote. Future runs may vary the
model, the harness, or both; the block is designed so those are separable
afterwards.

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
  proposer:                       # present on EVERY model-produced candidate,
                                  # including guideline-derived ones — the
                                  # source document is `provenance`, this block
                                  # is how the record was produced
    model: claude-opus-5          # exact model id
    prompt_version: proposer_v1   # pinned prompt, or null if none
    batch_id: cm-003              # or null
    invocation: subagent          # api | subagent | interactive | programmatic
    harness: claude-code          # claude-code | anthropic-sdk | script:<name>
                                  # | none
    source_document: null         # set when the record was read off a document
                                  # rather than mined, e.g. the Handbook
  evidence: [pair-0412, pair-0455]
  checker_sketch: "gold parties list non-empty AND matched span has no
                   named entity → applicable"
  review:
    decision: accept | edit | reject | defer
    reviewer: tyler
    date: 2026-08-__
    rationale: "one line — why, in your words"
    edited_from:                  # present only when decision: edit
      statement: "verbatim prior value"
      checker_sketch: "verbatim prior value"
      # one key per field actually changed
```

Rules: `rationale` is required on every decision including `accept` — a bare
accept tells the writeup nothing. `edit` preserves the original value of
**every** field changed, keyed by field name, not just `statement` — a model
that proposes a sound rule with an infeasible `checker_sketch` is a distinct
and reportable failure mode from one that gets the rule itself wrong, and a
statement-only `edited_from` would erase that distinction. `reject` records the reason; rejected
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

**Third hard constraint — compliance must be able to come apart from
correctness.** A principle enters the scored set only if **a model can pass its
checker and still be wrong, and fail it while still being right.** If those two
cells are empty, compliance is a restatement of answer correctness and the
`principles → compliance → success` chain is a tautology rather than a causal
claim — the mediation analysis H1 rests on cannot be estimated at all.

This is not hypothetical. Adversarial review of the pilot found **six of
sixteen checkers** with this defect: two gate applicability on
`gold.is_impossible` (so the checker asks the answer), and four define
compliance as emitting the gold answer. Every one of them looked reasonable as
prose. The defect lives entirely in the checker, which is why checkers must be
implemented and inspected **before** curation, not after.

Screening test, to be run mechanically per principle over dev: populate the
2×2 of {passes checker, fails checker} × {answer right, answer wrong}. If
either off-diagonal cell is structurally empty, the principle is excluded.

**Second hard constraint — a principle the schema already enforces is
unmeasurable.** The harness guarantees output coverage (exactly one decision
per target, D-14) and validates structure before scoring. Any candidate that
merely restates a schema guarantee — "emit a decision for every category",
"cite at least one principle" — will show 100% compliance in every condition by
construction, contributing nothing to the mediation analysis and quietly
inflating the compliance pass-rate. Compliance can only measure what the schema
does not already make impossible. Screen candidates for this at curation time:
if you cannot describe an output that is schema-valid yet violates the
principle, the principle is not scoreable.

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
