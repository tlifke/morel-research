# Round-2 cross-source validation

Each of the 23 round-2 candidates was checked against the derivation source it did
*not* come from.

- `atticus_guidelines` candidates (12) were tested against CUAD gold in **dev + ft_train**
  — 404 contracts, 4,052 gold spans over the 12-category subset. Holdout was never loaded.
- `data_mined` candidates (11) were checked against the **Atticus CUAD Labeling Handbook**
  (95 pp., read in full for the relevant chapters) and the **CUAD master clause list**
  shipped with the dataset (`data/raw/category_descriptions.csv`, CC BY 4.0).

The Handbook is copyrighted and non-redistributable. Everything below is paraphrase;
no Handbook prose is reproduced. Category descriptions are quoted, being CC BY 4.0.

| Direction | Corroborated | Contradicted | Silent |
|---|---|---|---|
| `atticus_guidelines` → data | 8 | 4 | 0 |
| `data_mined` → guidelines | 5 | 4 | 2 |
| **Total** | **13** | **8** | **2** |

Machine-readable results: `principles/pilot/round2/cross_source_validation.yaml`.

---

## Contradicted (8)

### p08 — the `<omitted>` marker does not exist in CUAD v1
**Guidelines → data.** The Handbook convention is real (ch. 1, pp. 5–6: fragments joined
by a marker, with worked subsection and definition examples). It describes the internal
labelling tool, and it does not survive into the release. **0 of 4,052** gold spans contain
`<omitted>`, and the string occurs **0** times in the 404 contract texts. The released
SQuAD-format data stores every annotation as a contiguous character range, so a
multi-fragment annotation arrives as *separate spans under the same category*.

Consequences beyond this record: a checker keyed on the marker can never fire; a model
instructed to emit it fails verbatim matching on every such span; and the lead-in half of
**p22** is unverifiable in this corpus for the same reason.

### p20 — post-signature attachments *are* annotated
**Guidelines → data.** The principle says exhibits, schedules and annexes after the
signature block are out of scope. Locating the execution block and the first attachment
heading after it, **113 gold spans** fall inside the attachment, across the **103**
contracts where that configuration exists:

| Category | Spans in post-signature attachments |
|---|---|
| Minimum Commitment | 26 |
| Cap On Liability | 21 |
| Revenue/Profit Sharing | 15 |
| License Grant | 14 |
| Anti-Assignment | 13 |
| Volume Restriction | 9 |
| Governing Law | 6 |
| Exclusivity | 4 |
| Expiration Date | 4 |
| Agreement Date | 1 |

The guideline citation should also be treated as unverified: the cited "Handbook ch. 1,
scope of the labelling task (p. 3)" is the table of contents, and no scope-of-annotation
section exists. The one attachment rule in the Handbook (p. 7) concerns not labelling
"Exhibit"/"Annex" as part of the *Document Name* — the heading, not the content.

A model following this principle would abstain on material CUAD scores as present,
concentrated in the pilot's confusable trio.

### p21 — the introductory date wins, not the signature-page date
**Guidelines → data.** Restricting to the exact conflict the principle governs (a date
literal appears in or after the execution block), gold takes the **earlier intro/cover
date in 138 of 151 contracts (91.4%)**; the signature-block date in 13. Across all present
contracts the first gold span precedes the execution block in **244 of 263** locatable
cases (92.8%).

The Handbook agrees with the data and not with the principle: introductory paragraph
first, cover page if none there, and only then the later of the two signature dates
(p. 8). The principle's second limb also misreads that page — "as of" is named there as
execution wording to keep *out of the span*, not as grounds to reject the intro date,
which the same page requires to be labelled under both Agreement Date and Effective Date.

p21 is directly opposed to **p07**, which encodes the correct order and is corroborated at
98.4%. Locking both would have them fight on the same instances.

### p12 — the single-value categories take more than one span
**Guidelines → data.** Multi-span annotation is systematic and scales with the category's
structural looseness:

| Category | Present | Exactly 1 span | >1 span |
|---|---|---|---|
| Agreement Date | 374 | 368 | 6 (1.6%) |
| Governing Law | 351 | 332 | 19 (5.4%) |
| Expiration Date | 332 | 292 | 40 (12.0%) |

Overall the principle holds on 992 of 1,057 present decisions (93.8%) and fails on 65.
The Handbook independently instructs the opposite for the middle case: where a contract
has two governing-law provisions, both are labelled and both answers recorded (p. 12).

This is a rule stated too absolutely rather than a wrong intuition. Narrowed to Agreement
Date it is sound — and already covered by p07.

### p17 — the conflicts-of-law tail belongs *inside* the Governing Law span
**Data → guidelines.** Two Handbook rules converge against the principle: the span unit is
one sentence, period to period (ch. 1, p. 4), and Governing Law asks for the responsive
sentence with the jurisdiction typed into a separate *answer* field (p. 12). A "without
regard to…" tail sits inside that sentence. The clipping the principle wants belongs to
the answer field, which the CUAD extraction task does not expose as a span.

The corpus agrees with the Handbook: **85 of 370** gold Governing Law spans (23.0%)
include a conflicts tail, and where such a tail exists within the span or the 250
characters after it, it is inside the span in **85 of 86** cases (98.8%).

Note that the mining evidence contradicts the principle it was used to justify —
pair-0029 and pair-0030 both carry the tail *inside* the gold span.

### p14 — the published Minimum Commitment definition is narrower than practice
**Data → guidelines.** The only guideline statement on this category defines it around the
buyer: *"Is there a minimum order size or minimum amount or units per-time period that one
party must buy from the counterparty under the contract?"* (CC BY 4.0). Supplier-side
supply floors, guaranteed-payment floors and capacity-access floors fall outside that
wording, and there is no Handbook chapter to soften it.

The corpus sides with the principle: only **77 of 334** gold Minimum Commitment spans
(23.1%) contain a purchase verb at all, and **30 of 334** (9.0%) state a minimum bound on
a supply/provide/allocate/access obligation with no purchase verb anywhere in the span.

This is the highest-value divergence in the `data_mined` half, and it runs *opposite* to
p02's: here the documentation is narrower than practice, and a model following the
published definition would under-extract roughly a tenth of Minimum Commitment gold.

### p02 — the near-miss date is labelled, not abstained on
**Data → guidelines.** The Handbook directs the opposite for exactly the headline case:
where a date in the introductory paragraph is defined as the Effective Date, it is
labelled under **both** Agreement Date and Effective Date (p. 8, restated with a worked
contract at pp. 14–15). The Term chapter adds that where a contract has no Effective Date,
the Agreement Date substitutes — the two are treated as interchangeable near-misses, not
as grounds for abstention.

Practice follows the documentation: **151** contracts have their gold Agreement Date span
sitting inside effective-date wording and are labelled anyway; only **9** gold-absent
contracts have effective-date wording near a head-of-document date (94.4% the documented
way). Those 9 — IOVANCE being the mined one — are real abstentions and worth reporting as
divergence, but they are the minority behaviour.

The mined support is also thin: pair-0027's absent side contains no date at all, so it
cannot evidence a near-miss rule.

### p15 — a floor adds the second label, it does not switch labels
**Data → guidelines.** The *exclusivity* is what fails. The Handbook makes a payment
calculated as a share of the other party's revenue responsive with no floor exception
(pp. 87–88), excludes payments in fixed amounts (p. 89) — so adding a floor to a
percentage does not remove the percentage — and settles it directly in ch. 1: a sentence
responsive to more than one label is labelled under each (p. 5).

Both cited royalty-with-floor sentences are labelled under **both** categories in gold
(2 of 2): JOINTCORP's *"seven percent (7%) of the gross revenues … with a minimum monthly
amount of $700.00"* and VirtuosoSurgical's *"minimum annual royalties"*.

Salvageable as a non-exclusive rule — which is p18/p23 applied to this pair. As written it
would score the correct double-label as a violation.

---

## Silent (2)

Both are structural, and neither is evidence against the principle.

### p03 — amendments and restatements
**Data → guidelines.** The Handbook has no amendment or restatement section, and its rules
are entirely document-internal: responsiveness is decided from the sentence in front of
the annotator, never from whether the language originates elsewhere. Amendments appear
only incidentally, as an ordinary annotation target (p. 7). The nearest adjacent rule
points mildly the other way — a clause cross-referencing another agreement's governing-law
provision is still labelled (p. 12) — but it addresses cross-references, not reproduction.

*Independent weakness for the reviewer:* the cited pairs are not amendment pairs.
pair-0031/0032/0035 contrast VARIABLESEPARATEACCOUNT (2014) with SEPARATEACCOUNTIIOFAGL
(2011) — two separate EDGAR filings of the same form capital-maintenance agreement,
neither amending the other. They evidence near-duplicate annotator disagreement.

### p19 — document furniture inside spans
**Data → guidelines.** The Handbook's span-construction rules cover subsections, lead-ins,
definitions and the read-together case, and never mention the EDGAR artefacts
(confidential-treatment legends, `Source:` filing lines, page numbers) that the released
text interleaves. The one adjacent rule is category-local and covers only the standalone
half: footer dates are not labelled, because on EDGAR the footer carries the filing date
(pp. 8, 16). Nothing addresses furniture falling *inside* a passage being labelled.

Structural reason: the Handbook describes annotating contracts, not the EDGAR text dumps
CUAD was built from. The behaviour is a property of span capture, not of any documented
convention. Support is a single pair (pair-0033) — though the claim is plainly visible in
that span, which swallows a confidential-treatment legend and a `Source: GLU MOBILE INC,
S-1/A, 3/19/2007` line mid-sentence.

---

## Corroborated (13)

### Guidelines → data (8)

| id | Claim | Rate in dev + ft_train |
|---|---|---|
| p01 | Revenue/Profit Sharing needs entitlement, not administration | 327 / 329 spans (99.4%); administration-only 2 (0.6%) |
| p04 | A blank/redacted agreement date is still extracted | **17 / 17 contracts (100%)**; 26 gold spans are blank/redacted shells |
| p05 | Every category gets an explicit ruling per contract | 4,848 / 4,848 decisions (100%) |
| p06 | Governing Law excludes venue and arbitration | 366 / 370 spans (98.9%); venue-only 4 (1.1%) |
| p07 | One Agreement Date, date text only, not header/recital | 368/374 single-span (98.4%); 373/380 free of execution wording (98.2%); 0/374 in recitals |
| p11 | Revenue/Profit Sharing must vary with revenue | exclusion side 325 / 329 (98.8%) |
| p22 | Spans are complete sentences, period to period | 2,413 / 2,921 (82.6%) |
| p23 | One sentence can carry several category labels | 118 overlapping pairs on 76 / 404 contracts; 90 verbatim shared span texts |

Two of these deserve a second look rather than a tick:

- **p04 resolves the LOUD FLAG** in its own checker sketch. The study plan assumed CUAD
  marks blank-date contracts gold-*absent* and that following the Handbook would cost
  answer accuracy. It does not — gold labels all 17, and 26 gold spans are themselves empty
  date shells (`this ___ day of _________, 2004`). Compliance and correctness point the
  same way here; there is no scoring conflict to decide.
- **p11's inclusion side is only 55.3% lexically visible** (182 / 329). That is a property
  of the proxy, not a gold violation rate — the invisible remainder is the Handbook's own
  stated extensions (agreements to enter a profit share, scope carve-outs, compensation
  clauses whose percentage lives elsewhere). Score the checker on the exclusion side.
- **p22 is corroborated as the dominant convention, not as an absolute** (17.4% fail), and
  its lead-in half cannot be tested at all — see p08.

### Data → guidelines (5)

| id | Claim | Where the guidelines say it |
|---|---|---|
| p09 | A volume ceiling needs a consequence | CUAD category description names *"a fee increase or consent requirement"* — the principle is a near-restatement of a definition it was mined without seeing |
| p10 | Extract the minimal expression | Handbook p. 8: mark the date itself, not the surrounding "dated"/"as of"/"entered into" reference |
| p13 | Threshold direction separates the two targets | The two category descriptions divide on exactly that axis — minimum-to-buy vs. exceeding-a-threshold |
| p16 | An unquantified undertaking satisfies nothing | Entailed, not stated: the Minimum Commitment definition is built entirely out of quantities |
| p18 | A passage can be extracted under several targets | Handbook ch. 1, p. 5, stated outright, with worked examples at pp. 8, 14–15, 41 |

Caveats the reviewer should carry:

- **p16 is the weakest corroboration in the set** (confidence: low) — an inference from a
  one-line definition, with no Handbook chapter behind it. The corpus complicates it:
  62 of 334 gold Minimum Commitment spans (18.6%) carry no quantity token, mostly lead-in
  fragments whose quantities live in the subsections beneath them.
- **p13's corroboration is partial.** The guidelines separate the pair on *more* than
  direction — Volume Restriction additionally requires a consequence (p09) and Minimum
  Commitment additionally names a buyer (p14). A checker keyed on direction cues alone
  will over-assign Volume Restriction to bare ceilings.
- **p10 does not generalise past its declared scope.** For Governing Law the Handbook wants
  the whole responsive *sentence*, with the jurisdiction in a separate answer field (p. 12).
- **p18 is right but its citation is not.** The miner excludes same-contract overlapping
  spans by construction (`exclude_same_contract_overlapping`), so cross-label mining is
  blind to multi-label annotation. pair-0004/0005 are the same boilerplate in two
  *different* contracts, each labelled under one category only — closer to evidence of
  annotator inconsistency than of multi-labelling.

---

## Cross-cutting observations

1. **Divergence runs in both directions.** p02 and p20 are cases where the documentation is
   *broader* than practice; p14 is the reverse, where the published definition is narrower
   than what annotators did. The two-arm design should carry named cases of each.
2. **Three records are mutually inconsistent as a set.** p07 and p21 give opposite priority
   orders for Agreement Date; p12 overlaps p07 and additionally over-reaches to Expiration
   Date, where it fails 12% of the time. At most one of p21/p07 can be locked.
3. **The `<omitted>` finding (p08) is infrastructure, not just one verdict.** It caps p22,
   invalidates any marker-keyed checker, and means the Handbook's most distinctive span
   convention is simply unmeasurable in CUAD v1.
4. **Mining evidence quality is uneven and does not track verdict.** p17 and p18 both cite
   pairs that argue against, or are structurally incapable of supporting, the principle
   they justify — yet p17 is contradicted and p18 corroborated. Citation quality should be
   reviewed separately from cross-source status.
5. **Handbook silence on Minimum Commitment and Volume Restriction is total** (0 of 95
   pages). Every guideline verdict for those two categories rests on a single line of the
   master clause list, which is why p09/p13/p14/p16 carry a range of confidences from high
   to low off the same source.
