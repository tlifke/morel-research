---
id: studies/001-tool-calibration/investigations/007-axes-performativity
title: Axes performativity — do our difficulty axes predict tool-call calibration?
status: planned
parents:
  - studies/001-tool-calibration
children: []
related:
  - studies/001-tool-calibration/investigations/002-difficulty-axes
  - studies/001-tool-calibration/investigations/004-calibration-pilot
  - studies/001-tool-calibration/investigations/006-temperature-prompt
  - studies/002-principle-bootstrapped-difficulty
axes:
  llm_capability: medium
  human_capability: high
tags:
  - methodology
  - axes
  - empirical-difficulty
aliases:
  - 007
  - axes-perf
created: 2026-05-12
updated: 2026-05-22
---

# Investigation 7 — Axes performativity

> **Scope update (2026-05-22).** This investigation now owns only the
> *diagnostic* question — establishing empirically that the difficulty
> axes from investigation 002 do not predict tool-call success. The
> *reformulation* question — what axes / features / principles would
> predict difficulty for a target model — has moved to
> `studies/002-principle-bootstrapped-difficulty` as its own study,
> since the approach (model self-prediction + auditable principle
> registry + nested actor-critic refinement) is methodologically
> distinct from the rest of study 001 and feeds back into it as input
> rather than as a sibling investigation. The `AuditablePrinciple` /
> `AuditableResponse` primitives that were scaffolded here have moved
> to `studies/002-principle-bootstrapped-difficulty/models.py`.

## Scope

Investigation 006 surfaced (F3, F4, F5) that the per-tool difficulty
axes frozen in 002 Decision 1 **do not predict** empirical tool-call
success on the A1 seed corpus. Records the curator labeled `hard`
land empirically in `trivial` for both 4B and 12B at neutral
temp=1.0; the diagonal of the curator×empirical heatmap is largely
empty.

This investigation asks two distinct questions, both load-bearing
for downstream calibration work:

1. **Diagnosis**: *why* don't the axes predict? Specifically, what
   *do* they predict (if anything), and what gap exists between
   "what the axes measure" (task difficulty) and "what our score
   measures" (tool-call decision)?

2. **Reformulation**: if the existing axes don't predict
   tool-call calibration, what set of axes / features *would*?
   Output: a candidate revised axis set, ideally validated on a
   held-out subset of the bulk corpus.

The framing distinction (from 006's analysis):
- **Task difficulty** (what 002's axes describe): could the model,
  in principle, solve the task without tools? Operand digit count,
  algorithm complexity, fact obscurity, etc.
- **Tool-call calibration** (what classify_trial measures): does
  the model's tool-invocation behavior match the curator's
  expected_tool_call? Driven by prompt surface features
  ("Compute X" triggers calc), refusal priors, training-data
  patterns.

These are not the same property. The axes-performativity
investigation tests this empirically and then proposes the
right-shaped axis system for what we're actually measuring.

## Methods

1. **Re-tag the A1 + bulk corpus with empirical difficulty.** Once
   A4 grading finishes (4B IT and 12B IT against `bulk_seeds.jsonl`
   under neutral baseline at temp=1.0, n=10), compute per-record
   `empirical_difficulty[model_id]` via `calibration_methodology.md`
   thresholds. Note that empirical bucketing is model-relative;
   the same record will have different per-model labels.

2. **Quantify predictive power.** For each pair (axis, model),
   compute the rank correlation between axis-derived predicted
   difficulty and empirical success rate. Where do the axes
   succeed? Where do they fail systematically?

3. **Discover predictors.** Hypothesis-driven feature engineering:
   propose candidate predictors for tool-call success
   (prompt-surface keywords, in-prompt-answer flags, refusal-mode
   triggers, tool-target ambiguity, training-cutoff distance). For
   each, test correlation with empirical success.

4. **Validate on held-out.** Hold out ~10% of the bulk corpus.
   Train (informally) a small classifier on the rest. Test on the
   held-out set. Report accuracy + per-tool breakdown.

5. **Synthesize.** Produce a revised axis-set proposal (analogue
   to 002's `difficulty_axes_proposal.md`) targeting tool-call
   calibration directly. Mark in writeup which 002 axes survive
   and which are superseded.

## Decisions

_Populate as work proceeds._

## Results

_Pending Phase A4 grading of `bulk_seeds.jsonl`._

Preliminary signal already visible in 006 F3/F4/F5 (n=18 corpus):
- Curator `hard` → empirical `trivial` for ~9/15 records at 12B,
  ~5/15 at 4B.
- `python_execute` records are over-represented in the empirically-
  hard tail; `general_knowledge_lookup` and `user_knowledge_lookup`
  cluster at the top of empirical success regardless of curator
  label. Reviewer observation in 006 commit: "I find it really
  interesting that the General Knowledge and User Knowledge don't
  fall under Extremely hard ever from an empirical perspective..."
- A1 corpus is missing `easy` and `extreme` curator labels
  entirely — the bulk corpus (003) fills these in.

## Forward-looking

- **The new axes proposal will likely live as Decision 1 of this
  investigation** once the empirical work is in. Don't pre-judge
  what the axes are; let the data drive.
- If the answer is "no single axis system predicts well; success
  is dominated by record-specific surface features," the practical
  output may be a feature library + a small classifier rather than
  a clean axis taxonomy. Worth signaling this honestly in the
  writeup.

## Things to flag

- Reviewer-flagged finding (2026-05-12): "we'll want to update our
  documentation of tasks so the empirical gradings are
  model-relative." Done in `calibration_methodology.md` —
  empirical bucketing is per-model by design. Methodologically,
  every empirical-difficulty citation must name the model.
- Reviewer interest in the **gkl/ukl never empirically extreme**
  observation. Likely explanation: gkl/ukl records have a clear
  cognitive moment ("model can't possibly know this from training,
  so the right move is to call the tool"), and even partial
  recognition gets the model to a high success rate. Whereas
  python_execute records require the model to (a) recognize a
  tool is needed AND (b) pick the right tool — two-stage
  failure mode. Worth testing this hypothesis explicitly.

## Limitations

- This investigation requires Phase A4 grading of the bulk corpus
  to have enough data to test rank correlations and validate any
  candidate predictors. Until then, the work is preliminary on
  n=18 / n=36 record sets.
- Any "predictor library" produced here is calibrated to the
  Gemma 3 4B / 12B IT model family. Cross-family transfer is not
  tested.
