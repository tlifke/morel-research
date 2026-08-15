# Principle claim checks — d02, d04, d07

Empirical verification of three factual claims underlying `principles/pilot/candidates_data_mined.yaml`,
run before Tyler's hand-review at gate G2. Read-only over `dev` + `ft_train` (408 contracts, 11,180 gold
spans across all 41 CUAD categories) via `scripts/cuad_dataset.py`. HOLDOUT was not loaded.
Date: 2026-08-15. AI Assistant Used: Claude Code.

## Verdicts

- **d02 (dual labelling) — CONFIRMED.** The two cited spans each carry both gold labels, and dual
  labelling is a corpus-wide property: 1,010 distinct character ranges (10.1% of all 9,997 distinct
  ranges) carry two or more categories, in 323 of 408 contracts.
- **d04 (floor binds whichever party) — CONFIRMED, and understated.** Only 25.0% of Minimum Commitment
  gold spans encode a purchase obligation by the party bound. 73.7% of MC-positive contracts contain
  **no** purchase-by-this-party span at all. The printed one-line definition, applied literally, would
  produce an AbsenceClaim on roughly three quarters of the contracts gold marks present.
- **d07 (page furniture inside spans) — MIXED, and its main clause is REFUTED as stated.** The second
  half ("furniture standing on its own is never extracted") is confirmed: 0 of 11,180 gold spans consist
  only of furniture. The first half ("furniture interrupting a passage is carried along inside the span")
  is the *minority* behaviour: 25 spans swallow furniture, but 204 same-category adjacent span pairs are
  separated by nothing but furniture — 127 of them splitting mid-sentence. The dominant convention is to
  **split at the furniture and exclude it**, by roughly 5:1 (8:1 counting all splits).

---

## Claim 1 — d02, dual labelling

### The cited spans

Both cited ranges carry two gold labels *inside their own contract*:

| contract | offsets | gold categories |
|---|---|---|
| `INTELLIGENTHIGHWAYSOLUTIONS,INC_01_18_2018-EX-10.1-Strategic Alliance Agreement` | `[3736:4373]` | Minimum Commitment **and** Revenue/Profit Sharing |
| `SIBANNAC,INC_12_04_2017-EX-2.1-Strategic Alliance Agreement` | `[3753:4384]` | Minimum Commitment **and** Revenue/Profit Sharing |

Both are ft_train. Note that pair-0004 and pair-0005 are recorded with `same_contract: false` — they are
cross-document pairs — so the proposer's reading was an inference from the symmetry, not from the pair
records. The inference was nonetheless correct: each span is independently double-labelled within its own
document. (The two contracts *are* near-twins, but here they agree, so this is not a twin-document defect
in either direction.)

### Corpus count

Over dev + ft_train, all 41 CUAD categories:

| measure | count | rate |
|---|---|---|
| gold spans | 11,180 | — |
| distinct character ranges | 9,997 | — |
| ranges carrying ≥2 categories (exact offsets) | **1,010** | **10.1% of ranges** |
| span pairs with identical offsets and different categories | 1,388 | — |
| additional pairs with near-identical offsets (IoU ≥ 0.80) | 123 | — |
| contracts with ≥1 exactly dual-labelled range | **323 / 408** | **79.2%** |

Restricted to the study's 12-category subset, the rate drops but stays real: 90 of 3,995 distinct ranges
(2.3%) in 67 of 408 contracts.

Most frequent category pairs (all 41 categories): Agreement Date | Effective Date (219),
License Grant | Non-Transferable License (183), Irrevocable Or Perpetual License | License Grant (121),
Cap On Liability | Uncapped Liability (120), Notice Period To Terminate Renewal | Renewal Term (87),
Exclusivity | License Grant (81). Within the 12-category subset: Exclusivity | License Grant (69),
Exclusivity | Minimum Commitment (5), Minimum Commitment | Revenue/Profit Sharing (4),
License Grant | Source Code Escrow (3), Minimum Commitment | Volume Restriction (2).

### Examples

1. `GOCALLINC_03_30_2000-EX-10.7-Promotion Agreement` `[2793:2998]` — Minimum Commitment **+** Volume
   Restriction — *"PageMaster Corporation shall provide a minimum of 100,000 up to 500,000 pagers for the
   fulfillment of this promotion…"* (one sentence carrying both a floor and a ceiling).
2. `ATMOSENERGYCORP_11_22_2002-EX-10.17-TRANSPORTATION SERVICE AGREEMENT` `[16435:16542]` — Minimum
   Commitment **+** Volume Restriction — *"Quantity of capacity to be released: Max 13,370 Dfli/Day, Min
   13,370 DthDay."*
3. `JOINTCORP_09_19_2014-EX-10.15-FRANCHISE AGREEMENT` `[41193:41432]` — Minimum Commitment **+**
   Revenue/Profit Sharing — *"…a continuing franchise royalty fee … of seven percent (7%) of the gross
   revenues … with a minimum monthly amount of Seven Hundred and No/100 Dollars ($700.00)."*
4. `AURASYSTEMSINC_06_16_2010-EX-10.25-STRATEGIC ALLIANCE AGREEMENT` `[5894:6250]` — Exclusivity **+**
   Minimum Commitment — *"In order to maintain the exclusivity granted hereunder, Zanotti shall provide
   Aura with orders for a minimum of (i) one thousand (1,000) AETRU Systems…"*
5. `CORIOINC_07_20_2000-EX-10.5-LICENSE AND HOSTING AGREEMENT` `[40193:40578]` — License Grant **+**
   Source Code Escrow.
6. `QIWI_06_16_2017-EX-99.(D)(2)-COOPERATION AGREEMENT` `[11401:12244]` — Cap On Liability **+** Minimum
   Commitment.

### Consequence

d02 stands and is important. The interaction with **D-14 (one decision per target)** is live: at a 10%
range-level rate and a 79% contract-level rate, the same characters will legitimately appear in several
decisions in most contracts. Note also the mechanism behind the largest pair counts — CUAD's Datasheet
II-D convention that categories inside one Group share a text context (Agreement/Effective Date; the
licence family; Cap/Uncapped Liability). Within the study's own five pilot categories the effect is
smaller but still present, so a checker must accept multi-assignment rather than treat it as a conflict.

---

## Claim 2 — d04, floor binds whichever party

### Method

All 336 Minimum Commitment gold spans in dev + ft_train (133 of 408 contracts have MC present) were read
and hand-classified by the obligation each span encodes. Fragments (bare section headers, cross-reference
tails) were bucketed separately rather than forced into a type.

### Distribution

| bucket | spans | share |
|---|---|---|
| **purchase-by-this-party** (the printed definition: a buyer must buy from the counterparty) | **84** | **25.0%** |
| payment / fee / royalty / spend floor | 81 | 24.1% |
| supply / delivery / provision **by the counterparty** | 59 | 17.6% |
| performance / effort / activity / revenue floor | 55 | 16.4% |
| spec, administrative or other minimum | 39 | 11.6% |
| uninformative fragment (header, cross-ref) | 16 | 4.8% |
| access or capacity floor | 2 | 0.6% |
| total | 336 | |

Contract-level: **98 of 133 MC-positive contracts (73.7%) contain no purchase-by-this-party span at
all.** Even a generous reading that folds "payment floor" into "purchase" leaves the printed definition
covering under half the spans, and the residual supply/performance/spec buckets (155 spans, 46%) are
flatly outside it.

### Representative spans

1. **Supply by the counterparty** — `InvendaCorp_20000828_S-1A_EX-10.2…Co-Branding Agreement`
   `[32258:32762]`: *"Excite@Home will supply to e-centives a minimum of ***** Payment-Eligible User Data
   records…"*
2. **Payment floor** — `PlayboyEnterprisesInc_20090220_10-QA_EX-10.2…` `[59881:60161]`: *"…the Royalty
   paid to Client in each Year of the Term shall not be less than the amounts set forth in Exhibit…"*
3. **Spend floor** — `ExactSciencesCorp_20180822_8-K_EX-10.1…Promotion Agreement` `[88643:88871]`:
   *"Exact agrees it shall spend at least eighty million dollars ($80,000,000) toward Marketing and
   Promotion…"*
4. **Access / capacity floor** — `RangeResourcesLouisianaInc_20150417_8-K_EX-10.5…` `[76820:76909]`:
   *"New Shippers will have access to a minimum of ten percent (10%) of the Available Capacity"* (the
   pair-0022 span the proposer cited; it holds).
5. **Performance / headcount floor** — `IMMUNOMEDICSINC_08_07_2019-EX-10.1-PROMOTION AGREEMENT`
   `[38270:38496]`: *"…Company shall use reasonable efforts to deploy and maintain a sales force … of at
   least [***] ([***]) Sales Representatives…"*
6. **Production-output floor** — `CANOPETROLEUM,INC_12_13_2007-EX-10.1-Sponsorship Agreement`
   `[1116:1204]`: *"The Company shall produce no less than forty (40) original episodes of the Show per
   year"*
7. **Spec minimum** — `ARMSTRONGFLOORING,INC_01_07_2019-EX-10.2…` `[51376:51423]`: *"Logo Size: The
   minimum logo size is 1" or 25mm."*
8. **Securities-offering minimum** — `BLUEHILLSBANCORP,INC_05_20_2014-EX-1.1-AGENCY AGREEMENT`
   `[8069:8818]`: *"In the event the Holding Company is unable to sell a minimum of 17,850,000 Shares
   within the period herein provided, this Agreement shall terminate…"*
9. **Payer-side share floor** — `PacificapEntertainmentHoldingsInc_20051115_8-KA_EX-1.01…` `[6202:6470]`:
   *"…THE HENRY FILM AND ENTERTAINMENT CORPORATION agrees to share a minimum of $50,000.00 annually…"*
   (pair-0012; it holds).

### Consequence

The proposer did not overread. If anything d04 understates the effect: it names supply, payment and
access, but the largest non-purchase bucket after payment is **performance/effort floors** (55 spans,
16.4%) — sales-force headcount, detailing quotas, episodes produced, events played, revenue targets — a
class d04's trigger_guidance does not mention and whose checker sketch (a `supply|deliver|provide|share|
allocate|make available` regex) would not fire on.

A model applying the printed one-line definition literally returns AbsenceClaim on ~74% of the contracts
where gold marks Minimum Commitment present. This is the single largest systematic effect found in these
three checks, and it is a recall failure concentrated exactly on the decision type the study cares about.

**Caveats on this claim.** The classification is one reader's judgement on 336 spans and the boundary
between "payment floor" and "purchase floor" is genuinely soft in take-or-pay and minimum-royalty
clauses; a second reader could plausibly move 10–20 spans across that line. The headline is robust to
that: the purchase bucket would have to more than double to rescue the literal definition. The 16
fragment spans and the spec bucket also confirm a separate, unrelated fact — CUAD's MC gold includes
keyword-driven labels (logo size, minimum weight, DTMF timing minima) that no definition covers. That is
noise, not convention, and worth flagging separately from d04.

---

## Claim 3 — d07, page furniture inside spans

### Counts (dev + ft_train, all 41 categories)

Furniture patterns searched: SEC `Source: …, M/D/YYYY` lines, confidential-treatment / "omitted portions
of this exhibit" legends, `Page N of M` lines, and bare page numbers alone on a line.

| measure | count |
|---|---|
| contracts containing ≥1 furniture occurrence | 321 / 408 |
| furniture occurrences | 7,569 |
| **gold spans containing furniture strictly inside** | **25** (20 contracts) |
| — by pattern | SEC Source line 13, bare page number 12, confidential legend 2 |
| **gold spans consisting only of furniture** | **0** (1 borderline, see below) |
| **same-category adjacent gold span pairs separated by nothing but furniture** | **204** (80 contracts) |
| — of which the left span ends mid-sentence (unambiguously one passage) | **127** |

### Furniture carried inside — confirmed but not dominant

The convention is real and is not a one-pair artifact: 25 spans across 20 contracts, spread over 13
categories (Cap On Liability 5, Revenue/Profit Sharing 4, Minimum Commitment 3, Exclusivity 3, …).
Examples beyond the cited GluMobile span:

- `StampscomInc_20001114_10-Q_EX-10.47…` Revenue/Profit Sharing `[35602:37838]` — swallows both a bare
  page number and a confidential-treatment legend.
- `UpjohnInc_20200121_10-12G_EX-2.6…` Insurance `[191824:193295]` — swallows an SEC `Source:` line.
- `ExactSciencesCorp_20180822_8-K_EX-10.1…` Minimum Commitment `[81638:82587]` — swallows an SEC
  `Source:` line.
- `CHANGEPOINTCORP_03_08_2000-EX-10.6-LICENSE AGREEMENT` Cap On Liability `[134356:135486]` — swallows a
  bare page number.

So the cheap confirmation the proposer named does succeed: n=1 becomes n=25.

### But the opposite behaviour is 5–8× more common

204 times, two gold spans of the *same* category sit adjacent with only furniture between them — i.e. the
annotator ended the span before the furniture and started a new one after it. 127 of these split
mid-sentence, which rules out "two separate clauses that happen to straddle a page break":

- `MPLXLP_06_17_2015-EX-10.1-TRANSPORTATION SERVICES AGREEMENT`, Anti-Assignment, gap `[49993:50003]` =
  `"\n\n15\n\n\n\n\n\n"`, splitting *"…without the prior written consent of the"* / *"other Party pursuant
  to Section 8.1."*
- `2ThemartComInc_19990826_10-12G_EX-10.10…`, Anti-Assignment, gap `[12361:12412]` =
  `"\n\nSource: 2THEMART COM INC, 10-12G, 8/26/1999\n\n\n\n\n\n"`, splitting *"…are not sublicenseable,"* /
  *"transferable or assignable."*
- `ADAPTIMMUNETHERAPEUTICSPLC_04_06_2017…`, Exclusivity, gap `[46204:46354]` = a "Portions of this page
  have been omitted pursuant to a request for Confidential Treatment" legend plus page number, splitting
  *"…an exclusive option to negotiate an"* / *"exclusive (subject to MD Anderson's…)"*.
- `KINGPHARMACEUTICALSINC_08_09_2006-EX-10.1`, Insurance, gap `[152454:152702]` = a confidential-treatment
  legend, splitting mid-sentence.
- `INNOVIVA,INC_08_07_2014-EX-10.1-COLLABORATION AGREEMENT`, Joint Ip Ownership and Post-Termination
  Services, gap `[163688:163701]` = `"   46\n\n\n\n\n\n  "`.

### Furniture alone is never a span — confirmed

Zero of 11,180 gold spans are pure furniture under the strictest test. The single near-exception is
`Magenta Therapeutics, Inc. - Master Development and Manufacturing Agreement`, Cap On Liability
`[59925:60326]`: the span opens with a full CONFIDENTIAL TREATMENT REQUESTED legend and then continues
*"…CONTRACT LAW, TORTS OR ANY OTHER AREA OF LAW SHALL BE LIMITED TO THE AMOUNT [***]."* — that is
furniture prefixed to real clause text, not furniture standing alone. So the complementary check in
d07's sketch ("no emitted span is wholly matched by F") is safe.

### Consequence and provenance

d07 as written is half right. Its compliance rule — *"violations are … emitting two spans split at the
furniture boundary"* — labels as a violation the behaviour gold exhibits 204 times, against 25 for the
behaviour it rewards. A checker built from d07 unchanged would penalise the majority case.

On provenance: the CUAD Datasheet convention noted in `plans/decisions.md` D-15 ("annotators deliberately
left confidential legends, footers and page numbers inside labelled sentences") is *corroborated but not
generalised* by the data — it happens, 25 times, and it is documented, but it is not the rule. The
guidelines arm already encodes the tension correctly: `candidates_guidelines.yaml` g07's checker sketch
speaks of "gold spans that were split around embedded furniture". So the two derivation sources do **not**
agree here, and the disagreement is on the data-mined side: the guidelines arm anticipated splitting; the
mined arm read one swallow case and generalised the wrong way. That is itself a result about the two
sources, and worth recording as such rather than quietly patching d07.

If d07 is kept, the defensible statement is the disjunctive one: *furniture is never a span on its own,
and a passage interrupted by furniture is annotated either as one span swallowing it or as two spans
split at it — so a scorer must not treat either shape as a violation.* That is weaker than d07 but it is
what the corpus supports.

---

## Reproduction

Analysis scripts were scratch-only and are not checked in (constraint: no dataset writes, no edits under
`principles/`). All numbers come from `scripts/cuad_dataset.py` over `dev` + `ft_train`; the Minimum
Commitment classification in Claim 2 is a hand labelling of all 336 spans and is the only non-mechanical
number in this report.
