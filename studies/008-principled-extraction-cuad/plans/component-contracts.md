# Component contracts — harness (WS5)

Shared study-level code at `studies/008-principled-extraction-cuad/harness/`.
Not an investigation: it is cross-cutting and long-lived, consumed by inv 004,
inv 005, and any later environment.

## Design rule

Condition logic, prompt templates, metrics, and analysis code are **fixed**.
An environment plugs in by supplying (a)–(g) below. If adding AbstentionBench
requires editing anything outside its own env module, the abstraction leaked.

## Environment interface

An environment provides:

- **(a) instance loader** → `{contract_id, title, text, n_tokens, split, gold}`
- **(b) task definition** → `{decision_kinds, targets, target_definitions}`
  - CUAD: decision_kinds `{extraction, absence}`; targets = the ~12-category
    subset with one-line definitions from `category_descriptions.csv`.
  - AbstentionBench: decision_kinds `{answer, abstain}`; targets = none.
- **(c) principle set**
- **(d) gold labels** — terms *and* per-decision principle applicability
- **(e) answer scorer**
- **(f) compliance checkers**
- **(g) a `TaskOutput` subclass + an iterator over its decisions**

The abstraction: *an environment's task definition enumerates decision points;
principles govern how decisions get made; citations attach to decisions.*

**Decision granularity (D-14).** One decision per **target**, always. For CUAD
that is exactly 12 decisions per contract — each category is either an
`Extraction` (with one or more spans) or an `AbsenceClaim`, never both and
never absent from the output. The decision count is therefore fixed by the task
definition, not by the model's output, which is what keeps the citation
denominator stable across models. Span-F1 aggregates *within* a decision.

Beyond the (a)–(g) list, the invariants force three further accessors, which
implementations must provide: instance-level applicability and per-decision
applicability as **separate** calls, a per-decision gold accessor, and an
enumerator of **unrealized decisions** — the targets a trial never produced —
so non-`ok` trials can still write one decision row per target.

## Core models

```python
class Principle(BaseModel):
    id: str                    # "p03"
    statement: str             # the rule, one sentence
    trigger_guidance: str      # when to consider it
    type: Literal["constraint", "procedure", "preference",
                  "disambiguation", "absence"]
    scope: list[str]           # target ids it can touch; [] = global
    provenance: str            # atticus_guidelines | savelka_confusion
                               # | data_mined | authored

class Decision(BaseModel):            # generic base; harness operates on these
    principles_cited: list[str] = []

class Extraction(Decision):           # CUAD
    category: CategoryId
    spans: list[str]                   # verbatim spans, >= 1 (see D-14)

class AbsenceClaim(Decision):         # CUAD
    category: CategoryId

class TaskOutput(BaseModel):          # CUAD concrete version
    extractions: list[Extraction]
    absent: list[AbsenceClaim]         # every category not extracted, explicit
```

`gold_applicability` is held **outside** the prompt, per principle: a checker
`(instance, gold_annotations) -> bool`, per decision point where the principle
is decision-scoped. Programmatic where possible, hand-labeled residual.
**A principle without a feasible checker/labeling plan does not enter the
scored set.**

## Conditions

Single source of truth for prompt assembly. Conditions differ only in these
three switches:

| Condition | Task definition | Principles | Citation required |
|---|---|---|---|
| C1 baseline | yes | no | no |
| C2 principles | yes | yes | no |
| C3 cite | yes | yes | yes |

Task definition is present in **all** conditions — without it the task is
undefined. The schema variant (`principles_cited` field present vs absent in
C1/C2) is a separate axis, resolved by P0 (inv 004).

## Model backends

The runner takes a **pluggable backend** interface, not a hardcoded client. A
backend supplies: a model id, a context-window limit, its **own tokenizer** (so
the runner can emit `infeasible_at_length` without a failed call), a
structured-output mechanism, and a sampling call.

**Two different token counts, and they must not be confused.**

- `n_tokens` / `length_bucket` in the manifest and results store come from a
  **single fixed reference tokenizer** (`Qwen/Qwen3-8B`, per D-12). This is the
  **analysis** axis: length stratification must be comparable across models, so
  it cannot move with the backend.
- **Feasibility** — whether a trial is `infeasible_at_length` — is decided
  **per backend**, with that backend's own tokenizer and context limit, against
  the **assembled prompt** (contract + task definition + principles), not the
  bare contract. A long principle set can push a trial over a limit the
  contract alone would clear, which also means C2/C3 can be infeasible where C1
  is feasible — itself a result.

The same contract can therefore sit in the `8k-16k` bucket for every model
while being feasible for one backend and infeasible for another. That
divergence is the H5 finding, not a bug. Record both: `length_bucket`
(reference) and, on `infeasible_at_length` trials, the backend's measured
prompt-token count and limit in `failure_detail`.

Two backends must work before the harness is considered done, and they must be
tested **separately** — they exercise different failure modes:

1. **Local GPU (ollama on the desktop RTX 3080, via the `desktop-gpu-access`
   skill).** Models: **Qwen/Qwen3.5-4B** and **Qwen/Qwen3.5-9B**. Watch:
   ollama's `format`/JSON-schema path, and the context window actually
   configured on the served model — a silently-truncating `num_ctx` would
   corrupt every `infeasible_at_length` determination in the study.
   **Deferred (2026-08-15): the desktop is offline, so the open-model arms run
   on Tinker for now** (see below). The ollama backend stays built and tested
   against a mock; `probe_ollama.py` runs the moment the box is up. Reviving it
   matters beyond convenience — it is the cheap iteration loop, and it is the
   only backend that exercises constrained decode.
2. **Tinker (inkling-small).** The P0 pilot model and the Phase-2 training
   target. **Both open questions are now answered by measurement (2026-08-15):**
   - Context window is **262,144 tokens** — measured, not documented: 150k
     prompt accepted, 300k rejected with an explicit limit message. Every CUAD
     contract fits with room to spare, so inkling-small will produce **no**
     `infeasible_at_length` trials. H5's length story on this arm is about
     degradation, not refusal.
   - Structured output is **prompt-plus-parse**, not schema-constrained decode:
     `response_format: json_schema` is silently ignored; `json_object` is
     honored. The backend declares this so repair accounting stays honest.
   - Env var is `TINKER_API_KEY`.
   - **Consequence for P0 that must be read carefully**: under a constrained
     decode (ollama) the `principles_cited` field *cannot* appear in the
     field-absent variant, so leakage there is structurally zero. On Tinker it
     can appear. Field-absent leakage rates are therefore **not comparable
     across backends**, and P0's leakage measurement is only meaningful on a
     prompt-plus-parse backend.

**Model axis, as of 2026-08-15.** All three open-model arms run through the
Tinker backend for now: **Qwen/Qwen3.5-4B**, **Qwen/Qwen3.5-9B**, and
**inkling-small** (the P0 pilot and Phase-2 training target). Model ids are
canonical and substrate-neutral (`model_registry.py`), resolving to a served
name per substrate, so the axis does not move when these ids migrate to ollama.

**Measured model facts** (bisected against each endpoint's own error text, not
documentation; an unmeasured model is *refused*, never guessed):

| model | advertised ctx | usable limit | structured output |
|---|---|---|---|
| inkling-small | 262,144 | 261,632 | **`prompt_only`** |
| Qwen/Qwen3.5-4B | 65,536 | 65,024 | **`prompt_only`** |
| Qwen/Qwen3.5-9B | 65,536 | 64,512 | **`prompt_only`** |

`context_limit = advertised − safety_margin` is the runner-facing number.
The margin is not cosmetic: the **9B fails *inside the server* at 65,530
tokens** — below the advertised 65,536 — with an opaque error, so there is a
band that passes the documented check and then dies. Last confirmed acceptance
was 65,357.

**No arm on Tinker gets constrained decode — established by evidence, not
inference** (`reviews/structured-output-evidence.html`). The endpoint accepts
and silently drops every structured-output parameter: 14 request shapes all
returned HTTP 200, *including deliberately invalid controls* that any server
parsing the field would reject, while an unknown `model` does 400 and
`temperature` is honored — so the body is parsed and these keys are dropped.
Corroborated by the docs (the OAI page documents only `model`, `messages`,
`prompt`, `max_tokens`, `temperature`, `top_p`, `separate_reasoning`,
`reasoning_effort`; native `SamplingParams` has six fields and no grammar or
logit-bias surface) and by Thinking Machines' own cookbook proxy, which lists
`response_format` in `_UNSUPPORTED_OPENAI_KEYS` and 400s it by design.
Nothing constrains: `guided_json`, `guided_decoding_backend` (xgrammar,
outlines), `structured_outputs`, `nvext`, `extra_body` nesting, and
`json_schema` with or without `strict`/`name` all match the no-parameter
control exactly.

An undocumented Anthropic-compatible endpoint (`/anthropic/api/v1/messages`,
`x-api-key` auth) accepts `tools` + `input_schema` + `tool_choice`, but does
not enforce either — forced `tool_choice` is ignored — and is **strictly worse
than plain prompting** on the real task across all three models. Not adopted.

**But conformance is not the problem it looked like.** With the schema
serialised into the prompt as `prompts.py` actually does it, all three models
returned **20/20 strict JSON and 19–20/20 schema+coverage valid**. The earlier
"models can't conform" reading came from a *prose-described* schema and was
largely a prompt artifact. Caveat, and it is a real one: those rates are from
one ~350-word synthetic contract, one condition, n=20 — floor-case numbers, not
the study's numbers, since real instances run 8k–82k tokens.

Consequence for P0: field-absent leakage is measurable on **all** current arms,
so P0 is clean today — but the moment ollama returns, its constrained decode
makes field-absent leakage structurally zero there and non-comparable.

**`separate_reasoning` must be set explicitly.** It defaults to `true` and that
default *flipped* from `false` in June 2026. A future flip would silently move
reasoning text back into `content` and corrupt every parse in the study.

The 9B's error text names an `--allow-auto-truncate` server flag. Silent
truncation is one flag away from being enabled upstream, which is the single
failure this study cannot tolerate. The truncation guard
(`prompt_eval_count` below 80% of estimate → raise) is not optional.

**Feasibility against the real manifest** (510 instances, longest 82,345
tokens, ~1.5k prompt overhead + 4k output reserve): 5/510 infeasible for the
4B, 6/510 for the 9B. On the **test, exactly 1 contract** (64,640 tokens) is
infeasible for both Qwen arms; **harness_val has zero**. So the open arms do produce
real `infeasible_at_length` trials, but H5's refusal story on the headline
split rests on a single contract, and harness_val cannot rehearse that path at all —
a direct, now-quantified consequence of D-13 (harness_val max 41,703 vs test
64,640).

**Reference tokenizer: verified, not assumed.** Qwen3.5 has a much larger vocab
(248,077 vs Qwen3-8B's 151,669), but on contract-shaped text the two produce
**identical** token counts (0.00% delta across legalese, OCR furniture, dates,
currency, boilerplate). The reference tokenizer stays `Qwen/Qwen3-8B` per D-12,
no caveat needed. Corollary: pass an explicit tokenizer id on real runs — the
4-chars/token fallback over-estimates CUAD by ~18%, which near a 65k boundary
could wrongly refuse a contract that fits.

A third backend (the frontier API arm) is expected but not yet chosen. The
interface is the deliverable; two working implementations are the test that it
generalizes. If adding the third requires changing anything outside its own
backend module, the abstraction leaked.

**On the "second environment" criterion.** WS5's acceptance says a second
environment should plug in via (a)–(g) alone. AbstentionBench is env #2 and is
deferred, so that criterion is not directly testable in Phase 1. The standing
proxy: the **fake environment** used for harness tests and the **CUAD
environment** are two independent implementations of (a)–(g), and no
condition/metrics/runner code may branch on which one is loaded. That is
testable now.

## Trial runner

- Trial key: `(instance, condition, model, seed, schema_variant)`.
- **Repair policy.** "Repair" = when a sampled output fails to parse or
  validate, the runner sends it back to the model with a targeted message
  naming the defect, and re-samples. Three defect classes draw on one shared,
  **bounded** budget (`max_repair_attempts`), distinguished by
  `failure_detail.stage`:
  `json_decode` (not valid JSON — fence-wrapping, truncation),
  `schema_validation` (valid JSON, wrong shape),
  `coverage` (valid shape, but targets missing or duplicated — D-14).
  Exhausting the budget ends the trial as `parse_failure`.
  Repair is **assistance**, and models need different amounts of it
  (inkling-small: 0 across every trial; both Qwen arms: routinely 1–2), so an
  equal budget is not equal help. This is resolved by scoring every metric
  twice, first-attempt and final — see the Metrics module — not by tuning the
  budget. The budget is identical across C1/C2/C3 so it can never manufacture a
  condition effect, and `repair_stages` on the trial row records what was
  actually repaired.
- Trial outcomes: `ok | parse_failure | infeasible_at_length | api_error`.
- `trial_id` = sha1 of the trial key and deliberately excludes `run_id`, so the
  store's uniqueness invariant makes runs resumable (`skip_existing`). A
  deliberate re-run of the same cell goes to a **fresh store directory**.
- Compliance `pass_rate` is **principle-level** (a principle passes iff it
  passed everywhere it applied); `pass_rate_micro` over principle × decision
  pairs is reported alongside. Both appear in the trial row.
- Context policy: feed the full contract. If it exceeds the model's context,
  record `infeasible_at_length`. Never truncate, never chunk.
- Sampling default: temp ~0.7, ≥3 seeds per instance.
- **Output budget is deliberately generous, not tight** (decided 2026-08-15).
  Reasoning verbosity differs sharply across models (4B ≈ 2,159 reasoning chars
  on a trivial prompt, 9B ≈ 870, inkling-small ≈ 195), so a tight
  `max_output_tokens` would handicap the smallest model specifically and
  contaminate H3 — a small model's apparent failure would partly be our budget.
  Set it high enough that truncation is rare, record the value, and treat any
  `completion_truncated` trial as a reportable outcome rather than a silent
  score. Do not tune it per model.

## Metrics module

Three levels, deliberately never collapsed into one number. Each answers a
different question and the informative one changes with the category's base
rate.

### Level A — the presence/absence call

*When the agent says a category is present or absent, how often is it right,
and what kinds of error is it vulnerable to?*

Per `(contract, category)` the call is binary. **Store the raw 2×2 counts**
(TP / FP / FN / TN) per category — every rate derives from them, and storing
counts rather than rates means any aggregation can be recomputed later without
re-running trials.

Derived and reported:

- **presence-class** P / R / F1 — of claimed clauses, how many exist; of
  existing clauses, how many were found
- **absent-class** P / R / F1 — `absent_class_recall` = TN/(TN+FP),
  `absent_class_precision` = TN/(TN+FN)
- **`decision_kind_accuracy`** = (TP+TN)/total, explicitly labelled as
  base-rate-dominated and never a headline number
- **false-present vs false-absent reported separately.** F1 collapses them, but
  hallucinating a liability cap and missing one are different errors, and
  principles plausibly move them in *opposite* directions — an absence-ruling
  principle should cut false-present while possibly raising false-absent.
- **trivial baselines printed alongside, per category**: always-absent and
  always-present. Non-negotiable. Source Code Escrow has 1 positive in 102
  test contracts and Most Favored Nation has 3, so always-absent scores 99%
  and 97% there; without the baseline a reader cannot tell signal from base rate.

Both classes are reported because the informative one **flips with base rate**:
for rare categories only the presence class carries information; for common
categories (Agreement Date, 93/102 present) always-present already scores 91%,
so only the *absent* class does. Macro-average the two classes **separately**,
never together, and report micro alongside.

The naming here is deliberate: the term "absence accuracy" is retired, because
it could mean overall accuracy, absent-class recall, or absent-class precision.

### Level B — span quality, conditional on agreement

*When a category is present in gold and the agent agrees, how close is its span
set to the gold span set?*

Defined **only on the TP cell**. FP contributes no span score (nothing to
compare against) and FN likewise, so any corpus-level span score must be
reported **with its TP denominator** — otherwise a model that finds three
clauses perfectly and misses nine looks excellent.

- **token-level soft P / R / F1**: each prediction scored against its best gold
  match, each gold against its best prediction, harmonic mean. Aggregated
  *within* a decision over the span sets (D-14).
- **exact-match rate** as the stricter, interpretable companion — "37% of spans
  were verbatim-exact" reads where an F1 of 0.85 does not.
- **verbatim fidelity — three-way, both matchers reported.**
  `Extraction.spans` carries text, not offsets, so nothing otherwise stops a
  paraphrased or normalised span earning partial token-F1 credit. Each span is
  classified:
  1. **exact** — a literal substring of the contract
  2. **normalised-only** — not a literal substring, but a substring after
     normalisation on both sides: whitespace runs collapsed, NFKC unicode
     folding, curly quotes/dashes folded to ASCII, hyphen-linebreak rejoined.
     Normalisation does **not** strip embedded OCR/SEC page furniture — that
     would be a scoring decision in disguise (D-15).
  3. **not found** — present under neither matcher
  Report all three rates. The exact matcher stays primary and is deliberately
  strict: after D-15 it will mark a model non-verbatim for emitting the clean
  legal sentence while omitting embedded page furniture, and that is the
  behaviour we want measured rather than smoothed away.
  The **gap between exact and normalised quantifies how much apparent
  non-verbatim output is merely cosmetic**, and the **not-found rate is the one
  that means invented contract language** — a categorically different, and in a
  legal-extraction framing more serious, failure than picking the wrong clause.
  Never fold any of this into token-F1.
- **span position** — the located character offset of each verified span,
  giving depth-into-document. This is a sharper H5 instrument than contract
  length alone: it separates "long contracts are harder" from "the model stops
  reading after N tokens."
- **multi-span recovery** — predicted vs gold span counts per decision, so
  "found the clause, missed its two cross-references" is visible.

### Level C — citation quality (C3)

*When the agent makes a decision, do its cited principles match the gold
applicable set?*

- per-decision **P / R / F1** against the **scope-relevant slice** of gold
  applicability, with explicit tp/fp/fn lists retained
- **per-principle marginal P / R / F1** — which principles are cited well and
  which are systematically confused. This *is* H4 and it is what makes the
  principle set maintainable.
- **confusion matrix** over principle ids, built by pairing fp against fn within
  a decision ("cited p03 where p11 applied")
- **F1, not recall**, so cite-everything cannot win
- **citation cross-tabulated by answer correctness, swept over the correctness
  threshold** — not a single 2×2. "Answer correct" depends on a span-F1
  threshold, so the cross-tab is computed at **t = 0.1 … 1.0 in 0.1 steps** and
  reported as a curve: each of the four cells as a function of t. Deterministic,
  cheap (it re-buckets stored per-decision scores; no re-running), and it
  removes the single most arbitrary constant in the metrics. The right threshold
  is use-case dependent — how much span overlap counts as "got it" differs
  between a reviewer triaging clauses and one extracting them verbatim — so we
  report the dependence instead of picking for the reader. A single headline
  threshold may still be named in the writeup, but it must be visibly one point
  on a published curve.
  The 2×2 at each t is
  {answer right, answer wrong} × {citation right, citation wrong}.
  **Right-answer-wrong-reason is the phenomenon this study exists to detect**
  and it is invisible in marginal citation F1. If citation helps by forcing
  deliberation, the right-answer cell should be enriched for correct citations.
  The wrong-answer-with-confident-citations cell is a **principle-refinement
  signal**: it localises which rule the model believed it was following when it
  erred. Secondary to the core question, but cheap and worth keeping.

### Compliance (all conditions)

Checker pass-rate over applicable principles, measured in **C1, C2 and C3**.
It is the **mediation variable**, not a robustness check. `pass_rate` is
principle-level (a principle passes iff it passed everywhere it applied);
`pass_rate_micro` over principle × decision pairs is reported alongside.

### Trial-outcome rates are metrics

Parse-failure, coverage-repair, and `infeasible_at_length` rates — per
condition, per model, per length bucket. If C3's richer prompt raises parse
failures, that is a real cost of the citation requirement and it appears
nowhere else.

### Scoring is reported twice: first-attempt and final

Every scoreable metric is computed both on the **first sampled output** and on
the **post-repair final output**. First-attempt is the unassisted number and is
the fair cross-model comparison; final is the assisted one. Reporting both
dissolves the repair-parity problem rather than arguing about it, and costs
nothing because both outputs are already stored.

### Aggregation and stratification

Length stratification is a property of this module, not of individual analyses
— every primary metric emerges bucketed (≤4k / 4k–8k / 8k–16k / >16k tokens).
Macro-over-categories and micro-over-decisions are both reported; macro is
never taken across the two Level-A classes.

Causal chain to report: principles → compliance → success; citation
requirement → Δcompliance beyond provision → Δsuccess.

### Not computed, and why

CUAD's own benchmark metrics are AUPR and Precision@80%Recall, which assume a
retrieval-ranking setup. This is generative extraction with no candidate
ranking, so they are not computable here. That is a **second** reason our
numbers are not leaderboard-comparable, on top of contamination.

## Trace store — tier 1

**Every experiment must be re-analysable without re-running it.** That is a
first-class requirement, not a debugging convenience: reasoning content,
repair sequences, and the exact prompt sent are all things we will want to
mine after the fact, and re-sampling at temp 0.7 cannot reproduce them.

Per trial, and per **attempt** within a trial (attempt 0 = first sample, then
one per repair), persist:

- the **exact assembled prompt as sent** — not the template plus arguments, the
  final string. Template version alone does not survive a template edit.
- the **raw response body**, verbatim, before any parsing
- **`reasoning_content`** where the backend separates it (Tinker does). This is
  the artifact the dropped output-budget constraint exists to preserve; the
  reasoning traces are expected to be independently interesting.
- `finish_reason`, `completion_truncated`, token usage, latency
- the parse outcome for that attempt and, on failure, the repair message sent

Layout: `data/traces/<run_id>/<trial_id>.json`, joined to `trials.jsonl` by
`trial_id` and verified by `response_sha256`. Append-only; never rewritten by a
re-run, which goes to a fresh `run_id`.

**Git policy.** Traces are bulk and stay gitignored, but "not in git" must not
mean "not durable" — they are the reason a re-run is unnecessary. Keep them on
disk, compressed per run, and treat deleting a run's traces as discarding the
experiment. The scored records in git remain the auditable summary; the traces
are the raw material behind them.

## Results store

Two append-only JSONL files per run, both in git; `response_sha256` joins them
to the trace store above.

**Why two levels.** Trial-level rows answer "did this trial run, and how well
did it do overall" (H1, H5, parse failures, feasibility). Decision-level rows
are what citation P/R/F1, the H4 confusion matrix, and Phase-2 reward
extraction actually consume — those are per-decision quantities and flattening
them into the trial row would destroy them.

### `trials.jsonl` — one row per trial key

```jsonc
{
  "trial_id": "sha1 of the trial key, for joins",
  // --- key ---
  "contract_id": "LOHACORP_...",
  "condition": "C1" | "C2" | "C3",
  "model": "inkling-small",
  "seed": 0,
  "schema_variant": "field_present" | "field_absent",

  // --- provenance ---
  "run_id": "2026-08-20T14:03:11Z-p0",   // groups trials from one invocation
  "prompt_template_version": "v3",
  "principle_set_version": "locked-2026-08-18",
  "harness_git_sha": "abc1234",
  "temperature": 0.7,
  "response_sha256": "…",                 // join to the local raw response
  "n_prompt_tokens": 7412,
  "n_completion_tokens": 903,
  "latency_ms": 18420,

  // --- outcome ---
  "outcome": "ok" | "parse_failure" | "infeasible_at_length" | "api_error",
  "n_repair_attempts": 0,                 // bounded; see repair policy
  "repair_stages": [],                    // e.g. ["json_decode","coverage"].
                                          // Records the DEFECT stages observed,
                                          // whether or not a repair followed —
                                          // under D-16 the budget is 0, so a
                                          // defect is terminal and no repair is
                                          // attempted. Name is kept for store
                                          // compatibility; read it as defects.
                                          // A count alone cannot distinguish a
                                          // JSON problem from a coverage one.
  "failure_detail": null,                 // parse/context numbers, plus
                                          // finish_reason, completion_truncated,
                                          // n_reasoning_chars — so a blown
                                          // reasoning budget is never misread
                                          // as a formatting failure

  // --- instance context (denormalized so analysis needs no join) ---
  "n_contract_tokens": 6412,
  "length_bucket": "4k-8k",
  "split": "harness_val" | "test",

  // --- trial-level scores (null when outcome != "ok") ---
  // NOTE: this sketch is illustrative. The Metrics module section above is
  // authoritative; regenerate this block from a real row rather than trusting
  // the field names here.
  "answer": {                             // FINAL (post-repair) scores
    "level_a": {"per_category": {"Governing Law": {"tp": 1, "fp": 0,
                                                   "fn": 0, "tn": 0}}},
    "level_b": {"soft_f1": 0.61, "exact_match_rate": 0.37,
                "verbatim_rate": 1.0, "n_tp": 9}
  },
  "first_attempt": { /* same shapes, plus parsed + failure_stage */ },
  "correctness_thresholds": {"answer_span_f1": 0.5, "citation": "exact_set"},
  "compliance": {                         // ALL conditions, incl. C1
    "n_applicable": 7, "n_passed": 5, "pass_rate": 0.714,
    "per_principle": {"p03": true, "p11": false}
  },
  "citation": {                           // null outside C3
    "precision": 0.72, "recall": 0.55, "f1": 0.62,
    "micro_over_decisions": true
  },
  "leakage": {                            // P0 instrument; cheap, always on
    "n_decisions_with_nonempty_cited": 0,
    "text_field_principle_refs": 0        // regex scan of all free-text fields
  }
}
```

### `decisions.jsonl` — one row per decision within a trial

```jsonc
{
  "trial_id": "…",                        // join key
  "decision_idx": 4,                      // the TARGET's position in the task
                                          // definition — stable across trials,
                                          // models, conditions and seeds, so
                                          // index N is the same category
                                          // everywhere and rows join without
                                          // carrying the target string
  "decision_kind": "extraction" | "absence",
  "target": "Agreement Date",             // category id; null in target-less envs

  "predicted": {"spans": ["signed on , in Hong Kong"],  // null for absence
                "verbatim": [true], "char_offsets": [4127]},
  "gold": {"spans": [], "is_impossible": true},

  "answer_score": {"span_f1": 1.0, "correct_kind": true},

  "principles_cited": ["p03"],            // as emitted
  "gold_applicable": ["p03", "p11"],      // scope-relevant slice only
  "citation_eval": {                      // null outside C3
    "tp": ["p03"], "fp": [], "fn": ["p11"],
    "precision": 1.0, "recall": 0.5, "f1": 0.667
  },
  "compliance_eval": {"p03": true, "p11": false}
}
```

**Invariants.**

- `gold_applicable` is the **scope-relevant slice** for this decision, not the
  instance-wide applicability set — citation precision is otherwise unfair to
  any model that doesn't cite globally-scoped principles everywhere.
- Every category not extracted produces an `absence` decision row. Absence is
  an explicit decision, never an empty slot.
- Rows are written for non-`ok` trials too, with score fields null. Dropping
  them would silently bias H5.
- `(trial_id, decision_idx)` is unique; both files are append-only and
  rebuildable from raw responses + the principle set version.
- The H4 confusion matrix is built by pairing `fp` against `fn` within a
  decision row — i.e. "cited p03 where p11 applied" — so it must be derivable
  from `decisions.jsonl` alone.
