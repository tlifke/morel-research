# Methods — scaffold and fact inventory

**Status: scaffold, not prose.** This file gives the section structure and, per
section, the locked facts, figures, tables, and citations that belong in it.
Tyler writes the human-readable prose from this; per repo convention Claude
does not write the writeup itself.

Each entry is tagged:
- **[locked]** — decided and measured; will not move
- **[pending: X]** — the fact exists but X must complete first
- **[human]** — a judgement or framing call that is Tyler's to make

Every number below traces to `plans/decisions.md` (D-N), an investigation doc
(INV<n>-D<m>), or a measurement recorded in this repo. Numbers with no such
trace do not go in the paper.

---

## §1 Task and environment abstraction

Write the general frame **before** CUAD, so the abstraction doesn't read as
retrofitted from one dataset.

- **[locked]** The frame: an environment's *task definition* enumerates
  decision points; *principles* govern how decisions get made; *citations*
  attach to decisions.
- **[locked]** Task definition = `{decision_kinds, targets, target_definitions}`.
  CUAD: decision_kinds `{extraction, absence}`, targets = 12 clause categories.
  AbstentionBench (env #2, deferred): decision_kinds `{answer, abstain}`,
  no targets.
- **[locked]** `Principle` schema: `id`, `statement`, `trigger_guidance`,
  `type ∈ {constraint, procedure, preference, disambiguation, absence}`,
  `scope` (target ids, empty = global), `provenance`.
- **[locked]** Environment interface: 13 methods. The plan specified (a)–(g);
  implementation forced three additions — instance-level and per-decision
  applicability as separate calls, a per-decision gold accessor, an enumerator
  of unrealized decisions — plus `validate_output`. Report the final surface,
  not the original seven, and say why each addition was forced (the
  non-`ok`-trial row invariant forced the enumerator; coverage validation
  belongs to the environment so a target-less environment returns `[]`).
- **[locked]** No condition, metrics, runner, or store code branches on which
  environment is loaded. Asserted by test.
- **[human]** How hard to push the generality claim. The honest position: two
  independent implementations of the interface exist (fake env, CUAD env);
  AbstentionBench is designed for but unbuilt, so generality is *argued*, not
  demonstrated.

## §2 Conditions and the manipulated variable

- **[locked]** C1 baseline / C2 principles / C3 cite. Switch table:
  task definition in all three; principles in C2, C3; citation required in C3.
- **[locked]** D-1 — the task definition is present in **all** conditions.
  Without it the task is undefined and C1 is not a fair baseline. State the
  rejected alternative (a bare C0).
- **[locked]** Prompt assembly has a single source of truth; conditions differ
  *only* by the documented switches. Asserted by test: the task-definition
  block is byte-identical across C1/C2/C3, the principle block is identical
  between C2 and C3, the citation block appears only in C3, and nothing outside
  the switch set varies.
- **[locked]** The schema variant (`principles_cited` field present vs absent
  in C1/C2) is a **fourth, independent axis**, not part of the condition.
- **[locked]** P0's decision rule was written **before** the pilot ran
  (inv 004). Say so explicitly — pre-registration is the reason the schema
  choice is credible rather than post-hoc.
- **[pending: inv 004]** P0 outcome and the resulting schema decision (gate G3).

## §3 Data

- **[locked]** CUAD (`hendrycks2021cuad`, arXiv:2103.06268), CC BY 4.0,
  attribute The Atticus Project. 510 contracts, 41 categories.
- **[locked]** Deterministic rebuild from upstream with sha256-pinned source
  files; verified byte-identical across two from-scratch runs (modulo a
  build timestamp).
- **[locked]** INV1-D1 — gold source of record is `CUADv1.json`;
  `test.json` supplies holdout titles only; `train_separate_questions.json`
  unused (68 questions/contract, does not align to the 41-category axis).
  Verified: test titles ⊂ CUADv1, contexts and gold byte-identical,
  test ∩ train = ∅, test ∪ train = 510.
- **[locked]** D-3 — splits: holdout = official test (102), dev = 40 sampled
  from official train, FT-train = remaining 368. Disjoint, asserted in code,
  persisted as id files and read back, never recomputed. Seed 20260815.
- **[locked]** D-12 — **the tokenizer correction.** Planning-time token figures
  came from a 4-chars/token heuristic. Measured rate on CUAD contract text is
  4.70 chars/token (`Qwen/Qwen3-8B`); the heuristic overstated length by ~18%.
  Character figures were correct. Table to include:

  | quantity | planning figure | n_chars/4 | measured |
  |---|---|---|---|
  | holdout median tokens | ~6.4k | 6,414 | 5,440 |
  | contracts ≤4k tokens | 27 | 27 | 37 |
  | ≤8k / ≤16k | 63 / 79 | 63 / 79 | 66 / 83 |
  | max tokens | ~75k | 75,192 | 64,640 |

  **[human]** This belongs in the paper, not just the repo. A methods section
  that silently reports corrected numbers is weaker than one that shows the
  correction — the correction is evidence the measurement was performed rather
  than assumed.
- **[locked]** D-13 — **dev is stratified to holdout's length profile**, not to
  its own pool's. Length bucket is the primary key; positive-category count is
  secondary, applied within bucket. Achieved match, all buckets within 1.2
  percentage points of holdout; no bucket capacity-constrained. Dev median
  6,424 tokens vs holdout 5,440 (gap reduced from 2,808 to 984).

  | bucket | holdout | dev |
  |---|---|---|
  | ≤4k | 36.3% | 37.5% |
  | 4k–8k | 28.4% | 27.5% |
  | 8k–16k | 16.7% | 17.5% |
  | >16k | 18.6% | 17.5% |

  State the costs, all three: dev is deliberately non-representative of
  official-train (FT-train is the pool of record for Phase 2); the ≤4k bucket
  draws 15 of 119 available short contracts, so effective diversity is narrower
  than the count suggests; and **dev's max length is 41,703 tokens against
  holdout's 64,640** — matching bucket proportions does not match bucket
  interiors, so dev under-represents the extreme tail.
- **[locked]** Final length distribution table (all four splits) —
  `data/processed/stats/length_distribution.csv`.
- **[locked]** INV1-D4 — the 12-category subset and its six selection criteria,
  including mandatory inclusion of the Savelka confusable trio (Minimum
  Commitment / Volume Restriction / Revenue-Profit Sharing). Per-split positive
  counts table. Document Name and Parties deliberately excluded as
  trivial / multi-span-inflating.
- **[locked]** INV1-D3 — the manifest carries all 41 categories, so a subset
  change is a config edit, not a rebuild.
- **[locked]** Repository policy: manifest and scored records in git; contract
  text and raw model responses out.
- **[pending: G1]** Tyler's sign-off freezing the splits.

## §4 Principle derivation

This is the section a reader would reuse in another domain. Give it room.

- **[locked]** Three sources, priority order: Atticus annotation guidelines PDF;
  literature confusions (Savelka 2023 trio); contrastive data mining.
- **[locked]** D-9 — the model-assisted proposal protocol:
  - pair mining is deterministic and runs on **FT-train only** (dev stays clean
    for P0 and iteration; holdout sealed until G4);
  - proposer is pinned — model id, prompt version, batch id stamped on every
    candidate;
  - mandatory `evidence` (pair ids) and `checker_sketch`; anything missing
    either is discarded **mechanically**, before human review;
  - the proposer never sees the guidelines-derived principles, so overlap
    between sources is real evidence about whether the conventions are
    recoverable from data alone.
- **[locked]** Human review protocol: `decision ∈ {accept, edit, reject, defer}`,
  `rationale` **required on every decision including accept**, `edited_from`
  recording the prior value of **every** changed field (not just the statement —
  a sound rule with an infeasible checker is a distinct, reportable failure mode
  from a wrong rule), rejects retained rather than deleted.
- **[locked]** Two hard constraints on entry to the scored set:
  1. no feasible checker or labeling plan → excluded;
  2. **a principle the schema already enforces is unmeasurable** — it would
     show 100% compliance in all conditions by construction, inflating the
     pass-rate and contributing nothing to mediation. Screening test: if you
     cannot describe a schema-valid output that violates the principle, it is
     not scoreable.
- **[locked]** Review is conducted in a purpose-built local app with
  append-only history; rationale drafts autosave, so a rationale cannot be lost.
  Storage keeps the source record verbatim plus an edit overlay, so the
  human-vs-model diff is *derived*, never reconstructed.
- **[pending: WS2 + G2]** The principle set itself: final count, type
  distribution, provenance distribution, and the 3–5 deliberately rare ones.
- **[pending: WS2 + G2]** Reportable directly from the review record, no extra
  bookkeeping: acceptance rate by provenance, edit rate, per-field edit
  distribution, and how many model proposals survived to the scored set.
- **[human]** How to frame the human-in-the-loop honestly. The model proposed;
  a human accepted, edited, or rejected each proposal with a written reason;
  the surviving set is a joint artifact. Resist both overclaiming ("automated
  principle discovery") and underclaiming ("hand-authored").

## §5 Applicability ground truth

- **[locked]** `gold_applicability` is held **outside** the prompt: a checker
  `(instance, gold) -> bool`, per decision point where the principle is
  decision-scoped.
- **[locked]** Three-way classification: fully-programmatic /
  heuristic-needs-spot-check / manual.
- **[locked]** D-4 — **no LLM judge anywhere in the scoring path**, in either
  phase. Every metric is programmatic or hand-labeled. State the reason: a
  judge in the loop would contaminate the Phase-2 reward, and the claim of the
  paper is that constraining the process *vocabulary* makes process supervision
  programmatically verifiable. A judge would concede that point.
- **[pending: WS3]** Labeling flow description, coverage over dev + holdout,
  and measured spot-check agreement on a sample of the programmatic checkers.
- **[pending: WS3]** The cost estimate from the 3-contract pilot sample, and
  whether it forced the principle set smaller. If it did, say so — it is a
  finding about the method's cost, not an embarrassment.

## §6 Metrics

- **[locked]** D-14 — **one decision per target**, always. A CUAD contract
  yields exactly 12 decisions: an `Extraction` with a list of spans, or an
  `AbsenceClaim`. Rejected alternative: one decision per span. Three reasons,
  all found by inspecting real gold: repeated verbatim boilerplate is marked
  per copy and `Extraction` carries text not offsets, so span-level scoring
  cannot distinguish "emitted once" from "missed the duplicate"; the citation
  P/R/F1 denominator would move with the model's own output, breaking
  cross-model comparison; and absence is inherently category-level, so
  span-level extraction breaks presence/absence symmetry.
- **[locked]** `decision_idx` = the target's position in the task definition,
  stable across trials, models, conditions and seeds.
- **[locked]** Answer score: token-level span F1 (Jaccard-style, per LLM-era
  CUAD literature), aggregating **within** a decision via soft precision (each
  prediction's best gold match) and soft recall (each gold's best prediction
  match), harmonic mean. Plus absence accuracy and category-match accuracy.
  Reported per-category and length-stratified.
- **[locked]** Compliance: pass-rate over applicable principles, measured in
  **all** conditions including C1. Say plainly that this is the **mediation
  variable**, not a robustness check. Principle-level `pass_rate` (a principle
  passes iff it passed everywhere it applied) with `pass_rate_micro` over
  principle × decision pairs reported alongside.
- **[locked]** Citation (C3 only): per-decision P/R/F1 against the
  **scope-relevant slice** of gold applicability — not the instance-wide set,
  which would penalise any model that doesn't cite globally-scoped principles
  on every decision. Explicit tp/fp/fn lists retained per decision; the H4
  confusion matrix is built by pairing fp against fn within a decision.
- **[locked]** F1 not recall, to block a cite-everything strategy.
- **[locked]** Length stratification is a property of the metrics module — every
  primary metric emerges bucketed. Buckets: ≤4k / 4k–8k / 8k–16k / >16k tokens.
- **[locked]** The causal chain to report: principles → compliance → success;
  citation requirement → Δcompliance beyond provision → Δsuccess.
- **[locked]** CIs are currently normal-approximation and named
  `ci95_normal_approx` so they cannot be misread. **[human]** The writeup
  probably wants bootstrap CIs recomputed from the stored per-trial rows.

## §7 Execution

- **[locked]** Model axis (2026-08-15): `Qwen/Qwen3.5-4B`, `Qwen/Qwen3.5-9B`,
  and `inkling-small`, all via Tinker for now. The two Qwen models are the same
  ids that will be served on the desktop GPU when it returns, so the model axis
  survives the substrate change.
- **[locked]** inkling-small context window = **262,144 tokens**, measured by
  bisection against the endpoint's own error message (150k accepted, 300k
  rejected), not from documentation. Consequence: **no CUAD contract is
  infeasible on this arm** (longest is 82,345 tokens), so H5's story here is
  degradation, not refusal.
- **[locked]** inkling-small structured output is **prompt-plus-parse**
  (`json_schema` silently ignored, `json_object` honored), which the backend
  declares so repair accounting is honest.
- **[locked]** **Two token counts, deliberately distinct.** `length_bucket`
  uses a single fixed reference tokenizer so stratification is comparable
  across models; **feasibility** is decided per backend, with that backend's
  tokenizer and limit, against the **assembled prompt** — meaning C2/C3 can be
  infeasible where C1 is feasible, which is itself a result.
- **[locked]** Repair policy is bounded and shared: JSON failures, schema
  failures, and **coverage** failures all draw from the same
  `max_repair_attempts` budget, with `failure_detail.stage` distinguishing
  them. The budget is identical across C1/C2/C3, so assistance is symmetric and
  cannot manufacture a condition effect.
- **[locked]** Trial outcomes `ok | parse_failure | infeasible_at_length |
  api_error` are **reported, not dropped**. Decision rows are written for
  non-`ok` trials with null scores. This is the paragraph that makes H5
  auditable — without it a reader cannot separate "the model failed" from "we
  did not try."
- **[locked]** Full contract fed; never truncated, never chunked (D-2).
- **[locked]** Two-level results store: `trials.jsonl` (one row per trial key)
  + `decisions.jsonl` (one row per decision), append-only, with provenance
  stamps (run id, prompt template version, principle set version, harness git
  sha, temperature, response hash). D-10.
- **[locked]** `trial_id` excludes `run_id`, making runs resumable; a
  deliberate re-run goes to a fresh store.
- **[pending]** Sampling parameters as actually run: temperature (~0.7 planned),
  seeds per instance (≥3 planned), instances per cell.
- **[pending]** Measured context windows and structured-output modes for the
  two Qwen arms.

## §8 Threats to validity and limitations

- **[locked]** **Contamination.** CUAD is public and in pretraining corpora.
  Condition *comparisons* are valid under shared contamination; absolute
  numbers are not leaderboard-comparable. This caveat travels with every
  results table.
- **[locked]** D-15 — **gold noise floor.** Gold is left uncorrected and text
  is not normalized before scoring. Observed defect classes, from direct
  inspection: outright mislabels (a nine-character span `"Business."` labeled
  License Grant); spans labeled by neighbourhood rather than content; **gold
  split around embedded OCR/SEC page furniture**, so one legal thought becomes
  two spans and a model emitting the coherent passage is penalised while one
  reproducing the scanning artifact is rewarded; boundary jitter of a few
  characters between equivalent spans; byte-identical and strictly-nested spans
  across categories; and redaction (`*****`) removing the decisive content so
  the call must rest on clause structure.
  Justification for leaving it: all conditions see the same corrupted gold, so
  condition contrasts — what H1 actually claims — remain valid; correcting gold
  would fork us from the CUAD literature; normalizing text would shift every
  offset in the manifest. Consequence to state plainly: **no arm can reach
  F1 = 1.0**, and the reader must not read the ceiling as model failure.
- **[pending: gold audit]** The measured defect rate — overall, per category,
  per defect type — with sample size and seed, reported as the span-F1 ceiling.
- **[locked]** Some CUAD "contracts" are fragments of a split exhibit. An
  absence in a fragment is not the same event as an absence in a whole
  agreement; the clause may live in a sibling record. Absence accuracy should
  not treat them as equivalent. **[human]** decide whether to exclude, flag, or
  merely caveat.
- **[locked]** Dev is deliberately non-representative of official-train, and
  under-represents the extreme length tail (see §3).
- **[locked]** Leakage detection is regex-based over free-text fields and will
  not catch a model that paraphrases a rule without naming it. **[human]** state
  this as a floor on the measured leakage rate, not a bound.
- **[locked]** Field-absent leakage is **structurally zero** under constrained
  decode and possible under prompt-plus-parse, so leakage rates are not
  comparable across backends and P0's measurement is only meaningful on a
  prompt-plus-parse backend.
- **[pending: inv 004]** If P0 forces field-absent schemas for C1/C2, the
  schema difference across conditions is a stated limitation.
- **[locked]** Single pilot model for P0; a model-specific schema effect would
  not show up.
- **[pending: WS3]** Human labeling reliability figure.
- **[locked]** Generality to a second environment is argued from the interface
  and two implementations, not demonstrated — AbstentionBench is unbuilt.

---

## Figures the methods section should carry

- **[locked]** The workstream dependency diagram (exists: `overview.html`).
- **[locked]** The measurement chain: principles → compliance → success, with
  compliance as the mediation node (exists: `overview.html`).
- **[human]** One figure carries the message in the one-pager, per repo
  convention — that one is a *results* figure, not a methods figure.

## Writing order

§1, §2, §6, §7 are fully determined and will not move. Draft them now, while
the reasoning is fresh, rather than reconstructing it from the decision log in
two months.

## Two rules to hold to

1. **Every number carries a provenance** — measured, planned, or
   literature-reference. The tokenizer episode (D-12) is the argument: a figure
   travelled three documents before anyone asked where it came from.
2. **Report the corrections.** D-12 and D-13 both describe catching something
   before it propagated. That is evidence of method quality; burying it trades
   credibility for tidiness.
