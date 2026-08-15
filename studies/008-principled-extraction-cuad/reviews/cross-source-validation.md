# Cross-source validation of the 16 pilot principles

Every candidate in `principles/pilot/candidates_pilot.reviewed.yaml` checked against the
**other** derivation source. Guideline-derived principles (g01–g08) are tested against gold
annotation; data-mined principles (d01–d08) are tested against the Atticus Labeling Handbook.

Scope: dev (40) + ft_train (364) = **404 contracts**, via `scripts/cuad_dataset.py`.
**Holdout was never loaded.** Date: 2026-08-15. AI Assistant Used: Claude Code.
Machine-readable companion: `principles/pilot/cross_source_validation.yaml`.

The Handbook is copyrighted, paywalled and non-redistributable. Nothing in this file quotes it;
every reference is a paraphrase with a section pointer. The CUAD v1 category descriptions
(CC BY 4.0) are quotable and are cited as such where used.

---

## Why this pass exists

Round 1 of curation produced 11 accepts, 5 defers, 0 rejects, 0 edits, with rationales like
*"I don't have the domain expertise to disprove this."* The non-expert curator could not judge
whether a principle is TRUE. But every decision he made with confidence was a **cross-source
comparison** — d01 deferred as *"in direct contradiction to g01"*, d02 accepted as *"aligned
perfectly with g03"*.

A relation between two independent sources is checkable where the truth of a proposition is not.
This pass generalises that accident into a procedure.

---

## Headline

| | corroborated | contradicted | silent | n |
|---|---|---|---|---|
| **guidelines-derived (g01–g08)**, tested against gold | **8** | 0 | 0 | 8 |
| **data-mined (d01–d08)**, tested against the Handbook | **3** | **3** | **2** | 8 |
| **total** | 11 | 3 | 2 | 16 |

**The asymmetry is the result.** The guidelines arm has a perfect record against the data: every
documented rule Opus read out of the Handbook is visible in gold, most of them decisively. The
mined arm has a 3/8 contradiction rate — and in two of those three cases the data-mined arm is
the one that is wrong.

Two secondary numbers the study wants regardless of curation:

- **Independent rediscovery: 2 of 8 (25%).** The mining arm, which never saw the Handbook,
  independently recovered two documented conventions: d02 recovers g03 (multi-label extraction),
  and d01 recovers the Handbook's own date-label exemption from the one-sentence rule. The other
  six guideline principles were not recovered from data.
- **Mining-only coverage: 5 of 8.** d03 (in part), d04, d05, d07's main clause and d08 concern
  conventions the Handbook does not document at all. Without the mining arm the study would have
  had nothing to say about two thirds of the Savelka confusable trio.

**Silence is not evidence against.** It is structural: the Handbook documents 30 of CUAD's 41
categories, and **Minimum Commitment and Volume Restriction appear zero times in its 95 pages.**
Neither does Price Restrictions, Cap on Liability, Uncapped Liability, Warranty Duration,
Affiliate License-Licensee or Unlimited/AYCE License. Two thirds of the confusable trio the pilot
was scoped around have no guidance to check against, by construction.

---

# 1. Contradicted — read these first

## d04 — floor binds whichever party. **CONTRADICTED by the published definition; gold sides with d04.**

**What d04 claims.** A guaranteed floor qualifies for Minimum Commitment whichever party it binds
and whatever it is a floor on — supply, payment or access — not only a buyer's purchase
obligation.

**What the other source says.** The Handbook itself is *silent* — there is no Minimum Commitment
section. The only guideline-side statement in existence is the published CUAD v1 category
description (CC BY 4.0, mirrored in `data/processed/categories.json`):

> "Is there a minimum order size or minimum amount or units per-time period that one party must
> buy from the counterparty under the contract?"

Applied literally, "must buy from the counterparty" excludes supplier-side floors, payment
floors, performance floors and access floors. That is a direct incompatibility with d04.

**What gold says — d04 wins, and understates itself.** From the hand classification of all 336
Minimum Commitment spans in `reviews/principle-claim-checks.md`:

| bucket | spans | share |
|---|---|---|
| purchase-by-this-party (the printed definition) | 84 | **25.0%** |
| payment / fee / royalty / spend floor | 81 | 24.1% |
| supply / delivery **by the counterparty** | 59 | 17.6% |
| performance / effort / activity / revenue floor | 55 | 16.4% |
| spec, administrative or other minimum | 39 | 11.6% |
| fragment | 16 | 4.8% |
| access or capacity floor | 2 | 0.6% |

**98 of 133 Minimum-Commitment-positive contracts (73.7%) contain no purchase-by-this-party span
at all.** A model given only the published definition returns an AbsenceClaim on roughly three
quarters of the contracts gold marks present.

**For the curator.** This is the highest-value record in the set. It is a
documentation-versus-practice divergence with a measured sign, on the decision type the study
cares most about (absence), and it is a *recall* failure. Two notes on d04 as drafted: it names
supply, payment and access but not **performance/effort floors**, which are the largest
non-payment bucket at 16.4% (sales-force headcount, detailing quotas, episodes produced) and
which its checker sketch's `supply|deliver|provide|share|allocate|make available` regex would not
fire on. Tyler accepted d04 "not seeing a reason not to" — this is the reason to, stated
precisely.

---

## d07 — furniture carried inside the span. **CONTRADICTED by gold. The method caught a bad principle.**

**What d07 claims.** Document furniture interrupting a passage is carried along inside the
extracted span, but furniture standing on its own is never extracted.

**What the other source says.** The Handbook is *silent on the main clause*. Its only furniture
rule is narrow and category-specific: a date in a header or footer is not an Agreement Date, and
a date in a footer is not an Effective Date — with a note that CUAD contracts come from EDGAR, so
a footer may carry the SEC filing date rather than the contract date. It never addresses whether
furniture interrupting a labelled passage is kept inside the span.

**What gold says, re-derived independently in this pass** (different regex family from the
earlier claim-check, deliberately):

| behaviour | count |
|---|---|
| gold spans containing furniture **strictly inside** | **22** |
| same-category adjacent gold span pairs separated by **nothing but furniture** | **175** |
| — of which the left span ends **mid-sentence** (unambiguously one passage) | **155** |
| gold spans consisting **only** of furniture | **0** |

The earlier pass in `reviews/principle-claim-checks.md` gave 25 / 204 / 127 / 0. Two independent
implementations, same conclusion: **the dominant convention is to split at the furniture and
exclude it, by roughly 8:1.**

Worked splits, all mid-sentence:

- `MPLXLP_06_17_2015-EX-10.1`, Anti-Assignment, gap `[49993:50003]` = `"\n\n15\n\n\n\n\n\n"`,
  splitting *"…without the prior written consent of the"* / *"other Party pursuant to Section 8.1."*
- `INNOVIVA,INC_08_07_2014-EX-10.1`, Joint Ip Ownership **and** Post-Termination Services, gap
  `[163688:163701]` = `"   46\n\n\n\n\n\n  "`, splitting *"…such transfer to be as permitted"* /
  *"by applicable Laws and regulations."*
- `CORIOINC_07_20_2000-EX-10.5`, Source Code Escrow, gap `[38218:38271]`, splitting
  *"…shall require Commerce One to place in an"* / *"escrow account in California…"*

**For the curator.** d07's second clause is confirmed (0 pure-furniture spans out of 11,180).
Its first clause is refuted, and its compliance rule explicitly names as a violation the
behaviour gold exhibits 175 times, in favour of the behaviour gold exhibits 22 times. A checker
built from d07 unchanged would penalise the majority case.

This is the worked example of the method doing its job. d07 was read off **one pair** and
generalised the wrong way. Tyler deferred it asking for "more support, either from guidelines or
evidence" — the guidelines have none to give, and the evidence points the other way. Note too
that the guidelines arm anticipated the correct answer without being told: g07's checker sketch
already speaks of gold spans *split* around embedded furniture.

If kept, the defensible form is disjunctive: *furniture is never a span on its own, and a passage
interrupted by furniture is annotated either as one span swallowing it or as two spans split at
it — so a scorer must not treat either shape as a violation.*

---

## d06 — claim absence over a near miss. **CONTRADICTED on its evidence; the abstract statement survives.**

**What d06 claims.** Claim absence when the document does not state the specific fact the target
asks for, even where it states a neighbouring fact that plausibly stands in for it.

**What the other source says — two different answers at two levels.**

*The abstract statement is corroborated.* The Handbook's Agreement Date IS-NOT list excludes
header/footer dates and Whereas/Recitals dates; its Effective Date IS-NOT list excludes the
agreement date and the signature-page date. Near-miss dates are not answers.

*The cited evidence is contradicted.* The Handbook's Agreement Date IS list carries an explicit
rule with a worked example: when a date in the introductory paragraph is defined as the Effective
Date, it is labelled under **both** Agreement Date and Effective Date. d06's only informative
pair — pair-0026, `IOVANCEBIOTHERAPEUTICS,INC_08_03_2017-EX-10.1`, which prints
`Effective Date: April 17, 2017` in its opening line and has Agreement Date **gold-absent** — is
a case where gold departs from that documented rule.

**How rare is that departure?** Gold follows the Handbook rule overwhelmingly: **207 character
ranges** in dev+ft_train carry both Agreement Date and Effective Date (the single largest
dual-label pair in the corpus). Against that, **6 contracts** have a concrete intro-region date
labelled Effective Date while Agreement Date is absent:

| contract | offset | Effective Date span |
|---|---|---|
| `IOVANCEBIOTHERAPEUTICS,INC_08_03_2017-EX-10.1` | 221 | `April 17, 2017` |
| `InmodeLtd_20190729_F-1A_EX-10.9` | 129 | `1.4.2011` |
| `LOYALTYPOINTINC_11_16_2004-EX-10.2` | 952 | `This Agreement is effective as of August 1, 2004…` |
| `NATIONALPROCESSINGINC_07_18_1996-EX-10.4` | 331 | `June 30, 1996` |
| `OPTIMIZEDTRANSPORTATIONMANAGEMENT,INC_07_26_2000-EX-6.6` | 1248 | `EFFECTIVE DATE: The earlier of…` |
| `WHITESMOKE,INC_11_08_2011-EX-10.26` | 430 | `1 August 2011` |

d06's evidence base sits in a **~3% annotation tail**, not in a convention.

**For the curator.** The proposer flagged d06 as weakly supported (effective n=1) and was right.
The cross-source check localises the weakness precisely: **the principle is not wrong, its single
piece of evidence is an annotation error against the Handbook.** Tyler deferred it saying he
couldn't see the pairs. This is what they say. If d06 is kept it needs different evidence; if it
is dropped, that outcome itself records that the mining recovered no Agreement Date absence
convention — which is a legitimate finding, since Agreement Date produced zero cross-label pairs.

---

# 2. The d01 vs g01 question — **NOT a contradiction. Scope-differentiated, and the Handbook draws the line itself.**

This is the record Tyler flagged as the single most important one, and the answer is that there
is no conflict to consolidate.

**What each claims.**

- **g01**: each extracted span is one complete sentence, period to period — *"does not govern the
  date and party categories, which the Handbook exempts."* The exemption is already in g01's
  `trigger_guidance`.
- **d01**: extract the minimal expression that answers the target, clipped out of its carrying
  sentence — `scope: [Agreement Date]`.

**Are they incompatible?** No, and the Handbook says so explicitly. Chapter 1 states the "label
one sentence at a time" rule and then carries an exceptions pointer that names the **Parties and
Agreement Date / Effective Date** labels by name. The Agreement Date section's IS-NOT list then
gives d01 as policy: label the date only, not the surrounding execution reference
("entered into" / "as of" / "dated"). **d01 is a documented Handbook rule that the mining arm
recovered from data without seeing the Handbook.**

**What gold says — the split is enormous and clean:**

| population | spans | both boundaries sentence-shaped |
|---|---|---|
| yes/no categories, 12-category study subset | 3,291 | **80.9%** |
| yes/no categories, all 33 in CUAD | 7,117 | 80.7% |
| **Agreement Date** | 380 | **1.3%** |

and from the other direction: **370 of 380 Agreement Date spans (97.4%) are under 40 characters,
and 365 (96.1%) are proper substrings of their containing sentence.** Median Agreement Date span
length is 16 characters.

**The apparent contradiction is a drafting artifact.** d01's `statement` is phrased generally
("rather than the whole containing sentence") while its `scope` field says Agreement Date. Read
the statement alone and it contradicts g01; read the record and it does not. **The fix is to move
the scope into the statement, not to choose between the two.** If d01 were applied unscoped it
would genuinely contradict g01, and gold would side with g01 by 80.9% to 1.3%.

Recommended consolidation, for Tyler's decision, not Claude's: keep both, and edit d01's
statement to open with its scope — e.g. *"For the date categories, extract the minimal date
expression…"* — with `edited_from.statement` recorded per the protocol. That converts a defer
into an edit and preserves the finding that the two arms independently found complementary halves
of the same Handbook rule.

---

# 3. Corroborated

## Guidelines-derived, tested against gold — 8 of 8

| id | claim | key number | verdict |
|---|---|---|---|
| **g01** | yes/no spans are sentence-shaped; dates exempt | 80.9% (3,291 spans) vs 1.3% for Agreement Date | corroborated, and the exemption is confirmed |
| **g02** | non-contiguous fragments labelled together | 38.9% of labels are multi-span; 1,512 pairs with >1,000-char gaps; 120 lead-in-colon cases | corroborated as a convention |
| **g03** | one sentence → several categories | 997 of 9,912 ranges (10.1%) dual-labelled, in 321 of 404 contracts | corroborated |
| **g04** | Governing Law excludes venue/arbitration | 6 of 1,176 venue-only sentences labelled (0.5%); 5 of 370 GL spans venue-only | corroborated, most decisively in the set |
| **g05** | Revenue/Profit Sharing needs a variable amount | 2 of 16 fixed-milestone sentences labelled (12.5%), both equity | corroborated in the negative direction |
| **g06** | administration machinery is not a revenue share | 2 of 196 admin sentences labelled (1.0%) | corroborated |
| **g07** | one Agreement Date, date text alone, no furniture/recitals | 368 of 374 contracts have exactly one span (98.4%); 7 of 380 contain execution wording; 0 in recitals | corroborated, with a 1.6% floor |
| **g08** | blank/redacted dates are still labelled | 30 of 380 gold spans are blank or redacted constructs (7.9%); 0 clean unlabelled counterexamples | corroborated |

Three of these deserve a sentence more.

**g04 is the strongest corroboration in the set.** Governing-Law-positive contracts contain 1,176
sentences that are venue/arbitration-only, a large and cleanly separated negative population, and
gold declines to label 99.5% of them. The five exceptions are pure arbitration clauses (two of
them adjacent AAA sentences in `UsioInc…Affiliate Agreement 2` at `[24826:25007]` and
`[25008:25179]`). This is exactly the confusion the study predicted and the guidelines document
it correctly.

**g02 is corroborated as a convention but its marker is untestable.** The literal string
`<omitted>` appears in **0 of 404 contract texts** — CUAD gold is character offsets into the raw
contract, so the marker lives only in the annotation UI. What survives into gold is the
multi-span shape, and that is abundant. A checker can test the shape; the marker half is a test
of instruction-following, not legal judgement.

**g08 overturns the study plan's own assumption, favourably.** The plan assumed CUAD marks a
contract gold-absent when the signing date is blank, which would have put compliance and
correctness in opposition. Gold follows the Handbook instead: 30 blank/redacted constructs are
labelled, 0 clean counterexamples. Following the documented rule is also the way to be right.
The tightening in `reviews/agreement-date-check.md` still applies — the trigger must be a
date-*shaped* construct with missing components, not a bare `Date:` slot.

**g07's one caveat.** The "exactly one span" test disagrees with gold on 6 of 374 positives (1.6%)
where CUAD labelled both the intro date and a partial date in an attached exhibit or order form.
Report that test separately and expect a 1.6% annotation floor.

## Data-mined, corroborated by the Handbook — 3 of 8

**d01** — see section 2. Documented in Chapter 1's exceptions pointer and the Agreement Date
IS-NOT list, and 96–97% visible in gold.

**d02** — Chapter 1 carries a dedicated rule directing that a sentence responsive to multiple
labels is labelled under each. **This is the one clean case of the two derivation arms converging
on the same convention from independent sources**, and it is the strongest single piece of
evidence that contrastive mining recovers real conventions rather than annotation noise. Tyler's
instinct ("aligned perfectly with g03") was correct and is now checkable.

**d03** — half corroborated, half silent. The Revenue/Profit Sharing half is documented policy:
the IS list covers payments calculated as a share of the other party's revenue, profit, sales or
margin; the IS-NOT list excludes fixed amounts, fixed-amount milestone payments and fixed-amount
tiered schedules, and states that a bare reference to a royalty or commission is not evidence
either way. The Minimum Commitment half has no Handbook section and rests on d03's own four mined
pairs. Tyler accepted this "unless it's in contradiction with the guidelines" — it is not, on the
half the guidelines cover.

---

# 4. Silent, with reason

Both silences are the *same* structural silence, and it is worth stating plainly: **the Atticus
Labeling Handbook documents 30 labels. Minimum Commitment and Volume Restriction are not among
them — zero occurrences of either name in 95 pages.**

**d05** (threshold direction distinguishes Minimum Commitment from Volume Restriction) — **silent.**
Both halves of the boundary are undocumented, so there is nothing to agree or disagree with. The
only guideline-side statement is the CC BY 4.0 one-line Volume Restriction description ("Is there
a fee increase or consent requirement, etc. if one party's use of the product/services exceeds
certain threshold?"), which weakly corroborates d05's upper-bound half and says nothing about the
lower bound.

This silence should raise d05's standing, not lower it. It is the most strongly evidenced mined
principle in the pilot — 8 pairs across 4 contracts, 6 of them same-contract contrasts, 4
near-verbatim (an identical content list headed "A minimum of:" against "Up to:"; adjacent
definitions of "Minimum Quantity" and "Maximum Quantity" differing by one word) — and it is
precisely the gap the mining arm exists to fill. Two thirds of the Savelka confusable trio have
no documentation, and the only derivation route to them is the data.

**d08** (an unquantified undertaking does not satisfy a target asking for a threshold) —
**silent**, same reason. The one-line Minimum Commitment description does presuppose a quantity
("minimum order size or minimum amount or units per-time period"), which weakly points d08's way
— but it is a definition, not guidance, and it is the same one-liner d04 contradicts on the other
axis, so it cannot bear much weight.

A separate caution on d08 that this pass turned up, about scoreability rather than truth: its
applicability trigger fires on **232 of 272 Minimum-Commitment-absent contracts (85.3%)**. A
principle that is applicable almost everywhere it could apply carries little information. Tyler
deferred d08 saying he had no idea what it means; the cross-source answer is that the guidelines
cannot help, so it must be kept on the strength of its three contract-level absence rulings alone
and its checker needs a far tighter trigger.

---

## Methods and caveats

- All counts computed read-only over `dev` + `ft_train` (404 contracts, post-INV1-D7
  split-contamination exclusion) through `scripts/cuad_dataset.py`. Holdout never loaded. No file
  under `principles/` was modified; `cross_source_validation.yaml` is added, not edited into an
  existing record. Analysis scripts were scratch-only and are not checked in.
- **g01's boundary test** allows a span to start after a section number or a paragraph break as
  well as after terminal punctuation. Under the strict terminal-punctuation-only test the yes/no
  rate is 63.3% rather than 80.9%. The Agreement Date contrast is unaffected (1.3% vs 0.5%). The
  residual is partly OCR and whitespace noise in the EDGAR text.
- **g05 and g06 use lexical proxies for semantic properties** and share that weakness. Both are
  reported on their *negative* direction (does gold decline to label the excluded population?),
  which is the discriminative test; g05's 59.3% positive-direction figure is a floor, not an
  estimate — several misses are plainly variable-amount clauses the regex cannot see.
- **d04's distribution** is a hand classification of 336 spans by one reader, carried over from
  `reviews/principle-claim-checks.md`. The purchase/payment boundary is genuinely soft in
  take-or-pay clauses; the headline is robust because the purchase bucket would have to more than
  double to rescue the literal definition.
- **d07's counts** differ slightly from the earlier pass (22/175/155/0 here against 25/204/127/0
  there) because the furniture regex families differ. The conclusion and the 5–8:1 ratio are
  stable across both.
- **Handbook page pointers** are to the extracted text of the 95-page PDF; nothing is quoted and
  no verbatim prose is reproduced. Only CC BY 4.0 CUAD material is quoted directly.
- Statuses are assigned at the level of the principle **as written**. d06 is the one record where
  the level matters — its abstract statement is corroborated and its evidence is contradicted —
  and that is stated rather than averaged away.
