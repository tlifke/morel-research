---
id: studies/008-principled-extraction-cuad/investigations/006-empirical-principle-selection
title: Empirical principle selection
status: planned
parents:
  - studies/008-principled-extraction-cuad
children: []
related:
  - studies/008-principled-extraction-cuad/investigations/002-principle-derivation
  - studies/008-principled-extraction-cuad/investigations/003-applicability-ground-truth
axes:
  llm_capability: medium
  human_capability: medium
tags: [principles, selection, methodology, ablation]
created: 2026-08-16
updated: 2026-08-16
---

# Investigation 6 — Empirical principle selection

## Scope

Select the principle set by **measured effect on task performance** rather than
by human judgement of whether each rule is true. A candidate is kept if adding
it improves scores on contracts where it applies, revised if it does not, and
dropped if revision does not help — iterated over the candidate pool until
adding, changing, or removing principles stops paying.

This is a methodology, not a single experiment, and it is expected to be a
substantial piece of work in its own right.

## Why (the argument, so a future reader can weigh it rather than inherit it)

**1. A null C3 result is currently uninterpretable.** If C3 shows no gain over
C2, "requiring citation does not help" cannot be distinguished from "the
principles were poor, so citing them was pointless." The round-1/round-2 pilot
makes the second explanation live: of 23 candidates, 13 failed separability,
one fired on 100% of decisions and another on none. Empirical selection makes
C2 a set of *known-useful* principles, so a C3 null becomes a finding rather
than a confound. **This is the strongest reason for the change** — stronger
than the expertise argument below.

**2. The curator is not a domain expert, and this was measured, not assumed.**
Round 1: 16 candidates, 11 accept / 5 defer / **0 reject, 0 edit**, with
rationales of the form "I don't have the domain expertise to disprove this."
The gate discriminates over *structural* properties (contradiction,
corroboration, evidence strength, comprehensibility) and near-zero over
*substantive* ones. See §4a of `../../methods-scaffold.md`. Empirical selection
replaces a judgement the curator cannot reliably make with a measurement.

**3. Provenance did not predict quality.** Measured in the pilot: of 8
guideline-derived principles one was unimplementable and two tautological; of 8
data-mined one was refuted, one fired once in 480 decisions, one on nearly
everything. The two best footprints were one from each arm. Source authority is
not a usable proxy for value.

## Conditions do NOT change

C1 / C2 / C3 are unchanged (D-1, `../../plans/component-contracts.md`). What
changes is **how the principle set entering C2 and C3 is constructed**. C1
remains the no-principles control; C2 provides the selected set; C3 requires
citation of it.

## What this does to the checker — it narrows, and gains a better justification

Under human curation, a checker had to *justify* a principle (feasible checker
or excluded). Under empirical selection the measured effect does the
justifying, and the checker's job becomes **targeting the test**: it identifies
the contracts where a principle applies, so the effect is measured where it can
appear instead of being diluted across a corpus where it is irrelevant. A
principle applying to ~35% of decisions loses roughly two thirds of its
measurable effect if tested corpus-wide. Applicability is a statistical-power
instrument.

This permits — and probably requires — a **two-tier set**:

- **prompt tier** — principles included in C2/C3 prompts, justified empirically
- **scored tier** — the subset that is *also* citation-scoreable, requiring a
  checker that is separable from correctness (D-21)

Today's rule ("no feasible checker → not in the scored set") wrongly excludes
principles that may genuinely help. Splitting the tiers decouples "does this
help?" from "can we score citation of it?", which are different questions that
have been entangled and causing loss.

## Design constraints — the parts that must not be got wrong

**Split discipline is non-negotiable.** Selecting on a signal and then reporting
that same signal is selection artifact, not effect.

- **`principle_train`** — carve from model_train. New; did not exist when this
  was written (carved at INV1-D8, 60 contracts, out of the then 364-contract pool).
- **harness_val** — iteration and validation, as now. Must NOT be the selection signal.
- **test** — sealed until G4. The headline is *"does an empirically-selected
  principle set transfer to held-out contracts?"*, which is a better question
  than the one it replaces.
- Carving from model_train reduces the Phase 2 pool; record the size taken and
  check it against Phase 2's needs before cutting.
- Re-run the cross-split contamination guard after any new split
  (`build_dataset.py`, INV1-D7) — content duplication crosses title boundaries.

**Multiple comparisons will manufacture winners.** ~25 candidates × revisions ×
noisy sampling. Required before any principle is kept:

- a **pre-registered effect-size threshold**, written down before running
- a fixed seed count per test, decided in advance
- a **confirmation pass on unseen contracts** — selection then confirmation,
  never selection alone

**Model axis.** Select with one model (the cheapest adequate arm), then test
whether the selected set transfers up the size axis. *"Does a principle set
selected for a 4B help a frontier model?"* is H3 restated and is the more
interesting form of it.

**Interaction.** Principles are not independent. Greedy forward selection alone
will both miss sets that only work jointly and retain redundancies — hence the
explicit add / revise / remove loop rather than a single forward pass.

## The tension to keep in view

Pure greedy search over principles is optimisation, not reasoning. What keeps
this on the right side of that line is that **generation stays reasoned**
(annotation guidelines + contrastive mining) and only **selection** becomes
empirical. If it drifts toward "generate hundreds of variants and search," it
has become instruction optimisation with extra steps, and that literature is
crowded. The novelty is that the selected units are **citable, checkable
principles**, not free-form prompt text. Protect that.

## Relationship to inv 002

Inv 002 is not superseded. It produced the candidate pool, the two-source
structure, and the curation findings. Those findings now become a **comparison
arm**: expert-free human curation versus empirical selection over the *same*
candidate set. That comparison is a stronger methods contribution than either
approach alone, and it is why round-2 curation should be completed before
switching — the calibration controls are single-use and cannot be cheaply
regenerated once burnt.

## Two constraints inherited from the split carve (INV1-D8)

**1. Derivation overlap.** Mining ran over the pre-carve 364-contract pool, so
some contracts a principle was read off now sit in `principle_train`. Testing a
principle there measures recall of its own evidence. Standing rule 5 in
`../../plans/splits.md`: exclude each principle's derivation contracts from its
own A/B and report the excluded count. **Measure the overlap first** — if it is
negligible the rule costs nothing; if it is large for a given principle, that
principle's effect estimate is weak regardless and should be flagged.

**2. Rare categories may be untestable, and this is arithmetic rather than
opinion.** The per-principle A/B is paired over contracts where the category is
positive, so n *is* the positive count. Under a paired sign test **n=4 cannot
reach p<0.05 even at 4/4** (one-sided p=0.0625); n=5 barely clears at 5/5
(p=0.031). Achieved floors: Source Code Escrow n=5, Most Favored Nation n=8.
Minimum detectable one-sided paired effects: **d≈0.95 (SCE), 0.67 (MFN), 0.58
(Volume Restriction) against 0.23 (Agreement Date)** — a rare-category
principle needs an effect roughly four times larger to clear the same bar, and
must help on *every* contract. More seeds do not rescue this: they reduce
measurement noise, not between-contract variance.

Three honest options, to be chosen and stated before running:
- report rare-category principles **descriptively**, with n inline and no
  significance claim;
- **pool** them into a family-level test across related categories;
- **drop** rare-category-scoped principles from the scored set.

Related: dropping Source Code Escrow from the 12-category subset at G2 is
probably the cleaner fix than shaving the selection floor, since it also
resolves the Phase-2 coverage problem (SCE has 2 positive contracts in
`model_train`).

## A third constraint, found 2026-08-16 (D-29)

**Every principle's A/B must measure effects both inside AND outside its
declared `scope`.** The design as written tests a principle on the contracts
where it applies, for statistical power. That is necessary but not sufficient:
`scope` is declarative to us and **invisible as a constraint to the model**.
Measured — `w06`, scoped to Agreement Date, is cited on 57 of 120 *Expiration
Date* decisions against 9 of 120 Agreement Date decisions, and is named in 43 of
63 false-absents on a category it does not claim.

So a principle can be near-inert inside its own scope while doing real damage
outside it. An in-scope-only A/B would have scored `w06` harmless. The
out-of-scope arm is where the surprises live, and it is cheap — the same trials
already produce all twelve decisions per contract.

Related, and already visible: `w11` (proposed, not added) carries
`conflicts_with: [w06]`, and `w01` interacts with it directly — `w01`'s
minimal-expression exception is right for Agreement Date and wrong for
Expiration Date, so `w11` alone would convert ~132 presence errors into span
errors. **Pairs must be testable, not just singletons.** This is the
interaction case the scope section already anticipated, now with a concrete
instance.

## Acceptance

- A selection protocol written down **before** any selection run: split,
  effect-size threshold, seed count, confirmation rule, stopping rule.
- A selection trace reported as a result, including principles dropped and why.
- A final set with each principle's measured effect and its tier.
- Transfer measured: selected-on-one-model set evaluated across the model axis.

## Decisions

_Populate as work proceeds. Use `INV6-D<n>`._

## Results

_To be populated._

## Forward-looking

_To be populated._

## Things to flag

- `principle_train` did not exist when this was written and comes out of the
  Phase 2 pool (carved at INV1-D8).
- Effect sizes on ~40-contract slices with noisy sampling may not clear any
  honest threshold. If nothing does, that is itself a reportable result about
  how much a principle can be expected to move extraction performance.

## Limitations

_To be populated._
