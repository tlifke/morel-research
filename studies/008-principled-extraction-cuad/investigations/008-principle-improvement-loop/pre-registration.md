# Pre-registration — rungs 1 and 2

**Status: DRAFT, awaiting Tyler's approval. Written 2026-08-17, before any
candidate principle existed and before the baseline failure taxonomy was read.**
Once approved this file is frozen; changing a threshold after seeing candidate
data voids the pre-registration and must be recorded as such rather than edited
in silence.

## What is fixed in advance

**Model and sampling.** Qwen/Qwen3.5-9B on Tinker, `temperature=1.0`,
`top_p=0.95`, `separate_reasoning=True` (Decision 6). `top_k`, `min_p` and
`presence_penalty` are unreachable through the shim and are not set.

**Repeats.** k = 3 per contract per arm. Seeds are not honoured on Tinker, so a
repeat is a repetition, not a seed. k is fixed in advance and may not be raised
because a result sat near a boundary.

**Pairing.** Every comparison is paired on the same contracts, same task
definition version, same wrapper. The two arms differ **only** in the principles
block — asserted by a test (`test_arms_differ_only_in_the_principles_block`).

**Split.** `principle_train` only. `principle_val` is not read at any rung of
the MVP. `test` is sealed.

**Scoring.** `harness/comparison_metrics.py`: detection F2 primary, F1 also
reported, localization on the TP cell with cell size alongside, micro and macro
at 41 categories.

## The unit of a claim

A **targeted cell** is one (contract, category) pair carrying the failure class
the candidate principle was proposed to fix.

A cell is **failing under an arm** when it fails in **at least 2 of the 3
repeats** under that arm. This majority rule is what makes a single-contract
claim mean anything at temperature 1.0; a 1-of-3 flip is noise.

## Lost repeats

A repeat can be lost to a parse failure. Observed in the baseline at **1 in 12**,
and the cause is not a wrong answer: the model emitted a verbatim span
containing an unescaped `"` — legal text is full of defined terms in quotation
marks — and the JSON died on it. The decision itself was correct.

- The majority rule is evaluated over the repeats that **parsed**, and always
  requires a strict majority: 2 of 3, or 2 of 2.
- If fewer than 2 repeats parse for a contract, that contract is **unevaluable**
  at that rung. It is excluded and the exclusion is reported with its reason —
  never silently dropped, and never re-run to obtain a better sample.
- Parse-failure counts are reported per arm. A candidate arm that parses
  markedly worse than its control is a finding about the principle, not a
  nuisance to be smoothed over.

**Lenient JSON parsing is not adopted.** Tolerating unescaped inner quotes would
recover these trials, and it is arguably parser leniency rather than the
model-assisting repair D-16 forbids. It is left off because the distinction is
not obviously ours to make; flagged for Tyler.

## Rung 1 — one contract

Pass requires **both**:

1. **The targeted cell is failing in the without-candidate arm and not failing
   in the with-candidate arm**, both under the 2-of-3 rule.
2. **Collateral damage is at most 1 newly-failing cell on that contract**,
   averaged over the 3 repeats and counted over all 41 categories. Cells that
   were already failing without the candidate do not count.

Fail on either → the candidate does not advance.

## Rung 2 — up to five contracts

The rung-2 set is the contracts in the MVP slice that carry the same failure
class as the rung-1 target. It may be fewer than five; if it is fewer than
three, the slice is extended from `principle_train` by the selection rule in
`investigation.md`, **not** by choosing a different failure to fit the slice.

Pass requires **all three**:

1. **Every** targeted cell in the set is fixed under the 2-of-3 rule. Not a
   majority of contracts — all of them.
2. **Mean detection F2 across the set does not fall.** Ties pass; any decrease
   fails.
3. **Collateral damage is at most 1 newly-failing cell per contract**, averaged
   over repeats, same counting as rung 1.

## Refinement

At most **3 refinement attempts** at rung 2. An attempt is one edit to the
candidate followed by a full re-run of the rung-2 set. Each edit is routed by
the citation triage of Decision 3 — not cited → edit `trigger_guidance`; cited
and score fell → edit `statement`, or remove — and **the routing is recorded
before the re-run**, so a post-hoc rationalisation is visible as one.

Exhausting 3 attempts without a pass = the candidate is **dropped**. Dropped
candidates are reported with their full attempt history; a selection trace that
reports only survivors is a selection artifact.

## What counts as a null

- Rung 1 passes and rung 2 fails after 3 attempts → **the principle is local to
  one contract**. Reported as such, not as a failure of the method.
- No candidate clears rung 1 across the whole proposal budget → **reportable
  result about the size of effect a single principle can produce**, per inv 006.
- Baseline has no failure class with enough shared instances to build a rung-2
  set → the slice is too small, and that is reported before any principle work.

## Multiple comparisons

The MVP proposes and tests **one** principle. If more than one candidate is
tested against the same slice, every candidate tested is reported, including the
ones dropped at rung 1 — the denominator travels with the claim.

## Not covered here

Rungs 3-5 (regression, subset, full `principle_train`) and the `principle_val`
confirmation get their own pre-registration before they run. Their thresholds
are deliberately **not** set now: setting them before the rung-1/2 effect sizes
are known would be guessing, and setting them after is only sound if this
document has already fixed what "passing" means at the lower rungs.
