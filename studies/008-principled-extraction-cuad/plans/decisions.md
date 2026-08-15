# Decision log — study 008

Study-level decisions that outlive any one investigation. Investigation-local
decisions stay in their own `investigation.md`.

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

## Pending

- **G3 schema decision** (from inv 004 / pilot P0) — field-present everywhere
  vs field-absent for C1/C2 vs field-present with post-hoc filtering. Decision
  rule is written down in inv 004's `investigation.md` **before** the pilot
  runs; record the outcome here.
- **Final category subset** (from inv 002) — must include the Savelka
  confusable trio (Minimum Commitment / Volume Restriction / Revenue-Profit
  Sharing).
- **Model axis** — inkling-small availability + context window on Tinker;
  ~8B and ~32B open picks; the frontier API model.
