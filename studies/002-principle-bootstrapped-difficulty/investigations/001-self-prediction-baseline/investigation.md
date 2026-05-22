---
id: studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline
title: Self-prediction baseline — does the target model know what's hard for itself?
status: planned
parents:
  - studies/002-principle-bootstrapped-difficulty
children: []
related:
  - studies/001-tool-calibration/investigations/004-calibration-pilot
  - studies/001-tool-calibration/investigations/006-temperature-prompt
  - studies/001-tool-calibration/investigations/007-axes-performativity
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - methodology
  - self-prediction
  - control-group
aliases:
  - 002-001
  - self-pred-baseline
created: 2026-05-22
updated: 2026-05-22
---

# Investigation 1 — Self-prediction baseline

## Scope

A **control-group experiment** for [[study-002-principle-bootstrapped-difficulty]].
Strip away every part of the study's eventual methodology — no principles,
no researcher-LLM critic, no actor-critic loop. The single question:

> **Does the target model know what's hard for itself?**

We already have empirical labels for what each Gemma model does on the
bulk corpus (n=10 trials per record under neutral baseline, temp=1.0, via
A4 grading). What we don't have is what each Gemma model **thinks** it
will do. This investigation gets that data and compares the two.

Result of investigation 1 is the floor for everything else study 002
might do. If the model has no useful self-prediction signal, the
principle-extraction premise is weakened (though not killed —
researcher-extractable signal in the reasoning text could survive even
when the predicted class is noise). If it has signal, we have something
to bootstrap from.

## Primary question

**Q1 — Does Gemma's self-prediction correlate with empirical outcome,
and how does that vary across tools?**

For each (record, model) pair:

- Ask the target model to predict what it would do on the task and
  whether it would handle it correctly. n=1 sample.
- Compare the prediction to the empirical modal outcome from A4
  grading (10 trials/record under the same prompt and sampling).
- Aggregate per tool: precision and recall against the empirical
  outcome, with bootstrap CIs.
- Aggregate per model: 4B vs 12B head-to-head.

This mirrors the per-tool analysis structure used for Opus's external
predictions in 006, so results drop cleanly alongside them.

## Secondary question

**Q2 — Where Gemma's self-prediction is correlated with outcome, is
that signal different from what Opus extracts from the same prompt?**

We already have Opus's external predictions for every record (the same
data analyzed in 006). Gemma's self-prediction and Opus's external
prediction are both functions of the same prompt — if they agree on
which records are trivial, self-prediction may just be reading surface
features the way Opus does, not the model knowing itself. If Gemma adds
signal on tools where Opus doesn't (especially the math-adjacent Group B
tools where Opus is at baseline), that's a more interesting finding.

Q1 is the headline; Q2 is a free secondary analysis since we have the
Opus data already. Don't overweight it in the writeup.

## Methods

1. **Self-prediction prompt** (`prompts/self_predict_v1.txt`). Embed the
   task's `system_prompt` and `user_prompt` as data. Frame the prediction
   as meta — "predict what you would do; do not actually do it." Use
   JSON output with the `SelfPredictionResponse` schema (see
   `../../models.py`).

   Critical design choice: **do not tell the model the expected
   behavior.** That would anchor the prediction. The model predicts its
   own `(predicted_behavior, predicted_tool, predicted_success)`; the
   analyzer compares those to the curator-specified
   `(expected_tool_call, tool_target)` to derive the predicted outcome
   class.

2. **Run once per record per model.** n=1 sample is sufficient — we are
   not measuring stochasticity of the self-prediction, we are measuring
   whether one sample correlates with the empirical mode. Stochasticity
   of self-prediction is a follow-on question.

3. **Score against empirical mode.** A record's empirical outcome for a
   model is the modal `error_type` (or `success`) across its 10 trials
   from A4. The predicted outcome class for a record is derived from
   `(predicted_behavior, predicted_tool, expected_tool_call,
   tool_target)`:
   - `predicted_behavior=call_tool ∧ expected_tool_call=true ∧ predicted_tool=tool_target` → success
   - `predicted_behavior=call_tool ∧ expected_tool_call=false` → over_call
   - `predicted_behavior=answer_directly ∧ expected_tool_call=true` → under_call
   - `predicted_behavior=call_tool ∧ expected_tool_call=true ∧ predicted_tool ≠ tool_target` → wrong_tool
   - `predicted_behavior=answer_directly ∧ expected_tool_call=false` → success

4. **Per-tool stats.** Same analysis shape as 006's
   `prediction_agreement_per_tool.py`: precision/baseline/lift on the
   trivial endpoint, recall, bootstrap CIs, paired 12B − 4B Δ.

5. **Confidence calibration (sub-question).** Does `confidence=high`
   predict accuracy better than `confidence=low`? Treat as a small
   secondary analysis, not headline.

## Decisions

_Populate as work proceeds._

## Results

_Pending. Self-prediction harness ready; A4 grading already in hand._

## Forward-looking

The result of this investigation is a real go/no-go gate for the rest of
study 002:

- **Gemma self-prediction at chance or worse.** Principle-extraction
  premise is wounded. Reasoning text might still contain useful features
  — could pivot the study toward "what does it take to give a model
  self-prediction signal?" — but the current methodology weakens.
- **Gemma self-prediction meaningfully above chance.** Proceed to
  investigation 2 (single-principle ablations using Gemma's self-
  explanations as source material).

Reasoning outputs are kept regardless of how Q1 lands. Even when
Q1 is null, the reasoning text is qualitative seed material for the
principle work — flagged as exploratory, not load-bearing.

## Things to flag

- Self-prediction prompt phrasing has known sensitivity. The current
  wording is a single best-guess design; a prompt-variation A/B is a
  worthwhile follow-up if results are equivocal.
- Empirical "modal outcome" can be ambiguous when n=10 splits 5-5.
  Treat those records as "uncertain ground truth," exclude from headline
  precision, and report separately.
- Don't anchor the self-prediction by exposing the expected behavior in
  the meta-prompt (see Methods §1). The whole control-group claim
  depends on this.
- Q2 (Gemma-vs-Opus comparison) is a free analysis since we have the
  Opus data, but the comparison is sensitive to prompt design: Gemma's
  self-prediction prompt and Opus's prediction prompt aren't identical,
  so any difference is partly methodological. Caveat appropriately.

## Limitations

- n=1 self-prediction per (record, model). Stochasticity of the
  prediction itself is not measured here.
- Gemma-only. Cross-family self-prediction is a future direction.
- Per-record empirical labels are model-relative — same record has
  different ground-truth labels for 4B vs 12B; correct and intended.
- The derived "predicted outcome class" is a function of the model's
  three structured-output fields plus curator metadata. If the model
  produces malformed JSON, that trial is excluded — track and report
  the parse-failure rate.
