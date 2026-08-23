---
id: studies/008-principled-extraction-cuad/investigations/007-comparison-metrics
title: Comparison metrics
status: in-progress
parents:
  - studies/008-principled-extraction-cuad
children: []
related:
  - studies/008-principled-extraction-cuad/investigations/005-phase1-condition-grid
axes:
  llm_capability: medium
  human_capability: high
tags: [metrics, cuad, contracteval, deberta, comparability, f2]
created: 2026-08-17
updated: 2026-08-17
---

# Investigation 7 — Comparison metrics

## Scope

Decide and justify the scoring methodology that lets us directly compare three
systems with incompatible output contracts — finetuned DeBERTa-xlarge,
ContractEval-prompted Qwen3.5-9B, and a principles-based Qwen3.5-9B — on CUAD
clause extraction, and record why the chosen methodology is defensible where
the existing published ones are not.

## Why this is its own investigation

The three systems do not emit the same kind of thing. DeBERTa emits a ranked,
scored candidate set with a tunable global threshold; both LLM arms emit one
committed answer per question with no score. Every published methodology
resolves this incompatibility by discarding something, and none of them state
which. The choice is load-bearing for every number the study reports and for
the reward decomposition in Phase 2, so it needs a citable decision rather than
an inherited default.

## Methods

Verification of the candidate methodologies is recorded in
`reviews/scoring-methodology-verification.md` (Task 0, 2026-08-17): three
independent blind passes over upstream CUAD `evaluate.py`, the ContractEval
paper and repo, and our own eval code.

_Remaining methods to be populated as the scorer is built._

## Decisions

> **Decision 1 — the task is scored as two separable sub-tasks, not one number.**
> (2026-08-17)
>
> **(A) Detection** — is this clause type present in this contract? Binary per
> (contract, category), scored as a full 2×2 confusion (TP/TN/FP/FN).
> **F2 is the key metric; F1 also reported.**
> **(B) Localization** — given presence, is the extracted text right? Scored
> against gold spans on the TP cell.
>
> Alternatives considered: CUAD's AUPR / P@80%R (requires a scored ranking the
> LLM arms do not produce, and has no true-negative cell at all, so correct
> silence on the ~70% negative majority earns nothing); ContractEval's
> pair-level exact-containment (cannot score DeBERTa natively, and its
> precision is substantially a string test for the phrase "no related clause");
> our own Level A/B/C (`token_f1` is bespoke and buys no external
> comparability).
>
> This decomposition wins because both halves are measurable identically for
> all three systems without either forcing a ranking onto the LLMs or forcing
> DeBERTa into an output contract it does not have. It also matches the reward
> decomposition Phase 2 RL will need.

> **Decision 2 — DeBERTa's free threshold is reported at two operating points,
> for two different reasons.** (2026-08-17)
>
> - **F2-optimal** — the threshold maximising F2. This is DeBERTa's best
>   possible showing by construction, chosen because recall is the priority
>   for this task. Any LLM win against it is therefore conservative: it beat
>   the baseline tuned in the baseline's own favour.
> - **Volume-matched** — the threshold at which DeBERTa emits the same number
>   of predictions as the LLM arm. This is **confound control**, not charity:
>   it answers "at equal output budget, who is more accurate?" and removes the
>   possibility that an observed difference is just one system being more
>   trigger-happy.
>
> **These two must not be described interchangeably.** F2-optimal already
> protects DeBERTa maximally on F2; volume-matched will score it at or below
> that point. Stating volume-matched as "so DeBERTa isn't penalised for
> emitting more" is wrong and invites the objection that F2-optimal already
> handles it.
>
> Where the two operating points disagree about system ordering, that
> disagreement is a reported finding, not a number to choose between.

> **Decision 3 — localization is defined on the TP cell, and cell size is
> always reported with it.** (2026-08-17)
>
> Conditioning on *predicted*-present rewards a system that only speaks when
> confident, since its localization score is then computed over a
> self-selected population. Conditioning on *gold*-present mixes in questions
> the system never attempted. `harness/metrics.py` already defines Level B on
> the TP cell (predicted present ∧ gold present) and enforces it.
>
> The consequence that must travel with every localization number: **the TP
> cell is a different size for each system**, so localization scores are not
> directly comparable without the cell size alongside them.

> **Decision 4 — matching topology stays many-to-many (CUAD's).** (2026-08-17)
>
> The eval-harness plan specified one-to-one greedy matching. Upstream CUAD,
> ContractEval, and all five of our existing scoring paths are many-to-many.
> Our Table 2 reproduction matched published AUPR to four decimals *because*
> of that topology; one-to-one would break that anchor and would penalise
> DeBERTa for near-duplicate candidates that are an artifact of its 512-token
> encoder — copying the artifact into the scoring. One-to-one is computed as a
> sensitivity check only.

> **Decision 5 — macro is reported alongside micro at 41 categories.**
> (2026-08-17)
>
> Measured on `harness_val`: `Parties` is 216 of 951 gold spans (22.7%) while
> 11 categories have fewer than 8. A micro-pooled number at 41 categories is
> substantially a `Parties` measurement. Neither CUAD nor ContractEval reports
> macro; we do.

> **Decision 6 — ContractEval's own metric is run as calibration, not as a
> headline.** (2026-08-17)
>
> The ContractEval-prompted arm is additionally scored exactly their way,
> known defects included, and checked against their published Table III. That
> validates our pipeline against the literature. The identical outputs are
> then rescored with our metric. Agreement on system ordering is corroboration;
> disagreement is a finding about the metric.

## Results

_To be populated._

## Forward-looking

_To be populated._

## Things to flag

Assumptions and choices made by Claude that need human review:

- **The Parties substring exception is restored as a bug fix, not a decision.**
  Both our scoring scripts drop upstream's `substr_ok` branch while the
  analysis scripts keep it. Harmless at 12 categories (Parties is excluded from
  the subset) but live at 41, where Parties is the largest category by gold
  mass. Treated as a defect to repair rather than an open choice.
- **Deduplication's mechanism is not what it first appears.** Under
  many-to-many, redundant predictions on gold-*present* questions cost no FP.
  Dedup's real effect is on gold-*empty* questions, where `fp += len(preds)`
  charges for every surviving candidate — ~70% of questions. Dedup is
  therefore mostly a precision intervention on the negative majority. The
  threshold (0.8 in the existing analysis scripts, distinct from the 0.5
  matching threshold) and the ordering relative to depth truncation are both
  still unruled.
- **ContractEval's stated 4,128 test points is treated as a typo for 4,182**
  (102 × 41). Not confirmed with the authors.
- **Whitespace normalization for the ContractEval arm is unruled.** 24 of 951
  `harness_val` gold spans (2.5%) contain a newline or tab — negligible under
  Jaccard ≥ 0.5, potentially decisive under their exact-substring rule.
- **F2 and F1 are new code**, not a port; nothing in the study computes any
  β ≠ 1 F-measure, and `point_pr`/`pr()` compute no F-measure at all.

## Limitations

- **None of these metrics measures usefulness to a lawyer.** CUAD's own framing
  is ranked-shortlist review; every methodology here, ours included, is a proxy
  for that and none is closer than the others.
- **The comparison is at a single operating point per LLM arm** because the
  output contract emits no score. A true like-for-like on CUAD's headline AUPR
  would require ranked top-k output from the LLMs — which needs the D-14
  ruling, a second Tinker backend, and a length-normalization decision. Kept as
  a Phase-2 option, not a prerequisite here.
- **Absolute figures remain flattered by the 12-category subset** where the
  subset is used (D-34). The 41-category runs are intended to remove this for
  the baseline comparison.
