# Adversarial critique of the 16 pilot principles

Written to give the curator a disagreement to adjudicate rather than an assertion to
rubber-stamp. For each candidate I made the strongest case I honestly believe, grounded in
gold wherever possible, and then said how strong I think that case actually is.

Scope: `dev` + `ft_train`, 404 contracts, via `scripts/cuad_dataset.py`. **Holdout was never
loaded.** The Handbook was not consulted — the guidelines side is another agent's job, so
everything below is gold-derived or internal-consistency reasoning. Machine-readable twin:
`principles/pilot/critiques.yaml`. Date: 2026-08-15. AI Assistant Used: Claude Code.

Ordered by how much you should worry. **Nothing below this line is an accept/reject decision —
they are all yours.**

---

## The headline number

**I could not break 5 of the 16 statements.** They are `g03`/`d02` (one claim, mined twice),
`g04`, `g06`, `d04`, and `d05`'s main clause. In each case I looked for gold contracts where
following the principle gives the wrong answer, and either found none or found a rate under 2%.
That is a real result about the derivation pipeline: roughly a third of what came out of both
arms is substantively correct about CUAD, which is a much better hit rate than a prior of "an
LLM proposed it" would suggest.

**But only 2 of those 5 have a checker I could not also break.** The gap between "the statement
is true" and "the sketch measures the statement" is where most of the damage is. `d04` is the
extreme: the best-supported statement in the pilot, attached to a regex that reaches 27% of the
spans it is about.

Counts: 3 statements I think are outright refuted by gold (`d06`, `d07`, `d08`), 1 that cannot
be measured at all (`g02`), 1 refuted as a routing rule (`d03`), 2 stated too broadly
(`g01`, `g08`), 1 whose checker fails on the majority of gold (`g05`), 1 redundant (`d01`),
and 1 with a small known inversion (`g07`).

---

## Worry 0 — cross-cutting: six checkers measure the answer, not compliance

This is the objection I would fix first, because it is invisible per-principle and it damages
the study's central causal claim rather than any one candidate.

The chain the study wants to report is **principles → compliance → success**. That requires
compliance to be a variable distinct from success. In six candidates it is not:

| principle | how compliance collapses into correctness |
|---|---|
| `d06` | applicability requires `gold.is_impossible == true`; compliance is "emit AbsenceClaim" |
| `d08` | same shape — the checker may only fire where the answer is already known to be absence |
| `g08` | compliance is "Extraction not AbsenceClaim", and D-19 showed gold agrees on all 30 |
| `d01` | compliance is literally "the emitted span set matches gold" |
| `g03`, `d02` | compliance is "the shared passage appears under both targets" = span recall, twice |

For these, a C2/C3 compliance gain **cannot** be evidence that principles work through
compliance, because passing the checker and getting the answer right are the same event. Worse,
the two gold-gated ones (`d06`, `d08`) are structurally incapable of registering their own cost:
they only look at contracts where absence is correct, so the false-absences they induce
elsewhere never enter the compliance number.

Contrast the ones that are clean: `g01`, `g04`, `g05`, `g07`, `d07` all test a property of the
output that is independent of whether the output is right. `g01` is actually *anti*-correlated
with correctness, which is uncomfortable but is at least a real measurement.

Suggested filter, offered as a candidate rule rather than a recommendation: **a principle enters
the scored set only if a model can pass its checker and still get the decision wrong, and fail
its checker while getting the decision right.** Six candidates fail that test today.

**My confidence this objection lands: strong.**

Second cross-cutting item, cheaper: **four candidates are two claims.** `g03` == `d02`;
`g07`'s second clause == `d01`. Keeping both members inflates the principle count, splits
citation credit, and makes the H4 confusion matrix mark a model wrong for citing the twin.

---

## Worry 1 — `g02` cannot fire. Ever.

The `<omitted>` marker **does not exist in CUAD v1**. Not in any gold span, not in any contract
text, not anywhere in `data/raw/CUADv1.json` (11.2M characters, four spelling probes, zero hits).

It cannot exist, structurally: the loader represents a gold span as a `(start, end)` range into
the contract, so every gold span is contiguous by construction. CUAD v1 encodes a discontiguous
selection the only way that representation allows — **as multiple spans**. That is exactly the
adjacent-pair phenomenon `d07` is fighting over.

So `g02`'s applicability condition ("the gold span set contains a span containing the literal
marker") is satisfied 0 times out of 404 contracts, and a principle that is never applicable
cannot enter the scored set under the component-contracts rule. Its own sketch already concedes
the marker would have to be injected into the prompt for a model to emit it — at which point
compliance measures instruction-copying, and every compliant span is scored a verbatim-fidelity
*failure* by Level B, because the marker is not in the contract.

This one is not a judgement call about contract law; it is a fact about the file. **Confidence:
strong.**

The salvageable version is the same claim in this corpus's encoding: *when responsive material is
discontiguous, emit one span per fragment in document order rather than one span swallowing the
intervening text.* That is measurable, and it is the same object as the corrected `d07`.

---

## Worry 2 — `d06` tells the model to claim absence on ~half the contracts where gold has an answer

`d06`'s own trigger guidance names the case: *"an effective date where an execution date is asked
for"*. In CUAD, the effective date **is** routinely the Agreement Date answer.

- 207 of 374 Agreement-Date-positive contracts (**55.3%**) share an exact gold character range
  with Effective Date.
- In 177 of them (**47.3%**) the two categories' gold range sets are *identical*.
- 55 of 380 Agreement Date gold spans sit directly after an "effective as of" / "Effective Date"
  lead-in. `StaarSurgicalCompany_20180801_10-Q_EX-10.37` is typical: *"made effective as of
  ____________ (the 'Effective Date')"* — and `____________` is the Agreement Date gold span.

Against that, `d06`'s own `defect_argument` concedes the informative evidence is **n=1** (Iovance).
One contract against a corpus-wide 47%.

The checker hides all of this, because applicability requires `gold.is_impossible == true`. Inside
that gold-gated window it fires on 11 of 30 contracts; the same textual trigger shape occurs in
116 of 374 Agreement-Date-*positive* contracts (31%), where it is blind. So the checker will
report a healthy pass rate while the principle, if the model actually follows it, costs recall on
the study's highest-base-rate category.

**Confidence: strong.** The narrow rule D-19 actually found — a date-*shaped* construct is
labelled, a bare slot is absence — is a different and defensible principle. `d06` as written is
not it.

---

## Worry 3 — `g05`'s checker flags 53.5% of gold, blowing its own pre-registered abort threshold

I believe `g05`'s **statement**. I could not find gold Revenue/Profit Sharing spans that are
genuinely fixed-sum payments. The problem is entirely the lexical proxy.

A model that reproduced the gold RPS span set **verbatim** would be scored non-compliant on
**176 of 329 spans (53.5%)**, because the entitlement is stated without a percentage token near a
revenue word:

- `CHINARECYCLINGENERGYCORP_11_14_2013-EX-10.6` `[2912:3036]` — fee *"according to the income
  from CDQ waste heat power generation station"*. Varies with revenue. No `%`.
- `INNOVIVA,INC_08_07_2014-EX-10.1` `[82805:82902]` — *"royalty payments... may be based on
  estimated Net Sales"*.
- `InvendaCorp_20000828_S-1A_EX-10.2` `[96435:96649]` — *"shall share equally all net revenue"*.
- `ChaparralResourcesInc_03_30_2000-EX-10.6` `[13563:13716]` — *"$1.00 per one net tonne of
  Commodity shipped"*. This is per-unit, which `g05` explicitly counts as responsive, and the
  `PERUNIT` regex misses it.

Of the 176, only 6 even look like fixed sums on inspection, and at least 3 of those 6 are per-unit.
So this is checker error, not a gold counterexample — but a 53.5% false-violation rate makes the
compliance number uninterpretable.

The sketch pre-registered its own rule: *"measure it on a hand-scored sample of ~20 spans... if it
exceeds ~15% either narrow the rule or move this principle to hand labelling."* Measured against
all of gold rather than a sample of 20, it is **3.5× over its own abort threshold**. That decision
has already been made by the author of the sketch; it just needs executing.

**Confidence: strong** on the checker, **could_not_break** on the statement.

---

## Worry 4 — `d08` is refuted at span level and its checker cannot see it

`d08` says an obligation with no quantified threshold does not satisfy Minimum Commitment,
"however emphatic the commitment language". Gold disagrees:

- **63 of 334** MC gold spans (18.9%) contain no digit or redaction token; **45** (13.5%) contain
  no number in words either.
- **4** of those match `d08`'s own undertaking-cue regex exactly — the precise shape it says must
  be ruled absent:
  - `InnerscopeHearingTechnologiesInc_20181109_8-K_EX-10.6` `[2381:2518]` — *"Distributor agrees
    that during the term of this agreement it meet the minimum performance goals set forth in
    Exhibit C"*. No quantity. Gold: Minimum Commitment.
  - `LUCIDINC_04_15_2011-EX-10.9` `[9291:9460]` — *"agrees to purchase from Lucid minimum agreed
    quantity of product"*. No quantity. Gold: MC.
  - `CoherusBiosciencesInc_20200227_10-K_EX-10.29` `[48667:48702]` — *"In particular, Licensee
    commits to:"*. Gold: MC.
  - `BloomEnergyCorp_20180321_DRSA (on S-1)` `[40894:40929]` — *"If the Minimum Efficiency Level
    has"*. Gold: MC.

The last two are plausibly the neighbourhood-label defect from D-15 — I would not lean on them.
The first two are not; they are ordinary unquantified undertakings that CUAD labels.

Two further problems. **Circularity**: the checker only fires where `gold.is_impossible == true`
and compliance is "emit AbsenceClaim", so the span-level refutation above is structurally
invisible to it. **Degeneracy**: inside that window it fires on **210 of 272** MC-absent contracts
(77%), and 272 of 404 contracts are MC-absent — so it approximates *"always claim absence for
Minimum Commitment"*, which the always-absent trivial baseline already scores for free.

Note the tension with `d04`, which the pilot also accepts: `d04` says the Minimum Commitment
convention is *broader* than the printed definition, `d08` pushes the model to rule absence more
often. They pull opposite ways on the same category, and `d04` has 20× the evidence.

**Confidence: strong.**

---

## Worry 5 — `d07`, re-derived independently, is refuted

I recomputed this from scratch without inheriting the prior check, on the post-exclusion
404-contract scope and with my own furniture regex:

- **22** gold spans swallow furniture internally.
- **158** same-category adjacent gold span pairs are separated by nothing but furniture, **145**
  of them splitting mid-sentence.

Ratio ~7:1 against `d07`'s compliance rule, which calls the split shape a violation. My counts
differ slightly from the earlier 25/204 (different regex, four fewer contracts) but the direction
and magnitude replicate cleanly. **I reach the same conclusion independently.**

The second half — furniture is never a span on its own — also replicates and is safe.

Only the disjunctive restatement is supportable: *furniture is never a span alone, and an
interrupted passage may be annotated either swallowed or split, so a scorer must accept both
shapes.* **Confidence: strong.**

---

## Worry 6 — `d03` forces an exclusive choice gold does not make, and its floor test misfires

Two objections, both landing.

**It contradicts `d02`/`g03`, and gold sides with `d02`.** `d03` routes a clause to *either*
sharing *or* minimum-commitment on the presence of a floor. Gold assigns **both** labels to the
same characters when the clause has both properties — 4 ranges do exactly this, and one of them is
in `d03`'s **own cited evidence contract**:

- `VirtuosoSurgicalInc_20191227_1-A_EX1A-6 MAT CTRCT` `[5047:5123]` — *"Company shall pay to JHU
  minimum annual royalties as set forth in Exhibit A."* Gold: **Minimum Commitment AND
  Revenue/Profit Sharing.** `d03` cites Virtuoso (pair-0010/0013) as evidence for exclusive routing.
- `JOINTCORP_09_19_2014-EX-10.15` `[41193:41432]` — *"7% of the gross revenues... with a minimum
  monthly amount of $700.00"*. Gold: **both**.
- `INTELLIGENTHIGHWAYSOLUTIONS,INC_01_18_2018` `[3736:4373]` and `SIBANNAC,INC_12_04_2017`
  `[3753:4384]` — gold: **both**. These are the same two spans `d02` cites as *its* evidence.

So `d02` and `d03` were mined from overlapping evidence and reach opposite conclusions about it.

**The `HAS_FLOOR` test misfires.** It is true on any span containing a bare currency literal
(`/\$\s?[\d,]+/`), and revenue-share clauses routinely name dollar amounts — tier boundaries,
caps, worked examples. **48 of 329** RPS gold spans (14.6%) have `HAS_FLOOR` true, but only **15**
contain an actual floor word; **33 are currency-literal-only false floors** that `d03` would route
into Minimum Commitment. The reverse error is negligible (1 of 334 MC spans).

Fix is cheap: drop the currency literal from `HAS_FLOOR`, and restate so "both" is a permitted
outcome rather than a forced choice. **Confidence: strong.**

---

## Worry 7 — `g01` is violated by a quarter of gold, and mostly on D-15 defects

Your round-1 note was that `g01` will fire on nearly every span. It will — but that is the smaller
problem. The larger one is that **gold itself is not sentence-shaped**.

Across the 10 yes/no subset categories, **3,291** gold spans:

| failure | n | rate |
|---|---|---|
| does not end on terminal punctuation | 356 | 10.8% |
| begins mid-sentence (generous section-number allowance) | 276 | 8.4% |
| contains more than one sentence | 293 | 8.9% |
| **any of the three** | **808** | **24.6%** |

Per category the union runs 22.8%–40.4% (Exclusivity 40.4%, Revenue/Profit Sharing 40.1%, Cap On
Liability 38.3%). Examples:

- `ALLISONTRANSMISSIONHOLDINGSINC_12_15_2014-EX-99.1` Anti-Assignment `[28319:28441]` — ends
  *"...enforceable by any other persons"*, mid-sentence.
- `INNOVIVA,INC_08_07_2014-EX-10.1` Revenue/Profit Sharing `[84910:85481]` — a royalty tier table.
  Not a sentence in any sense.
- `ArtaraTherapeuticsInc_20200110_8-K_EX-10.5` Revenue/Profit Sharing `[15243:15662]` — ends on
  `2.50%` inside a rate table.

A large share of the 10.8% end-boundary failures are the **furniture-split artifact** D-15 and
D-20 already identify. So `g01` penalises a model for emitting the coherent legal sentence on
exactly the spans D-15 calls defective, and rewards it for reproducing the scanning artifact. That
is defect-derived in effect even though it was derived from documentation.

I do not think this kills `g01` — it is a real convention and the violations concentrate in known
noise. But its pass rate is **bounded above at ~75%** by gold, and if that ceiling is not reported
alongside the pass rate it will be read as model failure. **Confidence: moderate** on the
substance, **strong** on "publish the ceiling".

---

## Worry 8 — `d01` is redundant, and the contradiction you flagged is not real

First, the defence: **your round-1 worry that `d01` contradicts `g01` is not sustained.** `g01`'s
trigger guidance explicitly exempts the date and party categories, and `d01`'s scope is Agreement
Date. The two can never apply to the same decision. There is nothing to consolidate.

The real problem is different. `d01` is **subsumed by `g07`** — *"the span is the date text alone,
excluding the surrounding execution wording"* is the same rule, derived from 374 positives instead
of 3 pairs. And its compliance test is *"the emitted span set matches gold under the same length
and regex tests"*, which is the answer scorer wearing a hat.

One scope hazard worth noting: the statement is written **globally** ("the minimal expression that
answers the target question... rather than the whole containing sentence") but scoped to Agreement
Date. A model sees the statement, not the scope field. Read globally it *does* oppose `g01`.

**Confidence: strong** on redundancy, **strong** that the g01 conflict is a non-issue.

---

## Worry 9 — `g07` disagrees with gold on ~3.5% of contracts

Re-derived: test (1) "exactly one span" fails on **6 of 374** positives (1.6%, matching D-19); test
(2) "no execution wording in the span" fails on **7 of 380** spans (1.8%); test (3) fires on **0**
spans — no Agreement Date gold span sits inside a recitals block, so test (3) is *untested* rather
than passed.

The test-(2) cases are cleaner counterexamples than I expected — gold sometimes takes the whole
execution sentence:

- `GULFSOUTHMEDICALSUPPLYINC_12_24_1997-EX-4` `[13360:13434]` — *"This Affiliate Agreement is
  executed as of the 14th day of December, 1997."*
- `MOVADOGROUPINC_04_30_2003-EX-10.28` `[16840:16942]` — opens *"IN WITNESS WHEREOF, the parties
  hereto have executed this Agreement as of..."*
- `MANUFACTURERSSERVICESLTD_06_05_2000-EX-10.14` `[2774:2788]` — *"Dated 05/05/98"*.

Combined ~13/374 (3.5%) annotation floor. Report the three tests separately, as the sketch already
intends for test (3). **Confidence: moderate** — this is a known, small, reportable inversion, not
a reason to reject.

---

## Worry 10 — `g08` is stated too broadly (one clause only)

The first half is confirmed by D-19 and I could not touch it. The second half — *"absence is
claimed only when no agreement date appears in the introductory paragraph, on the cover page, or on
the signature page"* — is contradicted. A bare `Date:` / `Dated:` slot **is** a date position on
the signature page, and gold rules those contracts absent: **8 of 30** absent contracts contain
one, and D-19 found 4+ independent contracts treating the pattern consistently.

D-19 already prescribes the fix (require a date-*shaped* construct). Without it, `g08` marks the
FUSION / Kitov / Cardlytics / Innerscope family non-compliant on a decision gold agrees with — a
false inversion of our own making. Also see Worry 0: `g08`'s compliance test is the decision kind,
which is the answer. **Confidence: moderate.**

---

## `d05` — the core survives; delete the strengthening sentence

The main clause is the cleanest thing in the pilot and **I could not break it**:

| | LOWER cue only | UPPER cue only |
|---|---|---|
| Minimum Commitment spans | **232** | 4 |
| Volume Restriction spans | 1 | **97** |

Five contradicting spans across 444. I tried and failed.

Two honest caveats and one refutation:

- **The optional strengthening clause is false in the large.** *"When both cue classes fire in one
  contract, require both decisions be Extractions"* — 219 of 404 contracts have both cue classes
  present, and in **183 of them (83.6%)** gold does not mark both categories present. As a rule it
  would be wrong 5 times out of 6. Bound cues are ambient legal vocabulary. **Delete that sentence.**
  Confidence: strong.
- 26 spans carry **both** cue classes, and the checker's "a span whose cue class contradicts the
  decision it appears in is a violation" is undefined for them. `TubeMediaCorp_20060310_8-K_EX-10.1`
  `[25006:25354]` — *"up to 5.0 mbps, but... not less than 2.0 mbps"* — is gold Minimum Commitment.
- 110 spans (24.8%) carry neither cue and are out of reach entirely.
- One counterexample sits in `d05`'s own evidence contract: `VERICELCORP_08_06_2019-EX-10.10`
  `[33196:33420]` — *"shelf-life... shall be at least [***]"*, a LOWER cue, gold **Volume
  Restriction**.

---

## `d04` — confirmed independently; only its checker is broken

Re-derived from scratch without inheriting D-20: **245 of 334** Minimum Commitment gold spans
(73.4%) mention no purchase verb, and **92 of 132** MC-positive contracts (69.7%) contain no
purchase-verb span at all. The prior hand classification put purchase-shaped spans at 25.0%; my
cruder verb test puts them at 26.6%. **Same conclusion, reached independently.** This is the
best-evidenced statement in the pilot and I could not dent it.

The checker is the problem: `d04`'s own applicability approximation (a minimum cue plus
`supply|deliver|provide|share|allocate|make available` and no `buy|purchase|order`) matches only
**90 of 334 spans (26.9%)**. It misses the performance/effort/production floors that are the
second-largest class. Also, its compliance test is "the decision is an Extraction covering that
sentence" — correctness against a *regex-derived pseudo-gold*, which will disagree with real gold
wherever the regex fires on an unlabelled sentence.

**Confidence: could_not_break** on the statement, **moderate** on the checker.

---

## `g04` — I attacked this hardest and it held

Governing Law is the category I most expected to break, because whole-sentence annotation should
drag venue language in. It did not:

- **370** Governing Law gold spans. **23 (6.2%)** contain venue/arbitration language — but the
  checker's escape clause (the sentence also matches a governing-law cue) absorbs those.
- Only **4 (1.1%)** contain venue/arbitration language with *no* governing-law cue. Those are the
  real counterexamples: `UsioInc_20040428_SB-2_EX-10.11` `[24826:25007]` and `[25008:25179]`,
  `KIROMICBIOPHARMA,INC_04_08_2020-EX-10.28` `[35631:36013]`, `ImperialGardenResortInc_20161028`
  `[11451:11712]` — arbitration clauses labelled Governing Law.
- **Zero** gold spans are a law scoped to a single section, so that half of the statement has no
  counterexample and also no test.

The only objection I can honestly raise is that it is nearly free: the applicability trigger fires
on 319 of 404 contracts (79%) and a model has to work to violate it, so it may show a ceiling pass
rate in every condition and discriminate nothing. **Confidence: weak. This one is sound.**

---

## `g06` — sound; its weakness is inherited

Only **3 of 329** RPS gold spans (0.9%) are administration-pattern with no entitlement signal, and
they are genuine counterexamples rather than noise — `ExactSciencesCorp_20180822_8-K_EX-10.1`
`[143896:144004]`, *"Such royalty payment shall be payable to Pfizer within thirty (30) days of the
end of each Calendar Quarter"*, is pure timing and gold calls it Revenue/Profit Sharing.

One internal-consistency note: `g06`'s exoneration path is "the span has `g05`'s signals", and
`g05`'s signals are absent from 53.5% of gold. That also contradicts `g06`'s own cited evidence,
which says a clause is responsive *even when the percentage lives in a different clause* — while
the checker requires the percentage in-span. Fix `g05`'s checker and this follows.

**Confidence: weak against the statement (could_not_break); moderate against the checker.**

---

## `g03` / `d02` — true, duplicated, and circular

Independently confirmed: **90** dual-labelled ranges in the 12-category subset, across **67 of 404**
contracts. There is no counterexample; the claim is a property of gold, not a hypothesis about it.

Three objections, none of which is "it's false":

1. **Duplicated** — `g03` and `d02` are the same claim from two arms (see Worry 0).
2. **Circular** — compliance is span recall on both targets (see Worry 0).
3. **Scope** — inside the 12-category subset the effect is 2.3% of ranges, not the corpus-wide
   10.1%, and the Minimum Commitment | Revenue/Profit Sharing pair this study actually cares about
   is **4 ranges total**. Whether 4 ranges can support a citation-level measurement is a real
   question.

**Confidence: could_not_break on the claim; strong on the redundancy and circularity.**

---

## Method and limits

- All counts are over `dev` + `ft_train` (404 contracts) via the public loader. Holdout untouched.
- My furniture, venue, floor and bound regexes are my own, deliberately built to be *generous to
  the principle* where a choice existed (e.g. a ±120-character adjacency window for `g05`, a
  section-number allowance for `g01`). Every rate above is therefore a **lower bound** on the
  failure rate under a stricter reading.
- I did not classify spans by hand at the scale `reviews/principle-claim-checks.md` did; my `d04`
  re-derivation is a verb-presence proxy, which is why it agrees with the hand count only
  approximately (26.6% vs 25.0%).
- I did not compute applicability footprints — another agent has that — but flagged degeneracy
  where I stumbled on it (`g01`, `g04`, `d08`).
- The Handbook was deliberately not read, so where a principle's warrant is documentary rather than
  empirical (`g02`'s marker convention, `g01`'s sentence rule), I can only say what CUAD v1 shows.
  For `g02` that happens to be decisive; for `g01` it is not.
