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

### §4a The curation gate is itself a measured object — **write this up**

The derivation method was **iterated across rounds, and the iteration is part
of the result.** Report round 1 as run, including what it exposed, rather than
presenting only the final procedure. A methods section that shows the gate
being tested is stronger than one that asserts a gate existed.

**Round 1, measured (2026-08-15).** 16 candidates (8 guideline-derived,
8 data-mined), one curator, five pilot categories.

- **11 accept, 5 defer, 0 reject, 0 edit.**
- By source: guidelines **7/8 accepted**, data-mined **4/8 accepted**.
- **[human]** The zero rejects and zero edits is the headline: the gate never
  exercised its negative power at all.

**The mechanism, in the curator's own rationales.** Accept-by-default under
uncertainty — *"I don't have the domain expertise to disprove this. Accepted."*
Absence of disconfirming knowledge was being read as support.

**But the gate was not uniformly non-discriminating, and where it worked is the
design lesson.** Every confident decision was a **cross-source comparison**:
`d01` deferred as directly contradicting `g01`; `d02` accepted as aligning with
`g03`. Both a contradiction and a corroboration were detected **without domain
expertise**, because a relation between two sources is checkable where the
truth of a proposition is not. Every low-confidence decision was single-source.

**And the defers were correct on the merits.** `d07` was deferred asking for
more support — independent verification later found its main clause refuted
(204 counterexamples to 25). `d06` was deferred — the proposer had already
conceded it sat below its own evidence bar. Two genuinely weak candidates were
caught by a curator with no contract-law background.

So the finding is not "the human gate is worthless" but a sharper claim worth
stating precisely: **the gate has discriminating power over *structural*
properties — contradiction, corroboration, evidence strength, comprehensibility
— and close to none over *substantive* ones.** `d08` drew *"I have no idea what
this means,"* which is a comprehensibility failure of the principle rather than
of the curator, and a legitimate rejection criterion in its own right.

**The expertise limitation, stated plainly.** The protocol assumes an expert
curator (D-9 describes curation as expert-derived or expert-curated in the
general case). This study substituted a **non-expert curator**, and the
mitigations below are the designed response to that constraint rather than a
post-hoc excuse. **[human]** Say so directly; it is the most contestable part
of the method and pre-empting it is stronger than defending it later.

**Round 2 design changes, each traceable to a round-1 observation:**

1. **Checkers are implemented and run against gold *before* curation, not
   after.** Each principle arrives with an empirical footprint — how often it
   fires, and whether violations correlate with wrong answers. This converts
   "is this a good principle?" (needs expertise) into "does this checker
   discriminate?" (needs none). A principle firing on 0% or 100% of decisions
   is useless however authoritative its source.
2. **Cross-source validation is structural.** Derive in one source, check for
   corroboration in the other; outcomes are *corroborated / contradicted /
   silent*. Directly generalises the only mechanism that produced curator
   confidence in round 1. Note "silent" will be common and is not evidence
   against: mining is blind to positional categories, and the guidelines are
   silent on two-thirds of the Savelka trio.
3. **Adversarial critique.** A second model argues *against* each principle,
   citing gold; the curator adjudicates a disagreement rather than judging a
   proposition in a vacuum — the same lower expertise bar that made the
   cross-source calls easy.
4. **Calibration controls.** Deliberately bad principles — plausible-sounding,
   contradicted by gold — are seeded into the queue. The curator knows controls
   exist but not which they are. **[human]** This turns rubber-stamping from an
   intuition into a measured rate, and makes "the curation gate discriminates"
   a claim with evidence rather than an assumption. Report the catch rate.
5. **Instrument fixes.** Evidence pair ids were opaque in the review UI, so
   single-source judgement was harder than it needed to be; the underlying
   spans are now shown inline. A distinct "I don't understand this" decision is
   separated from defer, since they are diagnostically different.

**[human]** The five deferred records are the highest-information output of
round 1 and should not be presented as a backlog that was cleared. In
particular the `d01`-vs-`g01` contradiction is a disagreement *between our two
derivation methods* and belongs in the results, not in a tidy-up.

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
Present the metrics as **three levels that are never collapsed into one
number**, in Tyler's framing:

**Level A — the presence/absence call.** *When the agent says a category is
present or absent, how often is it right, and what kinds of error is it
vulnerable to?*

- **[locked]** Raw 2×2 counts (TP/FP/FN/TN) stored per category; every rate
  derives from them, so aggregations recompute without re-running trials.
- **[locked]** Presence-class **and** absent-class P/R/F1, reported separately
  and macro-averaged separately, never together. The term "absence accuracy" is
  **retired** as ambiguous between overall accuracy, absent-class recall, and
  absent-class precision; the fields are now `absent_class_recall` and
  `absent_class_precision`. `decision_kind_accuracy` = (TP+TN)/total ships with
  a note that it is base-rate-dominated and never a headline.
- **[locked]** False-present and false-absent reported separately, not only via
  F1 — principles plausibly move them in opposite directions, and an
  absence-ruling principle should cut false-present while possibly raising
  false-absent.
- **[locked]** **Trivial baselines per category** (always-absent,
  always-present), printed alongside. Required, not optional: Source Code
  Escrow has 1 positive in 102 holdout contracts, so always-absent scores 99%
  there. **[human]** The reason both classes are reported is worth a sentence —
  the informative class *flips with base rate*: for rare categories only the
  presence class carries information; for common categories (Agreement Date,
  93/102) always-present already scores 91%, so only the absent class does.

**Level B — span quality, conditional on agreement.** *When a category is
present in gold and the agent agrees, how close is its span set to the gold
span set?*

- **[locked]** Defined **only on the TP cell**, and any corpus-level span score
  is reported **with its TP denominator** — otherwise a model that finds three
  clauses perfectly and misses nine looks excellent.
- **[locked]** Token-level soft P/R/F1 (each prediction against its best gold
  match, each gold against its best prediction, harmonic mean), aggregated
  *within* a decision per D-14. Plus **exact-match rate** as the stricter,
  interpretable companion.
- **[locked]** **Verbatim fidelity, three-way, both matchers reported**:
  *exact* (literal substring), *normalised-only* (matches after whitespace
  collapse, NFKC, quote/dash folding, hyphen-linebreak rejoin — but **not**
  after stripping OCR page furniture, which would be a scoring decision in
  disguise), and *not found*. **[human]** The framing carries the result: the
  exact-vs-normalised **gap measures how much apparent non-verbatim output is
  merely cosmetic**, and the **not-found rate is the one that means invented
  contract language** — a categorically different and, in legal extraction,
  more serious failure than picking the wrong clause.
- **[locked]** Span position (located character offset → depth into document),
  giving a sharper H5 instrument than contract length alone: it separates "long
  contracts are harder" from "the model stops reading after N tokens."
- **[locked]** Multi-span recovery — predicted vs gold span counts per decision.

**Level C — citation quality (C3).** *When the agent makes a decision, do its
cited principles match the gold applicable set?*

- **[locked]** Per-decision P/R/F1 against the **scope-relevant slice** of gold
  applicability — not the instance-wide set, which would penalise any model
  that doesn't cite globally-scoped principles on every decision. Explicit
  tp/fp/fn lists retained.
- **[locked]** F1 not recall, to block a cite-everything strategy.
- **[locked]** Per-principle marginal P/R/F1 — which principles are cited well
  and which are systematically confused. This *is* H4, and it is what makes the
  principle set maintainable.
- **[locked]** Confusion matrix over principle ids, from pairing fp against fn
  within a decision.
- **[locked]** **Citation × answer-correctness, swept over the threshold.**
  "Answer correct" depends on a span-F1 cutoff, so rather than fix one, the
  2×2 is computed at t = 0.1 … 1.0 in 0.1 steps and reported as a **curve**.
  Deterministic, recomputed from stored per-decision scores, no re-running.
  **[human]** Say why: the right overlap threshold is genuinely use-case
  dependent — triage tolerates loose overlap, database extraction does not — so
  we report the dependence rather than choosing for the reader. A headline
  threshold may be named in prose but must be a visibly marked point on the
  published curve.
  **[human]** **Right-answer-wrong-reason is the phenomenon this study exists
  to detect**, and it is invisible in marginal citation F1. The
  wrong-answer-with-confident-citations cell is a principle-refinement signal:
  it localises which rule the model believed it was following when it erred.

**Compliance (all conditions).**

- **[locked]** Checker pass-rate over applicable principles, measured in C1,
  C2 **and** C3. Say plainly this is the **mediation variable**, not a
  robustness check. `pass_rate` is principle-level (a principle passes iff it
  passed everywhere it applied), with `pass_rate_micro` over principle ×
  decision pairs alongside.

**Trial-outcome rates are metrics.**

- **[locked]** Parse-failure, coverage-repair, `infeasible_at_length`, and
  completion-truncated rates, per condition / model / length bucket. If C3's
  richer prompt raises parse failures, that is a real cost of the citation
  requirement and appears nowhere else.
- **[locked]** Length stratification is a property of the metrics module — every
  primary metric emerges bucketed. Buckets: ≤4k / 4k–8k / 8k–16k / >16k tokens.
- **[locked]** The causal chain to report: principles → compliance → success;
  citation requirement → Δcompliance beyond provision → Δsuccess.
- **[locked]** CIs are currently normal-approximation and named
  `ci95_normal_approx` so they cannot be misread. **[human]** The writeup
  probably wants bootstrap CIs recomputed from the stored per-trial rows.

## §7 Execution

- **[locked]** Model axis (2026-08-15): `Qwen/Qwen3.5-4B`, `Qwen/Qwen3.5-9B`,
  and `inkling-small`, all via Tinker for now. Model ids are canonical and
  substrate-neutral, resolving to a served name per substrate, so the axis does
  not move when these ids migrate to the desktop GPU.
- **[locked]** **Context windows were measured, not read from documentation** —
  bisected against each endpoint's own error text. inkling-small 262,144;
  both Qwen arms 65,536. An unmeasured model is refused by the backend rather
  than guessed.
- **[locked]** The runner uses `context_limit = advertised − safety_margin`.
  **[human]** Worth reporting: the 9B fails *inside the server* at 65,530 —
  **below its own advertised limit** — with an opaque error, so a band exists
  that passes the documented check and then dies. Its error text also names an
  `--allow-auto-truncate` server flag, meaning silent truncation is one
  upstream config change away. Since every `infeasible_at_length` determination
  and the whole H5 length story depend on truncation never happening quietly,
  the truncation guard (prompt-token count below 80% of estimate → raise) is
  documented as load-bearing, not defensive.
- **[locked]** Feasibility against the real manifest (510 instances, longest
  82,345 tokens; ~1.5k prompt overhead + output reserve): **5/510 infeasible
  for the 4B, 6/510 for the 9B, 0/510 for inkling-small.** On the **holdout,
  exactly 1 contract** is infeasible for both Qwen arms; **dev has zero.**
  **[human]** Two consequences to state: H5's refusal story on the headline
  split rests on a single contract, so the length result is mostly degradation
  rather than refusal; and dev cannot rehearse the infeasibility path at all —
  a direct, now-quantified cost of D-13 (dev max 41,703 vs holdout 64,640).
- **[locked]** **Reference tokenizer verified, not assumed.** Qwen3.5's vocab is
  63% larger than Qwen3-8B's (248,077 vs 151,669), but on contract-shaped text
  the two produce **identical** token counts (0.00% delta across legalese, OCR
  furniture, dates, currency, boilerplate). The reference tokenizer stays
  `Qwen/Qwen3-8B` per D-12 and no caveat is needed — but record that this was
  checked rather than assumed.
- **[locked]** **Two token counts, deliberately distinct.** `length_bucket`
  uses a single fixed reference tokenizer so stratification is comparable
  across models; **feasibility** is decided per backend, with that backend's
  tokenizer and limit, against the **assembled prompt** — meaning C2/C3 can be
  infeasible where C1 is feasible, which is itself a result.
- **[locked]** **Define repair explicitly** — it is a methods commitment, not an
  implementation detail. When a sampled output fails to parse or validate, the
  runner returns it to the model with a message naming the defect and
  re-samples. Three defect classes share one bounded budget, distinguished by
  `failure_detail.stage`: `json_decode` (not valid JSON), `schema_validation`
  (valid JSON, wrong shape), `coverage` (valid shape, targets missing or
  duplicated). Exhausting the budget ends the trial as `parse_failure`.
  The budget is identical across C1/C2/C3, so assistance is symmetric and
  cannot manufacture a condition effect. `repair_stages` records what actually
  fired.
- **[locked]** **Coverage failures are irreducible, and the reason belongs in
  the paper.** "The union of extractions and absent covers each of the 12
  targets exactly once" is a cross-field cardinality constraint that **JSON
  Schema cannot express** — so even a perfect constrained decode permits 11
  extractions with an empty absent list, or a category appearing in both. This
  splits the taxonomy: `json_decode` and `schema_validation` are eliminable by
  correct decoding configuration; `coverage` is not, and measures whether a
  model tracks a 12-way partition over a long document.
- **[locked]** **Scoring is reported twice**: first-attempt (attempt 0,
  unassisted) and final (post-repair). Repair is assistance and models need
  different amounts of it, so equal budgets are not equal help; reporting both
  dissolves the parity problem rather than arguing about it.
  **[human]** State the survivorship caveat plainly. A repair only occurs when
  attempt 0 failed, so `first_attempt == final` whenever no repair happened and
  `first_attempt.parsed` is false whenever one did. "First-attempt score"
  therefore means "score on the subset that needed no help." The honest headline
  is a **pair** — first-attempt parse rate, and first-attempt scores on that
  surviving subset — never the mean alone. `n_scored` is emitted beside every
  scope so denominators stay visible.
- **[locked]** **Output budget is deliberately generous, not tuned per model**
  (16,384 tokens; recorded). Reasoning verbosity differs sharply — on a trivial
  prompt the 4B emits ~2,159 reasoning chars, the 9B ~870, inkling-small ~195 —
  so a tight budget handicaps the smallest model specifically and would
  contaminate H3, making a small model's apparent failure partly our own
  configuration. **[human]** Worth reporting as a caught error, not a silent
  setting: at a 4,000-token budget the 4B produced a `parse_failure` that
  **disappeared entirely** at 16,384 (4/4 ok, zero repairs). Per-model tuning
  was rejected — it would bake a per-model correction into the H3 comparison.
- **[locked]** **Structured-output conformance is a measured outcome.**
  **[pending: evidence probe]** Whether the Tinker endpoint enforces
  `response_format` at all is under independent verification, with raw payloads,
  at `reviews/structured-output-evidence.html`. Two branches, and the writeup
  differs by which holds: if output is genuinely unconstrained, per-model
  valid-JSON and schema-valid rates become a **reported result with CIs**; if
  we were misconfigured (the live hypothesis is vLLM-style `guided_json` rather
  than OpenAI `response_format`), the backend is fixed and only coverage
  remains instrumented. Note the substrate asymmetry either way: ollama's
  `format` genuinely constrains, so the two substrates will not be comparable
  on conformance or on field-absent leakage.
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
- **[locked]** **Trace store — every experiment is re-analysable without
  re-running it.** Per trial *and per attempt within a trial*: the exact
  assembled prompt **as sent** (not template-plus-arguments — a template edit
  would otherwise orphan old traces), the verbatim raw response before parsing,
  `reasoning_content` where the backend separates it, finish reason, truncation
  flag, usage, latency, and the repair message sent on each failure. Non-`ok`
  trials leave traces too, so a refusal can be audited without re-running.
  Compressed per trial, append-only, re-runs go to a fresh `run_id`.
  **[human]** State this as a methods commitment: re-sampling at temperature
  0.7 cannot reproduce a trace, so deleting a run's traces means discarding the
  experiment. The reasoning traces are also expected to be independently
  interesting — they are the artifact the relaxed output budget exists to
  preserve (observed range so far: 5,871–20,634 characters on a single trial).
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
- **[locked]** **Exact verbatim matching is deliberately strict and will read
  as harsh** on contracts with embedded OCR/SEC page furniture: a model emitting
  the clean legal sentence is marked non-verbatim for omitting the scanning
  artifact. That is the behaviour we want measured rather than smoothed away,
  which is why the normalised matcher is reported *alongside* rather than
  instead. **[human]** the pairing is the defence — a reader who thinks the
  exact matcher too strict can read the normalised rate.
- **[locked]** The first-attempt/final split is determined entirely by whether
  repair occurred, so first-attempt scores are conditioned on the
  no-help subset (see §7). Report the pair, never the mean alone.
- **[pending: evidence probe]** If structured output proves genuinely
  unconstrained on Tinker, conformance rates are a limitation *and* a result,
  and the substrate asymmetry with ollama's constrained decode must be stated
  wherever conformance or field-absent leakage is compared.
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
- **[locked]** **The citation × answer-correctness threshold sweep**
  (t = 0.1 … 1.0), four cells as a function of t. Plotly, Morel branding,
  source script + PNG checked in, figure data kept separate from rendering
  code. This is the natural home for the right-answer-wrong-reason series.
- **[pending: gold audit]** Defect rate by type and category, as the span-F1
  ceiling.
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
