# Decision log — study 008

Study-level decisions that outlive any one investigation, numbered `D-N`.
Investigation-local decisions stay in their own `investigation.md` and are
numbered `INV<n>-D<m>` (e.g. `INV1-D5`) so they never collide with these.

Format:

> **D-N — short title** (YYYY-MM-DD)
> What was chosen, alternatives considered, why this won.

---

> **D-1 — Task definition is present in all conditions** (2026-08-15)
> C1 gets the task definition (decision kinds, targets, one-line target
> definitions) but no principles. Alternative: a bare C0 with neither.
> Rejected — without the task definition the task is undefined and C1 stops
> being a fair baseline for "does business logic help".

> **D-2 — Full dataset, no length filtering or chunking** (2026-08-15)
> Long contracts stay in; over-context trials are recorded as
> `infeasible_at_length`. Alternative: filter to contracts that fit every
> model's context, or chunk. Rejected — H5 is specifically about where the
> system breaks with contract length; filtering assumes away the result.

> **D-3 — Official CUAD test split (102 contracts) is the final hold-out**
> (2026-08-15)
> Touched only for headline results, in both phases. Dev = ~40 contracts
> sampled from official train, stratified by length and positive-category
> count, seeded and persisted. Remaining official-train reserved for Phase 2
> fine-tuning. No contract in more than one of {dev, FT-train, holdout}.

> **D-4 — No LLM judge in the scoring path** (2026-08-15)
> Every Phase-1 and Phase-2 metric is programmatic or hand-labeled.
> Alternative: judge-scored compliance, as in studies 004/005. Rejected — a
> judge in the loop would contaminate the Phase-2 reward story, and the whole
> point is programmatic verifiability of the process.

> **D-5 — Harness is study-level, not an investigation** (2026-08-15)
> `harness/` + `plans/component-contracts.md`. Alternative: an
> `003-harness` investigation. Rejected — an investigation is a bounded unit
> with a definite end; the harness is cross-cutting and outlives Phase 1.

> **D-6 — Repository policy: manifests + scored records, not raw**
> (2026-08-15)
> See `study.md` → Repository policy. Contract text and raw model responses
> stay out of git; the instance manifest and per-trial scored records go in.

> **D-7 — Study-007 orchestration machinery is not inherited** (2026-08-15)
> No ticket system, no drain, no agent-trace/three-tier renderers. This study
> runs a deterministic trial grid, not an autonomous researcher loop.

> **D-8 — Verbatim CUAD text is usable, with attribution** (2026-08-15)
> CUAD is released under CC BY 4.0. Category definitions and guideline text may
> be quoted verbatim in prompt templates and checked-in artifacts; the
> paraphrase fallback is dropped. In exchange, attribution to The Atticus
> Project is a standing obligation on every derivative in git (manifest, prompt
> templates, principle statements) and the one-pager cites the CUAD paper.
> **Sub-question resolved 2026-08-15, unfavourably.** The *CUAD Labeling
> Handbook* is **not** CC BY 4.0. It carries `© 2021 by The Atticus Project` on
> all 95 pages, is sold for personal use, grants no redistribution or
> derivative-works license, and its access terms forbid implying Atticus
> endorsement. It is also no longer free — it moved behind a paywall between
> the 2025 and 2026 site rebuilds, and the Wayback captures never included the
> client-rendered body.
> Consequences, all binding:
> - The Handbook PDF is **gitignored** (`assets/*.pdf`, `literature/*.pdf`) and
>   must never enter this public repo.
> - **No Handbook prose is reproduced verbatim anywhere** — not in principle
>   statements, not in prompts, not in the writeup. Paraphrase only. The
>   paraphrase fallback that D-8 dropped for CUAD text is **required** for
>   Handbook-derived text.
> - Two secondary sources *are* CC BY 4.0 and quotable, and should be preferred
>   wherever they cover the same ground: the **CUAD v1 Datasheet** (§II-F,
>   §III-B carry real annotation conventions) and the archived Atticus Labels
>   page.
> - Reproducibility note for the writeup: a reader cannot obtain this source
>   for free. Say so, and lean on the Datasheet where possible.

---

> **D-9 — Model-assisted principle proposal is logged, not ambient**
> (2026-08-15)
> Contrastive-pair mining is deterministic and runs on FT-train only; proposals
> come from a pinned frontier model (`claude-opus-5`) with a pinned prompt
> version; every candidate carries evidence pointers, a checker sketch, and a
> Tyler `review` block with a required rationale. Rejected candidates are
> retained. Protocol lives in inv 002; it exists so the writeup's methods
> section can state exactly what the model contributed and what survived
> review.

> **D-10 — Two-level results store** (2026-08-15)
> `trials.jsonl` (one row per trial key) + `decisions.jsonl` (one row per
> decision). Alternative: a single trial row with nested decisions. Rejected —
> citation P/R/F1, the H4 confusion matrix, and Phase-2 reward extraction are
> all per-decision, and nesting makes them awkward to compute and impossible to
> stream. Schema in `plans/component-contracts.md`.

> **D-11 — CUAD citation** (2026-08-15)
> `hendrycks2021cuad` (arXiv:2103.06268), in
> `literature/references.bib`. Cited in the one-pager; pairs with the CC BY 4.0
> attribution obligation in D-8.

> **D-12 — Length is measured with a real tokenizer; the 4-chars/token
> planning figures are retired** (2026-08-15)
> inv 001 measured CUAD contract text at 4.70 chars/token under the Qwen3
> tokenizer (`Qwen/Qwen3-8B`, the family of the ~8B arm). The planning-time
> token figures came from `n_chars / 4` and overstated length by ~18%. Char
> figures were correct. `n_tokens` in the manifest is tokenizer-derived; any
> context-window feasibility claim must use it. Open sub-check: confirm
> `qwen3.5:8b` shares the Qwen3 tokenizer before inv 005 leans on it.

> **D-13 — Dev is stratified to holdout's length profile, not to its own pool's**
> (2026-08-15, at gate G1, before the split freeze)
> The first build stratified dev to mirror the official-train pool it is drawn
> from, which left dev systematically longer than holdout (median 8,248 vs
> 5,440 tokens). Changed: dev now matches the **holdout** length distribution.
>
> Why. Dev has exactly one job in this study — to predict how the system will
> behave on holdout before holdout is opened at G4. Every use of dev is a
> forecast: the P0 schema decision, prompt iteration, and the feasibility
> planning behind `infeasible_at_length`. All of those are length-sensitive, and
> H5 is *specifically* a claim about degradation with contract length. A dev set
> 50% longer than holdout would have biased every one of those forecasts in the
> same direction — pessimistic on feasibility, pessimistic on long-context
> failure — and we would not have found out until the holdout was already open.
> Being representative of the training pool buys us nothing we need; being
> representative of the evaluation target buys us the entire purpose of a dev
> set.
>
> What it costs, stated plainly. Dev is now a deliberately **non-representative**
> sample of official-train. It cannot be used to characterize the training pool,
> which matters for Phase 2, where FT-train — not dev — is the pool of record.
> Matching holdout's profile also means drawing more heavily from the short end
> of official-train, so the short buckets sample a smaller effective pool and
> may show less contract diversity than their count suggests.
>
> Stratification priority is now explicit: **length bucket first** (matched to
> holdout's proportions), positive-category count balanced **within** each
> length bucket as a secondary key. With n=40 the two keys cannot both be
> satisfied exactly; length wins, because length is the axis a hypothesis rests
> on and positive-count is not.
>
> Made at G1 by design — this is the last point at which splits are cheap to
> change. After the freeze, this decision is not revisited.

> **D-14 — One decision per category, not per span** (2026-08-15)
> A contract yields exactly **12 decisions**, one per subset category: an
> `Extraction` carrying a **list** of spans, or an `AbsenceClaim`. Alternative:
> one decision per span. Rejected on three grounds found by inspecting real
> gold (see `reviews/sample-contracts.html`): (1) CUAD marks each copy of
> repeated verbatim boilerplate, and since `Extraction` carries text rather
> than offsets, a model emitting the passage once is indistinguishable from one
> that missed a duplicate — unscoreable at span granularity; (2) the citation
> P/R/F1 denominator would move with the model's own output, making C3 numbers
> non-comparable across models; (3) absence is inherently category-level, so
> span-level extraction would make the two decision kinds asymmetric — and the
> symmetry is the point, since absence rulings are where principles bite
> hardest.
> Consequence: `Extraction.text: str` becomes a span list, and span-F1
> aggregates *within* a decision (soft precision/recall over the span sets).
> Citations attach to the category-level decision.

> **D-15 — Gold is left untouched; the noise floor is measured and reported**
> (2026-08-15)
> Inspection found demonstrably bad gold: at least one plain mislabel
> (`"Business."`, nine characters), spans labeled by neighbourhood rather than
> content, and — worst — gold spans **split around embedded OCR page furniture**,
> so one legal thought becomes two spans and a model emitting the coherent
> passage is penalised while one reproducing the scanning artifact is rewarded.
> We do **not** correct gold and do **not** normalize the text before scoring.
> Instead: hand-audit a sample, estimate the fraction of spans affected, and
> report it as a **ceiling on achievable span-F1** in limitations.
> Why. Every condition sees the same corrupted gold, so condition *contrasts* —
> which is what H1 actually claims — remain valid. Correcting gold would fork us
> from the CUAD literature and make our absolute numbers incomparable, and
> normalizing text would shift every offset in the manifest. The noise is a
> constant added to all arms, not a confound between them. It does mean no arm
> can reach F1 = 1.0, and the writeup must say so rather than let a reader read
> the ceiling as model failure.
>
> **Partially reframed 2026-08-15.** The CUAD Datasheet documents that
> annotators *deliberately* left confidential legends, footers and page numbers
> inside labelled sentences. So a share of what inspection read as gold
> corruption is **documented convention**, and the true noise floor is smaller
> than the raw defect count suggests. The split-around-furniture cases still
> stand as genuine hazards. The audit must separate "violates the documented
> convention" from "follows a convention we find awkward" — otherwise the
> published ceiling overstates the corruption.
>
> **New defect class, found by contrastive mining 2026-08-15**:
> **near-duplicate documents with inconsistent gold.** CUAD contains near-twin
> contracts (an agreement and its amendment; two filings of substantially the
> same contract) where an identical clause is annotated in one and left
> unannotated in the other — observed on NETGEAR, AIG and Excite pairs, and on a
> blank signing date. This is a defect in **absence labels specifically**, the
> decision type this study cares most about, and it is invisible to any
> single-document inspection.

> **D-16 — Run without repair; record reasoning rather than constrain it**
> (2026-08-15, resolving the cross-model assistance-parity question)
> `max_repair_attempts = 0`. A parse, schema, or coverage failure is
> **terminal**. The machinery stays built and tested so re-enabling is a config
> change, not a rewrite.
> Why. The structured-output probe showed the repair need was largely a *prompt
> artifact*: with the schema serialised into the prompt as the harness already
> does it, all three models returned 20/20 strict JSON and 19–20/20
> schema+coverage valid. Repair was buying little while costing comparability,
> since models needed it in unequal amounts and repair is assistance.
> Two consequences, both improvements:
> 1. The **score-twice design collapses** — with no repair, attempt 0 is the
>    final attempt, so there is no assisted variant and therefore no
>    survivorship caveat at all. The `first_attempt` block stays emitted so the
>    schema survives repair returning, but it is not a second measurement.
> 2. **The parse-failure rate, broken down by stage** (`json_decode` /
>    `schema_validation` / `coverage`), *becomes* the clean unassisted
>    conformance result — per condition, per model, per length bucket. This is
>    the measurement Tyler asked for when he pushed back on the conformance
>    question, and removing repair is what makes it uncontaminated.
> On the other half of parity: output budget stays **generous and unconstrained,
> not tuned per model**. Native reasoning verbosity is recorded, not clipped —
> the traces are expected to be independently interesting.

> **D-17 — Gold defect classes are counted both ways** (2026-08-15)
> Three classes sit on the boundary between "gold is wrong" and "gold is
> inconsistent / the task is just hard": `redaction_dependent`,
> `cross_category_overlap`, and `inconsistent_across_duplicates`. Rather than
> rule now, every audit report carries **both** `defect_rate` (inclusive) and
> `defect_rate_excluding_unruled`, plus the per-class breakdown. The published
> span-F1 ceiling is stated as a range with the classification made explicit,
> so a reader can recompute under their own reading.

> **D-18 — The duplicate census runs by default, with multiple detectors**
> (2026-08-15)
> Near-duplicate gold inconsistency is enumerated exhaustively rather than
> sampled (prevalence ~0.3%: a random n=120 draw would contain ~0.4 cases).
> The census is tagged and **excluded from every rate** — it is a targeted
> enumeration of suspected defects, not a draw, and pooling it would bias the
> noise floor upward. More than one matcher is run (exact-normalised, plus the
> contrastive miner's idf-weighted Jaccard) with per-detector counts reported
> side by side, on the principle that the detectors should be compared and the
> unhelpful ones dropped later rather than chosen blind now. Exact-only
> prevalence is a **lower bound**.

> **D-19 — The blank-signing-date assumption is falsified; documented rule and
> gold agree** (2026-08-15, `reviews/agreement-date-check.md`)
> The plan assumed CUAD marks a contract gold-absent for Agreement Date when
> the signing date is literally blank. Measured over dev + ft_train (408
> contracts, holdout untouched): **30 of 377 positives (8%) have a blank or
> redacted date as their gold span**, and **zero** gold-absent contracts have a
> clean date-shaped blank belonging to the agreement. Gold follows the
> Handbook.
> **There is no compliance-vs-correctness inversion on the absence principle** —
> following the documented rule is also how to be right. That was the risk
> worth checking, and it did not materialise.
> The line CUAD actually draws is **not** intro-vs-signature-block (3 labelled
> blanks sit at relative position ≈0.99): it is *whether a date-shaped
> construct exists*. A month, a year stub, or a `day of` phrase with components
> blanked gets labelled; a bare `Date:` / `Dated:` slot gets ruled absent —
> consistent across 4+ independent contracts, so a convention rather than noise.
> Consequences: keep g08, drop its warning flag, and tighten its applicability
> to require a date-shaped construct (otherwise it fires on bare `Date:` slots
> and *manufactures* a false inversion). Drop position from its trigger.
> Keep g07 but report its "exactly one span" test separately — it genuinely
> disagrees with gold on **6/377 positives (~1.6%)** where CUAD labelled both
> an intro date and an exhibit's partial date. That is a real, small inversion
> and must be reported rather than smoothed.
> Also surfaced: two byte-identical documents filed twice under different names
> carry opposite Agreement Date labels (SINA/Leju; PfHospitality Franchise
> Agreement 1 vs 3) — ready-made instances for D-15 and the near-duplicate
> defect class.

> **D-20 — Three pilot-principle claims verified before curation**
> (2026-08-15, `reviews/principle-claim-checks.md`)
> Candidates whose factual basis was an unverified inference were checked
> against gold before Tyler spent judgement on them.
>
> **d02 (dual labelling) — CONFIRMED.** 1,010 of 9,997 distinct gold character
> ranges (10.1%) carry ≥2 categories, across 79% of contracts; within the
> 12-category subset, 90 of 3,995 ranges (2.3%). Driven by documented CUAD
> Datasheet §II-D groups. **This settles `cross_category_overlap`**: it is a
> *documented convention*, not gold corruption, and should not count toward the
> defect rate. It also makes the D-14 interaction live — the same text
> legitimately appears in two decisions, which the per-target decision model
> handles correctly and which nothing in scoring needs to change to accommodate.
>
> **d04 (a floor binds whichever party) — CONFIRMED, and understated.** Across
> all 336 Minimum Commitment gold spans: purchase-by-this-party 25.0%,
> payment/fee/royalty floor 24.1%, supply-by-counterparty 17.6%,
> performance/effort/revenue floor 16.4%, administrative 11.6%.
> **98 of 133 MC-positive contracts (73.7%) contain no purchase-obligation span
> at all.** A model applying CUAD's printed one-line definition literally
> returns `AbsenceClaim` on roughly three quarters of the contracts gold marks
> present. This is the study's thesis in miniature: the task definition is not
> merely terse but *wrong*, and the gap is exactly what a principle supplies.
> d04's own checker regex misses the second-largest class (performance/effort
> floors) and needs widening before it enters the scored set.
>
> **d07 (page furniture) — MIXED; its main clause is REFUTED.** The "furniture
> stays inside the span" half holds (25 spans, 20 contracts) and the
> complementary half is clean (0 of 11,180 spans are pure furniture). But the
> opposite behaviour dominates: **204 same-category adjacent span pairs are
> separated by nothing but furniture, 127 of them splitting mid-sentence.**
> d07 as written calls that a violation, so its checker would penalise the
> majority case ~5:1. The defensible restatement is disjunctive: furniture is
> never a span alone, and an interrupted passage is annotated *either* swallowed
> *or* split — a scorer must accept both shapes.
> **The two derivation arms disagree here and the guidelines arm was right**
> (g07 already refers to spans split around embedded furniture). That
> disagreement is a result about the derivation method, not a defect to patch
> away: data mining generalised from a single pair, documentation did not.

> **D-21 — Compliance must be separable from correctness, or the mediation
> analysis is a tautology** (2026-08-15, from adversarial review)
> Third hard constraint on entry to the scored set: a principle qualifies only
> if **a model can pass its checker and still be wrong, and fail it while being
> right.** Screening is mechanical — populate the 2×2 of {passes, fails} ×
> {right, wrong} over dev; a structurally empty off-diagonal disqualifies.
> **Refinement (2026-08-15), important and easy to get wrong.** A checker is
> *supposed* to read gold — `gold_applicability` is defined as
> `(instance, gold_annotations) -> bool`. Using gold is not the defect. The
> defect is **gating applicability on the answer of the very decision being
> scored**: if a principle applies only where gold is present, or only where
> `is_impossible`, compliance cannot vary independently of correctness and the
> mediation coefficient is unidentifiable. A checker may read gold for *other*
> categories, or read the instance text, and remain separable.
>
> **The 2×2 that is computable before any model runs is a different one.**
> {passes, fails} × {right, wrong} needs model outputs. Pre-model the screening
> table is **{applicable, not applicable} × {gold present, gold absent}**, which
> answers the prior question — could compliance *ever* be separable here. A
> structurally empty cell there disqualifies on its own; the full table is
> checked after the first real run.
>
> **Measured systematically over the 23-record round-2 queue: 13 of 23 fail
> separability, 1 partial, 1 vacuous, 8 clean.** Ten are gold-presence-gated
> (three showing phi = +1.00, the arithmetic signature of the gate rather than
> evidence of anything), two gold-absence-gated. The earlier "6 of 16" was
> spotted by inspection; this is the same defect counted properly, and it is
> the most common failure mode in the pilot by a wide margin.
>
> Found by adversarial review in **6 of 16** pilot checkers: two gate
> applicability on `gold.is_impossible` (the checker asks the answer), four
> define compliance as emitting the gold answer. All six read as sound prose.
> Consequence, and it is the reason checkers now precede curation: **a
> principle can be true while its checker is unusable.** "Is this a good
> principle?" decomposes into two independent questions — is the statement
> right, and does the checker measure anything the answer does not already
> determine. The pilot's adversarial pass could not break 5 of 16 *statements*
> but only 2 of those also had unbreakable *checkers*; the statement/checker gap
> is where most of the damage was.
>
> Two further pilot findings of the same family:
> - **g02 can never fire.** Its `<omitted>` marker occurs 0 times in gold
>   spans, contract text, and the entire raw `CUADv1.json` — CUAD encodes
>   discontiguity as *multiple spans*, not a marker. It was **accepted** in
>   round 1 and is provably inert.
> - **g05's checker flags 53.5% of gold** (176/329), 3.5× over the abort
>   threshold its own sketch pre-registered. The pre-registration worked: the
>   sketch named the condition under which it should be abandoned, and the
>   measurement hit it.

> **D-22 — Principles are selected by measured effect, not by judged truth**
> (2026-08-16, opens `investigations/006-empirical-principle-selection`)
> A candidate is kept if adding it improves scores on contracts where it
> applies, revised if not, dropped if revision does not help — iterated to
> diminishing returns.
>
> Why, in order of force:
> 1. **A null C3 result is otherwise uninterpretable.** Without known-useful
>    principles, "citation does not help" cannot be separated from "the
>    principles were poor." The pilot makes the second live: 13 of 23 failed
>    separability, one fired on 100% of decisions, one on none.
> 2. **The curator is a non-expert, measured not assumed** — round 1 was 11
>    accept / 5 defer / 0 reject / 0 edit with expertise-disclaiming rationales.
> 3. **Provenance did not predict quality**, so source authority is not a usable
>    proxy.
>
> **C1/C2/C3 are unchanged** (D-1). Only the construction of the set entering
> C2/C3 changes.
>
> Consequences that must survive into implementation:
> - **A new selection split, carved from FT-train.** Selecting on a signal and
>   reporting that signal is artifact, not effect. Dev stays for iteration,
>   holdout stays sealed, and the headline becomes whether an
>   empirically-selected set *transfers*.
> - **Pre-registered effect threshold, fixed seed count, and a confirmation
>   pass on unseen contracts.** ~25 candidates × revisions × noisy sampling will
>   otherwise manufacture winners.
> - **The checker's role narrows and improves.** It no longer justifies a
>   principle; it *targets the test*, identifying where a principle applies so
>   the effect is measured where it can appear. A principle applying to ~35% of
>   decisions loses most of its measurable effect if tested corpus-wide.
> - **Two tiers replace the single scored set**: a prompt tier justified
>   empirically, and a scored tier that additionally needs a separable checker
>   (D-21). The current "no feasible checker → excluded" rule wrongly discards
>   principles that may help; "does this help?" and "can we score citation of
>   it?" are different questions and have been entangled.
> - **Inv 002 is not superseded.** Its curation findings become a comparison
>   arm — expert-free human curation versus empirical selection over the same
>   candidate pool — which is a stronger methods result than either alone.
>   Round-2 curation should therefore be completed before switching, since the
>   calibration controls are single-use.
>
> Standing tension to watch: pure greedy search is optimisation, not reasoning.
> Generation stays reasoned (guidelines + mining); only selection becomes
> empirical. If it drifts to "generate hundreds of variants and search," it has
> become instruction optimisation and the novelty — that the selected units are
> citable, checkable principles rather than free-form prompt text — is lost.

> **D-23 — Empirical improvement selects; guideline grounding is recorded
> separately and always** (2026-08-16, refines D-22)
> A principle enters the set on **measured improvement**. Independently of that,
> every principle records whether it is grounded in the annotation guidelines.
> The two are orthogonal and both are reported:
>
> | | in guidelines | not in guidelines |
> |---|---|---|
> | **improves scores** | strongest — documented convention, followed in practice | implicit convention *or* an annotation artifact; cannot tell which from the data |
> | **does not improve** | documented but not followed — questionable as guidance | no support from either source |
> | **sources contradict** | genuinely unresolved; report as such rather than picking |
>
> Why the second axis is mandatory rather than nice-to-have: the gold is
> annotation *practice*, not domain truth, and the two demonstrably diverge —
> the pilot found conventions gold follows that the Handbook never documents,
> and Handbook statements gold does not follow. **A principle selected purely
> on F1 is teaching the model to match the annotators**, which is legitimate for
> a benchmark but is a different claim from capturing legal convention. Without
> the provenance axis we could not tell those apart, and the distinction bears
> directly on whether any of this transfers off CUAD.

> **D-24 — Revisit the checkers; a regex proxy for a semantic condition is a
> design smell, not an implementation detail** (2026-08-16, for the next agent)
> Most pilot failures were failures of the **checker**, not the principle. The
> checkers are lexical instruments doing semantic work: a date regex that misses
> a fifth of the dates, a `shares?` pattern matching the verb "share", a
> conflicts-of-law test defeated by the word "its". Many principles have no
> plausible regex formulation at all.
>
> **The resolution has to respect D-4 (no LLM judge in the scoring path), and it
> can, because two different things have been conflated:**
>
> - **Applicability** — *does this principle bear on this decision?* A function
>   of `(instance, gold)` only. It never sees model output. An LLM computing
>   this is a **labeling tool**, not a judge: run once, frozen to a file,
>   auditable, and spot-checkable against human labels with measured agreement.
>   This is what inv 003's "hand-labeled residual" always was; an LLM is a
>   cheaper first pass at the same job. **Permitted, under those conditions.**
> - **Compliance** — *did this output obey the principle?* A function of model
>   output. An LLM here **is** a judge and is barred by D-4. Where compliance
>   cannot be checked programmatically, the principle stays **prompt-tier** and
>   is not scored (the two-tier split in inv 006).
>
> Conditions on LLM-assisted applicability, all required: computed once and
> frozen as data before any trial runs; the labeling model and prompt version
> recorded like any other proposer; human spot-check on a sample with agreement
> reported; and the scoring path reads only the frozen file, never the model.

## Pending

- ~~**Cross-model assistance parity**~~ — resolved by D-16. Original framing
  kept below for the writeup's benefit, since the reasoning matters:
  1. **Reasoning verbosity differs sharply.** On a trivial prompt the 4B emits
     2,159 reasoning chars, the 9B 870, inkling-small 195. A fixed
     `max_output_tokens` therefore handicaps the 4B specifically — and its one
     smoke-test failure was exactly this: `finish_reason: length` after ~15k
     chars of reasoning with empty content. **This directly threatens H3**, the
     small-model-leverage claim: some of a small model's apparent failure would
     be our budget, not its capability.
  2. **Repair need differs systematically.** inkling-small needed 0 repairs
     across every trial; both Qwen arms routinely needed 1–2. Repair *is*
     assistance, so an equal repair budget is not equal help.
  Options to weigh: a fixed generous budget reported as a parameter; a
  per-model budget calibrated to reasoning verbosity; reporting results at
  multiple budgets; or treating budget-exhaustion as its own outcome class
  excluded from answer scoring. Tyler's call — it changes what H3 can claim.

- **G3 schema decision** (from inv 004 / pilot P0) — field-present everywhere
  vs field-absent for C1/C2 vs field-present with post-hoc filtering. Decision
  rule is written down in inv 004's `investigation.md` **before** the pilot
  runs; record the outcome here.
- **Final category subset** (from inv 002) — must include the Savelka
  confusable trio (Minimum Commitment / Volume Restriction / Revenue-Profit
  Sharing).
- **Model axis** — inkling-small availability + context window on Tinker;
  ~8B and ~32B open picks; the frontier API model.
