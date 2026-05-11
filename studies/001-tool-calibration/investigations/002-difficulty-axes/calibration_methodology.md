# Calibration methodology (A2 / "A4 thresholds")

Per Decision 13, the schema's `difficulty_calibrated` field stores
raw empirical signal per model (`success_rate`, `n`, `last_run`).
Bucket assignment from `success_rate` into the 5-level difficulty
enum happens at analysis time using thresholds defined here, *not* at
data-write time. Changing the thresholds therefore does not require
re-running any calibration trials — it's a config change.

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
