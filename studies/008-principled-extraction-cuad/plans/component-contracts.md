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
    text: str                          # verbatim span

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
backend supplies: a model id, a context-window limit (so the runner can emit
`infeasible_at_length` without a failed call), a structured-output mechanism,
and a sampling call.

Two backends must work before the harness is considered done, and they must be
tested **separately** — they exercise different failure modes:

1. **Local GPU (ollama on the desktop RTX 3080, via the `desktop-gpu-access`
   skill).** Target model: **qwen3.5:8b**. This is the ~8B arm of the model
   axis and the cheap iteration loop. Watch: ollama's `format`/JSON-schema
   path, and the context window actually configured on the served model —
   a silently-truncating `num_ctx` would corrupt every `infeasible_at_length`
   determination in the study.
2. **Tinker (inkling-small).** The P0 pilot model and the Phase-2 training
   target. Watch: availability and real context window (open question), and
   whether structured output comes from a schema-constrained decode or from
   prompt-plus-parse — the repair-policy accounting differs.

A third backend (the frontier API arm) is expected but not yet chosen. The
interface is the deliverable; two working implementations are the test that it
generalizes. If adding the third requires changing anything outside its own
backend module, the abstraction leaked.

## Trial runner

- Trial key: `(instance, condition, model, seed, schema_variant)`.
- Structured-output parsing with a **bounded** repair policy: log parse
  failures as a trial outcome, do not silently retry beyond N.
- Trial outcomes: `ok | parse_failure | infeasible_at_length`.
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
  "decision_idx": 4,                      // order from the TaskOutput iterator
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
