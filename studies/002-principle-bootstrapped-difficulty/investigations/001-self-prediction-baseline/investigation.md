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

> **Decision 1 — four-question ladder over single-shot prediction** (2026-05-22)
> The original design was a single structured prediction emitting
> `(predicted_behavior, predicted_tool, predicted_success, confidence,
> reasoning)`. Restructured into four independent questions (Q1: could
> you answer without tools / Q2: could you answer with the appropriate
> tool / Q3: would you reach for a tool / Q4: which tool). Independent
> calls — no shared conversation context. Reason: the single-shot
> version conflated capability self-knowledge with behavioral
> self-prediction. The ladder separates them, and the (Q1, Q2, Q3, Q4)
> × (actual behavior, actual answer correctness) cross-product is
> where the diagnostic structure lives.

> **Decision 2 — Q1 includes `i_cannot_know` as a distinct verdict** (2026-05-22)
> Distinct from `no` (which means "I'd attempt it but probably be
> wrong"). The new option covers cases where the task asks for
> information the model has no access to in principle — personal data,
> real-time facts, post-cutoff knowledge. Necessary for ukl records
> where "cannot know" and "would get wrong" are different cognitive
> moments. Adds a third class to Q1's analysis but the signal is worth
> it.

> **Decision 3 — sweep n=3 uniformly across all four questions** (2026-05-22)
> Stochasticity pre-experiment (24 records × 4 questions × n=5)
> showed Q2 and Q3 are essentially deterministic (mean entropy 0.030,
> 22–23/24 unanimous), Q1 mildly noisy (entropy 0.121, 20/24
> unanimous), Q4 noisiest (entropy 0.242, 17/24 unanimous, 7/24 split
> ≤4/5). n=3 gives Q4 the precision it needs without overspending on
> the deterministic questions. Records with split modal predictions at
> n=3 can be re-run at higher n if they fall in load-bearing positions
> for the analysis.

## Results

> ### Pre-experiment: stochasticity (n=24 records × n=5 trials, 2026-05-22)
>
> Quick check before committing to the full corpus run. Per-question
> stability of the model's structured-output answer across 5 trials:
>
> | Question | Unanimous | 4/5 | 3/5 | Mean entropy | Parse fail |
> |---|---|---|---|---|---|
> | Q1 (capability, no tools) | 20/24 | 1 | 3 | 0.121 | 1/120 |
> | Q2 (capability, with tools) | 22/24 | 2 | 0 | 0.030 | 1/120 |
> | Q3 (behavior) | 23/24 | 1 | 0 | 0.030 | 0/120 |
> | Q4 (tool selection) | 17/24 | 4 | 3 | 0.242 | 0/120 |
>
> Parse-failure rate: 2/480 = 0.4%. Meta-prompts elicit reliable JSON
> from 4B IT.
>
> ### Pre-experiment side finding: directional Q3 error pattern (n=24)
>
> While the pre-experiment was scoped to stochasticity, the sample
> also lets us peek at Q3 accuracy against A4 empirical behavior.
> **Result on n=24: 15/24 = 62.5% accuracy** — modestly above the
> better naive baseline ("always predict call_tool" = 58.3% on this
> stratified sample). Wide CI at this n; not the headline number.
>
> What is interesting at n=24: **the Q3 errors cluster directionally.**
> Of 9 mispredictions, **6 are records where Gemma predicted
> `answer_directly` but empirically called the tool** (under-prediction
> of own tool use). Only 2 are the reverse (predicted `call_tool`,
> actually answered directly). One was a wash.
>
> Specific records worth highlighting (gemma3:4b-it-qat):
>
> - `datetime_now-time-easy-current_date-002`: Q1 says `i_cannot_know`,
>   Q3 says `answer_directly`, **empirically calls the tool 10/10**.
>   The model says it can't know the current date AND that it would
>   answer directly — and then empirically reaches for the tool every
>   time.
> - `datetime_now-time-hard-biz_days_30-001`: same pattern,
>   `i_cannot_know` → `answer_directly` → 10/10 tool calls empirically.
> - `calculator-math-medium-mult_3d_p0-005` and `-009`: Q1=yes
>   ("I can do this in my head"), Q3=`answer_directly`, **empirically
>   calls calculator 9/10 and 10/10**. Mirrors the
>   `calculator-math-trivial` 006 over-call cluster — but now with
>   evidence that the model itself believes it would behave correctly.
>
> **Implications, n=24 anecdotal but directional:**
>
> - The error pattern in Gemma 3 4B IT is *systematically directional*,
>   not random. The model under-predicts its own tool-calling behavior.
>   This is *principle-extractable* — a principle that captures the
>   gap ("on calculator and datetime_now trivial cases, you predict
>   you'll answer directly but you actually call the tool") would have
>   a clear behavioral target.
> - The Q1 ↔ Q3 disagreement (model says it could answer / model says
>   it wouldn't reach for a tool / model empirically reaches for the
>   tool) is a *three-way mismatch* worth analyzing in its own right.
>   It separates "I have the capability" from "I would invoke that
>   capability" from "I actually do invoke that capability." The full
>   corpus run should make this visible at scale.
> - This is a finding about Gemma 3 4B IT specifically. The pattern
>   may not transfer to 12B IT (which 006 showed fixes most
>   trivial-half over-calling). Cross-model comparison is a follow-on.
>
> Full corpus run pending.

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
