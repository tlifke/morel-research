---
id: studies/001-tool-calibration/investigations/004-calibration-pilot
title: Calibration pilot — neutral-baseline empirical runs
status: in-progress
parents:
  - studies/001-tool-calibration
children: []
related:
  - studies/001-tool-calibration/investigations/001-foundations
  - studies/001-tool-calibration/investigations/002-difficulty-axes
  - studies/001-tool-calibration/investigations/005-tool-spec-optimization
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - calibration
  - pilot
  - empirical
aliases:
  - A4
  - phase-a4-pilot
created: 2026-05-12
updated: 2026-05-12
---

# Investigation 4 — Calibration pilot (neutral baseline)

## Scope

Run the A1 seed corpus against target models at **neutral baseline**
tool descriptions (the canonical A1 system prompts) and produce
headline per-model calibration numbers. The point of this
investigation is **measurement of the model**, not optimization of
the prompt — that lives separately in `005-tool-spec-optimization`.

Methodology lives in `../002-difficulty-axes/calibration_methodology.md`.

Target models (current set; extend as authorized):
- Gemma 3 4B IT (QAT Q4_0) — pilot done
- Gemma 3 12B IT (QAT Q4_0) — planned
- Gemma 3 4B / 12B base — deferred (no chat-template / tool-call
  training; requires a separate harness for base-model probing)

## Methods

For each (record, model) pair:
1. Build the user-facing prompt by composing the record's
   `system_prompt_id` template + the record's `user_prompt`.
2. Send to the inference backend (Ollama HTTP on the desktop, or
   API).
3. Run `n` trials at the methodology's default sampling
   (currently temperature=1.0, top_p=0.95 — see
   methodology Decision below).
4. Score each trial: `success | over_call | under_call | wrong_tool`.
5. Aggregate per record: success_rate at n=5, n=10, n=20 checkpoints
   for retrospective N-sufficiency analysis.

The runner, parser, and analyzer live at `harness/` under the study
root.

## Decisions

> **Decision 1 — `wrong_tool` error_type** (2026-05-12)
> The pilot surfaced records where the model invoked a tool but not
> the target (SHA-256 hash, sum-of-primes — model picked `calculator`
> with python-style expressions instead of `python_execute`). The
> initial classifier scored these as `under_call`, conflating "wrong
> tool" with "no tool." Added a third error_type to disambiguate.
> Reviewer severity ordering: `under_call` (worst) > `wrong_tool` >
> `over_call` (least undesirable). Captured in
> `../002-difficulty-axes/calibration_methodology.md`.

> **Decision 2 — sampling defaults switched to temperature=1.0, top_p=0.95** (2026-05-12)
> Original pilot used temperature=0.0 (greedy). Reviewer direction:
> temperature=0 is a legacy convention that doesn't cleanly probe
> production-typical behavior. Updated `harness/inference.py`
> defaults. The 4B pilot data below was collected at temp=0 and
> serves as a deterministic baseline; future runs (including 12B IT)
> use the new defaults. Captured in methodology doc.

## Results

### Pilot run — Gemma 3 4B IT (QAT Q4_0), n=20, temp=0 (2026-05-12)

First end-to-end calibration run against the full A1 corpus
(18 pairs / 36 records). Ollama on the desktop WSL, reachable via
Tailscale.

**Run metadata**
- model: `gemma3:4b-it-qat`
- n: 20 trials per record
- total trials: 720
- temperature: 0.0 (legacy default; future runs use 1.0)
- run_id: `9119ff96`
- results file (gitignored): `results/gemma3_4b-it-qat/2026-05-12.jsonl`

**Headline numbers**
- 23/36 records: perfectly calibrated (20/20 right behavior)
- 11/36 records: systematic miscalibration (0/20)
- 2/36 records: near-boundary with 1 outlier each (0.95)
- 4B IT is decisive — almost no stochastic uncertainty (no records
  in the 0.30–0.70 middle band). Likely partly an artifact of
  temp=0 sampling; future runs at temp=1.0 will reveal whether the
  decisiveness holds under production-typical sampling.

**Convergence finding (answers the methodology Open Question on
N-sufficiency).** 34/36 records were bucket-stable from n=5
onwards. Only 2 records drifted between n=5 and n=20, each by
exactly one outlier trial (0.80→0.90→0.95). **For 4B IT on this
corpus at temp=0, n=10 would have been sufficient**, saving half
the compute. Worth re-checking at temp=1.0 — stochastic sampling
may surface more boundary cases.

**Failure mode taxonomy** (output-content audit; patterns verified
across all 20 trials of each record):

| Mode | Records | What the model did |
|------|---------|--------------------|
| **Tool-blind deferral** | 3 (all `user_knowledge_lookup` hard halves) | Correctly recognized "I don't have access to your personal profile" but did NOT invoke `user_knowledge_lookup` |
| **Wrong tool selected** | 2 (`python_execute` SHA-256, sum-of-primes) | Recognized need for compute, invoked `calculator` with python-style expressions instead |
| **Confident confabulation** | 1 (`general_knowledge_lookup` NLA paper hard) | Fabricated a 2020 publication date and incorrect description; same wrong answer 20/20 |
| **Correct without verification** | 1 (`python_execute` leap-year hard) | Answered "February 29, 2028" — correct 20/20 — without calling `python_execute` to verify |
| **Trivial over-call** | 4 (calc "Compute 4 × 7", dt in-prompt date, unit_convert "5 m to cm", gkl "decade of Transformer paper") | Invoked the target tool when answering directly would have sufficed |

**Per-tool calibration distribution**:

| Tool | Clean | Over-call | Under-call |
|------|-------|-----------|------------|
| `calculator` | 5/6 | 1 | 0 |
| `python_execute` | 3/6 | 0 | 3 |
| `datetime_now` | 3/4 | 1 | 0 |
| `unit_convert` | 3/4 | 1 | 0 |
| `general_knowledge_lookup` | 4/6 | 1 | 1 |
| `user_knowledge_lookup` | 3/6 | 0 | **3 (all hard halves)** |

The `user_knowledge_lookup` column is the cleanest single finding:
4B IT fails to invoke the persona-lookup tool 20/20 even when the
prompt is unambiguously personal and the tool is in the available
set. Under-calls outweigh over-calls 7:4 across miscalibrated
records.

### Hypotheses for follow-up

1. **Tool-blind deferral on personal info is most likely an
   instruction-tuning overshoot.** Safety / refusal training
   probably weighted "I cannot access personal information" so
   heavily that the model learned this is the correct response
   independent of available tooling. The follow-on A/B experiment
   in 005 found this is **defeatable at the prompt layer** with
   prescriptive language — strong evidence that the model retains
   the capability but defaults to refusal.
2. **Wrong-tool selection (calculator vs. python_execute) suggests
   the tool descriptions in system prompts may be too thin.** The
   prompt distinguishes "arithmetic expression" from "Python
   snippet" but the model may not be carving the boundary at the
   right place. See 005 for boundary-clarification probe.
3. **The over-call cluster is heuristic-driven, not knowledge-driven.**
   "Compute X × Y" triggers `calculator`; "What is X / Y" does not.
   Suggests training-data surface features. Likely persists at 12B;
   can be probed with paraphrase pairs in A3 bulk generation.

## Forward-looking

- **12B IT run** under the *same neutral baseline* (estimate ~2–3 hr
  wall time). Comparing 4B vs 12B at neutral isolates the
  "more parameters → better calibration" question without confound
  from prompt-engineering.
- **Re-pilot at temperature=1.0** for 4B IT. The original run at
  temp=0 was deterministic; production-typical sampling may reveal
  records that were deterministically miscalibrated to be
  stochastically near-boundary.
- **Recalibration under optimized prompts** (counterfactual). Once
  005 produces a tool-description style guide, re-run the pilot
  with those prompts and measure the *prompt-engineering
  contribution* to calibration improvement. Splits "intrinsic to
  model" from "fixable via prompt."
- **Base-model harness.** Required for the IT-vs-base architecture
  question (study.md Forward-looking). Out of scope for this
  pilot; gated on a separate base-model prompt-format design.

## Things to flag

- The A1 corpus is small (18 pairs / 36 records). Per-tool sample
  sizes (4–6 records each) are too small to draw confident
  per-tool conclusions; treat the per-tool distribution as
  exploratory. The A3 bulk corpus will fix this.
- Temperature=0 results may not generalize to production sampling.
  Re-pilot at temp=1.0 before drawing strong claims.
- The pilot's neutral baseline is "neutral by our authoring
  conventions" — not a calibrated neutral. Multiple-author-style
  ablations would tighten the baseline; currently out of scope.

## Limitations

- Pilot ran only one model at one sampling regime under one set of
  neutral tool descriptions. All three axes (model, sampling, prompt)
  are open; this is a single point.
- The runner's original 4B output preserves only the first 400 chars
  of each response (`output_preview`). Subsequent runs store full
  outputs — but the 4B JSONL is lossy for retrospective rescoring.
  Trust the originally-logged `success` / `error_type` fields for
  the 4B data.
