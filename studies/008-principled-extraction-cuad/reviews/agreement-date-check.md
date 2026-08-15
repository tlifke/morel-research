# Agreement Date: documented rule vs. actual gold

**VERDICT: the gold follows the Handbook, not our plan's assumption.** A blank or redacted
agreement date in the document's own execution/introductory wording is labelled *present* in
CUAD, with the blank text itself as the gold span — 30 such contracts in dev+ft_train, and zero
clean counterexamples where such a construct was left gold-absent.

**Our plan's assumption ("blank signing date ⇒ gold-absent") is contradicted and should be
dropped.** g08 as written is directionally correct and does *not* create a compliance-vs-correctness
inversion — but it needs one refinement (below), because gold draws a line g08 currently does not:
a bare `Date:` slot with no date-shaped text is *not* a redacted date, and is gold-absent.

Scope: dev (40) + ft_train (368) = 408 contracts. Holdout untouched. Loader-only, read-only.

---

## Counts

| quantity | n | of |
|---|---|---|
| Agreement Date gold-**absent** | 31 | 408 (7.6%) |
| Agreement Date gold-**present** | 377 | 408 |
| present **whose gold span is itself blank/redacted** | **30** | 377 (8.0%) |
| absent contracts matching any blank-date pattern anywhere | 9 | 31 |
| …of those, containing a **date-shaped** blank construct belonging to **this** agreement | **0 clean** (2 borderline) | 31 |
| present with 2 gold spans (g07 "exactly one" violations) | 6 | 377 |

So the Handbook-prescribed behaviour is not a rarity: **8% of all Agreement Date positives are
blank or redacted dates**, and they are labelled, not ruled absent. On the other side, the
absence set contains no instance that would score a principle-follower wrong for extracting a
blank intro date, because no such construct is left unlabelled.

Patterns actually observed in gold-present spans (built from the data, superset of the briefed
list): `this ___ day of ______, 20__`, `this day of , 2012` (blanks collapsed to nothing by the
PDF extraction), `November ___, 2006`, `[ ] day of [ ], 2020`, `[___], 2020`, `[*]`,
`____________`, `_____ day of ________, 19____`, `the ____ day of _______________2000`.

Patterns observed in gold-**absent** contracts: bare `Date:` / `Date: Date:` signature slots,
`Dated: .`, cover-page label `Agreement Date` with no value, `[***]` confidential-treatment
markers not in a date position, and blank date constructs belonging to a *different* agreement.

---

## The line CUAD actually draws

Not intro-vs-signature-block — three of the 30 labelled blanks sit at relative position ≈0.99,
i.e. in the signature block. The operative distinction is **is there a date-shaped construct**:

- **Labelled** when a date-shaped construct exists and its components are blanked or redacted:
  the wording contains a month, a year stub, and/or `day of`. Position is irrelevant; the
  construct is what matters.
- **Not labelled** when there is only a *slot* with no date-shaped text — `Date:`, `Dated:`,
  a cover-page field name — or when the blank construct is the date of a referenced/other
  agreement.

## Inspected cases

**1. `UsioInc_20040428_SB-2_EX-10.11_..._Affiliate Agreement 2`** (dev) — **PRESENT**,
span `________ day of ______________________, in the year ____________` at relpos 0.989.
Context: "…supersede all prior agreements… EXECUTED this ________ day of
______________________, in the year ____________. Network 1 Affiliate By: ______".
The intro paragraph carries no date at all. The *only* date in the document is a fully blank
signature-block execution line — and it is the gold answer. Handbook behaviour, in dev,
directly against our plan's assumption.

**2. `AULAMERICANUNITTRUST_04_24_2020-EX-99.8.77-SERVICING AGREEMENT`** (ft_train) —
**PRESENT**, span `this day of , 20` at offset 79. Context: "SERVICING AGREEMENT NATIONWIDE
MUTUAL FUNDS Agreement, made as of this day of , 20 between Nationwide Fund Management LLC…".
This is the exact shape of the motivating LOHAS example — an execution phrase with the date
literally missing — and CUAD labels it, span = the empty construct including the truncated
`20`. This single case is the cleanest refutation of the plan's assumption.

**3. `StaarSurgicalCompany_20180801_10-Q_EX-10.37_..._Distributor Agreement`** (ft_train) —
**PRESENT**, span `____________`. Context: "…is entered into and made effective as of
____________ (the "Effective Date"), by and between STAAR SURGICAL AG…". A bare underscore run
is a valid gold span when it sits in the date position of the execution phrase.

**4. `LUCIDINC_04_15_2011-EX-10.9-DISTRIBUTOR AGREEMENT`** (ft_train) — **PRESENT**, span `[*]`.
Context: "This Distributor Agreement (the 'Agreement') dated [*] is between Lucid Inc.…".
Redaction marker as the answer. Note the span is `[*]` alone — the execution verb `dated` is
excluded, consistent with g07's IS-NOT list.

**5. `InnerscopeHearingTechnologiesInc_20181109_8-K_EX-10.6_..._Distributor Agreement`**
(ft_train) — **ABSENT**. Context: "…being herein merged. Dated: . Erchonia Medical Corporation.
By _____________________ Its _____________________ Distributor: ________________". The intro
paragraph names the parties but carries no date. The only date position is a bare `Dated: .`
This is the closest thing in the corpus to the LOHAS "signed on , in Hong Kong" case, and it is
gold-absent — but note the difference from case 2: no month, no year, no `day of`. There is no
date-shaped construct, only an empty label.

**6. `FUSIONPHARMACEUTICALSINC_06_05_2020-EX-10.17-Supply Agreement - FUSION`** (ft_train) —
**ABSENT**. Intro: "SUPPLY AGREEMENT … effective as of the date of last signing ("Effective
Date")". Signature block: "…Title Title Date Date [SIGNATURE PAGE]" — both date fields empty.
Same shape as case 5. Also gold-absent. `Cardlytics… Maintenance Agreement2` and
`KitovPharmaLtd_…_EX-4.15_… Manufacturing Agreement` are two further instances of the identical
`By: By: Name: Name: Title: Title: Date: Date:` empty-slot pattern, both gold-absent. Four
independent contracts treat the empty signature-block slot the same way, so this is a rule, not
noise.

**7. `PfHospitalityGroupInc_20150923_10-12G_EX-10.1_..._Franchise Agreement1`** (ft_train) —
**ABSENT**, vs. **`…Franchise Agreement3`** (ft_train) — **PRESENT**, span
`this  _____ day of _________, 20___`. Same SEC filing, same franchise package, opposite gold.
Doc 1's cover page reads "Location of the Premises: Agreement Date Franchisee Business
Address…" — a form field *label* with no value and no date-shaped text, and the body says
"entered into as of the Agreement Date shown on the cover page". Doc 3 is Appendix C's sample
NDA whose own opening is "…is made this  _____ day of _________, 20___". Under the construct
rule these are consistent; under a naive "cover page is a search location, so a blank cover-page
date counts" reading of the Handbook, doc 1 is a miss. **Borderline case #1.**

**8. `SoupmanInc_20150814_8-K_EX-10.1_..._Franchise Agreement2`** (ft_train) — **ABSENT**.
Intro: "As an inducement to Kiosk Concepts, Inc. ("Franchisor") to enter into a Master Franchise
Agreement with __N/A____________________ ("Master Franchisee") dated __________________, 20____
(the "Master Franchise Agreement")…". A date-shaped blank construct (`dated ______, 20____`)
in the first sentence — but it dates the *referenced* Master Franchise Agreement, not this
Guarantee attachment, whose own execution reads "Date: Date: Date:" (empty). Excludable under
g07's other-agreement rule, but it is the one instance where an intro-position date-shaped
blank is unlabelled. **Borderline case #2 — the only real ambiguity in the absent set.**

**9. `ChinaRealEstateInformationCorp_20090929_F-1_EX-10.32_..._Content License Agreement`**
(ft_train) — **ABSENT** — vs.
**`LejuHoldingsLtd_20140121_DRS (on F-1)_EX-10.26_..._Content License Agreement2`** (ft_train) —
**PRESENT**, span `day of , 2009`. The same SINA/Leju document, filed twice. In the China Real
Estate filing the whole agreement plus Exhibit B is one file; its main agreement is "made
effective as of the Effective Date (defined below)" (no date), and Exhibit B's "THIS MUTUAL
TERMINATION AGREEMENT … is made and entered into this day of , 2009" is *not* labelled →
absent. In the Leju filing the main agreement is one file (absent, correctly) and Exhibit B is
its own file, where the identical string `day of , 2009` **is** the gold span. Byte-identical
text, opposite label — resolved entirely by document segmentation, not by annotator disagreement.
This is a **near-duplicate-inconsistency defect-class instance** and it is a g07 (scope) issue,
not a g08 (blank) issue: the question is whether an exhibit's date counts as the contract's
Agreement Date, and the answer depends on where the file boundary happened to fall.

---

## Is the gold internally consistent?

**Mostly yes, on the g08 question.** 30 labelled blanks vs. 0 clean unlabelled blanks is not a
coin flip; the annotation is following a rule. The two borderline absent cases (PfHospitality1
cover-page label; Soupman2 referenced-agreement date) are ~6% of the 31-contract absent set and
both are explainable by rules we already encode (no date-shaped construct; other agreement's
date). Call it consistent with a residual ambiguity of ≈2/31.

**No, on the adjacent scope question**, and that is where the noise lives:

- The China Real Estate / Leju pair shows the exhibit-vs-main-document boundary is decided by
  file segmentation, not annotation policy. Feed this to **D-15's noise floor** and to the
  **near-duplicate-inconsistency defect class** — it is a clean, citable instance of both.
- 6 of 377 positives carry **two** gold spans, which g07 ("exactly one") scores as
  non-compliant even when the extraction matches gold. `OASYSMOBILE,INC_07_05_2001-EX-10.17`
  is the worked example: gold holds both the real intro date `31 day of July, 2000` **and** the
  partial `July __, 2000` from Exhibit A's order form. g07's test (1) will fire against gold
  itself on these. That is a real compliance-vs-correctness inversion — just on g07, not g08,
  and at 1.6% rather than 8%.

---

## Recommendation

**Do not drop the Agreement Date absence principle. It is scoreable, and the sign of the
disagreement is favourable: following the documented rule is also the way to be right.**
Remove the LOUD FLAG from g08's checker sketch and replace it with the finding.

**g08 — keep, with one tightening.** Amend the statement so the trigger is a *date-shaped
construct* with missing components, not merely a missing date. Concretely: the applicability
regex should require a month name, a `day of` phrase, a year or year-stub (`20__`, `19____`),
or a redaction marker sitting inside such a phrase — and should **not** fire on a bare `Date:` /
`Dated:` label or an unfilled cover-page field name, which gold treats as absence (4+ contracts,
consistent). Without this tightening, g08 marks the FUSION/Kitov/Cardlytics2/Innerscope family
non-compliant-and-wrong for a decision gold agrees with, which is a false inversion of our own
making. Position (intro vs. signature block) should **not** enter the trigger: 3 of the 30
labelled blanks are signature-block execution lines.

**g07 — keep, but split the reporting.** Its "exactly one span" test disagrees with gold on 6/377
positives where CUAD labelled both the intro date and a partial date in an attached exhibit or
order form. Report test (1) separately from tests (2) and (3) — as the sketch already does for
test (3) — and expect a ~1.6% floor on test (1) that is annotation, not model behaviour.

**Feed D-15**: the ChinaRealEstate/Leju pair and the PfHospitality 1-vs-3 pair are two ready-made
near-duplicate-inconsistency cases for the noise-floor estimate.

## Caveats

- The LOHAS contract that motivated the whole question **is not in CUAD v1** — no title matches
  and the string `signed on ,` appears in zero dev/ft_train contracts. The motivating example is
  external to the corpus; case 2 (AUL American Unit Trust) is its in-corpus analogue.
- Classification of the 31 absent contracts into "no construct" vs. "other agreement's date" is
  my hand judgement over the head-4000/tail-8000 window of each; a date-shaped blank buried in
  the middle of a long contract would have been missed by the sweep.
- The Handbook is paraphrased throughout; nothing is quoted.
