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
**inkling-small** (the P0 pilot and Phase-2 training target). The two Qwen
models are also available on the desktop GPU once it is back, so the same
model ids move to the ollama backend without changing the model axis — which
is the point of the backend abstraction, and incidentally gives a clean
same-model / two-substrate comparison if we ever want one.

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
- Structured-output parsing with a **bounded** repair policy: log parse
  failures as a trial outcome, do not silently retry beyond N.
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

## Metrics module

- **Answer** — token-level span F1 (Jaccard-style, per the LLM-era CUAD
  literature) + exact category match + absence accuracy. Reported per-category
  and length-stratified.
- **Compliance** — checker pass-rate over applicable principles. Measured in
  **all** conditions (C1/C2/C3); it is the mediation variable.
- **Citation (C3 only)** — per-decision precision / recall / F1 of cited ids
  against the scope-relevant slice of gold applicability, plus a confusion
  matrix over principle ids (feeds H4).

Causal chain to report: principles → compliance → success; citation
requirement → Δcompliance beyond provision → Δsuccess.

Length stratification is a property of the metrics module, not of individual
analyses — every primary metric comes out bucketed.

## Results store

Two append-only JSONL files per run, both in git. Raw model responses stay
local (see the study's Repository policy); `response_sha256` is the join key
back to them.

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
  "failure_detail": null,                 // parse error / context-limit numbers

  // --- instance context (denormalized so analysis needs no join) ---
  "n_contract_tokens": 6412,
  "length_bucket": "4k-8k",
  "split": "dev" | "holdout",

  // --- trial-level scores (null when outcome != "ok") ---
  "answer": {
    "span_f1_macro": 0.61,                // mean over the ~12 categories
    "absence_accuracy": 0.83,
    "per_category": {"Governing Law": {"span_f1": 0.9, "kind": "extraction"}}
  },
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

  "predicted": {"text": "signed on , in Hong Kong"},  // null for absence
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
