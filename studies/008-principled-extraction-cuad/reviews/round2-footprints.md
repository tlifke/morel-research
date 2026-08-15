# Round-2 applicability footprints — p01–p23

Every round-2 candidate in `principles/pilot/candidates_round2.yaml` had its `gold_applicability`
checker implemented and run over the **dev split only** (40 contracts × 12 categories = 480
decisions). `holdout` was never loaded; `ft_train` was not used for any number here.

Artifacts: `principles/pilot/round2/checkers/` (code + 21 tests),
`principles/pilot/round2/footprint.yaml` (the review-app sidecar, complete for all 23),
`principles/pilot/round2/footprints.json` (raw).
Date: 2026-08-15. AI Assistant Used: Claude Code.

Blinding held: `controls.yaml`, `controls_key.yaml`, `round2_key.yaml`, `round1/`,
`cross_source_validation.yaml`, `critiques.yaml`, `round2/` (pre-existing content),
`reviews/cross-source-validation.md`, `reviews/principle-critiques.md` and
`reviews/calibration-controls.md` were not opened.

---

## The table

`applicability` is the headline rate over all 480 dev decisions. `in scope` is the rate over the
categories the record declares (identical to the headline for the seven whole-corpus principles).
`phi` is the 2×2 correlation between *applicability* and *gold presence*, computed in scope.

| id | applicability | in scope | phi | separability | why |
|---|---|---|---|---|---|
| p01 | 5/480 = 1.0% | 12.5% | +0.38 | **pass** | Instance-only administration-plus-royalty test; rare but real, 5 contracts. |
| p02 | 1/480 = 0.2% | 2.5% | −0.70 | **fail** | Applicability requires gold `is_impossible`; one firing in the whole split. |
| p03 | 0/480 = 0.0% | 0.0% | — | pass | Cue fires on 4 contracts, none shares 400 chars with another dev contract → empty. |
| p04 | 5/480 = 1.0% | 12.5% | +0.09 | **pass** | Instance-only blank-date test; fires, but barely moves gold presence. |
| p05 | 480/480 = 100% | 100% | — | pass-but-vacuous | Applicable to every decision by construction; cannot select anything. |
| p06 | 21/480 = 4.4% | 52.5% | +0.40 | **pass** | Venue/arbitration text present in half the contracts; strongest clean footprint. |
| p07 | 38/480 = 7.9% | 95.0% | +1.00 | **fail** | Applicability *is* "gold marks Agreement Date present". |
| p08 | 0/480 = 0.0% | 0.0% | — | fail | `<omitted>` occurs 0 times in dev text and 0 times in dev gold spans. |
| p09 | 21/480 = 4.4% | 52.5% | +0.15 | **pass** | Instance-only ceiling test; fires on half of Volume Restriction, weak association. |
| p10 | 28/480 = 5.8% | 70.0% | +0.35 | **fail** | Applicability is "gold already has the clipped date shape". |
| p11 | 23/480 = 4.8% | 57.5% | +0.27 | **pass** | Instance-only payment-plus-amount test; healthy rate, real association. |
| p12 | 103/480 = 21.5% | 85.8% | +1.00 | **fail** | Applicability is gold presence on the three single-value categories. |
| p13 | 60/480 = 12.5% | 75.0% | +0.29 | **pass** | Instance-only, but a quantity plus a bound cue is ambient legalese: 30/40 contracts. |
| p14 | 14/480 = 2.9% | 35.0% | +0.21 | **pass** | Instance-only non-purchase floor test; fires on 14 contracts. |
| p15 | 12/480 = 2.5% | 15.0% | +0.47 | partial | Reads gold span text, but of the *sibling* category, so both answers stay reachable. |
| p16 | 22/480 = 4.6% | 55.0% | −0.72 | **fail** | Applicability requires gold `is_impossible`; only absences are ever scored. |
| p17 | 3/480 = 0.6% | 7.5% | +0.14 | **fail** | Gold-presence gated, and the sketch's own regex misses the common phrasing. |
| p18 | 12/480 = 2.5% | 2.5% | +0.18 | **fail** | Applicability is computed from the category's own gold spans. |
| p19 | 0/480 = 0.0% | 0.0% | — | fail | Furniture is common (219 matches, 12 contracts) but never *inside* a dev gold span. |
| p20 | 40/480 = 8.3% | 8.3% | +0.34 | **fail** | Real text test, but gated behind "gold has a span"; 40 firings in 6 contracts. |
| p21 | 19/480 = 4.0% | 47.5% | +0.22 | **fail** | Gold-presence gated before the execution-block text test runs. |
| p22 | 108/480 = 22.5% | 30.0% | +1.00 | **fail** | Applicability is gold presence on the nine yes/no categories. |
| p23 | 12/480 = 2.5% | 2.5% | +0.18 | **fail** | Same firing set as p18; applicability is own-gold span text. |

---

## What the separability column means

The instruction asked for the 2×2 of {passes, fails} × {gold present, gold absent}. **That table
cannot be filled yet** — no model outputs exist, so nothing has passed or failed anything. What
*can* be filled, and what decides whether the compliance table could ever be informative, is
{applicable, not applicable} × {gold present, gold absent}. That is what is in
`footprint.yaml → principles.<id>.separability.twobytwo_applicability_x_gold`, with the
structurally-empty cells named explicitly.

Three failure shapes appear, and all three make compliance a restatement of correctness:

1. **Gold-presence gating** (p07, p12, p17, p20, p21, p22 — and via own-span content p10, p18,
   p23, p08). The checker asks the gold whether the category is present before it does anything
   else, so `applicable × gold-absent` is **0 by construction**. Any compliance rate computed on
   the applicable set is conditioned on the answer being present. p07, p12 and p22 have phi
   exactly +1.00, which is the arithmetic signature of this, not evidence of anything.
2. **Gold-absence gating** (p02, p16). Applicability requires `is_impossible`, so
   `applicable × gold-present` is 0 and phi is strongly *negative* (−0.70, −0.72) for structural
   reasons alone. These principles can only ever be scored on the contracts where the right answer
   is "no answer" — a model that abstains everywhere scores 100%.
3. **Vacuity** (p05). Applicable to all 480 decisions; `not-applicable` is empty, phi undefined.
   It leaks nothing because it consults nothing, and it selects nothing for the same reason.

p15 is the only intermediate case: it reads gold span text, but of Minimum Commitment /
Revenue-Profit-Sharing *siblings*, so an applicable decision can be gold-absent (2 of 12 are).
It is still not computable at inference time. Marked `partial`, not `pass`.

The eight that pass cleanly — **p01, p03, p04, p06, p09, p11, p13, p14** — compute applicability
from contract text alone (p03 also from cross-contract text overlap). For these, and only these,
a later compliance measurement is a fact about the model rather than a re-derivation of the gold.

---

## The three empty footprints

- **p08 (`<omitted>` marker) — disqualifying.** The literal marker appears **0 times** in dev
  contract text and **0 times** in dev gold spans. The checker is implementable as written and can
  never fire on this corpus. Status `unimplementable`. The sketch's own caveat is the explanation:
  the marker only exists if the prompt introduces it, which makes the principle a test of
  instruction-following against a convention CUAD v1's released text does not carry.
- **p19 (furniture inside a span) — empty, but not for a lexicon reason.** The furniture regex
  matches 219 times across 12 of 40 dev contracts, so the trigger vocabulary is fine; what is
  absent is any 12-category dev gold span with furniture *strictly inside* it. The widened variant
  finds exactly one. This reproduces the earlier corpus finding that CUAD's dominant convention is
  to split at furniture and exclude it, i.e. the principle's main clause describes the minority
  behaviour.
- **p03 (amendments reproduce earlier text) — empty on dev, and the emptiness is a split artefact.**
  The derivative cue alone fires on 4 of 40 contracts (48 decisions; the loosened `amend*` cue
  fires on 9 contracts / 108 decisions), but none of those four shares a 400-character window with
  any other dev contract. The shared-text half was computed *within dev only*, because ft_train was
  out of scope for these numbers. This is the one zero that would plausibly move on a larger
  population, and it should not be read as a settled finding.

---

## Frequency warnings

- **p05 at 100%** is the pure ceiling case. It will dominate any citation-frequency aggregate it is
  pooled into and must be reported apart from the discriminating set.
- **p07 (95% in scope) and p12 (85.8%)** are near-ceiling *and* gold-gated: both problems at once.
- **p13 at 75% in scope, 30 of 40 contracts.** Instance-only, so it passes separability, but
  "a number plus a bound word" is ambient contract language. It fires on 44 gold-absent in-scope
  decisions against 16 gold-present ones — the positive phi comes entirely from the fact that
  *every* non-applicable decision is gold-absent, not from precision.
- **p18 and p23 are the same measurement**: identical firing sets (12 decisions, 6 contracts). They
  are one principle reached from two provenances (data-mined and Handbook) and should be merged or
  reported jointly, never counted twice.
- **p20's 40 firings sit in 6 contracts** (8 categories in each). A rate of 8.3% overstates its
  breadth: it is six documents, not forty.
- **p09's association is weak in absolute terms**: P(present | applicable) = 3/21 = 14% against
  1/19 = 5%. It clears the phi floor on four positive decisions.
- **p04's lift is near zero** (phi +0.09): it fires on 5 decisions, all gold-present, but so is
  most of the non-applicable Agreement Date set (33 of 35).

## Stability

Every checker was re-run under lexicon and threshold variants; `footprint.yaml →
principles.<id>.stability` carries the full grid. Material swings:

| id | variant | effect |
|---|---|---|
| p17 | `wide_tail` (add "its"/"giving effect to" phrasings) | 3 → 13 firings, phi +0.14 → +0.35 |
| p03 | `wide_cue_no_shared_text` | 0 → 108 decisions (9 contracts) |
| p09 | `wide_ceiling` (add cap/ceiling/up to/not to exceed) | +7 decisions, ~1.5% of the split |
| p13 | `lower_only` / `upper_only` | ±2.5% of the split; the two halves are not symmetric |
| p14 | widened verb lexicon | 14 → 19 firings, recall on gold-present MC improves |
| p20 | `strict_heading` | 40 → 31 firings |

p17 is the clearest warning: the sketch's regex is used verbatim and it misses
"without regard to **its** conflicts of laws", which is the more common phrasing. A one-word regex
change quadruples the footprint. A number that moves that much on a spelling is not yet a
measurement.

Two "swings" are scope changes rather than lexicon tweaks and should not be read as instability:
p12's `agreement_date_only` (−13.5%) and p22's `value_categories_included` (+21.5%).

## Checker provenance

Sixteen round-2 records matched an existing checker in `principles/pilot/checkers/` **by statement
content**, and reuse it unmodified so the numbers stay comparable across passes:

| round-2 | existing | round-2 | existing |
|---|---|---|---|
| p01 | g06 | p13 | d05 |
| p02 | d06 | p14 | d04 |
| p04 | g08 | p15 | d03 |
| p06 | g04 | p16 | d08 |
| p07 | g07 | p18 | d02 |
| p08 | g02 | p19 | d07 |
| p10 | d01 | p22 | g01 |
| p11 | g05 | p23 | g03 |

Seven were implemented fresh: **p03, p05, p09, p12, p17, p20, p21**.

Faithfulness deviations, all recorded in the sidecar under
`scope_and_faithfulness.faithfulness_note`:

- **p03** — the sketch defers the shared-substring computation to
  `scripts/scan_split_contamination.py`; implemented instead as an exact 400-character shared-window
  test on whitespace-normalised text across the 40 dev contracts.
- **p04** (reused g08) — "first ~3000 characters or the signature block" implemented as head-3000
  plus trailing-3000; the sketch's "bare comma where a date should follow an execution verb" clause
  was dropped as unimplementable without false-firing on ordinary prose.
- **p17** — "within 200 characters of a governing-law cue" implemented as a character window around
  the conflicts tail rather than a sentence-level test.
- **p20** — implemented exactly as prescribed, searching for the attachment heading *from* the
  execution block; contracts with no locatable execution block are not applicable, as the sketch says.
- **p21** — the applicability half is as written; the sketch's compliance half needs a cross-format
  date normaliser, which is a compliance-time concern and is out of scope for a footprint.

No sketch was found unimplementable-as-written in a way that forced abandonment. p08 is
implementable and measures zero, which is a finding about the corpus, not a failure of the sketch.

## What these numbers can and cannot show

They can show: how often a principle's trigger condition is met on dev, where in the category and
length space it concentrates, whether its applicability is a function of the gold answer, and how
much it moves under a plausible lexicon change.

They cannot show: whether a model that follows the principle extracts better than one that does
not; whether the principle is legally correct; or whether the compliance half of any sketch is a
good proxy for the behaviour the statement describes. Every phi in this document is a property of
the checker and the corpus, not of any model. The compliance × correctness table the two-arm design
exists to fill stays empty until the runs happen — and for the fourteen `fail`/`partial` principles
above it will stay structurally degenerate even then.
