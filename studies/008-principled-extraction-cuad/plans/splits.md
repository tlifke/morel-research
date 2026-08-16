# Data splits — purpose, discipline, and what may touch what

Single source of truth for which contracts are used for what. If a use is not
listed here, it is not authorised. Sizes and construction live in
`../investigations/001-dataset-and-splits/investigation.md`; **this file is
about purpose.**

CUAD v1 is 510 contracts. Every one belongs to exactly one split.

## The splits

| split | n | purpose | may be touched by |
|---|---|---|---|
| `excluded` | 4 | **smoke tests and debugging.** Content duplicates of contracts in other splits (INV1-D7), so they carry no information the other splits don't already have — which makes them free to burn. | anyone, any time |
| `selection` | ~60 | **per-principle A/B testing** (inv 006). Selection signal. Assume it is overfit by the end. | inv 006 selection loop only |
| `confirmation` | ~40 | **one confirmation pass per principle** that passes selection. Each principle touches it once. | inv 006 confirmation only |
| `dev` | 40 | **harness and prompt iteration, and pilot P0.** The dress rehearsal for the grid. Deliberately *not* used for principle selection or confirmation. | inv 004, harness work |
| `ft_train` | ~264 | **Phase 2 fine-tuning pool.** | Phase 2 only |
| `holdout` | 102 | **final headline results, both phases.** Sealed until gate G4. | nothing, until G4 |

`selection` and `confirmation` are carved from the current 364-contract
`ft_train`, reducing the Phase-2 pool to ~264. Nothing moves between existing
splits; `dev` and `holdout` are untouched, preserving D-13's length match and
the frozen-splits guarantee.

## Why selection and confirmation are separate splits

Selecting principles on a signal and then reporting that signal measures
selection artifact, not effect. The selection split will be queried once per
candidate per revision — dozens of times — and should be assumed exhausted.
The confirmation split is queried **once per surviving principle**, so the
multiple-comparisons pressure on it is roughly an order of magnitude lower.
Neither is the headline; that is holdout.

## Why dev is kept out of principle work

Dev's job is to predict how the system behaves on holdout before holdout opens
(D-13 stratified it to holdout's *length profile* for exactly this reason). If
dev also carries the selection or confirmation load, it stops being an
independent rehearsal and the Phase-1 grid loses its only pre-holdout sanity
check. Keeping it clean costs us 40 contracts and buys an honest dry run.

## Stratification differs by split, because the jobs differ

- **dev** is stratified to **holdout's length profile** (D-13). Its job is
  forecasting behaviour at length, so it must resemble the evaluation target.
- **selection** is stratified for **statistical power per principle** — every
  one of the 12 categories must have enough positive contracts that a principle
  scoped to a rare category can still show an effect. Source Code Escrow has
  ~11 positives in the whole of ft_train; a length-stratified draw could easily
  contain zero. Length spread is a secondary key.
- **confirmation** mirrors selection's category coverage, so a principle
  confirmed there is confirmed on the same kind of evidence it was selected on.

This is a deliberate divergence, not an inconsistency: a split's stratification
should follow from what it has to support.

## Standing rules

1. **Holdout is sealed until G4.** Contamination checks may compare its text
   for duplication; nothing else may read it.
2. **No contract appears in two splits.** Enforced by title disjointness *and*
   by a content-hash plus cross-split containment assertion in
   `build_dataset.py` — title disjointness alone is insufficient, since
   identical contracts are filed under different titles (INV1-D7). **Re-run the
   guard after carving the new splits.**
3. **Splits are frozen once carved.** Any change is a G1-class decision and
   invalidates every measurement taken against the previous arrangement.
4. **Every result names its split.** A number without a split is not a result.
5. **The excluded set is for smoke tests only.** It must never enter a reported
   metric — its contracts duplicate content in dev and holdout, so scoring on
   it would be scoring on those.

## Open

- Is ~264 contracts enough for the Phase 2 fine-tuning pool? At 12 decisions
  per contract that is ~3,168 decision-level training targets. Check against
  Phase 2's needs **before** carving, since taking it back later means
  re-freezing splits.
- Exact selection/confirmation sizes are proposals, not decisions.
