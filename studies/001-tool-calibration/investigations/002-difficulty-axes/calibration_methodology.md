# Calibration methodology (A2 / "A4 thresholds")

Per Decision 13, the schema's `difficulty_calibrated` field stores
raw empirical signal per model (`success_rate`, `n`, `last_run`).
Bucket assignment from `success_rate` into the 5-level difficulty
enum happens at analysis time using thresholds defined here, *not* at
data-write time. Changing the thresholds therefore does not require
re-running any calibration trials — it's a config change.

## Sampling defaults (Decision in `004-calibration-pilot`, 2026-05-12)

Default sampling for calibration trials: `temperature=1.0,
top_p=0.95`. Original pilot used `temperature=0.0` (greedy); reviewer
flagged this as a legacy convention that doesn't cleanly probe how
models actually behave in deployment. Future runs use the new
defaults; the 4B IT pilot data is preserved as a deterministic
baseline. Captured in `harness/inference.py`.

## Error-type classification (Decision 2, 2026-05-12)

Beyond success vs. failure, every failed trial is classified as one
of three error types — distinguishing **how undesirable** the
failure is. Per reviewer direction, severity ordering (worst →
least undesirable): `under_call > wrong_tool > over_call`.

- **`over_call`** — the model invoked the target tool when none was
  warranted (or invoked any tool when none was warranted).
  *Least undesirable.* The tool typically returns the correct
  answer anyway, so over-calling produces correct outputs at the
  cost of unnecessary tool invocations. A model that consistently
  over-calls has a *cost* problem, not an *accuracy* problem.

- **`wrong_tool`** — the model invoked some tool, but not the
  target. *Intermediate.* The model correctly recognized that a
  tool was needed but picked the wrong one. Surfaced by the
  SHA-256 / sum-of-primes cases in the 4B IT pilot
  (`../004-calibration-pilot/`), where the model invoked
  `calculator` with python-style expressions instead of
  `python_execute`.

- **`under_call`** — the model invoked no tool when a target was
  warranted. *Most undesirable.* The model likely produced a wrong
  or fabricated answer in lieu of the lookup/computation it should
  have used. This is the failure mode the matched-pair design is
  most worried about.

The runner records `error_type` per trial alongside `success`. The
analyzer aggregates by record and reports per-record over_call /
under_call counts at each N checkpoint. Whether to weight these
asymmetrically in the bucket-assignment thresholds (e.g., penalize
under-calls more in `calibration_status: contested` detection) is an
open question — for the first calibration pass we treat both as
equal failures, with the asymmetry captured in the per-record
breakdown rather than baked into the bucket boundaries.

## Per-record success criterion

A trial is **scored success** when the target model's behavior on a
record matches the record's `expected_tool_call` field for the
record's `tool_target`:

| `expected_tool_call` | success iff … |
|----------------------|---------------|
| `true`               | the model invokes `tool_target` (any argument shape) |
| `false`              | the model does NOT invoke `tool_target` |

For records with `tool_target: none` (control prompts), `success` =
the model invokes no tool at all.

This is the *anticipatory* calibration check Phase A1 was designed
for. The *interpretive* calibration check ("did the model use the
returned snippet correctly?") is deferred to investigation 004
(tool-failure-recognition) and may use a separate methodology.

## Bucket thresholds — success_rate → difficulty enum

```
success_rate < 0.05            → extreme
0.05  ≤ success_rate < 0.30    → hard
0.30  ≤ success_rate < 0.70    → medium
0.70  ≤ success_rate < 0.95    → easy
0.95  ≤ success_rate           → trivial
```

Symmetric around `medium` to match the curator-enum semantic (medium
is the calibration boundary). Boundaries are defaults — revisit if
post-hoc analysis on the bulk corpus shows bimodal or non-monotone
behavior.

## Trial count

Default `n = 20` per (record, model). Standard error of a binomial
proportion at n=20 is √(0.5·0.5/20) ≈ 0.11, which is tight enough to
distinguish adjacent buckets at the band midpoints with reasonable
confidence. Higher-stakes records (especially records sitting at
bucket boundaries) can be sampled at `n = 50` in a re-run pass.

The minimum sufficient n for a bucket assignment is recorded in
`difficulty_calibrated[model_id].n`, so downstream analyses can
filter on confidence.

**Checkpointing for retrospective sufficiency analysis.** The runner
always writes per-trial data with a stable `trial_idx`, so the
analyzer can compute success_rate at any sub-N (default checkpoints:
5, 10, 20). After a full run, retrospective comparison of
success_rate@5 / @10 / @20 surfaces which records had clean signal
early (bucket stable across checkpoints) and which were noisy
(bucket changed with N). This drives future-experiment sizing —
records that converge at n=5 can be cheaper to recalibrate;
boundary records may justify n>20.

## `calibration_status: contested`

A record's bucket is **contested** when, for some target model,
the empirical bucket (from `success_rate` under the thresholds above)
differs from `difficulty_label.value` by more than one band. E.g.,
LLM-curator said `hard`, empirical is `medium` → not contested (one
band away). LLM-curator said `hard`, empirical is `trivial` → contested
(three bands away).

Contested records are research signal in two directions:

- The curator-LLM (claude-opus-4-7 by default; see seeds_spec.yaml
  metadata) miscalibrated. Either model-specific (one target model
  found it easy, others hard) or curator-side miscalibration.
- The seed prompt is ambiguous — different runs produce wildly
  different rates, indicating sensitivity to factors the matched-pair
  design tried to hold constant.

## Multi-tool seeds

For pairs where multiple tools could plausibly satisfy the prompt
(e.g. pair 5 hard, where both `python_execute` and `calculator` could
sum primes), the `tool_target` field still identifies *the* tool the
prompt was designed to probe. The success criterion checks only that
tool — calling a different tool still counts as failure for the
target. This is deliberate: matched-pair design isolates one decision
at a time. Future investigations may want to track tool-choice
ambiguity as a separate signal.

## Open questions

- **N sufficiency for boundary cases.** For records that land near
  bucket boundaries (e.g., success_rate around 0.30 or 0.70), how
  many trials are needed to distinguish "this is genuinely boundary"
  from "we just haven't sampled enough"? After the first full
  calibration run, sweep the per-record checkpoint data (n=5, 10,
  20) and characterize convergence-vs-N. If most records stabilize
  by n=10, default future runs to n=10 and reserve n=20+ for
  identified boundary records.
- Should bucket thresholds be tool-agnostic (as drafted) or per-tool?
  Different tools may have different baseline call rates, so the same
  success rate may carry different signal.
- How should `expected_call_confidence: medium` records (pairs 8 and
  10) be graded? Default: same as `high` confidence records, with
  divergence reported in the analysis layer rather than absorbed into
  the bucket assignment.
- What's the cost/benefit of running framing-variant trials
  (`sys_all_tools_proactive_v1` swapped for `sys_all_tools_neutral_v1`)
  on the same records? Cheap to run since seeds are fixed; surfaces
  framing-sensitivity directly. Likely belongs in A2 or as a separate
  short investigation.

## To freeze in this investigation

- Per-tool difficulty axes (the *original* A2 scope; see
  investigation.md).
- Bucket thresholds (this doc).
- Trial count defaults.
- Pass/fail semantics including the "none" / control-prompt case.
