# Working set — 9 principles, 3 dropped, and the round-2 control scoring

Companion to `principles/working_set.yaml`. Date: 2026-08-16. AI Assistant
Used: Claude Code.

This is the consolidation of the 16 **real** round-2 candidates after Tyler's
decisions were recorded and the calibration controls unblinded. The 7 controls
are excluded from the working set entirely regardless of their decision — they
are fabricated instrument records, not candidates. `principles/pilot/` is
untouched; it is the archived record of how this set was reached.

The set is **not locked**. No review block has been filled — this set has never
been curated *as a set* — and under D-22 entry to the scored set is decided by
measured improvement, not by the judged truth summarised here.

## The nine at a glance

`appl` is the harness_val applicability rate (480 decisions = 40 contracts × 12
categories) with the in-scope rate in brackets; `phi` is the pre-model
applicability × gold-presence correlation on the in-scope subset. Where a
record merges several, each contributing round-2 id is shown.

| id | one line | axis | from | appl (in-scope) | sep | cross-source | critic | checker |
|---|---|---|---|---|---|---|---|---|
| w01 | whole sentence, period to period — except single-value date/party categories, which take the minimal expression | both | p22 (g01) + p10 (d01) | 22.5% (30%) · 5.8% (70%) | fail · fail | corroborated 82.6% (med) · corroborated (high) | keep w/ rewrite (mod) · could-not-break | needs_rebuild |
| w02 | a passage answering two targets is extracted under both | both | p18 (d02) + p23 (g03) | 2.5% (2.5%) both, byte-identical | fail · fail | corroborated (high) · corroborated (high) | drop (mod) · drop (mod) | needs_rebuild |
| w03 | Governing Law excludes venue, forum, jurisdiction-consent, arbitration, single-section law | both | p06 (g04) | 4.4% (52.5%), phi 0.40 | pass | corroborated 98.9% (high) | could-not-break | **usable** |
| w04 | exactly one Agreement Date, date text only, no header/footer/recital | both | p07 (g07) | 7.9% (95%), phi 1.00 | fail | corroborated 98.4/98.2/100% (high) | keep w/ rewrite (weak) | needs_rebuild |
| w05 | a blank or redacted date is still an extraction | both | p04 (g08) | 1.0% (12.5%), phi 0.09 | pass | corroborated 17/17 (high) | rewrite statement (mod) | needs_rebuild |
| w06 | claim absence when the document states a neighbouring fact, not the asked-for one | **contradict** | p02 (d06) | 0.2% (2.5%), phi −0.70 | fail | contradicted 151/160 (high) | drop (strong) | needs_rebuild |
| w07 | a floor binds whichever party, on supply/payment/access | **contradict** | p14 (d04) | 2.9% (35%), phi 0.21 → 47.5%/0.47 widened | pass | contradicted by definition, backed by gold (high) | keep w/ rewrite (strong) | needs_rebuild |
| w08 | floor vs ceiling by threshold direction | both | p13 (d05) | 12.5% (75%), phi 0.29 | pass | corroborated (high) | keep w/ rewrite (mod) | needs_rebuild |
| w09 | a payment answers the sharing target only when it varies with the counterparty's outcome | both | p11 (g05) + p15 (d03) + p01 (g06) | 4.8% (57.5%) · 2.5% (15%) · 1.0% (12.5%) | pass · partial · pass | corroborated 98.8% (med) · contradicted (high) · corroborated 99.4% (high) | rewrite ×3 | needs_rebuild |

**Provenance-axis distribution (D-23): 7 `both`, 2 `sources_contradict`, 0
`guidelines_only`, 0 `data_only`.** The two contradictions run in opposite
directions, which is why the axis is mandatory rather than decorative:

- **w06** — the Handbook says label the near-miss date under both categories,
  and gold follows the documented rule on 151 of 160 applicable contracts
  (94.4%). The principle describes the 9 residual annotator abstentions. The
  documentation is *broader* than the principle.
- **w07** — the printed Minimum Commitment definition is buyer-centric, and
  practice ignores it: only 77 of 334 gold spans (23.1%) contain a purchase
  verb at all, and 98 of 133 MC-positive contracts (73.7%) contain no
  purchase-obligation span whatsoever. The documentation is *narrower* than
  practice, and a model following the printed definition under-extracts.

That is the study's thesis in miniature, and it is only visible because the
grounding axis is recorded independently of any performance claim.

### Checker status

**1 usable (w03), 8 needs_rebuild, 0 not_yet_specified.** No checker was fixed
here (D-24). The failures split into two families:

- **Separability (D-21)** — w01, w02, w04, w06 gate applicability on the gold
  answer of the very decision being scored. w04's phi of exactly 1.00 is the
  arithmetic signature of a gold-presence gate, not evidence of anything.
- **Lexical proxy for a semantic condition (D-24)** — w07's floor lexicon is too
  narrow (widening moves in-scope applicability 35% → 47.5% and phi 0.21 →
  0.47), w08's trigger is too loose to localise an effect (75% of in-scope
  decisions), and w09 carries the set's sharpest instrument failure: p11's
  checker false-fails 50.2% of gold Revenue/Profit Sharing spans (165/329; the
  round-1 measurement recorded under D-21 puts it at 176/329, 53.5%) against an
  abort threshold its own sketch pre-registered at ~15%. **The
  pre-registration worked** — the sketch named the condition under which it
  should be abandoned and the measurement hit it. That is a methods result, not
  just a broken regex.

### Merges that required a judgement call

- **w01** — the exception is written as *the date and party categories*, not
  "dates and jurisdictions". Cross-source found p22 and p10 scope-differentiated
  rather than contradictory, with the Handbook drawing the line itself; but the
  same entry records that for Governing Law the Handbook wants the *whole
  sentence* labelled with the jurisdiction typed into a separate answer field
  the extraction task does not expose, and gold agrees (85 of 370 Governing Law
  spans carry the conflicts-of-law tail inside the span — the very behaviour the
  d11 control asserted against). Extending the exception to jurisdictions would
  contradict both sources, so it was not done. Tyler should confirm.
- **w09** — p15's direction is **inverted**. As written it routed a
  floor-plus-share clause to Minimum Commitment *instead of* Revenue/Profit
  Sharing; the merged statement makes the floor **additive**, which is the
  salvage cross-source named and what gold does (JOINTCORP and VirtuosoSurgical
  are each dual-labelled). It is still a rewrite of a record Tyler deferred.
- **w09** also forfeits a diagnostic separation: the critic's argument for
  keeping p01 distinct from p11 was that p01 catches right-topic-wrong-function
  and p11 catches wrong-arithmetic, and an H4 confusion matrix can only tell
  them apart if they are separate ids. The merge keeps the distinction in prose
  and loses it in the id space.
- **w02** — `type` is recorded as `constraint` (p18's value) rather than
  `procedure` (p23's). Minor, and both originals are preserved in lineage.

## The three dropped

Recorded in the same file under `dropped:`, because the rejection set is itself
a finding about what the derivation arms get wrong.

- **p08 / g02 — the `<omitted>` marker does not exist in CUAD v1.** 0 of 4,052
  gold spans, 0 occurrences in the 404 contract texts, 0 in the raw
  `CUADv1.json`. The Handbook convention is real but describes the internal
  annotation tool; released CUAD encodes discontiguity as *multiple spans*.
  Applicability is empty, the checker can never fire, and instructing a model to
  emit the marker would break verbatim matching on every such span and change
  every arm's output format. **It was accepted in round 1** and is provably
  inert — a named calibration failure of the round-1 gate. Knock-on: the lead-in
  half of w01 is unverifiable in this corpus for the same reason.
- **p16 / d08 — gold-gated so unmeasurable, and its own cited pairs contradict
  it.** Applicability requires gold `is_impossible`, so every applicable decision
  is gold-absent by construction (phi −0.72) and compliance restates correctness.
  The 63 gold-present spans satisfying the text-side condition are invisible to
  the checker and they are the refuting cases: all three cited pairs have a
  gold-present left span, including pair-0037's own "In particular, Licensee
  commits to:" and pair-0038's "You agree that:", both labelled Minimum
  Commitment with no quantity token. Cross-source corroboration was the weakest
  in the set (`low` confidence, an entailment from a one-line definition).
- **p19 / d07 — refuted as written; furniture-split dominates.** 25 gold spans
  swallow furniture versus 204 same-category adjacent pairs separated by nothing
  but furniture, 127 of them splitting mid-sentence — 8:1 against across all
  categories, ~5:1 by the round-1 count in `plans/decisions.md`, 2:1 within the
  12-category subset. The checker would penalise the majority gold shape. The
  principle rests on a single mined pair whose right-hand side is gold-absent.
  **A disjunctive rewrite exists if wanted** — furniture is never a span alone,
  and an interrupted passage may be annotated either swallowed or split, so a
  scorer must accept both shapes — but it is not adopted and no record was
  created for it. Note the derivation-method result: the two arms disagreed here
  and the guidelines arm was right; data mining generalised from a single pair.

## Round-2 control scoring — why this set is trustable further than round 1's

Round 1 returned **11 accept / 5 defer / 0 reject / 0 edit** on 16 candidates,
with rationales that repeatedly cite absence of domain expertise. That is a gate
that might be measuring nothing. Seven demonstrably-wrong controls were seeded
into the round-2 queue to find out. Scoring rule, fixed in advance
(`reviews/calibration-controls.md`): **catch** = reject, or an edit removing the
wrong claim; **miss** = accept; **abstention** = defer, reported separately and
never counted as a catch.

| control | original | failure mode | difficulty | decision | outcome |
|---|---|---|---|---|---|
| p03 | d09 | defect-derived | medium | reject | **catch** |
| p17 | d11 | inverted convention | medium | reject | **catch** |
| p05 | g12 | degenerate | easy | accept | miss |
| p12 | g11 | over-broad scope | hard | accept | miss |
| p09 | d10 | circular | easy | unclear | abstention |
| p20 | g10 | plausible-but-absent | hard | defer | abstention |
| p21 | g09 | inverted convention | medium | unclear | abstention |

**Controls: 2 caught, 2 accepted, 3 abstained. Real candidates: 11 of 16
accepted, 0 rejected.**

The measured justification for trusting this set more than round 1's is the
*contrast*, not the catch rate:

- **Acceptance rate separates by kind.** Controls were accepted at 2/7 (29%);
  real candidates at 11/16 (69%). The gate is no longer indifferent to what is
  in front of it.
- **Both rejections in the entire round were controls.** Zero real candidates
  were rejected, so the false-alarm rate is 0/16. That matters because the
  instrument's own limitation section warns that a curator who rejects
  everything scores 7/7 and has learned nothing. This curator rejected only
  seeded errors.
- **Every catch was a *medium* control, both inverted-convention or
  defect-derived** — i.e. wrongness detectable from the gold-side evidence
  packet, which is exactly what the instrument predicted the round-1 rationales
  implied. The misses are the two the packet does not help with in the same way:
  a degenerate restatement of the harness's own output contract (easy, but it
  requires applying the investigation's *second hard constraint* rather than
  reading evidence) and an over-broad scope widening (hard).

Caveats that must travel with these numbers:

1. **n = 7, and the 95% Clopper-Pearson interval on 2/7 is [0.04, 0.71].** This
   instrument is powered to separate "near zero" from "substantial", not to
   estimate a rate. The stratified reading — *which kinds* of wrongness were
   caught — is the primary result.
2. **The controls were pre-flagged.** Round 2 ran cross-source validation and
   the adversarial critique over the controls along with everything else, so the
   authored difficulty tags do not apply as written; what was measured is
   whether the curator *acts on a contradiction flag*. That makes the two misses
   a stronger negative than the raw rate suggests, and makes the catch rate not
   comparable to an unaided condition.
3. **Missing a degenerate control is a live threat to this set**, because w04
   and w08 sit closest to that failure mode: w04 fires on 95% of in-scope
   decisions and w08 on 75%, and footprint classes w08 as
   `near-degenerate-frequency`.
4. **The controls are burnt.** A round-3 measurement needs new ones, and they
   will be harder to write.
5. **Nothing here says good-but-unobvious principles survived.** The defers are
   exactly that population and the instrument is silent on them.
6. **One curator, one round, one queue.** No claim about human curation in
   general follows.

## What this set is for

Under D-22 this working set is the **comparison arm**: expert-free human
curation over the round-2 candidate pool, to be set against empirical selection
over the same pool in `investigations/006-empirical-principle-selection`. That
comparison is a stronger methods result than either arm alone, which is why
round-2 curation was completed before switching. The checkers are next (D-24),
and the applicability/compliance split there decides which of these nine can be
scored at all versus which stay prompt-tier.
