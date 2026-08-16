# Data splits — purpose, discipline, and what may touch what

Single source of truth for which contracts are used for what. If a use is not
listed here, it is not authorised. Sizes and construction live in
`../investigations/001-dataset-and-splits/investigation.md`; **this file is
about purpose.**

CUAD v1 is 510 contracts. Every one belongs to exactly one split.

## The splits

| split | n | purpose | may be touched by |
|---|---|---|---|
| `scratch` | 4 | **smoke tests and debugging.** Content duplicates of contracts in other splits (INV1-D7), so they carry no information the other splits don't already have — which makes them free to burn. | anyone, any time |
| `principle_train` | 60 | **per-principle A/B testing** (inv 006). The signal principles are fitted on. Assume it is overfit by the end. | inv 006 selection loop only |
| `principle_val` | 40 | **one confirmation pass per principle** that passes `principle_train`. Each principle touches it once. | inv 006 confirmation only |
| `harness_val` | 40 | **harness and prompt iteration, and pilot P0.** The dress rehearsal for the grid. Deliberately *not* used for principle selection or confirmation. | inv 004, harness work |
| `model_train` | 264 | **Phase 2 fine-tuning pool.** | Phase 2 only |
| `test` | 102 | **final headline results, both phases.** Sealed until gate G4. | nothing, until G4 |

`principle_train` and `principle_val` were carved from the 364-contract `model_train` at
INV1-D8, reducing the Phase-2 pool to 264. Nothing moved between existing
splits; `harness_val`, `test` and `scratch` are byte-identical to the pre-carve
build, preserving D-13's length match and the frozen-splits guarantee.

## Naming

The scheme is `(what is being fitted)_(role)`. Three different objects get
fitted in this study — the harness and its prompts, the principle set, and the
model weights — and each needs its own train/val. `test` is the sealed final
split.

Splits were renamed on 2026-08-16; membership did not change. The old names map
as follows, and appear in records written before that date:

| old | new |
|---|---|
| `holdout` | `test` |
| `dev` | `harness_val` |
| `selection` | `principle_train` |
| `confirmation` | `principle_val` |
| `ft_train` | `model_train` |
| `excluded` | `scratch` |

One caveat when reading older records: **`ft_train` before INV1-D8 meant a
364-contract pool, not today's `model_train` (264).** The carve took
`principle_train` (60) and `principle_val` (40) out of it. Figures reported over
"dev + ft_train (404 contracts)" are over `harness_val` plus that pre-carve
pool, and no single split name covers them today.

## Why `principle_train` and `principle_val` are separate splits

Selecting principles on a signal and then reporting that signal measures
selection artifact, not effect. `principle_train` will be queried once per
candidate per revision — dozens of times — and should be assumed exhausted.
`principle_val` is queried **once per surviving principle**, so the
multiple-comparisons pressure on it is roughly an order of magnitude lower.
Neither is the headline; that is test.

## Why harness_val is kept out of principle work

harness_val's job is to predict how the system behaves on test before test opens
(D-13 stratified it to test's *length profile* for exactly this reason). If
harness_val also carries the selection or confirmation load, it stops being an
independent rehearsal and the Phase-1 grid loses its only pre-`test` sanity
check. Keeping it clean costs us 40 contracts and buys an honest dry run.

## Stratification differs by split, because the jobs differ

- **harness_val** is stratified to **test's length profile** (D-13). Its job is
  forecasting behaviour at length, so it must resemble the evaluation target.
- **principle_train** is stratified for **statistical power per principle** — every
  one of the 12 categories must have enough positive contracts that a principle
  scoped to a rare category can still show an effect. Source Code Escrow has
  ~11 positives in the whole of model_train; a length-stratified draw could easily
  contain zero. Length spread is a secondary key.
- **principle_val** mirrors `principle_train`'s category coverage, so a principle
  confirmed there is confirmed on the same kind of evidence it was selected on.

This is a deliberate divergence, not an inconsistency: a split's stratification
should follow from what it has to support.

## Standing rules

1. **test is sealed until G4.** Contamination checks may compare its text
   for duplication; nothing else may read it.
2. **No contract appears in two splits.** Enforced by title disjointness *and*
   by a content-hash plus cross-split containment assertion in
   `build_dataset.py` — title disjointness alone is insufficient, since
   identical contracts are filed under different titles (INV1-D7). Re-run after
   any change to split membership; it was re-run and passes on the six-split
   arrangement (INV1-D8), where it caught a real violation before it landed.
3. **Splits are frozen once carved.** Any change is a G1-class decision and
   invalidates every measurement taken against the previous arrangement.
4. **Every result names its split.** A number without a split is not a result.
5. **A principle is never tested on the contracts it was derived from.**
   Contrastive mining ran over the pre-carve 364-contract `model_train`, so some
   of the contracts a principle was read off now sit in `principle_train`. Selecting
   a principle on the very contracts that produced it is circular — it would
   measure recall of its own evidence, not generalisation.
   Each principle's derivation contracts are recoverable (its `evidence` pair
   ids resolve to contract ids in `mined_pairs.jsonl`), so the fix is per
   principle rather than global: **exclude a principle's own derivation
   contracts from its A/B**, and report the excluded count alongside its
   effect. Re-mining on the post-carve pool is the alternative, but it would
   change the candidate set and discard the curation work already done against
   it. Measure the overlap before choosing.
6. **The `scratch` set is for smoke tests only.** It must never enter a reported
   metric — its contracts duplicate content in harness_val and test, so scoring on
   it would be scoring on those.

## Open

- ~~Is ~264 contracts enough for the Phase 2 fine-tuning pool?~~ **Answered at
  INV1-D8: yes, and the binding constraint was never contract count.** Reasoning
  in the decision; the short version is that Phase 2's SFT stage is
  rejection-sampled per `(contract, category)` decision (264 x 12 = 3,168 prompt
  units before any k>1 sampling) and its RL stage reuses prompts across epochs,
  so unique prompts are not the scarce resource — reward signal per rare
  category is. What 264 costs is `Source Code Escrow`, which drops to **2
  positive contracts** in the Phase-2 pool. That is a category-coverage problem,
  not a volume problem, and it is recorded as such.
- ~~Exact `principle_train`/`principle_val` sizes are proposals, not decisions.~~ Decided at
  INV1-D8: 60 / 40, with per-category positive floors of 5 / 4.
- **Near-duplicate clusters inside the old `model_train` are now bound to
  `model_train`** (INV1-D8). Carving three splits out of one promoted internal
  duplicate clusters into cross-split pairs and the standing guard fired on one.
  23 contracts in 11 clusters are therefore ineligible for `principle_train` and
  `principle_val`. This does not fix Phase 2's double-weighting problem; it
  concentrates it in the one split where it is a data-loader question rather
  than a validity question.
