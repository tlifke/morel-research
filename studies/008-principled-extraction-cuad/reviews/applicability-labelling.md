# Applicability labelling — LLM-labelled, frozen, D-21 screened

Written 2026-08-16 by Claude Code (assistant), study 008, workstream inv 003
(`investigations/003-applicability-ground-truth`), under **D-24**.

Artifact: `principles/applicability/frozen/applicability-app-2026-08-16.json`
(plus a `.scored.json` variant carrying only the D-21 survivors).
Pipeline and prompts: `principles/applicability/`.

**4,498 judgements over 100 contracts** (`harness_val` 40 + `principle_train`
60) × 12 categories × the 10 working-set principles in scope. `test` was never
loaded; `model_train` was not touched. Labeller: `claude-opus-5`, prompt
`applicability_v2`, `kind: llm`, **gold visibility: none**.

---

## 1. D-21 screening — the pre-model table

This is the `{applicable, not applicable} × {gold present, gold absent}` table
D-21 requires, populated **at generation time** over all 100 contracts. Verdict
is on the union of the two splits; the per-split and untruncated-only tables are
in `frozen/screening.json` and agree with it in every case.

| id | scope | n | app×present | app×absent | not×present | not×absent | rate | phi | verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| w01 | all 12 | 1200 | 515 | 179 | 41 | 465 | 0.578 | +0.655 | **pass** |
| w02 | all 12 | 1200 | 246 | 87 | 310 | 557 | 0.278 | +0.342 | **pass** |
| w03 | Governing Law | 100 | 71 | 8 | 12 | 9 | 0.790 | +0.355 | **pass** (near-degenerate warning) |
| w04 | Agreement Date | 100 | 90 | 10 | **0** | **0** | 1.000 | n/a | **FAIL — degenerate_universal** |
| w05 | Agreement Date | 100 | 19 | 9 | 71 | **1** | 0.280 | −0.460 | **pass** |
| w06 | Agreement Date | 100 | 51 | 10 | 39 | **0** | 0.610 | −0.267 | **pass** (warning) |
| w07 | Minimum Commitment | 100 | 27 | 42 | 4 | 27 | 0.690 | +0.262 | **pass** |
| w08 | MC + Volume Restriction | 200 | 41 | 88 | 4 | 67 | 0.645 | +0.300 | **pass** |
| w09 | RPS + MC | 200 | 48 | 72 | 14 | 66 | 0.600 | +0.238 | **pass** |
| w10 | all 12 | 1200 | 107 | 16 | 449 | 628 | 0.102 | +0.276 | **pass** |

**Nine of ten pass. One fails, and it fails for a new reason.**

- **w04 (exactly one Agreement Date, date text alone) is disqualified**: the
  labeller called it applicable on **every** Agreement Date decision in the
  corpus. Both `not applicable` cells are structurally empty. A principle that
  applies to 100% of its scope cannot localise an effect and its citation metric
  measures nothing — the same defect the pilot recorded for the `p05` control.
  This is *not* the pilot's failure mode: w04's regex (`p07`) failed D-21 by
  gating on gold presence (phi = 1.00). Under LLM labelling the gate is gone and
  the record fails on degeneracy instead. Both verdicts are "unusable as a
  scored applicability trigger"; the diagnosis differs, and the LLM one is the
  honest one, because w04 genuinely does bear on every Agreement Date decision.
- **w03 carries a near-degeneracy warning** at 0.790 in scope. It is scoped to a
  single category that nearly every contract has, so this is close to "Governing
  Law is hard", which is a weaker claim than "this principle selects".
- **w05 and w06 have an empty or near-empty `not applicable × gold absent`
  cell** and negative phi. Their off-diagonals in the D-21 sense are populated,
  so they pass, but the pattern is worth naming: *not applicable ⇒ gold present*
  in this sample. The labeller is, in effect, predicting absence when it says
  these absence principles are live. That is legitimate — they are absence
  principles — but the citation metric built on them will correlate with the
  answer, and a mediation coefficient computed on w05/w06 alone should be read
  with that in mind.

**Why gold-gating cannot happen here at all.** D-24 permits applicability to
read gold. This pipeline declines that permission: the labeller sees contract
text and the CUAD one-line category definition, and no gold annotation — its
own or any other category's. So the pilot's dominant failure (13 of 23 round-2
checkers failed separability, ten of them gold-presence-gated) is structurally
impossible rather than screened for after the fact. What screening now tests is
the residual question — degeneracy and de-facto correlation — which is what it
found in w04.

---

## 2. LLM vs regex — the direct test of D-24's premise

D-24's premise is that most pilot failures were failures of the **checker**, not
the principle: lexical instruments doing semantic work. Nine of the ten
working-set principles have at least one round-2 regex counterpart. Running both
over the same 100 contracts and the same decisions:

| principle | regex | n | LLM app. | regex app. | both | LLM-only | regex-only | disagree |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| w01 | p22 | 900 | 448 | 301 | 280 | 168 | 21 | **0.210** |
| w01 | p10 | 100 | 96 | 63 | 63 | 33 | 0 | **0.330** |
| w02 | p18 | 1200 | 333 | 24 | 24 | 309 | 0 | **0.258** |
| w02 | p23 | 1200 | 333 | 24 | 24 | 309 | 0 | **0.258** |
| w03 | p06 | 100 | 79 | 57 | 53 | 26 | 4 | **0.300** |
| w04 | p07 | 100 | 100 | 90 | 90 | 10 | 0 | **0.100** |
| w05 | p04 | 100 | 28 | 10 | 9 | 19 | 1 | **0.200** |
| w06 | p02 | 100 | 61 | 2 | 2 | 59 | 0 | **0.590** |
| w07 | p14 | 100 | 69 | 29 | 24 | 45 | 5 | **0.500** |
| w08 | p13 | 200 | 129 | 156 | 113 | 16 | 43 | **0.295** |
| w09 | p11 | 100 | 92 | 53 | 53 | 39 | 0 | **0.390** |
| w09 | p15 | 200 | 120 | 28 | 19 | 101 | 9 | **0.550** |
| w09 | p01 | 100 | 92 | 13 | 13 | 79 | 0 | **0.790** |
| w10 | — | — | — | — | — | — | — | no regex checker exists |

Disagreement runs **10% to 79%**, median ~30%. The two instruments are not
measuring the same thing, and the direction is almost entirely one-sided:
**the regexes under-fire.** In 8 of 13 comparisons `regex_only` is 0 or 1 — the
regex's applicable set is a near-subset of the LLM's.

### The regexes also fail D-21 on this corpus, and the LLM labels do not

Same 100 contracts, same decisions, screening applied to the regex's own
applicability:

| principle | regex | declared dependency | regex screening verdict | regex phi |
|---|---|---|---|---:|
| w01 | p22 | gold_presence | **fail** — gold-presence-gated | **+1.000** |
| w01 | p10 | gold_span_content_own | **fail** — gold-presence-gated | +0.435 |
| w02 | p18 / p23 | gold_span_content_own | **fail** — gold-presence-gated | +0.154 |
| w03 | p06 | instance_only | pass | +0.467 |
| w04 | p07 | gold_presence | **fail** — gold-presence-gated | **+1.000** |
| w05 | p04 | instance_only | **fail** — empty applicable×absent cell | +0.111 |
| w06 | p02 | gold_absence | **fail** — gold-absence-gated | −0.429 |
| w07 | p14 | instance_only | pass | +0.239 |
| w08 | p13 | instance_only | pass | +0.257 |
| w09 | p11 / p01 | instance_only | pass | +0.328 / +0.384 |
| w09 | p15 | gold_span_content_other | pass | +0.353 |

**Six of thirteen regex checkers are disqualified on the same decisions where
all ten LLM-labelled principles except w04 qualify.** Two show phi = +1.00, the
arithmetic signature of a gold gate rather than evidence of anything — exactly
as recorded in `working_set.yaml`, now reproduced on a 100-contract corpus
rather than the 40-contract one. Note `p04` (w05): declared `instance_only` in
the round-2 footprint, it nevertheless produces an empty `applicable × gold
absent` cell here, because it fires on only 10 of 100 contracts and all ten are
gold-present. Separability by construction is not separability in practice at
small firing rates.

### What the disagreements actually are

The interesting output is *why* they differ. Sampling from
`frozen/regex_comparison.json`:

**w03 / p06 (Governing Law: venue and arbitration are not responsive).** The
regex looks for a venue/arbitration cue in the contract. The LLM adds 26
decisions where the competing clause is a *jury-waiver* or a *personal
jurisdiction consent* sitting in the same paragraph as the true governing-law
sentence — "consents to submit itself to the personal jurisdiction of the Court
of Chancery", "Section 20. Waiver of Trial by Jury". These are precisely the
confusions the principle exists to resolve and the lexicon has no entry for
them. In the other direction the regex fires on 4 decisions where the LLM sees a
governing-law subsection standing alone with nothing competing — the regex
cannot tell "a venue clause exists" from "a venue clause competes".

**w07 / p14 (a floor binds whichever party).** The largest one-sided gap, 45
LLM-only. `working_set.yaml` already predicted it: the regex approximates "the
obligated party is not the purchaser" with a
supply/deliver/provide/share/allocate alternation and misses
performance/effort/revenue floors. The LLM's added cases are exactly that class
— "Newegg shall remain responsible ... for the full payment ... for Contract
Year 1 and Contract Year 2" (a guaranteed *payment* floor), "Sponsor shall
provide Club with food, beverage and serving products ... equal to the following
Annual Trade Value" (a supplier-side floor stated as a value, not a verb). This
is D-20's finding about d04 reproduced by a different instrument.

**w09 / p01 (79% disagreement, the largest).** `p01` fires on 13 of 100
decisions; the LLM on 92. `p01` is `p11`'s regex with an administration
prefilter, and it is testing for lexical variability markers that
`working_set.yaml` measured as absent from 45% of gold spans. The LLM instead
labels the decision applicable whenever a payment clause exists whose arithmetic
has to be examined — "per copy fees", "€500 per hour" — which is what the
principle actually says. The regex is not a weaker version of the principle; it
is a different, much narrower rule.

**w08 / p13 is the one comparison running the other way** (43 regex-only vs 16
LLM-only). `p13` fires on any quantity token near a bound cue — 156 of 200
decisions, the "near-degenerate frequency" the round-2 footprint flagged. The
LLM declines most of those and picks up cases the regex misses, like a consent
requirement above a €5,000 ceiling that is a *threshold direction* question and
not a quantity-token question. Here the LLM is the more selective instrument.

**w02 (dual labelling) is the clearest case of a checker measuring the wrong
thing.** Both regexes fire on 24 of 1200 decisions and both are gold-gated: they
detect *that gold assigned one passage to two categories*, which is the answer.
The LLM labels 333 decisions where a passage plausibly answers two targets —
"This Reseller Agreement is entered as of this ___ day of ______, 2004
('Effective Date') by and between ..." answers agreement date, effective date,
document name and both party targets at once. The regex could not have found
that without gold, and with gold it is not an applicability test.

**Read against D-24's premise: supported, with one qualification.** The pilot
checkers were doing semantic work lexically, and the disagreements are dominated
by semantic conditions a regex has no representation for. The qualification is
w08: a lexical trigger can also be *too broad*, and there the LLM's value is
restraint rather than reach.

---

## 3. What an LLM labeller cannot do here

Stated plainly, because the artifact is frozen and load-bearing.

1. **It cannot tell "the principle governs this decision" from "this category is
   hard here" for a scope-1 principle.** w03 at 0.790 and w04 at 1.000 are the
   evidence. When a principle is scoped to one category and that category is in
   nearly every contract, the labelling question degenerates. **This is a finding
   about the principles, not about the labeller**, and it is the two-tier input
   inv 006 needs: w04 is prompt-tier material (it may well help the model) and is
   not scorable as a citation target.
2. **It has no ground truth of its own.** The agreement column below is empty
   until Tyler adjudicates. Everything above is *internal* structure —
   screening, disagreement, degeneracy — none of which certifies that the labels
   are right.
3. **It is not reliable on truncated contracts.** 19 of 100 contracts exceed the
   80,000-character cap and were shown head + tail. The labellers correctly
   flagged the affected questions and answered `not_applicable` at `low`
   confidence, per the prompt's instruction, so those rows are *missing data
   recorded as negatives*. `screening.json` carries an `untruncated_only`
   sensitivity table for every principle; no verdict changes, and phi moves by at
   most 0.04. But the applicable rates on truncated contracts are biased low and
   the frozen file has no field to say so.
4. **23% of its `applicable` labels are `low` confidence** (985 low of 4,498
   overall). The prompt asked for honest low use and got it; a downstream
   consumer treating every label as equally firm is over-reading the file.
5. **It cannot judge compliance, and this pipeline never asks it to.** D-4 is
   untouched: nothing here sees model output, and the scoring path reads only the
   frozen JSON.

### Principles that are not reliably labellable

- **w04** — labellable but degenerate (see above). Fails D-21. Prompt tier.
- **w03** — labellable, near-degenerate. Usable but its citation metric will be
  weak; worth re-scoping or accepting a low-power test.
- **w01** — the hardest genuine call in the set. Its applicability rests on
  "would a span-boundary rule change what is emitted", which is undefined when
  the category is absent. The first prompt version (`applicability_v1`, run over
  5 contracts) contained a bullet asserting that boundary principles bear
  regardless of presence; the labeller flagged it as contradicting the evidence
  requirement, and it did. `applicability_v2` replaces it with an explicit rule
  (a boundary principle cannot bear on a category the document is silent on).
  The resulting phi of +0.655 is the honest consequence: **w01's applicability is
  intrinsically correlated with presence**. It passes D-21 with 179 applicable ×
  gold-absent decisions, but it is the record whose mediation estimate is most at
  risk of being partly a presence effect.
- **w02, w07, w08, w09, w10** — labellable, non-degenerate, semantically live.
  These are the records the LLM labeller earns its place on.

---

## 4. Spot-check — built, awaiting adjudication

- Artifact: `reviews/applicability-spot-check.html` (114 items, 69 contracts,
  all 12 categories, every principle).
- Sampling: `principles/applicability/spot_check.py`, seed 8003, **balanced by
  (principle × model label)**, 6 applicable + 6 not-applicable per principle.
  w04 supplies only 6 because it has no `not_applicable` rows — hence 114 and
  not 120.
- Design: each item shows the principle, the category and its definition, and an
  excerpt window around the model's evidence quote, with the model's own answer
  **behind a disclosure element** so the adjudicator decides first. Gold is not
  shown — the labeller did not see it and the adjudicator should not either, or
  the agreement number stops measuring the same function.
- Record verdicts in `principles/applicability/frozen/spot_check_labels.yaml`
  (`applicable` / `not_applicable` / `unclear`), then
  `uv run python spot_check.py --score`, then re-run `freeze.py` to stamp the
  `spot_check` block into the frozen artifact.

**What the estimate will be worth.** At n = 114, a 95% Wilson interval is about
±6.5 points: agreement of 0.85 lands at [0.774, 0.905], 0.90 at [0.835, 0.945].
Per *label arm* (n = 57) it is about ±10 points. **Per principle (n = 12) the
interval is roughly ±20 points and is not worth reporting as a number** — those
cells are for finding which principle the disagreements concentrate in, not for
estimating its accuracy.

Because the sample is balanced rather than drawn from the population, the raw
figure is *not* the artifact's error rate. `--score` therefore reports three
things: agreement on the balanced sample, agreement within each label arm, and a
prevalence-weighted estimate using the population applicable rate of 0.386.

Until then, `spot_check` in the frozen file is `{}` — **unavailable, not zero**,
the same discipline D-25 imposed on the citation block.

---

## 5. How it was run, and what is pinned

```
principles/applicability/
  config.yaml            version, splits, labeller pin, caps, thresholds, lineage map
  prompts/applicability_v1.md, applicability_v2.md   pinned, versioned prompts
  render.py              one prompt file per contract, 45 questions each
  freeze.py              ingest -> validate -> screen -> frozen artifact
  screen.py              D-21 pre-model screening
  compare_regex.py       LLM vs round-2 regex checkers
  spot_check.py          sample, HTML, and --score with Wilson CIs
  work/                  gitignored: rendered prompts and raw responses carry contract text
  frozen/                the artifact, screening, regex comparison, spot-check sample
```

Reproduce with `uv run python render.py`, run the labeller, then
`uv run python freeze.py && uv run python compare_regex.py`.

**Pins.** Model `claude-opus-5`, prompt `applicability_v2`, one question grid
(45 = 10 principles × their in-scope categories), fixed for all 100 contracts.
The labeller ran as Claude Code **subagents**, not through the API, because no
provider key exists in this environment; `config.yaml` records that honestly —
the alias requested was `opus` and the harness returns no resolved model-id
string, so the stamp is a declaration, not a value read back. An API-key run
would be strictly better provenance and the config has a slot for it.

**Validation at ingest.** Every `applicable` answer must carry a verbatim quote,
checked whitespace-insensitively against the contract body **or the title line**.
Title quotes are accepted deliberately: the prompt prints `Title:` (and, per
D-25, no longer prints `Id:`), and **w10 is the principle that governs sourcing
values from the title**, so a title-sourced quote is the correct evidence for a
w10 judgement rather than a validation failure. **2 of 4,500 judgements failed
validation** (0.04%) — one quoted the literal `Title: ` prefix, one paraphrased —
and were dropped, which the schema renders as "no principle applies". Both are
listed in `work/problems.json`.

### Judgement calls a reviewer should check

1. **Gold visibility set to none.** D-24 allows the labeller to read gold; this
   pipeline does not let it. It buys structural D-21 compliance and costs the
   ability to label principles that genuinely need another category's gold. w02
   is the case: its round-2 checkers used gold overlap, and the instance-only
   restatement ("a passage that plausibly answers two targets") is the rebuild
   `working_set.yaml` itself prescribes — but it is a different test.
2. **Everything is decision-scoped; `__instance__` is never used.** Citation
   scoring reads only per-target keys, so instance-scoped labels would be
   invisible to it. w02 and w10 could arguably be instance-scoped.
3. **Disqualification does not delete labels.** The full artifact carries all ten
   principles; `.scored.json` carries the nine survivors. Which file the runner
   loads is a decision for inv 005/006, not this pipeline.
4. **The 80,000-character cap** (head 50k + tail 30k) was chosen to keep 81 of
   100 contracts whole. It is a labelling-time cap only and has no relationship
   to the models' context windows in the trial grid.
5. **`common.py` re-implements `load_category_definitions`** rather than
   importing it from `harness/envs/cuad_env.py`, which is not importable from
   outside the harness package. The logic is copied verbatim, including the
   deliberate omission of the CSV's `Answer Format` column (D-25). If that loader
   changes, this copy must change with it.
6. **One contract was labelled twice** by concurrent labellers
   (`PrudentialBancorpInc_...Endorsement Agreement`); the later write won. The
   two runs differed (7 vs 10 applicable of 45), which is a free, unplanned
   data point on labeller variance — and a reason not to treat any single label
   as deterministic.

---

## 6. What this changes downstream

- **Citation scoring can now run.** `ApplicabilitySource.load()` accepts the
  artifact unchanged and `assert_ready(["C3"])` passes, so C3 stops reporting
  `available: false`. It must load the frozen file and never a model.
- **inv 006's two-tier split has its first real input**: w04 to prompt-tier
  (degenerate applicability), w03 flagged as low-power, w01 flagged as
  presence-correlated, and w02/w07/w08/w09/w10 as scorable candidates — subject
  to the human spot-check and to a *compliance* checker existing, which is a
  separate question this pipeline does not answer.
- **The compliance half stays barred.** Nothing here weakens D-4. Where
  compliance cannot be checked programmatically, the principle stays prompt-tier
  and is not scored.
- **The post-model D-21 table is still owed.** `{passes, fails} × {right,
  wrong}` needs model outputs and must be computed after the first real run, per
  D-21's own refinement.
