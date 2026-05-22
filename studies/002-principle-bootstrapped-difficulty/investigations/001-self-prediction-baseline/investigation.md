---
id: studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline
title: Self-prediction baseline — does the target model know what's hard for itself?
status: planned
parents:
  - studies/002-principle-bootstrapped-difficulty
children: []
related:
  - studies/001-tool-calibration/investigations/004-calibration-pilot
  - studies/001-tool-calibration/investigations/007-axes-performativity
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - methodology
  - self-prediction
  - baseline
aliases:
  - 002-001
  - self-pred-baseline
created: 2026-05-22
updated: 2026-05-22
---

# Investigation 1 — Self-prediction baseline

## Scope

Before introducing any principle-library machinery, establish the
empirical baseline: **how well does the target model predict its own
tool-call success?**

Concretely, for each (record, model) pair in the bulk corpus, prompt the
model — once — with the user query, the available tools, and a
structured-output request:

```
predicted_outcome: success | over_call | under_call | wrong_tool
confidence: low | medium | high
reasoning: <prose>
```

Compare each prediction to the empirical success rate from
[[investigation-007]]'s A4 grading (n=10 trials per record under neutral
baseline, temp=1.0).

This investigation introduces no principles. It tests only the raw
self-assessment capability — a calibration of the calibrator. Whatever
predictive accuracy the model achieves here is the baseline that
principle-library work needs to beat.

## Questions

1. **Headline accuracy.** Across the bulk corpus, what fraction of
   predictions match the empirical modal outcome?
2. **Confidence calibration.** Does `confidence=high` predict accuracy
   better than `confidence=low`? Or is the confidence signal noise?
3. **Per-tool breakdown.** Is the model better at predicting its own
   behavior on some tool families than others? (Hypothesis from
   [[investigation-007]]: `general_knowledge_lookup` and
   `user_knowledge_lookup` are easier to self-predict than
   `python_execute` — the latter requires two recognitions, not one.)
4. **Per-model comparison.** Does 12B IT self-predict more accurately
   than 4B IT? If yes — by how much, and is the gain uniform across
   tools?
5. **Error-mode prediction.** Beyond `predicted_outcome`, the model
   predicts the *kind* of failure. When the model says "under_call,"
   does it actually under-call? Diagnostic for which failure modes the
   model is self-aware about.
6. **Reasoning quality.** Qualitative: when the model is correct, does
   the reasoning surface anything coherent? When wrong, is there a
   pattern? This seeds the first batch of candidate principles for
   investigation 002.

## Methods

1. **Build the self-prediction prompt.** A new prompt template
   `prompts/self_predict_v1.txt` that frames the task: "Here is a user
   query and the tools available to you. You will not actually answer.
   Predict whether you would handle this correctly..." Structured
   output via the existing Pydantic shape (see `models.py` — define a
   `SelfPredictionResponse` extending the structured-output pattern).
2. **Run once per record per model.** n=1 is sufficient for the baseline
   — we are not measuring stochasticity of the prediction, we are
   measuring whether one sample correlates with empirical mode.
   Stochasticity of self-prediction is a follow-on question.
3. **Align with empirical labels.** Empirical bucketing is per-model;
   read it from [[investigation-007]] output. A record's "empirical
   outcome" is the modal `error_type` (or `success`) across its 10
   neutral-baseline trials.
4. **Score.** Per-record agreement, per-tool agreement, confusion
   matrices, per-confidence-band accuracy.

## Decisions

_Populate as work proceeds._

## Results

_Pending. Gated on [[investigation-007]] A4 grading completing for both
4B IT and 12B IT on the bulk corpus._

## Forward-looking

Whatever the headline accuracy turns out to be, the *reasoning* outputs
are the seed material for investigation 002. Specifically:

- Where reasoning correctly identifies a load-bearing feature →
  candidate principle.
- Where the prediction is wrong but the reasoning sounds plausible →
  candidate principle that needs an empirical check to distinguish
  rationalization from insight.
- Where the prediction is right but the reasoning is incoherent → flag
  for the "citation faithfulness" thread (study.md motivation §).

## Things to flag

- Self-prediction prompt phrasing has known sensitivity. The wording
  here will be a confound. Worth a small prompt-variation A/B before
  treating the baseline as authoritative.
- The model's `predicted_outcome` is over a 4-class label
  (success/over/under/wrong_tool). Disagreement at the failure-mode
  level (predicted over_call, actually under_call) is informative even
  when the binary success/fail prediction matches.
- Empirical "modal outcome" can be ambiguous when n=10 splits 5-5.
  Treat those as "uncertain ground truth" and exclude from headline
  accuracy; report them separately.

## Limitations

- One-shot prediction. Whether the prediction is stable across
  resamples is a separate question.
- Gemma-only. Cross-family self-prediction is a future-direction.
- Per-record labels are model-relative. The "same" record has different
  ground-truth labels for 4B vs 12B; that's correct and intended.
