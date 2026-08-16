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
> Touched only for headline results, in both phases. harness_val = ~40 contracts
> sampled from official train, stratified by length and positive-category
> count, seeded and persisted. Remaining official-train reserved for Phase 2
> fine-tuning. No contract in more than one of {harness_val, model_train, test}.

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
> Contrastive-pair mining is deterministic and runs on model_train only; proposals
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

> **D-13 — harness_val is stratified to test's length profile, not to its own pool's**
> (2026-08-15, at gate G1, before the split freeze)
> The first build stratified harness_val to mirror the official-train pool it is drawn
> from, which left harness_val systematically longer than test (median 8,248 vs
> 5,440 tokens). Changed: harness_val now matches the **test** length distribution.
>
> Why. harness_val has exactly one job in this study — to predict how the system will
> behave on test before test is opened at G4. Every use of harness_val is a
> forecast: the P0 schema decision, prompt iteration, and the feasibility
> planning behind `infeasible_at_length`. All of those are length-sensitive, and
> H5 is *specifically* a claim about degradation with contract length. A harness_val set
> 50% longer than test would have biased every one of those forecasts in the
> same direction — pessimistic on feasibility, pessimistic on long-context
> failure — and we would not have found out until the test was already open.
> Being representative of the training pool buys us nothing we need; being
> representative of the evaluation target buys us the entire purpose of a harness_val
> set.
>
> What it costs, stated plainly. harness_val is now a deliberately **non-representative**
> sample of official-train. It cannot be used to characterize the training pool,
> which matters for Phase 2, where model_train — not harness_val — is the pool of record.
> Matching test's profile also means drawing more heavily from the short end
> of official-train, so the short buckets sample a smaller effective pool and
> may show less contract diversity than their count suggests.
>
> Stratification priority is now explicit: **length bucket first** (matched to
> test's proportions), positive-category count balanced **within** each
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
> the signing date is literally blank. Measured over harness_val + the pre-carve
> training pool (408 contracts, test untouched; that pool has since been carved
> into model_train 264 / principle_train 60 / principle_val 40, so no current
> pair of split names names it): **30 of 377 positives (8%) have a blank or
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
> {right, wrong} over harness_val; a structurally empty off-diagonal disqualifies.
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
> - **A new `principle_train` split, carved from model_train.** (Carved at
>   INV1-D8 from the then 364-contract pool; model_train is 264 after the carve.)
>   Selecting on a signal and
>   reporting that signal is artifact, not effect. harness_val stays for iteration,
>   test stays sealed, and the headline becomes whether an
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

> **D-25 — Smoke-test findings: three blockers before any selection run**
> (2026-08-16, first contact between the metrics and real model output)
> The CUAD environment is built and C1/C2/C3 ran clean on 2 scratch contracts
> with Qwen3.5-9B — 6/6 conformant, no parse/schema/coverage failures, traces
> and decision rows complete. The pipeline works. Three defects surfaced that
> would have corrupted results, and **none is fixed yet**.
>
> **1. Citation scoring rewards silence when applicability is absent.** With no
> applicability file, `gold_applicable` is `[]` and `citation_eval([], [])`
> returns precision = recall = f1 = **1.0** — a model that cites nothing scores
> perfect, while any citation scores 0. The environment guards this via
> `assert_ready`, but the runner computes the citation block unconditionally for
> C3. Fix: citations must carry an explicit `available: false` rather than a
> number. An unmeasured quantity reported as a value is the same class of error
> as compliance-reported-as-zero, which we already fixed.
>
> **2. Answer granularity is unspecified, and our own prompt biases it.** All
> smoke spans were verbatim-exact, yet Governing Law scored span-F1 0.176 and
> Expiration Date 0.261, because the model returned `"State of California"` and
> `"December 31, 2020"` against **sentence-level gold**. Contributing cause: the
> task definition appended the CSV's `Answer Format` column, which actively
> pushes minimal-value answers.
> **This is the most consequential finding, and it is a design decision rather
> than a bug.** Gold is mostly sentence-level; working-set `w01` legislates
> exactly this granularity. So a badly-specified task definition would let C2
> "improve" largely by *repairing our own prompt* — meaning H1 would be
> measuring prompt repair, not business logic. **The C1 task definition must be
> as good as we can make it before any condition comparison is run**, and the
> granularity choice must be stated and held constant across conditions.
>
> **3. Filename leakage.** `prompts.render_instance` prints `Title:` and `Id:`,
> and CUAD ids encode dates and document types. The model extracted an
> Agreement Date of `03_29_2000` that appears in the *filename* and nowhere in
> the contract text — scored `not_found`, inflating invented-language rate and
> corrupting the presence call. Fix: withhold the id, and decide deliberately
> whether the title is part of the document (it often is, for Document Name).
>
> Also observed, not blocking: C1 and C2 produced byte-identical extractions on
> one contract at n=1, principles costing ~2.4k prompt tokens for no change;
> reasoning ran 5–35× the answer length; and `working_set.yaml` will not load
> because merged records carry list-valued `provenance` against a single-value
> `Literal` — the model widens or the file normalises, someone must choose.
>
> **Amplified 2026-08-16 by reading the real prompt** (`reviews/prompt-inspector.html`,
> byte-identity against the trace store asserted and passing for all three
> conditions). Six further defects, one of which makes blocker 2 far worse:
>
> - **The answer-format hint affects 9 of the 12 targets, not one.** Nine carry
>   `(answer format: Yes/No)`. **The model is told the answer is a yes/no while
>   being asked to return spans**, against sentence-level gold. Governing Law was
>   merely the visible casualty because it is a TP with a short span; the same
>   mismatch sits under most of the task. This is the single largest known
>   defect in the prompt.
> - **C1 is not principle-free.** Under `field_present` it receives a 25-token
>   block instructing it to leave `principles_cited` empty — so C1 mentions a
>   principle-shaped field, and **C3−C2 is a substitution (+48 tokens), not the
>   addition of a citation instruction from zero.** Must be stated in methods;
>   it changes what the C1 baseline is.
> - **The citation block's exemplar id is `"p03"`.** Harmless with the as-run
>   pilot set; the moment the working set (`w01`–`w09`) is used, the example
>   names a principle that is not in the prompt.
> - **Nothing tells the model that category strings must match exactly.** Targets
>   are prose bullets, the schema types `category` as a bare string with no enum,
>   and exactness is enforced only post hoc in `validate_output()`.
> - **Raw CSV artifacts reach the model** — non-breaking spaces and curly quotes
>   from the category descriptions, unnormalised.
> - **The CC BY attribution notice sits inside the task-definition block**, so
>   ~20 tokens of dataset licensing are in the instruction stream.
>
> On the leakage channel: on this contract the model answered the Agreement Date
> correctly from the text despite the id encoding a different date, while on the
> sibling contract it took the id's date. **The channel is open on both and was
> exploited on one** — which is the argument for closing it rather than
> concluding it is benign.
>
> Measured prompt costs, same tokenizer as D-12: principle block **2,295
> tokens** for the as-run 23-principle set, **1,133** for the 9-principle working
> set. Backend-measured C2−C1 is +2,360, C3−C2 is +48.
>
> A curiosity worth remembering: the two most-cited principles in the smoke run
> were both **fabricated calibration controls**. The set loaded was all 23
> round-2 candidates because it was the only loadable file. Models cite
> plausible fabrications readily.

> **D-26 — The external comparison runs through THEIR evaluator, not ours**
> (2026-08-16, `reviews/cuad-baseline-comparability.md`)
> The earlier claim that "we cannot compute their metrics and they cannot
> compute ours" was **half wrong**, and the wrong half is the useful one. We
> still cannot compute AUPR or P@80%R — those summarise a curve and we produce
> one committed decision. But **CUAD's own `evaluate.py` scores our output
> unmodified**: our `Extraction(category, spans)` maps to their `preds_list`,
> our `AbsenceClaim` maps to `[]`, and `compute_precision_recall` runs with **no
> invented parameters**. The unit of prediction is already the
> `(contract, category)` pair, which matches D-14 exactly.
>
> **The artifact is their PR curve with our point plotted on it** — same gold,
> same split, same Jaccard≥0.5 matcher, same micro-pooling. Their side
> contributes the entire curve, so we cannot be accused of choosing their
> operating point; our side contributes a committed decision, which is what this
> study produces.
>
> **The reverse direction is rejected.** Taking their top-1 span above "their
> operating threshold" is not merely unfair to them — that threshold is a value
> `evaluate.py` discovers *on the test set* to force recall to 0.8, so the
> comparison would measure our thresholding choice rather than their model. If
> ever done, it must use their genuine absence signal (`null_odds`, which their
> SQuAD-2 training actually optimised) with τ swept, reporting their best
> achievable Level-A F1 — and only as appendix material, since their framework
> has no TN cell and our absent-class metrics have no counterpart there.
>
> **Two consequences for sequencing:**
> 1. **No rehearsal split exists for this run.** Every non-`test` split was
>    carved from CUAD's official *train* set — these models' fine-tuning data.
>    Their models are only honest on `test`, so the baseline run is inherently
>    **G4-gated**. `harness_val` can shake out the wiring; any score it produces
>    is meaningless.
> 2. **Reproducing their Table 2 is a hard gate, not overhead.** The 41-category
>    run must recover AUPR 42.6 / 48.2 / 47.8 and P@80%R 31.1 / 38.1 / 44.0 from
>    the released checkpoints. If it does not, everything downstream is void.
>
> **Framing corrected 2026-08-16 (Tyler).** The "one-sided claim" reading below
> answers a question this study is not asking. The CUAD baseline is a
> **calibration point, not a hypothesis test.** Its job is to tell a reader
> whether our starting point is reasonable or a strawman — which is precisely
> what makes an unoptimised iteration 0 defensible.
>
> The decisive distinction: **the level is confounded, the delta is not.**
> Contamination and their training advantage both affect where our absolute
> numbers sit. Neither affects the *difference* between our own iteration 0 and
> our own ladder endpoint, which share contamination exactly. The result this
> study reports is that delta.
>
> And contamination probably works **against** us on the delta, which makes the
> measurement conservative: a model that has effectively seen CUAD's
> annotations already performs well without principles, leaving *less* headroom
> for a principle to demonstrate. A measured principle effect under
> contamination is therefore closer to a lower bound than an inflated one.
>
> Two obligations follow. **Preempt the misreading explicitly** — if our number
> lands above theirs, readers will read "LLM beats CUAD models" whatever the
> surrounding prose says, so the disclaimer has to sit with the number, not in a
> limitations section. And note that **Phase 2 is the better-matched
> comparison**: fine-tuning on `model_train` (264 of their 408 contracts) puts
> us in the same regime they were in, which is a reason to keep the baseline
> infrastructure once it is built.
>
> The original reasoning, retained because the asymmetry is real and belongs in
> limitations:
> **The claim is one-sided, and that is what makes it usable.** They consumed
> 408 expert-annotated contracts (favours them); their encoders' pretraining
> predates CUAD's 2021 release so their test exposure is genuinely zero while
> ours is plausibly nonzero and may include the annotations (favours us).
> Therefore **a result at or below their baseline is strong evidence; a result
> above it is confounded and cannot be read as a modelling claim.** This is also
> the argument that the study's load-bearing results remain the internal
> condition contrasts, which share contamination exactly.
>
> Feasibility is not the constraint: the 3080's 12GB fits all three checkpoints
> (sequences are fixed at 512, so the sliding window removes long-document VRAM
> pressure), ~3.4 GPU-h for all three at 41 categories; Modal is $10–30 all-in
> but **must be Ampere** — the pinned 2021 stack supports sm_80/86 and nothing
> newer. The real bottlenecks are CPU and RAM, not GPU.

> **D-27 — Applicability is labelled without gold visibility, and the D-24
> premise is supported** (2026-08-16, `reviews/applicability-labelling.md`)
> 4,498 judgements over `harness_val` + `principle_train` (100 contracts),
> frozen, loading through `ApplicabilitySource` unchanged. `assert_ready(["C3"])`
> now passes, so citation metrics are measurable.
>
> **The design call that matters: `gold_visibility: none`.** D-24 permits the
> labeller to read gold; this pipeline declines. That makes the pilot's dominant
> failure — gold-gated applicability, 13 of 23 round-2 checkers —
> **structurally impossible rather than screened for afterwards.** Prevention
> over detection, and it is why the D-21 pass rate inverted.
>
> **D-21 screening: 9 of 10 principles pass.** `w04` fails as
> `degenerate_universal` — applicable on 100% of Agreement Date decisions, both
> not-applicable cells empty. Note it fails *differently* from its regex
> counterpart, which was gold-presence-gated at phi = 1.00: same principle, two
> instruments, two distinct disqualifying defects.
>
> **The D-24 test, and it is the headline.** LLM-vs-regex disagreement runs
> 10–79%, median ~30%, and is **almost entirely one-sided** — in 8 of 13
> comparisons the regex's applicable set is a near-subset of the LLM's. On the
> same decisions, **6 of 13 regex checkers are disqualified by D-21 while 9 of 10
> LLM-labelled principles qualify.** Concrete: `w03`'s regex has no entry for
> jury-waiver or personal-jurisdiction-consent clauses — the exact confusions the
> principle exists to resolve; `w07`'s supply-verb alternation misses guaranteed
> *payment* floors, independently reproducing D-20's d04 finding with a different
> instrument.
> **One counter-case keeps this honest**: `w08`'s regex fires too broadly
> (156/200) and the LLM is the more selective instrument. So lexical triggers
> fail in **both** directions, and the claim is "regex proxies were the wrong
> tool", not "regex was always under-inclusive".
>
> **Limits, all feeding inv 006's two-tier split.** `w04` is prompt-tier, not
> scorable. `w03` is low-power. `w01`'s applicability is *intrinsically*
> presence-correlated (phi +0.655) — the v1 prompt asserted otherwise, the
> labeller caught the contradiction, and v2's honest consequence is that its
> citation metrics will track the answer. 19 contracts truncated, so some
> negatives are missing data rather than measured absence. 23% of `applicable`
> labels are low-confidence.
>
> **Unplanned but important: labeller variance is real and unmeasured.** One
> contract was labelled twice by concurrent agents and the runs disagreed —
> 7 vs 10 applicable of 45. A frozen artifact hides this by construction, so
> repeat-labelling a sample belongs on the list before these labels carry a
> published number.
>
> **Awaiting Tyler**: `reviews/applicability-spot-check.html`, 114 items, model
> answer hidden behind a disclosure and gold withheld so he decides first. At
> n=114 the 95% Wilson interval is ±~6.5pp; per principle (n=12) it is ±~20pp
> and should not be reported as a number. `spot_check` in the artifact is `{}` —
> unavailable, not zero.

> **D-28 — C2 vs C3 on answer metrics is a clean null, with two real side
> effects** (2026-08-16, `reviews/c2-vs-c3-answer-metrics.md`)
> First real experimental result of the study. 240 trials on `harness_val`,
> Qwen3.5-9B, paired over the 38-contract intersection.
>
> **Requiring citation does not change what the model extracts.** Every accuracy
> CI contains zero: presence F1 +0.0029 [−0.0048, +0.0121], span F1 −0.0075
> [−0.0406, +0.0252], exact-match −0.0027. **The manipulation demonstrably
> took** — C2 cited on 0 of 1,260 decisions, C3 on 1,077 of 1,200 (89.8%), zero
> leakage either way — so this is a null *effect*, not a null treatment.
>
> **Two things did move, neither an accuracy gain:**
> - **Verbatim exact rate −2.5 pts** [−0.0462, −0.0050], 17 of 23 moving
>   contracts down, while span F1 stayed flat. Spans remain as *correct*;
>   slightly fewer are literal substrings.
> - **+627 completion tokens** [+219, +1039] for a **+48-token** prompt delta.
>   The citation requirement costs ~13× its prompt cost in reasoning.
>
> **A near-significant result was chased down and killed**, which is the part
> worth imitating. Pooled presence F1 came out +0.0169 [+0.0004, +0.0340],
> clearing zero by 0.0004 — but C3 lost more trials to parse failure, so the
> pooled figure is survivorship. On the 18 contracts with a full 3/3 in **both**
> arms the sign reverses to −0.0022 [−0.0172, +0.0117]. The null is reported.
>
> **The most actionable defect: truncation is condition-dependent and
> counter-intuitive.** 4 of 240 trials truncated, **all C3, three on the
> *shortest* contracts** — the citation requirement tips reasoning past budget
> precisely where the document gives least to reason about. This is the
> mechanism behind C3's conformance deficit (89.3% vs 92.1%). The budget was not
> changed (`max_output_tokens=16384`, recorded per D-16); note the earlier
> 12-trial probe showed 0 truncations and did **not** generalise.
>
> **Feasibility.** One contract was infeasible identically in C2 and C3, so it
> introduces no asymmetry — and is probably an estimator artifact, since the
> gate's 4-chars/token heuristic overstates by 13.9% against a fit on the
> contracts that ran. Reported, not fixed. The feasible sets still differ for a
> different reason (one contract lost all 3 C3 trials to `json_decode`), so all
> paired stats use the intersection with the excluded contract reported apart.
>
> **Two findings that outrank the null:**
> 1. **Citation frequency is not principle quality.** `w06` — whose checker
>    fires on 1 of 480 decisions — drew **368 citations**; `w10`, which has *no
>    measured footprint at all*, drew 91. Same pattern as the smoke run citing
>    fabricated calibration controls. Models cite what sounds apt.
> 2. **Two categories lose to a trivial baseline in both arms.** Expiration Date
>    scores 0.317/0.337 presence F1 against an **always-present baseline of
>    0.895** — the model claims absent on 69 of 85 present decisions. Worst cell
>    in the study, and a task-definition problem rather than a principle one.
>    Volume Restriction is 0.100/0.000 against 0.158. **Two thirds of the
>    Savelka trio sit at or below trivial.**
>
> Also flagged rather than silently handled: 8 trials died on transient
> connection resets and were not retried, because deleting store rows to re-roll
> them is exactly the kind of thing that biases a result.
>
> Cost: 5.26M tokens (3.19M prompt / 2.07M completion), 6.55 model-hours of
> summed latency, ~5h wall clock. Parallelism bought nothing — Tinker capped
> aggregate throughput at ~1.4 trials/min regardless of shard count.
>
> **Scope, stated in the write-up itself**: with 9 of 10 principles carrying
> `needs_rebuild` or `not_yet_specified` checkers, this tests the **citation
> requirement**, not whether the principles are good.

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
