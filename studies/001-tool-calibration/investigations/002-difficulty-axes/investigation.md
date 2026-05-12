---
id: studies/001-tool-calibration/investigations/002-difficulty-axes
title: Per-tool difficulty axes (Phase A2)
status: in-progress
parents:
  - studies/001-tool-calibration
children: []
related:
  - studies/001-tool-calibration/investigations/001-foundations
axes:
  llm_capability: medium
  human_capability: high
tags:
  - difficulty-axes
  - calibration
  - tooling
aliases:
  - A2
  - phase-a2
created: 2026-05-11
updated: 2026-05-11
---

# Investigation 2 — Per-tool difficulty axes (Phase A2)

## Scope

Define, per tool, the **dimensions along which difficulty varies**, so
that A1's hand-curated seeds and A3's bulk-generated prompts can sit at
*known* difficulty bands rather than at hypothesized ones. Concretely:

1. For each of the six palette tools, identify the small set of
   structural axes that drive prompt difficulty (e.g. for calculator:
   digit count + operation type + precision).
2. Bind each axis to concrete value ranges that map onto the existing
   5-level `difficulty_label.value` enum (trivial | easy | medium |
   hard | extreme).
3. Implement the tool **execution layer** so prompts can actually be
   run end-to-end (Decision 18 fixed-return for `datetime_now`;
   Decision 19 verified KB for general/user lookups; calculator,
   python_execute, unit_convert wired up properly).
4. Define the **calibration methodology** for translating per-model
   empirical `success_rate` into one of the 5 difficulty buckets, so
   downstream `difficulty_calibrated` reports are interpretable
   (Decision 13 deferred this to "A4 thresholds" — landed here as
   part of A2 because it gates everything downstream).

## Methods

_Populate as we go. Pre-A2 sketch:_

1. **Per-tool axis drafting** (LLM-led, human-reviewed). For each
   tool, propose 2–4 structural axes and the value ranges that anchor
   each difficulty band. Surface assumptions explicitly. Frozen
   per-tool by a Decision-block sign-off from the human.

2. **Tool execution layer** (LLM-led, runnable). Replace the
   `NotImplementedError`-only Python stubs with KB-backed / actual
   implementations:
   - `calculator(expression)` — `safe_eval` over an arithmetic AST.
   - `python_execute(code)` — sandboxed subprocess returning stdout.
   - `datetime_now()` — returns a **fixed** value pinned to the
     corpus runtime anchor (2026-05-11T12:00:00Z; see Decision 18).
   - `unit_convert(value, from_unit, to_unit)` — actual conversion
     via a small unit table.
   - `general_knowledge_lookup(query)` — BM25-lite over
     `general_knowledge_real.json` (Decision 19 makes this the
     canonical source).
   - `user_knowledge_lookup(query)` — BM25-lite over
     `user_knowledge.json`.

3. **Calibration methodology** ("A4 thresholds"). Define
   `success_rate → difficulty bucket` thresholds, the trial count `n`,
   pass/fail semantics per tool, and how `calibration_status:
   contested` is computed.

4. **Pipeline dry run**. With the tool execution layer wired up, run
   each of the 34 A1 seed records through the harness *without*
   calling any target model — confirms the prompt-to-tool plumbing
   works end-to-end. Actual model trials are deferred to Phase A4
   when the user authorizes target-model API access.

## Decisions

> **Decision 1 — per-tool difficulty axes frozen as drafted** (2026-05-11)
> The axes in `difficulty_axes_proposal.md` (for all six tools:
> calculator, python_execute, datetime_now, unit_convert,
> general_knowledge_lookup, user_knowledge_lookup) are signed off
> as-is by the human reviewer. The proposal's "Things to flag" list
> remains open as research questions — particularly:
> band-shift arithmetic (additive vs. multiplicative vs. table),
> datetime_now's runtime-dependence floor, python_execute's squishy
> "steps" axis, and cross-tool axis sharing for `precision_decimals`
> and `temporal_position`. None of these block downstream work.
> The performativity of the axes themselves (do they predict
> empirical difficulty?) is logged as a sibling-investigation
> Forward-looking entry in `studies/001-tool-calibration/study.md`.

## Results

### Pilot calibration run — Gemma 3 4B IT (QAT Q4_0), n=20 (2026-05-12)

First end-to-end pilot of the calibration harness against the full
A1 corpus (18 pairs / 36 records). Ollama on the desktop WSL,
reachable via Tailscale; runner backend `ollama`.

**Run metadata**
- model: `gemma3:4b-it-qat`
- n: 20 trials per record
- total trials: 720
- run_id: `9119ff96`
- date: 2026-05-12
- results file (gitignored): `studies/001-tool-calibration/results/gemma3_4b-it-qat/2026-05-12.jsonl`

**Headline numbers**
- 23/36 records: perfectly calibrated (20/20 right behavior)
- 11/36 records: systematic miscalibration (0/20)
- 2/36 records: near-boundary with 1 outlier each (0.95)
- 4B IT is decisive — almost no stochastic uncertainty (no records
  in the 0.30–0.70 middle band)

**Convergence finding (answers the methodology Open Question on N
sufficiency).** 34/36 records were bucket-stable from n=5 onwards.
Only 2 records drifted between n=5 and n=20, each by exactly one
outlier trial (0.80→0.90→0.95). **For 4B IT on this corpus, n=10
would have been sufficient**, saving half the compute. This argues
for n=10 as the default for future runs against this model class,
with n=20+ reserved for identified boundary records flagged at n=10.

**Failure mode taxonomy** (from output-content audit across all
under- and over-call records — patterns verified consistent across
all 20 trials of each record):

| Mode | Records | What the model did |
|------|---------|--------------------|
| **Tool-blind deferral** | 3 (all `user_knowledge_lookup` hard halves: anniversary, daughter_school, aunt_nina) | Correctly recognized "I don't have access to your personal profile" but did NOT invoke `user_knowledge_lookup` — appears not to map "need private info" → "use the tool that returns private info" |
| **Wrong tool selected** | 2 (`python_execute` hard cases: sum-of-primes, SHA-256) | Recognized need for compute, invoked `calculator` with python-style expressions instead of `python_execute` |
| **Confident confabulation** | 1 (`general_knowledge_lookup` NLA paper hard) | Fabricated a 2020 publication date and an incorrect description of the technique; answered the same wrong answer 20/20 times |
| **Correct without verification** | 1 (`python_execute` leap-year hard half) | Answered "February 29, 2028" — **correct** 20/20 — without using `python_execute` to verify. Reviewer policy treats this as least-undesirable: under-call but accuracy preserved |
| **Trivial over-call** | 4 (`calculator` "Compute 4 × 7", `datetime_now` in-prompt date, `unit_convert` "5 m to cm", `general_knowledge_lookup` "decade of Transformer paper") | Invoked the target tool when answering directly would have sufficed. Per reviewer policy, less undesirable than under-call (tool returns the right answer) |

**Per-tool calibration distribution**:

| Tool | Clean | Over-call | Under-call |
|------|-------|-----------|------------|
| `calculator` | 5/6 | 1 | 0 |
| `python_execute` | 3/6 | 0 | 3 |
| `datetime_now` | 3/4 | 1 | 0 |
| `unit_convert` | 3/4 | 1 | 0 |
| `general_knowledge_lookup` | 4/6 | 1 | 1 |
| `user_knowledge_lookup` | 3/6 | 0 | **3 (all hard halves)** |

The `user_knowledge_lookup` column is the cleanest single research
finding: 4B IT consistently fails to invoke the persona-lookup tool
even when the prompt is unambiguously personal and the tool is in
the available set. Under-calls outweigh over-calls 7:4 across all
miscalibrated records.

### Notes on scoring gaps surfaced by this run

The current `classify_trial` scoring treats "invoked the wrong tool"
as `under_call of target` — the SHA-256 and prime-sum cases counted
as `python_execute` under-calls even though the model *did* invoke
a tool (just the wrong one). A finer-grained scoring step that
distinguishes `target_invoked / wrong_tool_invoked / no_tool` is
worth adding before the 12B run; the JSONL outputs already preserve
enough information to re-score retrospectively without re-running.

### Hypotheses for follow-up

1. **Tool-blind deferral on personal info is most likely an
   instruction-tuning overshoot.** Safety / refusal training
   probably weighted "I cannot access personal information" so
   heavily that the model learned this is the correct response
   independent of available tooling. If true, 12B IT (similar
   post-training but more capacity) would show the same pattern;
   base (non-IT) variants would not — but base models lack the
   chat-template / tool-call infrastructure anyway, so testing
   directly is hard.
2. **Wrong-tool selection (calculator vs. python_execute) suggests
   the tool descriptions in system prompts may be too thin.** The
   prompt distinguishes "arithmetic expression" from "Python
   snippet" but the model may not be carving the boundary at the
   right place. Testing variant system prompts with explicit
   "calculator is for arithmetic only, not lambda/filter/sum
   expressions" framing could probe this.
3. **The over-call cluster is heuristic-driven, not knowledge-driven.**
   "Compute X × Y" triggers `calculator`; "What is X / Y" does not.
   Suggests training-data surface features rather than reasoning.
   Likely persists at 12B; can be probed with paraphrase pairs in
   A3 bulk generation.

### Tool-definition A/B experiment — user_knowledge_lookup (2026-05-12)

Follow-on to the pilot's tool-blind-deferral finding. Probed whether
the 0/20 under-call on user_knowledge_lookup hard halves could be
fixed by *only* changing the tool definition in the system prompt
(not the rest of the prompt). Five variants tested at n=5 across the
3 ukl hard records; winners re-validated at n=10. Sampling
temperature=1.0, top_p=0.95 (Decision 3 below).

Variants:
- **v0_baseline**: original A1 wording — "search the current user's
  private profile (identity, family, calendar, preferences); same
  shape as general_knowledge_lookup."
- **v1_directive**: same tool name + description that begins
  "REQUIRED whenever the user asks about themselves (their family,
  schedule, history, preferences, or anything they personally know)..."
- **v2_renamed**: rename tool to `lookup_user_info`, baseline
  description.
- **v3_epistemic**: same tool name + description that addresses the
  refusal pattern: "Use whenever the user asks about themselves
  ('I', 'my', 'me'); the tool DOES give you access to this
  information even though you cannot know it directly."
- **v4_combined**: rename + directive + epistemic framing.

Results:

| Variant | n=5 overall | n=10 overall | Note |
|---------|------------:|-------------:|------|
| v1_directive | 73.3% | 60.0% | Single-variable winner — prescriptive language alone fixes most |
| v4_combined | 26.7% | 26.7% | Worse than v1; suggests over-cueing confuses |
| v3_epistemic | 6.7% | — | Addressing refusal directly without prescription barely helps |
| v0_baseline | 0.0% | — | Control |
| v2_renamed | 0.0% | — | Naming alone has no effect |

**Conclusion:** the under-call failure is *not* an irreducible
post-training bias. It can be substantially mitigated by adding
prescriptive language to the tool description (e.g. "REQUIRED
whenever..."). Naming, epistemic framing, and combined cues are
strictly weaker.

**Hypothesis revision:** the original tool-blind-deferral pattern
isn't "the model can't connect refusal to tooling" — it's "the
model's prior on refusal is stronger than its prior on tool use,
unless tool-use is made imperative." The instruction-tuning effect
is real but defeatable at the prompt layer.

**Practical recommendation for the canonical A1 system prompts:**
upgrade the user_knowledge_lookup description to v1_directive
wording. The other tools' descriptions probably benefit from the
same prescriptive treatment but weren't part of this experiment;
worth a brief sweep before the bulk A3 generation phase. This is
a tool-spec edit, not a methodology change — doesn't invalidate
prior A4 pilot data, but means subsequent A4 runs should use the
upgraded prompts and we re-baseline against them.

> **Decision 2 — `wrong_tool` error_type added** (2026-05-12)
> The pilot run surfaced two records (SHA-256 hash, sum-of-primes)
> where 4B IT invoked `calculator` with python-style expressions
> instead of `python_execute`. The old classifier scored these as
> `under_call` (target tool not invoked), conflating "called the
> wrong tool" with "called nothing." Added a third error_type
> `wrong_tool` — invoked some tool but not the target — and updated
> the analyzer to surface it. Reviewer policy on severity (Decision
> 2 of `calibration_methodology.md`) still has under_call most
> undesirable, wrong_tool intermediate, over_call least.

> **Decision 3 — switch sampling defaults to temperature=1.0, top_p=0.95** (2026-05-12)
> The original pilot used temperature=0.0 (greedy). Per reviewer
> direction, temperature=0 is a legacy convention that doesn't
> cleanly probe production-typical behavior. New defaults in
> `harness/inference.py`: temperature=1.0, top_p=0.95. Future
> runs (including 12B IT) use these. The 4B pilot data was at
> temp=0 and remains valid as a deterministic baseline; the n=10
> tool-variant confirmation runs were already at the new defaults.

### Next steps queued

1. ~~Add wrong-tool-selection to the scoring step.~~ (Done —
   Decision 2.)
2. Sweep the other tool descriptions for prescriptive-language
   upgrades analogous to v1_directive — before the bulk A3
   generation phase. The 4B pilot showed wrong-tool selection on
   python_execute and confabulation on general_knowledge_lookup
   ai_tech; the same prescriptive pattern may help both.
3. Run 12B IT (`gemma3:12b-it-qat`) — same harness, same corpus,
   same upgraded system prompts. Estimate ~2–3 hours wall time.
   Compare per-record failure modes to 4B; expect 12B to fix some
   heuristic over-calls and possibly the wrong-tool selection
   cases. Open question: does 12B still need the v1_directive
   upgrade, or does it correctly invoke user_knowledge_lookup on
   the baseline tool description?
4. Reset n default to 10 for routine runs; reserve n=20 for
   records with `expected_call_confidence: low` and any flagged-
   boundary records.

## Forward-looking

- `003-bulk-generation` (Phase A3) — once axes are frozen, generate
  the larger corpus.
- Phase A4 — empirical calibration runs against target models;
  populate `difficulty_calibrated`. Initial target set: Gemma 3 4B IT,
  4B base, 12B IT, 12B base. See `calibration_cost_estimate.md` for
  cost/feasibility analysis.
- Axes-performativity sibling investigation — once Phase A4 has enough
  empirical signal, test how well the axes here predict
  `success_rate`. See study-level Forward-looking entry.
- Per-record `runtime_overrides` infrastructure and Type-C
  (scenario-manipulation) pair support — needed to express
  leap-year-style probes via tool overrides rather than in-prompt
  dates. Belongs to investigation 004 (tool-output-interpretation).

## Things to flag

_Surface assumptions explicitly as drafting proceeds. Particularly:_

- Whether per-tool axes are independent vs. interacting (the difficulty
  manifold may not factorize cleanly).
- Whether bucket thresholds should be tool-agnostic or per-tool.
- How `expected_call_confidence: medium` records (e.g. pair 8,
  pair 10) should be graded — they sit deliberately on the calibration
  boundary.

## Limitations

_To be populated._
