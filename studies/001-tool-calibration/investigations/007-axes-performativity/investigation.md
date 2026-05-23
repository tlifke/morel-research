---
id: studies/001-tool-calibration/investigations/007-axes-performativity
title: Axes performativity — do our difficulty axes predict tool-call calibration?
status: in-progress
parents:
  - studies/001-tool-calibration
children: []
related:
  - studies/001-tool-calibration/investigations/002-difficulty-axes
  - studies/001-tool-calibration/investigations/004-calibration-pilot
  - studies/001-tool-calibration/investigations/006-temperature-prompt
  - studies/002-principle-bootstrapped-difficulty
axes:
  llm_capability: medium
  human_capability: high
tags:
  - methodology
  - axes
  - empirical-difficulty
aliases:
  - 007
  - axes-perf
created: 2026-05-12
updated: 2026-05-23
---

# Investigation 7 — Axes performativity

> **Scope update (2026-05-22).** This investigation now owns only the
> *diagnostic* question — establishing empirically that the difficulty
> axes from investigation 002 do not predict tool-call success. The
> *reformulation* question — what axes / features / principles would
> predict difficulty for a target model — has moved to
> `studies/002-principle-bootstrapped-difficulty` as its own study,
> since the approach (model self-prediction + auditable principle
> registry + nested actor-critic refinement) is methodologically
> distinct from the rest of study 001 and feeds back into it as input
> rather than as a sibling investigation. The `AuditablePrinciple` /
> `AuditableResponse` primitives that were scaffolded here have moved
> to `studies/002-principle-bootstrapped-difficulty/models.py`.

## Scope

Investigation 006 surfaced (F3, F4, F5) that the per-tool difficulty
axes frozen in 002 Decision 1 **do not predict** empirical tool-call
success on the A1 seed corpus. Records the curator labeled `hard`
land empirically in `trivial` for both 4B and 12B at neutral
temp=1.0; the diagonal of the curator×empirical heatmap is largely
empty.

This investigation asks two distinct questions, both load-bearing
for downstream calibration work:

1. **Diagnosis**: *why* don't the axes predict? Specifically, what
   *do* they predict (if anything), and what gap exists between
   "what the axes measure" (task difficulty) and "what our score
   measures" (tool-call decision)?

2. **Reformulation**: if the existing axes don't predict
   tool-call calibration, what set of axes / features *would*?
   Output: a candidate revised axis set, ideally validated on a
   held-out subset of the bulk corpus.

The framing distinction (from 006's analysis):
- **Task difficulty** (what 002's axes describe): could the model,
  in principle, solve the task without tools? Operand digit count,
  algorithm complexity, fact obscurity, etc.
- **Tool-call calibration** (what classify_trial measures): does
  the model's tool-invocation behavior match the curator's
  expected_tool_call? Driven by prompt surface features
  ("Compute X" triggers calc), refusal priors, training-data
  patterns.

These are not the same property. The axes-performativity
investigation tests this empirically and then proposes the
right-shaped axis system for what we're actually measuring.

## Methods

1. **Re-tag the A1 + bulk corpus with empirical difficulty.** Once
   A4 grading finishes (4B IT and 12B IT against `bulk_seeds.jsonl`
   under neutral baseline at temp=1.0, n=10), compute per-record
   `empirical_difficulty[model_id]` via `calibration_methodology.md`
   thresholds. Note that empirical bucketing is model-relative;
   the same record will have different per-model labels.

2. **Quantify predictive power.** For each pair (axis, model),
   compute the rank correlation between axis-derived predicted
   difficulty and empirical success rate. Where do the axes
   succeed? Where do they fail systematically?

3. **Discover predictors.** Hypothesis-driven feature engineering:
   propose candidate predictors for tool-call success
   (prompt-surface keywords, in-prompt-answer flags, refusal-mode
   triggers, tool-target ambiguity, training-cutoff distance). For
   each, test correlation with empirical success.

4. **Validate on held-out.** Hold out ~10% of the bulk corpus.
   Train (informally) a small classifier on the rest. Test on the
   held-out set. Report accuracy + per-tool breakdown.

5. **Synthesize.** Produce a revised axis-set proposal (analogue
   to 002's `difficulty_axes_proposal.md`) targeting tool-call
   calibration directly. Mark in writeup which 002 axes survive
   and which are superseded.

## Decisions

_Populate as work proceeds._

## Results

> **Status update (2026-05-22).** Phase A4 grading on `bulk_seeds.jsonl`
> was in fact completed under this investigation's 2026-05-12 rollout
> (`results/gemma3_{4b,12b}-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl`).
> The "pending A4" framing below predates that run. The corresponding
> analyses live at:
>
> - `../006-temperature-prompt/results-analysis/prediction_agreement_summary.md`
>   — corpus-wide agreement between Opus difficulty labels and empirical
>   success. Headline: Opus's predictions function as a trivial-task
>   detector, not an ordinal scale. 12B precision 0.83 vs 0.67 baseline;
>   4B essentially at noise; `extreme` anti-informative for 4B.
> - `../006-temperature-prompt/results-analysis/prediction_agreement_per_tool_summary.md`
>   — per-tool breakdown of the same data. Headline: the trivial detector
>   is tool-conditioned. `python_execute` precision 1.00 on both models;
>   `gkl`/`ukl` strong on both; `calculator` and `datetime_now` are
>   anti-informative or at baseline. The corpus-wide 4B-vs-12B gap is
>   largely an artifact of where the trivial baseline is already high.
>
> Both summaries materially sharpen this investigation's diagnostic
> finding from "axes don't predict" to "the predictive structure that
> exists lives at the tool-family level, not the ordinal axis level."
> Reformulation work moved to `studies/002-principle-bootstrapped-difficulty`.

### Failure breakdown by tool (4B, 2026-05-23)

Stepping back from the question "how often does the model do the right
thing?" toward "what kind of wrong thing does it do when it doesn't?" —
because the headline calibration success rate (0.69 across n=3,660
trials) lumps together six tool families with qualitatively distinct
failure regimes.

Figure: `figures/out/failure_breakdown_by_tool.png`.

The bucket assignment uses `harness.parser.classify_trial` for the
error class (over_call / under_call / wrong_tool / success) and the
new `classify_no_tool_behavior` to split `under_call` into
`clarifying_question`, `refusal`, and `direct_answer` based on the
output text. The refined parser is documented in the case-study
section of `studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline`.

Per-tool failure signature (4B, neutral baseline, n=10 trials/record):

| Tool | n trials | success | dominant failure | minor failures |
|---|---|---|---|---|
| calculator | 1,180 | 0.82 | over-call (~14%) | trace under-call/wrong-tool |
| unit_convert | 520 | 0.78 | over-call (~17%) | trace others |
| gen_knowledge_lookup | 580 | 0.78 | under-call · refusal (~20%) | small over-call |
| datetime_now | 250 | 0.66 | over-call (~32%) | small under-call |
| user_knowledge_lookup | 480 | 0.51 | under-call · clarifying (~25%) + refusal (~18%) | small over-call, ~4% direct |
| python_execute | 650 | 0.47 | wrong-tool (~35%) | ~10% under-call · direct |

The headline observation is that **"failure rate" is the wrong
abstraction**. The interventions that would move each tool's number are
qualitatively different:

- Tools with **over-call** as the dominant failure (calc, unit_convert,
  datetime) need a "trust your own knowledge on trivial cases" signal.
- **python_execute** failures are routing failures — the model
  recognizes a tool is needed and picks the wrong one (calculator for
  SHA-256, prime sums, etc).
- **user_knowledge_lookup** failures are dominated by a behavior the
  parser previously couldn't see: the model asks the user a clarifying
  question instead of invoking ukl. This is the population-scale
  version of the daughter/brother case studies in study 002 inv 001.
- **general_knowledge_lookup** failures are refusals — the model
  declines to look up rather than reaching for gkl.

Only one failure class — **`under_call · direct_answer`** — produces a
confidently-wrong answer with no signal that anything went wrong.
That class is small on every tool (highest on python_execute at ~10%
of trials). Most "model failed" trials are the model recognizing a
limit and either escalating to the wrong tool, asking the user, or
refusing.

### What "success" hides

A natural follow-up: success itself is not homogeneous. There are
four distinct ways to register as a success under the calibration
rules — only the first is "the model called the right tool":

| Mode | When | What we know about correctness |
|---|---|---|
| `success_tool_called` | warranted record, target tool invoked | We don't execute the call; can't grade the args. Likely correct on calc/datetime/unit_convert (deterministic), uncertain on gkl/ukl/python. |
| `success_direct` | unwarranted record, model answered without a tool | Answer correctness is **ungraded.** Could be confident-correct or hallucination. |
| `success_clarify` | unwarranted record, model asked the user | Honest deferral. Not an answer at all. |
| `success_refusal` | unwarranted record, model refused | Honest deferral. Not an answer at all. |

Figure: `figures/out/success_decomposition_by_tool.png`.

Exact counts on 4B:

| Tool | warranted half successes | unwarranted half: direct | clarify | refusal | wA/wB record pool |
|---|---|---|---|---|---|
| calculator | 540 | 423 | 0 | 2 | 590/590 |
| python_execute | **8** | 274 | 0 | 25 | 300/350 |
| gen_knowledge_lookup | 178 | 220 | 0 | 55 | 290/290 |
| unit_convert | 170 | 237 | 0 | 0 | 200/320 |
| user_knowledge_lookup | **28** | 121 | 27 | 67 | 240/240 |
| datetime_now | 81 | 63 | 0 | 19 | 90/160 |

Two findings that the headline calibration rate obscures:

1. **python_execute's 0.47 success rate is almost entirely from the
   unwarranted half.** Of 300 trials where python_execute was the
   warranted tool, the model called it correctly **8 times**. The other
   ~292 are wrong-tool or under-call failures. The pair-B half props up
   the overall number.
2. **user_knowledge_lookup is the same story.** 28/240 on the warranted
   half — the model invokes ukl in roughly 12% of trials where it
   should. The 0.51 headline is held up by the unwarranted half, where
   the model correctly doesn't call ukl by mixing direct answers,
   clarifying questions, and refusals.

The third observation worth flagging: **`success_clarify` is structural
to user_knowledge_lookup**. Across all six tools, clarifying-question
successes only appear on ukl (27 trials). That's a function of what the
prompts look like — ukl prompts are the only ones where the model has a
coherent reason to ask the user for more info. It's a clean structural
signal in the data.

### What's still ungraded

- For `success_tool_called`: argument correctness. The harness emits
  the call expression but doesn't execute it. Whether the call would
  have produced the right answer if executed is unknown.
- For `success_direct`: answer correctness. The model answered without
  a tool; we don't grade whether the answer is right.

These are the two real gaps to a "did the model correctly answer the
question?" view. (a) is addressable on calc/datetime/unit_convert with
a deterministic evaluator. (b) needs a grader on every unwarranted
record. Programmatic for gkl/ukl (KB-backed), Haiku-as-judge or
domain-specific for the rest. Sketched at
`../../studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline/GRADING.md`.

### Answer correctness vs calibration success (4B, 2026-05-23)

Deterministic graders for `calculator`, `unit_convert`, and `datetime_now`
let us score answer correctness independent of calibration. Module:
`harness/correctness.py`. Driver: `scripts/grade_a4_deterministic.py`.
Output: `results-correctness/gemma3_4b-it-qat/`. Full assumption list:
`results-correctness/REPORT.md`.

Figure: `figures/out/correctness_vs_calibration_heatmap.png`.

Three-panel 2×2 heatmap of (answer-correct × calibration-success) per
tool. Headline numbers:

| Tool | n graded | correctness | calibration | correct ∧ calibrated | correct, calibration FAIL | calibration OK, answer WRONG |
|---|---|---|---|---|---|---|
| calculator | 1,180 | 0.86 | 0.82 | 833 (71%) | 177 (15%) | 132 (11%) |
| unit_convert | 520 | 0.81 | 0.78 | 338 (65%) | 86 (17%) | 69 (13%) |
| datetime_now | 230 | 0.13 | 0.67 | 29 (13%) | 2 (1%) | 124 (54%) |

(datetime_now excludes 110 trials marked `ambiguous_ground_truth` —
wall-clock-time prompts that need the trial's clock time, not just date.)

Three findings the calibration view alone doesn't surface:

1. **Calculator and unit_convert: correctness slightly *exceeds*
   calibration.** The 15-17% "calibration FAIL, answer correct" cell
   is the model under-calling but solving in-head correctly. The
   over-call pattern is therefore **not** the model needing the tool
   to be right — the model is capable of answering, and reaches for
   the tool anyway. This sharpens the over-call finding rather than
   undermines it.
2. **Calculator: 132 trials are calibration ✓ but answer ✗.** The model
   called the tool with arguments that would evaluate to the wrong
   answer. The dominant subpattern (per the grader's notes): "natural
   logarithm of N" → `math.log(N, 10)` instead of `math.log(N)`. This
   is a real calibration-of-arguments bug invisible to the calibration
   classifier.
3. **Datetime_now: 54% of graded trials are calibration ✓ but answer
   ✗.** The model dutifully calls `datetime_now(...)` and then stops
   without producing a prose answer. This is largely a **harness
   artifact** — the harness doesn't execute tool calls, so the model
   has nothing to compose an answer from. The 0.67 calibration number
   on datetime grossly overstates how often the user gets an answer.
   Treat datetime correctness as uninterpretable until tool execution
   is wired up.

The calculator and unit_convert numbers are interpretable as-is. The
datetime number is currently a measurement of the harness, not the
model.

### Synthesis (2026-05-23)

Working summary across this investigation, study 002 inv 001, and the
correctness pass:

1. **Tool-use evaluation has multiple failure points and multiple ways
   to succeed.** "Success" lumps four behaviors (tool called, direct
   correct answer, clarifying question, refusal); "failure" lumps four
   more (over-call, wrong-tool, under-call to direct/clarify/refusal).
   Aggregating these as a single rate destroys the signal.
2. **Self-prediction is not uniformly weak.** F3 (Q3 behavior
   prediction vs A4 empirical) ranges from 0.43 on calculator to 0.875
   on user_knowledge_lookup. The dominant self-prediction error across
   all tools is **under-prediction of own tool use** — 86% of F3 errors
   are "I said I'd answer directly, but I called a tool." Calculator
   carries this pattern most strongly because it's the largest bucket.
3. **Calibration failure modes are tool-conditioned.** Over-call
   dominates on calc / unit_convert / datetime_now. Wrong-tool
   dominates on python_execute. Under-call · refusal dominates on gkl.
   Under-call · clarifying question dominates on ukl. There is no
   single failure pattern; the right intervention is per-tool.
4. **Correctness and calibration are partially orthogonal.** Calc and
   unit_convert: ~15% of trials are correct despite calibration
   failure; ~12% are calibration ✓ but answer ✗. The two axes measure
   different things and should be reported jointly, not as a single
   "success rate." (Datetime confirms this in the extreme — 67%
   calibration vs 13% correctness — though that's harness, not model.)
5. **python_execute's wrong-tool dominance has two components.** Some
   wrong-tool failures are real (SHA-256 isn't computable in
   calculator). Others may reflect a corpus-construction ambiguity
   (sum-of-primes is computable in either calculator or python). The
   "test construction error" framing is partially right; need to
   triage the python pool before treating the 35% wrong-tool rate as
   a clean model signal.

### Methodological pivot (2026-05-23)

The 366-record breadth corpus has earned its keep — without it, the
ukl clarifying-question pattern, the python wrong-tool dominance, and
the datetime calibration-vs-correctness gap would have been invisible.
But the marginal value of additional breadth is now low. The corpus
has surfaced 4–5 distinct signals; each deserves a focused,
hypothesis-driven investigation rather than more sampling.

Going forward: **wide screening, then deep targeted drills.** Below
are candidate next investigations, each scoped to ~50–100 trials and
each with a falsifiable hypothesis.

#### Candidate next investigations

##### NS-1 — Calculator over-call ablation
Hypothesis: a single instruction-prompt addition ("on arithmetic
problems with operands ≤ 3 digits and no precision specification, do
not call the calculator — answer directly") reduces the over-call rate
on the trivial half of calculator pairs without hurting the warranted
half. Pre-register the cutoff. Run on ~50 calculator pair-B records,
compare against neutral baseline. Outcome metric: change in
correctness on pair-B; check pair-A correctness doesn't drop.

##### NS-2 — Calculator argument-bug forensics
Hypothesis: the `math.log(N, 10)` pattern reflects a "natural
logarithm" → "common logarithm" semantic confusion specific to a
phrasing of the prompt, not a deeper issue. Construct ~20 prompts
varying phrasing ("natural log", "log base e", "ln", "loge") and
sampling temperature. See if the pattern shifts. If it doesn't, this
is a real semantic gap in 4B; if it does, it's a prompt-sensitivity
artifact worth documenting.

##### NS-3 — ukl clarifying-question intervention
Hypothesis: prepending "if a private fact is missing from the prompt,
call user_knowledge_lookup immediately; do not ask the user for
clarification first" measurably shifts the clarifying-question rate
toward tool-calls. Run on the ~25% of ukl pair-A records that
empirically resolve via clarifying-question in the neutral baseline.
Outcome: per-trial tool-call rate; check that clarification rate
doesn't simply get replaced by refusal.

##### NS-4 — python_execute corpus triage
Not a model experiment but a corpus audit. For each python pair-A
record, hand-classify whether the task is unambiguously python (e.g.,
SHA-256), ambiguously python-or-calculator (sum-of-primes), or wrong
seed (could be done by calculator alone). Report the proportions and
re-run the wrong-tool rate on the unambiguous subset. If the
unambiguous subset still shows ≥20% wrong-tool, the routing failure
is real; if it drops below baseline, the original number was a
seed-construction artifact.

##### NS-5 — Tool execution and datetime correctness
Infrastructure question, not a model experiment. Decide whether to
wire up tool execution in the harness. If yes, re-grade datetime
correctness with the executed-tool path; expect correctness to jump
toward calibration. If no, exclude datetime from correctness reporting
and document it as a measurement limitation.

Of these, NS-1 is the cleanest first drill: hypothesis is sharp,
existing corpus suffices, the principle-library framing of study 002
maps directly onto it.

_Original (pre-A4) preliminary signal preserved below._

Preliminary signal already visible in 006 F3/F4/F5 (n=18 corpus):
- Curator `hard` → empirical `trivial` for ~9/15 records at 12B,
  ~5/15 at 4B.
- `python_execute` records are over-represented in the empirically-
  hard tail; `general_knowledge_lookup` and `user_knowledge_lookup`
  cluster at the top of empirical success regardless of curator
  label. Reviewer observation in 006 commit: "I find it really
  interesting that the General Knowledge and User Knowledge don't
  fall under Extremely hard ever from an empirical perspective..."
- A1 corpus is missing `easy` and `extreme` curator labels
  entirely — the bulk corpus (003) fills these in.

## Forward-looking

- **The new axes proposal will likely live as Decision 1 of this
  investigation** once the empirical work is in. Don't pre-judge
  what the axes are; let the data drive.
- If the answer is "no single axis system predicts well; success
  is dominated by record-specific surface features," the practical
  output may be a feature library + a small classifier rather than
  a clean axis taxonomy. Worth signaling this honestly in the
  writeup.

## Things to flag

- Reviewer-flagged finding (2026-05-12): "we'll want to update our
  documentation of tasks so the empirical gradings are
  model-relative." Done in `calibration_methodology.md` —
  empirical bucketing is per-model by design. Methodologically,
  every empirical-difficulty citation must name the model.
- Reviewer interest in the **gkl/ukl never empirically extreme**
  observation. Likely explanation: gkl/ukl records have a clear
  cognitive moment ("model can't possibly know this from training,
  so the right move is to call the tool"), and even partial
  recognition gets the model to a high success rate. Whereas
  python_execute records require the model to (a) recognize a
  tool is needed AND (b) pick the right tool — two-stage
  failure mode. Worth testing this hypothesis explicitly.

## Limitations

- This investigation requires Phase A4 grading of the bulk corpus
  to have enough data to test rank correlations and validate any
  candidate predictors. Until then, the work is preliminary on
  n=18 / n=36 record sets.
- Any "predictor library" produced here is calibrated to the
  Gemma 3 4B / 12B IT model family. Cross-family transfer is not
  tested.
