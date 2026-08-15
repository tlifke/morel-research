# Round-2 principle critiques — adversarial arm

Adversarial review of `principles/pilot/candidates_round2.yaml` (23 candidates, p01–p23),
ordered strongest-worry-first. All evidence is `dev` (40) + `ft_train` (364) = **404 contracts**,
12-category subset, read-only through `scripts/cuad_dataset.py`. **HOLDOUT was never loaded.**
Date: 2026-08-15. AI Assistant Used: Claude Code.

Machine-readable form: `principles/pilot/round2/critiques.yaml`, keyed by id, uniform fields.

## Headline

**I could not break 2 of 23 statements outright (p06, p10), and 2 more survive as statements
while their checkers do not (p11, p14).** Nine candidates are refuted by gold or structurally
unmeasurable and should not ship: **p02, p03, p05, p08, p09, p16, p17, p21** and (as written)
**p19**. The remaining ten are salvageable with a checker or statement rewrite.

Three failure families account for almost all of it:

1. **Gold-gated applicability** (p02, p16, and softer forms in p10, p12, p18, p21, p23). Five
   checkers make applicability depend on `is_impossible` or on gold span overlap. Two of them
   (p02, p16) have a structurally empty off-diagonal: applicable-and-compliant implies correct,
   applicable-and-non-compliant implies incorrect. The principles → compliance → success chain
   is a tautology on those columns.
2. **Statements read off the wrong side of a mined pair** (p03, p09, p16, p17, p19). In five
   cases the proposer generalised from the *absent* half of a cross-document similarity pair
   while the *present* half of the same pair contradicts the principle. These pairs are
   near-duplicate annotation noise, not convention.
3. **Checkers that penalise gold** (p09 80%, p11 50%, p17 ~100%, p21 96%, p22 30%, p20 9%,
   p12 6%). A gold-perfect model would be scored non-compliant at these rates, which inverts the
   compliance/correctness relationship the study is trying to measure.

Confidence distribution: strong 11, moderate 8, weak 2, could-not-break 2.

## Blinding disclosure

I did not open `controls.yaml`, `controls_key.yaml`, `round2_key.yaml`, `round1/`,
`cross_source_validation.yaml`, `principles/pilot/critiques.yaml`, `principles/pilot/round2/`
(pre-existing content), `reviews/cross-source-validation.md`, `reviews/principle-critiques.md`,
`reviews/calibration-controls.md`, or the Atticus Handbook PDF.

**One leak to record:** a `grep` over the permitted `plans/decisions.md` surfaced two summary
lines from the round-1 adversarial pass (aggregate counts of how many round-1 checkers and
statements were broken). I stopped reading at that point and did not open the section. Round-1
ids do not map to round-2 ids in anything I saw, and every conclusion below was derived
independently from gold before or without reference to it. Treat my strong/moderate split as
uncontaminated; treat the *count* similarity, if any, as coincidence rather than corroboration.

---

## Tier 1 — refuted by gold; do not ship

### p17 — Governing Law span ends at the jurisdiction (conflicts tail excluded) — **strong**

Backwards. **194 of 370 Governing Law gold spans (52.4%) contain a conflicts-of-law tail.** Only
**3** gold spans corpus-wide stop before a conflicts tail beginning within the next 200
characters. The compliance rule ("no emitted span's end offset falls at or beyond the start of
that tail") would fail a gold-perfect model on essentially every applicable decision.

Worse, the principle's own cited evidence contains the counterexample:
`LejuHoldingsLtd_20140121_DRS (on F-1)_EX-10.26...` `[1286:1401]` — pair-0029's left span — is
*"...governed by the laws of the PRC, without regard to conflicts of law principles."* Tail
inside the span. Both cited pairs share that left span (the same SINA/Leju sentence filed twice),
so the whole principle rests on one sentence in two near-duplicate documents.

Other counterexamples: `BLACKSTONEGSOLONG-SHORTCREDITINCOMEFUND_05_11_2020-EX-99.(K)(1)`
`[24399:24565]`, `ADIANUTRITION,INC_04_01_2005-EX-10.D2` `[24928:25157]`,
`ArmstrongFlooringInc_20190107_8-K_EX-10.2` `[33798:33915]`.

**Drop.** The inverse principle is the one gold supports.

### p21 — Agreement Date is the signature-page date — **strong**

Refuted at every level of strictness.

| applicability reading | applicable | gold takes execution date | gold takes intro date |
|---|---|---|---|
| the checker's own rule (any date literal after the execution block) | 145 | 6 | **139 (95.9%)** |
| same, with SEC `Source:` furniture lines masked | 77 | 2 | **75 (97.4%)** |
| strictest (an explicit `Dated: <date>` signature date exists) | 35 | 9 | 26 (15 same-day, **11 conflicting**) |

Even on the 20 genuinely conflicting contracts under the strictest reading, gold prefers the
*intro* date 11 to 9. And the sketch's same-day escape hatch never fires: in **0 of 75** cases
does a post-block date resolve to the same calendar day as gold.

Clean counterexamples: `GOCALLINC_03_30_2000-EX-10.7-Promotion Agreement` gold `[243:256]` =
"March 12,1999" while the signature block reads "Dated: 3/13/99" twice;
`ASHWORTHINC_01_29_1999-EX-10.(D)` gold "June 1, 1998" against signature dates of December 16,
1998 — six months apart; `CORIOINC_07_20_2000-EX-10.5` gold "October 29, 1999" against 11/5/99;
`ConformisInc_20191101_10-Q_EX-10.6`; `PapaJohnsInternationalInc_20190617_8-K_EX-10.1`.

**Drop as a compliance principle.** If the Handbook really says execution block, this is the
study's cleanest documentation-versus-practice divergence and deserves to be reported *as* a
divergence — but scoring it would penalise correct answers on ~96% of the contracts where it bites.

### p09 — Volume Restriction needs a consequence, not just a ceiling — **strong**

**82 of 103 ceiling-bearing Volume Restriction gold spans (80%) carry no consequence cue**
(fee/price/charge/rate/consent/approval); 106 of all 136 VR gold spans (78%) carry none at all.
"A span carrying the ceiling alone is a violation" describes gold's default behaviour.

Its own mined batch contradicts it: `GluMobileInc_...Content License Agreement` `[102627:102895]`
— *"Up to: 1 Java Game ... 5 MMS 10 Wallpapers"* — is the right-hand span of pairs 0014/0016/0018,
a bare list of ceilings, gold Volume Restriction. Also `MPLXLP_06_17_2015-EX-10.1` `[32140:32305]`
("shall not exceed ninety percent (90%) of the total expansion capacity"),
`ATMOSENERGYCORP_11_22_2002-EX-10.17` `[916:...]` (a bare MDDO definition), and
`GOCALLINC_03_30_2000-EX-10.7` `[2793:2998]`.

Provenance is also weak: both cited pairs (0017, 0021) come from one contract,
`SUMMAFOURINC_06_19_1998-EX-10.3`, whose "fewer than 1 talkoff in 5 hours of voice" engineering
acceptance criteria CUAD has keyword-labelled into both Minimum Commitment and Volume Restriction.

**Drop**, or recast as a positive rule about the ~20% of caps that *do* carry a consequence.

### p16 — an unquantified commitment is not a Minimum Commitment — **strong**

Two independent kills.

*Axis 5.* Applicability is `gold is_impossible == true`. Compliance is "emit an AbsenceClaim".
Compliant-and-applicable implies correct; non-compliant-and-applicable implies incorrect. Empty
off-diagonal.

*Counterexamples, from its own evidence.* All three cited pairs have a **gold-present** left span
that the statement says should have been ruled absent:

- `CoherusBiosciencesInc_20200227_10-K_EX-10.29` `[48667:48702]` = *"In particular, Licensee
  commits to:"* — undertaking cue, no quantity, gold Minimum Commitment (pair-0037).
- `JOINTCORP_09_19_2014-EX-10.15` `[66768:66783]` = *"You agree that:"* — 15 characters, gold
  Minimum Commitment (pair-0038).
- `CytodynInc_20200109_10-Q_EX-10.5` `[116212:116356]` — a termination-rights lead-in with no
  quantity, gold Minimum Commitment (pair-0036).

Corpus-wide: **63 of 334 Minimum Commitment gold spans (18.9%) contain no quantity token at
all**, and 4 of those match the checker's undertaking cue exactly. The gold gate hides every one
of them from the checker.

**Drop.**

### p19 — furniture carried inside the span — **strong (rewrite required)**

Half right, and the half that is wrong is the compliance rule. Its violation clause — "emitting
two spans split at the furniture boundary" — names the behaviour gold exhibits **204 times**
across all categories against **25** for the behaviour it rewards (8:1); in the study's own
12-category subset it is 17 splits against 8 swallows (2:1). 127 of the 204 split *mid-sentence*,
so they are unambiguously one passage.

Counterexamples: `MPLXLP_06_17_2015-EX-10.1` Anti-Assignment gap `[49993:50003]` = `"\n\n15\n\n..."`;
`2ThemartComInc_19990826_10-12G_EX-10.10` gap `[12361:12412]` = an SEC `Source:` line splitting
*"are not sublicenseable,"* / *"transferable or assignable."*; `OTISWORLDWIDECORP_04_03_2020-EX-10.4`.

Built on a single mined pair (pair-0033). The complementary half is unbreakable but fires on
nothing: **0 of 4,052** subset gold spans (0 of 11,180 corpus-wide) are pure furniture.

**Rewrite to the disjunctive form** the corpus supports: furniture is never a span on its own,
and a passage interrupted by furniture is annotated either way — so neither shape is a violation.

### p03 — amendments carry no responsive text for reproduced clauses — **strong**

**All 25 amendment-shaped contracts in dev+ft_train carry gold-present categories** (86 gold
spans in the subset). Agreement Date is present in 24/25 (96%, *higher* than the 92% baseline).
Governing Law (36% vs 90%) and Expiration Date (32% vs 85%) are genuinely depressed, so the true
effect is category-specific, not the blanket rule stated.

The cited evidence points the other way. Pairs 0031/0032/0035 are the AIG capital-maintenance
twins — and the document titled **"AMENDED AND RESTATED UNCONDITIONAL CAPITAL MAINTENANCE
AGREEMENT"** (`VARIABLESEPARATEACCOUNT_04_30_2014-EX-13.C`) is the **gold-present** one, while the
non-amendment original (`SEPARATEACCOUNTIIOFAGL_05_02_2011-EX-99.(J)(4)`) is **gold-absent**.
Exactly backwards. Pair-0034 (`GSVINC` / `VITAMINSHOPPECOMINC` sponsorship agreements) is the same
shape and neither document amends the other.

The checker's applicability (400+ char shared substring with another contract) is a cross-document
*contamination* test, not an amendment test — it selects for precisely the near-duplicate
population INV1-D7 has been excluding.

**Drop.** The one genuine amendment family (NETGEAR: the reproduced entire-agreement/Governing Law
paragraph is absent in both amendments, present in the base agreement) would support a much
narrower Governing-Law-scoped claim, if Tyler wants one.

### p02 — claim absence over a neighbouring fact — **strong**

Axis 5. Applicability is `gold is_impossible == true`, compliance is "emit an AbsenceClaim".
The clearest possible demonstration: **11 of 404 contracts are applicable, all gold-absent by
construction, while 116 gold-present contracts satisfy the identical *text-side* condition** (a
date literal in the first 2,000 characters not preceded by an execution cue) and are excluded
solely by the gold gate. The gate removes 91% of the cases where the principle could have been
shown wrong.

The behaviour is real (`IOVANCEBIOTHERAPEUTICS,INC_08_03_2017-EX-10.1` offers "Effective Date:
April 17, 2017" and gold still marks Agreement Date absent), so keep the idea — but with an
instance-only trigger over all 127 near-miss contracts. **Drop as written.**

### p08 — `<omitted>` marker for discontiguous spans — **strong**

**The string `<omitted>` occurs 0 times in gold spans (0/4,052) and 0 times in the 404 contract
texts.** The checker's applicability condition can never be satisfied. The convention is an
annotation-tool artefact that did not survive into CUAD v1's SQuAD-format release, which
represents discontiguity as *multiple spans* — Expiration Date 40/332 positives carry 2–7 spans,
Governing Law 19/351, Agreement Date 6/374.

The sketch also concedes the fatal design problem: the marker must be injected into the prompt or
no model emits it, which changes every arm's output format and contaminates the comparison.

**Drop**, and restate the underlying behaviour (lead-in plus operative subsection, intervening
subsections omitted) as a multi-span principle.

### p05 — every category gets an explicit ruling — **strong (unmeasurable)**

Axis 4, by the reviewer's own disqualification rule. The output schema guarantees exactly one
decision per target, so applicability is 100% of decisions and compliance is 100% by
construction. The only residual test (never an `Extraction` with an empty span list) is schema
validation, which the harness should reject before scoring. The sketch already proposes
quarantining it from the headline; a principle that must be quarantined is not carrying weight.

**Drop.**

---

## Tier 2 — statement survives, checker does not

### p11 — Revenue/Profit Sharing is about the arithmetic, not the label — **strong (checker)**

The statement is, in my judgement, the most useful disambiguation in the round and is not
derivable from the one-line category definition. The checker is unusable: **165 of 329 gold RPS
spans (50.2%) fail all three lexical tests** (percentage-near-revenue / per-unit / equity), so a
gold-perfect model scores ~50% compliance. The sketch set its own tolerance at a ~15% false-*pass*
rate; the false-*fail* rate is 50%.

CUAD's RPS gold includes many spans that reference the sharing arithmetic without restating it —
`INNOVIVA,INC_08_07_2014-EX-10.1` `[82805:...]` ("may be based on estimated Net Sales"),
`CORIOINC_07_20_2000-EX-10.5` `[11952:...]` ("shall share certain revenues"),
`CHINARECYCLINGENERGYCORP_11_14_2013` `[2912:...]`.

**Keep the statement; move compliance to hand labelling or a much softer rule** (e.g. no predicted
span whose *only* monetary content is a fixed sum).

### p14 — a floor binds whichever party, on whatever — **strong (checker)**

The statement is the best-evidenced claim in the whole set and I could not touch it: only 25.0% of
Minimum Commitment gold spans encode purchase-by-this-party, and 73.7% of MC-positive contracts
contain no such span at all (`reviews/principle-claim-checks.md`, independently verified).

The checker is the problem, and it fails in the dangerous direction — it *rewards a wrong answer*.
Compliance is "the decision is an Extraction rather than an AbsenceClaim", triggered on a purely
lexical supply-side-minimum pattern. **136 of 404 contracts match; 56 of those (41%) are gold-ABSENT
for Minimum Commitment,** and on all 56 the checker demands an extraction.

Its regex also misses the largest non-purchase bucket in gold — performance and effort floors, 55
of 336 spans (16.4%): `IMMUNOMEDICSINC_08_07_2019-EX-10.1` `[38270:38496]` (sales-force headcount),
`CANOPETROLEUM,INC_12_13_2007-EX-10.1` `[1116:1204]` (episodes produced).

**Keep the statement; rebuild the checker so that "found a supply-side minimum sentence" does not
imply "must extract".**

---

## Tier 3 — salvageable with a rewrite

### p22 — one complete sentence, period to period — **moderate**

Over the 9 yes/no categories (2,921 gold spans): 78% start cleanly, 88% end on terminal
punctuation, **only 70% satisfy both**. 886 gold spans (30.3%) would be scored non-compliant for a
gold-perfect model, and a large share of those failures are the same furniture-split artefact that
sinks p19 — the check would partly measure PDF extraction, not model behaviour.

Second problem: the statement's operative clause ("includes the lead-in clause needed to make the
subsection read as a complete sentence") is **not tested at all** — the section-number allowance
explicitly passes a subsection extracted without its lead-in. Gold itself keeps them apart in
`CoherusBiosciencesInc_20200227_10-K_EX-10.29` (`[48667:48702]` then `[49054:49743]`).

Third: `trigger_guidance` says the confusable trio, `scope` is `[]`, and the checker covers 9
categories — a 3.7× disagreement in denominator (799 vs 2,921 spans).

**Keep; report the ~30% gold floor and split furniture-adjacent spans out.**

### p20 — attachments after the signature block are not annotated — **moderate**

91% of gold respects the boundary, which is real. But **110 of 1,211 gold spans (9.1%) in the 97
applicable contracts fall at or beyond the first post-execution attachment heading**, in 30 of
those 97 contracts, and they concentrate in the study's hard categories: Minimum Commitment 28,
Cap On Liability 19, License Grant 14, Anti-Assignment 13, Revenue/Profit Sharing 13, Volume
Restriction 9 — against Governing Law 6, Expiration Date 3, Agreement Date 1.

`GluMobileInc_...Content License Agreement` alone contributes MC `[99482:99726]`, `[99915:100190]`
and VR `[102627:102895]` from post-signature schedules.

Gold is also internally inconsistent here: `LejuHoldingsLtd_20140121_DRS...EX-10.26` takes its
Agreement Date from an Exhibit B (`[133:146]`) while the byte-identical passage in
`ChinaRealEstateInformationCorp_20090929_F-1_EX-10.32` (`[47029:47298]`) is gold-absent — the
boundary was decided by file segmentation. Same flip in the `PfHospitalityGroupInc` 1-vs-3 pair.

**Scope it to the answer-shaped categories (10 of the 110 offending spans) or drop it.**

### p12 — single-value categories take exactly one span — **moderate**

Multi-span gold positives: Expiration Date **40/332 (12.0%**, one contract with 7 spans), Governing
Law 19/351 (5.4%), Agreement Date 6/374 (1.6%) — **65 of 1,057 applicable decisions (6.2%)** where a
gold-perfect model is scored non-compliant. Plus the redundancy the sketch already admits: p07's
test (1) is this same boolean on 374 of the 1,057 decisions (35%).

**Keep, per category, and drop Expiration Date from scope. Keep only one of p07-test-1 and p12.**

### p15 — floor vs. share routing — **moderate (rewrite)**

The exclusive routing is wrong: gold **dual-labels** the hybrid clause.
`JOINTCORP_09_19_2014-EX-10.15` `[41193:41432]` — *"a continuing franchise royalty fee of seven
percent (7%) of the gross revenues ... with a minimum monthly amount of $700.00"* — carries **both**
Minimum Commitment and Revenue/Profit Sharing on the same character range, and it is pair-0009's own
left span. p15 forces it into MC alone and loses the RPS decision. 4 such ranges exist in the subset,
and they are precisely the clauses p15 exists to govern.

Also, `HAS_FLOOR` fires on any currency literal, which misroutes **10 of 134 (7.5%)** sharing spans
out of RPS — e.g. `INNOVIVA,INC_08_07_2014-EX-10.1` `[83681:...]` ("15% royalty payable on the first
U.S. $3 Billion of Net Sales" — a tier boundary, not a floor).

And pair-0012, one of its four cited pairs, does not show what the proposer read: the MC span
("share a minimum of $50,000.00") and the RPS span ("share 10% of the net revenue") are two
*different* clauses.

**Rewrite to the non-exclusive form:** a clause that both fixes a floor and states a share answers
*both* targets. That version matches gold and is testable.

### p23 / p18 — dual assignment across targets — **moderate (both)**

Near-duplicate statements with the same defect. Both gate applicability on gold overlap and define
compliance as reproducing the shared gold passage under both categories — which is the Level B
correctness metric. Empty off-diagonal.

Rarity is also worse than the sketch assumes for this study: **90 dual-labelled ranges in 67 of 404
contracts, and 69 of the 90 (77%) are the single Exclusivity | License Grant pair.** Inside the
confusable trio only 6 remain (MC|RPS 4, MC|VR 2).

**Collapse to one (keep p23's soft matcher) and give it an applicability gate computed from the
model's own output plus a category-pair prior, not from gold — or drop both.** The underlying fact
is verified corpus-wide (1,010 dual ranges, 79% of contracts), so this is a measurement problem, not
a truth problem.

### p13 — threshold direction assigns the category — **moderate**

The direction is empirically clean — 231 LOWER-only MC spans against 4 UPPER-only; 97 UPPER-only VR
spans against 1 LOWER-only — so the statement holds at ~99%. Two objections stand.

*The proposed strengthening is refuted.* "When both cue classes fire in one contract, require both
decisions be Extractions": of 249 contracts with both cue classes, **109 have BOTH categories
gold-absent, 83 only MC, 19 only VR — 211 of 249 (85%) would be scored non-compliant while matching
gold exactly.**

*The compliance rule is undefined for the case it exists to govern.* 26 of 470 MC+VR gold spans
(5.5%) carry both cue classes, and gold assigns the clearest of them to *both* categories:
`GOCALLINC_03_30_2000-EX-10.7` `[2793:2998]` ("a minimum of 100,000 up to 500,000 pagers"),
`ATMOSENERGYCORP_11_22_2002-EX-10.17` `[16435:16542]` ("Max 13,370 Dfli/Day, Min 13,370 DthDay").

Also close to circular: a model that routes "minimum"→MC and "maximum"→VR passes 465 of 470
applicable spans without legal reasoning.

**Keep, drop the strengthening, define the both-cue case as dual assignment.**

### p04 — redacted/blank dates are still extractions — **moderate**

First half confirmed: date-**shaped** blank constructs are **32 gold-present vs 2 gold-absent (94%)**.
Second half over-reaches. Contracts whose only evidence is a bare `Date:` / `Dated:` **slot** with no
date-shaped text are **11 gold-absent vs 85 gold-present**, and the checker's stated trigger ("a bare
comma or blank sitting where a date should follow an execution verb") fires on the 11 and demands an
Extraction — wrong (`InnerscopeHearingTechnologiesInc_20181109_8-K_EX-10.6`,
`FUSIONPHARMACEUTICALSINC_06_05_2020-EX-10.17`).

Separately, the statement's answer-format clause ("recorded with the unknown components bracketed")
is untested by the checker *and* unsupported by gold — gold spans are the raw blank text
("this day of , 20", "____________", "[*]").

**Rewrite the trigger to require a date-shaped construct; drop the "cover page / signature page"
clause; and remove the stale LOUD FLAG** — `reviews/agreement-date-check.md` already resolved the
sign in the principle's favour.

---

## Tier 4 — minor objections only

### p07 — exactly one Agreement Date, date text only — **weak**

Test (1) disagrees with gold on 6/374 positives (1.6%, e.g. `OASYSMOBILE,INC_07_05_2001-EX-10.17`);
test (2) on 7/380 spans (1.8%, e.g. `GULFSOUTHMEDICALSUPPLYINC_12_24_1997`,
`MOVADOGROUPINC_04_30_2003-EX-10.28`). The convention itself is solid — median gold span length 16
characters, only 9/380 over 40. The real issue is redundancy: test (1) is p12 restricted to
Agreement Date, covering 35% of p12's denominator. **Keep tests (2) and (3), delete test (1).**

### p01 — administration is not Revenue/Profit Sharing — **weak**

Only 4 of 329 RPS gold spans (1.2%) are administration-only, so the IS-NOT rule holds — but those 4
exist and would fail a gold-perfect model: `ExactSciencesCorp_20180822_8-K_EX-10.1` `[143896:144004]`
(*"Such royalty payment shall be payable to Pfizer within thirty (30) days of the end of each
Calendar Quarter."*), `JOINTCORP_09_19_2014-EX-10.15` `[50494:...]`,
`NakedBrandGroupInc_20150731_POS AM...EX-10.75` `[18140:...]`.

The live objection is redundancy: p01's compliance test is p11's test with an administration
prefilter, and all 4 flagged spans are inside p11's 165. Independent discriminating power over p11 is
at most 4 spans corpus-wide, which will not populate the H4 confusion matrix the sketch is counting on.

---

## Could not break

### p10 — extract the minimal expression, not the containing sentence — **could_not_break**

Gold is unambiguous: median Agreement Date span 16 characters, only 9 of 380 over 40. The failure
mode it targets (returning the whole preamble sentence) is the most likely span-boundary error on
this category. Two drafting notes rather than objections: the statement is universal while `scope` is
`[Agreement Date]` — read universally it contradicts gold on Governing Law, where spans are full
sentences — and applicability is computed from gold *shape* (which is brittle enough that pair-0001's
own span, `"25th day of May, 1999."`, falls out on the trailing period). Make applicability
instance-only and it is clean.

### p06 — Governing Law excludes venue, forum and arbitration — **could_not_break**

The strongest candidate in the set. **Only 4 of 370 Governing Law gold spans (1.1%) are pure
venue/arbitration with no governing-law verb** (`UsioInc_20040428_SB-2_EX-10.11` ×2,
`KIROMICBIOPHARMA,INC_04_08_2020-EX-10.28`, `ImperialGardenResortInc_20161028_DRS`); a further 18
match both patterns and the checker explicitly permits those. Applicability is instance-only with no
gold gate, the checker tests what the statement says, and the off-diagonal is populated in both
directions. My only complaints are that the trigger fires on 63% of contracts and that the
"single-section law" half is close to definitional. **Report the 1.1% gold floor and ship it.**

---

## Reproduction

Analysis was scratch-only (constraint: no writes outside `principles/pilot/round2/` and this file)
and ran through `scripts/cuad_dataset.py` over `dev` + `ft_train`. Every count above is mechanical
except where it cites `reviews/principle-claim-checks.md` (the 336-span Minimum Commitment hand
classification and the 204-vs-25 furniture counts) or `reviews/agreement-date-check.md` (the
blank-date case inspection), which are that report's numbers, not mine.
