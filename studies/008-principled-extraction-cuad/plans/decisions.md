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
> Open sub-question: confirm the annotation-guidelines PDF falls under the same
> release rather than a separate license.

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

## Pending

- **Cross-model assistance parity** — raised 2026-08-15 by the backend
  measurements, unresolved. Two findings make "same settings for every model"
  *not* the same as "equal assistance":
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
