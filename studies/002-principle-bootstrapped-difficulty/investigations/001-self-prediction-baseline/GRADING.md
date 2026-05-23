# Answer-correctness grading workflow (sketch)

Self-prediction facets F1 (capability without tools) and F2 (capability
with tools) need a ground-truth label for whether the *model's actual
A4 response* contained a correct answer. `classify_trial` measures
behavior calibration (right tool / correct abstention), not answer
correctness. We need a separate pipeline.

## Two-tier grader

**Tier 1 — programmatic**, where the ground truth is deterministically
derivable from the task:

| Tool family | Approach | Notes |
|---|---|---|
| `calculator` | Parse expression from `user_prompt`; eval safely; substring/regex match the numeric answer in the model's final user-facing text | Need a safe arithmetic parser (no raw `eval`). Handle commas, scientific notation, rounding. |
| `unit_convert` | Parse "<n> <unit_a> to <unit_b>" pattern; compute via a unit library; match numeric answer | `pint` library handles most. Tolerance for rounding. |
| `datetime_now` | Resolve query type (today's date, day-of-week, days-until-X, etc.); compute against the runtime-anchor date | Runtime-anchor is `2026-05-11` per `kb/*.json`. Be careful: the model might use its own current-date assumption. |
| `python_execute` | Run the implied computation in a sandbox; compare to model output | Hardest. Heuristic: pull numeric/string answer from model output, run a minimal computation derived from `user_prompt`. Punt: defer to LLM judge for python. |
| `general_knowledge_lookup` | Look up the relevant entry in `studies/001-tool-calibration/kb/general_knowledge_real.json` via the same alias matching the tool would do; fuzzy text match the snippet against the model's response | Use the *real* KB (not the fabricated `general_knowledge.json`). Note in writeup: a correct-by-real-world answer may differ from a correct-by-fabricated-KB answer; consider running both. |
| `user_knowledge_lookup` | Look up the relevant `user_knowledge.json` entry via alias matching; check value presence in the model's response | For records where the answer is in the prompt itself, the curator's expected behavior is `answer_directly` — grader checks whether the answer appears in the response. |

Tier 1 grader output schema per (record, trial):

```json
{
  "record_id": "...",
  "trial_index": 3,
  "grader": "programmatic.calc.v1",
  "answer_correct": true | false,
  "extracted_answer": "8832354",
  "expected_answer": "8832354",
  "notes": "exact match"
}
```

When tier 1 can't grade confidently (ambiguous extraction, format
mismatch, missing KB entry), it emits:

```json
{
  "record_id": "...",
  "trial_index": 3,
  "grader": "programmatic.calc.v1",
  "answer_correct": null,
  "fallback_reason": "no_numeric_answer_in_response",
  ...
}
```

**Tier 2 — LLM-as-judge (Haiku 4.5)**, called only on rows where tier
1 returned `answer_correct == null`. Uses a Claude Code subagent.

Subagent prompt skeleton (per batch of ~50 trials):

```
You are an answer-correctness grader. For each trial below, decide whether
the model's response contains a correct answer to the user's question.

Be strict on numeric answers (off-by-one is wrong). Be lenient on phrasing
(any equivalent expression of the same fact is correct). When the model
refused or said "I don't know," answer_correct=false.

Trials:
  [batch of 50 trials, each with: record_id, user_prompt, expected_answer (if known),
   model_response]

Return JSON: [{record_id, trial_index, answer_correct: bool, justification}, ...]
```

## Batching for context

Per trial: ~750 tokens input (system + user_prompt + model_response + schema) + ~80 tokens output. At 50 trials per subagent invocation, ~40K context per invocation. Comfortable within a Haiku subagent's window.

Volume to grade for 4B IT only (no A4 12B grading yet per current scope):

- Trials where `classify_trial` returned non-success: ~30% × 3,660 = ~1,100
- Sample of success trials for validation: ~10% × 2,560 = ~256
- Total: ~1,356 trials
- After dedup by (record_id, output_hash): probably ~800 unique
- Subagent invocations: ~16 at 50/batch

**Cost on Haiku 4.5:** ~600K input tokens × $0.80/M + ~50K output × $4/M ≈ $0.70 total. Fast and cheap.

**Cost on Opus 4.7 (if escalation needed):** same volume × ~20× pricing ≈ $14. Still cheap, but reserve Opus for spot-checks where Haiku and tier-1 disagree.

## Implementation order

1. **Tier 1 graders for the four programmatically-tractable tools**
   (calc, unit_convert, datetime_now, and gkl via KB lookup) — write
   first, validates on the existing A4 jsonls.
2. **Haiku-subagent grader** — implemented as a `grade.py` script that
   reads the trial JSONLs, builds batches, spawns Claude Code subagents
   via the Agent tool (with `subagent_type: claude` and model override
   to haiku-4.5), collects judgments.
3. **Validation pass**: on a sample of ~100 trials, run Opus-judge,
   compare to Haiku-judge + tier 1. Estimate the inter-grader agreement.
   If <90%, escalate the workflow.
4. **Compute F1 and F2** facets in `analyze.py` using the merged grading
   output.

## What's deferred

Don't build this yet. The four-question self-prediction sweep on the
full corpus is the gating step — F1 and F2 only matter if the
self-prediction data shows any signal worth correlating. Build tier 1
graders after the self-prediction sweep lands, then the Haiku subagent
pipeline.
