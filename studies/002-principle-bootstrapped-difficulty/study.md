---
id: studies/002-principle-bootstrapped-difficulty
title: Principle-bootstrapped difficulty
status: planned
parents: []
children:
  - studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline
related:
  - studies/001-tool-calibration
  - studies/001-tool-calibration/investigations/007-axes-performativity
axes:
  llm_capability: medium
  human_capability: high
tags:
  - methodology
  - difficulty
  - principles
  - actor-critic
  - dataset-construction
created: 2026-05-22
updated: 2026-05-22
---

# Study 2 — Principle-bootstrapped difficulty

## Question

Can a researcher LLM, given empirical labels and a target model's own
self-explanations, bootstrap an auditable set of principles that predicts
task difficulty for that target model well enough to:

1. **Predict** — assign difficulty to held-out tasks accurately, and
2. **Generate** — design new tool-call pairs at desired difficulty levels
   for that model (and serve as a starting hypothesis when escalating to a
   stronger model).

This is methodological research about LLM-driven research methodology. A
negative result ("Opus 4.7 cannot bootstrap useful principles from Gemma's
self-explanations on this task") is itself a publishable finding.

## Motivation

[[study-001-tool-calibration]] discovered in [[investigation-006]] and
[[investigation-007]] that the *a priori* difficulty axes from
[[investigation-002]] do not predict empirical tool-call success rate. The
curator's `hard` labels land empirically as `trivial` for ~9/15 records at
12B IT. Whatever drives the empirical distribution of difficulty, the
curator's intuitions about it are not it.

The honest position: we don't know what the predictive features are. Two
prior approaches we considered:

1. **Researcher-hypothesized features.** Propose predictors (in-prompt
   answer, prompt-surface keywords, refusal-mode triggers, tool-target
   ambiguity, training-cutoff distance) and rank-correlate each against
   empirical success. Cheap, but the researcher's guesses are the
   bottleneck. The same intuitions that produced the failed axes in
   [[investigation-002]] are doing the proposing.
2. **End-to-end black-box classifier.** Train a small model to predict
   empirical success from prompt features. Predictive but uninterpretable;
   doesn't tell us *why* a record is hard.

This study explores a third path: **ask the target model itself**, force
the answer into an auditable structured form (predicted difficulty plus
cited principles), then use a researcher LLM (with human oversight) to
iteratively refine the principle library based on empirical feedback.

## Framing — nested actor-critic

Two loops, each with a model in the actor role and a stronger judge in
the critic role:

| Layer | Actor | Critic | Task |
|-------|-------|--------|------|
| Inner | Target model (e.g. Gemma 3 4B IT) | Researcher LLM (Opus 4.7) | Predict task difficulty; cite which principles guided the prediction. |
| Outer | Researcher LLM (Opus 4.7) | Human researcher | Propose, refine, retire principles based on inner-loop failures and successes. |

The framework is deliberately modular. Each role is a contract, not a
specific model:

- Swap Opus for Gemini 3 Pro at either critic position.
- Swap the human for Opus, producing a fully-LLM-driven pipeline whose
  output can be compared to the human-in-the-loop baseline.
- Swap the inner actor across model scales (4B → 12B → larger).

Hot-swappability is a design goal, not a starting requirement. The first
working configuration is `Gemma-actor / Opus-critic / human-outer-critic`;
abstractions for the swap will be earned, not pre-paid.

## Two distinct calibration questions

The system measures two related but non-identical properties. Experiments
should be explicit about which is the target:

- **Stated-difficulty calibration.** When the target model is asked to
  predict its own success, how well does its prediction match the
  empirical outcome? Improvements here come from giving the model better
  principles to reason with.
- **Actual tool-call calibration.** When principles are added to the
  target model's production tool-call system prompt, does its
  call/no-call behavior improve? Improvements here are the downstream
  application — what [[study-001-tool-calibration]] would consume.

A principle can improve stated-difficulty accuracy without changing
actual tool-call behavior, and vice versa. Both are interesting; do not
collapse them.

## On citation faithfulness

A target model citing principles in its reasoning is making a *claim*
about what guided it, not delivering ground truth. The literature on
chain-of-thought faithfulness suggests these claims can be unreliable.
This study takes a more nuanced position:

- The empirical test of a principle is whether adding/removing it shifts
  behavior, not whether the model's cited reasoning is causally accurate.
- *Where* the citation-faithfulness link breaks is itself a research
  finding. Trends in which principles get cited inaccurately, on which
  tasks, by which models — that's a future-direction lead toward
  mechanistic interpretability work.
- The system is designed to encapsulate *why* things happen behaviorally,
  giving descriptive tooling that supports both behavioral and (eventual)
  mechanistic interventions.

## Likely outcomes to be honest about up front

The corpus-wide and per-tool agreement analyses from
[[investigation-006]] (see
`../001-tool-calibration/investigations/006-temperature-prompt/results-analysis/`)
establish strong priors on what this study's results will look like, and
those priors should shape what we promise:

1. **Likely outcome: a structured trivial detector, not a 5-band
   ordinal classifier.** Opus — a substantially stronger model than the
   target Gemmas — produces predictions that function as a trivial-task
   detector with no surviving ordinal signal. Expecting a Gemma actor
   plus a principle library to outperform Opus on the *ordinal* task is
   ambitious. The realistic deliverable is a high-quality
   *trivial-detector with structure*: principles that explain **why** a
   record will be trivial for a given model, conditioned on tool target.
   This is a narrower claim than "model-specific ordinal difficulty
   labels" — and a more defensible one.

2. **Principles will likely be tool-conditioned, not global.** The
   per-tool breakdown shows the trivial detector behaves in two regimes:
   near-perfect for `python_execute`, strong for `gkl`/`ukl`,
   anti-informative for `calculator`/`datetime_now`. A single global
   principle library would average over those regimes. Plan for
   per-tool principle sets (or principles with explicit tool scope, per
   the `scope` field on `AuditablePrinciple`) from the start.

3. **The "extreme" / "impossible" endpoint will likely stay noisy.**
   Opus is anti-informative at the impossible endpoint for 4B and at
   noise for 12B. The signal that *will* exist is at the trivial
   endpoint. Don't burn cycles trying to bootstrap impossible-prediction
   first.

These are priors, not predictions. Investigation 001's self-prediction
baseline is what makes them empirical for the Gemma actor specifically.

## Investigations

- `001-self-prediction-baseline` — does the target model know what's
  hard for itself? Cheap first run: structured self-prediction over the
  bulk corpus, compared to empirical success from
  [[investigation-007]]'s A4 grading. **Planned.**

Planned follow-ons:

- `002-single-principle-ablations` — with/without ablation per candidate
  principle, on a stratified record subset. Tests the "this specific
  principle moves the matched-pair gap" claim cleanly.
- `003-principle-combination-search` — greedy forward selection within
  tool families; cross-tool merging.
- `004-cross-model-transfer` — do principles validated on Gemma 4B carry
  to Gemma 12B? Do they carry to a different model family?
- `005-researcher-substitution` — replace human outer-critic with Opus
  acting as its own critic. Does the loop still converge?
- `006-difficulty-targeted-generation` — given the validated principle
  library, can the system generate held-out tool-call pairs at requested
  difficulty levels for a target model? This is the second of the two
  top-level goals.

## Registry policy

- `registry/principles.jsonl` is the append-only log of principle
  versions. Every revision writes a new row with a new uuid; the parent
  uuid links lineage.
- `registry/principles.yaml` (optional, derived) summarizes the current
  state for human reading.
- Experiment configs cite principles by uuid + version, never by inlined
  text. The model is given a *subset* of the registry as its active
  library; selection-of-library is itself an experimental variable.

## Experiments policy

- `experiments/exp_NNN/config.yaml` is the source of truth for a run.
- `experiments/exp_NNN/results.jsonl` is the raw per-trial output
  (gitignored — re-runnable from config + registry).
- `experiments/exp_NNN/summary.yaml` is the checked-in aggregate:
  per-principle effect sizes, matched-pair gap deltas, decisions.
- The per-investigation `investigation.md` summarizes the experiments
  it owns; it does not duplicate config bodies.

This layout deliberately keeps experiment-level frontmatter light. With
hundreds of small ablation configs expected, full study/investigation
frontmatter per experiment would be over-engineered.

## Repository policy

- Principle registry checks in.
- Experiment configs and summaries check in.
- Raw experiment results gitignored (mirrors [[study-001-tool-calibration]]
  repository policy).
- The `AuditablePrinciple` / `AuditableResponse` primitives live at
  `models.py` under the study root and are imported by investigations.

## Forward-looking

Beyond the planned investigations:

- **Mechanistic interpretability layer.** Where citation faithfulness
  breaks, what's the model actually doing? Probe / activation-patching
  work on the cases where stated and acted principles diverge.
- **What makes a human researcher better than Opus at this?** If the
  outer loop only converges with a human critic, characterizing *which*
  principles the human contributes (and which Opus contributes) becomes a
  research question about LLM-assisted research methodology.
- **Recursion.** Principles for principle-design — meta-principles
  derived from cases where the outer loop converged. Apply them; do
  weaker researcher LLMs improve?
- **Cross-domain transfer.** The framework is not specific to tool-call
  calibration. Any task where "is this hard for model X?" admits
  empirical labels could be plugged into the same loop.
