---
id: studies/001-tool-calibration/investigations/006-temperature-prompt
title: Temperature × prompt interaction (methodology lockdown)
status: complete
parents:
  - studies/001-tool-calibration
children: []
related:
  - studies/001-tool-calibration/investigations/004-calibration-pilot
  - studies/001-tool-calibration/investigations/005-tool-spec-optimization
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - methodology
  - temperature
  - prompt-engineering
  - 2x2
aliases:
  - 006
created: 2026-05-12
updated: 2026-05-12
---

# Investigation 6 — Temperature × prompt interaction

## Scope

Lock down the empirical methodology for downstream calibration runs
(including the planned 12B IT escalation in
`../004-calibration-pilot/`) by running a **2×2 factorial** on 4B
IT before scaling up. The two factors:

- **Sampling temperature**: `0.0` (deterministic / greedy) vs `1.0`
  (production-typical, with top_p=0.95).
- **Prompt set**: `neutral` (A1's canonical tool descriptions —
  `sys_*_neutral_v1.txt`) vs `directive` (the bundled-winners
  prompts from 005 — `sys_*_directive_v1.txt`).

Each cell is the full A1 corpus (36 records) at n=10 trials, so
4 × 36 × 10 = 1,440 calls total. Two questions:

1. **Main effect of temperature.** How much of the original 4B
   pilot's "20/20 deterministic failure" pattern was sampling
   artifact vs. intrinsic model behavior? 005's experiments
   surfaced that baseline rates at temp=1.0 are markedly higher
   than at temp=0; this run quantifies the effect on the full
   corpus.
2. **Main effect of prompt.** How much of the calibration map is
   intrinsic to the model vs. fixable via tool-description
   engineering? Difference of B − A at temp=0, and of D − C at
   temp=1.0, gives the "prompt-engineering contribution."
3. **Interaction.** Does the prompt-engineering delta change with
   temperature? If directive-prompt benefit shrinks at temp=1.0
   (because the model already does the right thing some of the
   time), the prompt-engineering work has a *complementary* role
   to sampling. If it persists, prompt engineering matters
   regardless of sampling regime.

|                | Neutral | Directive |
|----------------|---------|-----------|
| **temp=0.0**   | A       | B         |
| **temp=1.0**   | C       | D         |

## Methods

Runner: `harness/runner.py` with the new `--temperature` and
`--prompt-set` flags. The four cells run sequentially via a small
shell driver. Results written to
`results/gemma3_4b-it-qat/006_<cell>_<date>.jsonl`. Per-trial rows
capture `prompt_set`, `resolved_system_prompt_id`, `temperature`,
`top_p` — so the analyzer can slice cleanly.

System prompts: the four `sys_*_directive_v1` entries added to the
manifest bundle the 005 winners:
- ukl: v1a_antirefusal (REQUIRED + anti-refusal clause)
- python_execute / calculator: vP1_boundary (boundary clarification)
- general_knowledge_lookup: vG1_temporal (specificity + temporal cue)
- calc / datetime_now / unit_convert: vT1_skip_trivial (skip-trivial
  clause). Calculator description merges vP1 + vT1.

`sys_no_tools_v1` has no directive variant (no tools to make
directive about); it stays unchanged across cells.

## Decisions

_Populate as work proceeds._

## Results

### 4B IT 2×2 — Gemma 3 4B IT (QAT Q4_0), n=10 (2026-05-12)

Run metadata:
- model: `gemma3:4b-it-qat`
- corpus: full A1 seed set (36 records)
- n: 10 trials per (cell, record); 4 cells × 36 × 10 = 1,440 calls
- results files (gitignored):
  `results/gemma3_4b-it-qat/006_{A,B,C,D}_{cell-tag}_2026-05-12.jsonl`
- analyzer: `harness/analyze_2x2.py` (rescores from raw output)

**Cell means (success_rate averaged across 36 records):**

|              | neutral | directive | Δ prompt |
|--------------|--------:|----------:|---------:|
| **temp=0.0** |  0.664  |   0.747   |  +0.083  |
| **temp=1.0** |  0.631  |   0.739   |  +0.108  |
| Δ temp       | -0.033  |  -0.008   |          |

**Interaction (Δprompt at temp=1.0 − Δprompt at temp=0):** **+0.025**.
Prompt-engineering benefit is slightly larger at temp=1.0 than
temp=0; the two effects are close to additive. Plausibly because
at temp=0 the model deterministically resists some prompts even
under directive, while at temp=1.0 stochasticity gives the
directive more room to nudge behavior. The interaction is small
(2.5 pp) compared to the main effects.

**Error-type counts per cell** (summed across all 360 trials):

| cell | over_calls | under_calls | wrong_tool | total |
|------|-----------:|------------:|-----------:|------:|
| A — neutral, temp=0 | 50 | **51** | 20 | 121 |
| B — directive, temp=0 | 51 | **20** | 20 | 91 |
| C — neutral, temp=1.0 | 52 | **59** | 22 | 133 |
| D — directive, temp=1.0 | 49 | **28** | 17 | 94 |

**Single most-important finding: directive prompts cut under_calls
by ~60% (51→20 at temp=0; 59→28 at temp=1.0) but leave over_calls
basically unchanged.** The prompt-engineering benefit lives almost
entirely in the under_call column. Over-calling is a structurally
separate failure mode that the "REQUIRED whenever..." pattern does
not address.

### Directive-induced regressions

Per-record analysis (full matrix in the analyzer output) surfaces
4 records where directive prompts strictly worsen behavior:

| Record | sr A→B | sr C→D | What changed |
|--------|--------|--------|--------------|
| `gkl-arsenal-trivial` (1966 World Cup) | 1.00 → 0.00 | 1.00 → 0.00 | Model now over-calls gkl on pre-cutoff fact it knows directly |
| `ukl-aunt_nina-trivial` (in-prompt) | 1.00 → 0.00 | 0.80 → 0.10 | Model over-calls ukl despite the answer being in the prompt |
| `python-leap_year-trivial` (Feb 28 2026) | 1.00 → 0.00 | 0.80 → 0.10 | Model over-calls when expected to abstain |
| `python-fibonacci-hard` (F_1000 mod 1M) | 1.00 → 0.00 | 0.20 → 0.20 | At temp=0, py_only_directive's "REQUIRED..." pattern makes the model think harder and try Pisano-period in head |

Three of these are **directive triggering over-calls on trivial
halves** — the matched-pair partner of a record where the directive
correctly helped on the hard half. The "REQUIRED whenever..."
language is too aggressive and breaks the trivial/warranted
asymmetry the matched-pair design relies on.

The fibonacci regression is different — the py_only_directive's
"REQUIRED for any computation calculator cannot do" framing
inadvertently signals "this is a hard problem; reason about it
carefully" — and the model chooses to reason rather than offload.

### Big wins from directive

Records where Δprompt is ≥ +0.50 in at least one temperature row:

| Record | A→B | C→D | Failure mode neutral fixed by directive |
|--------|-----|-----|-----------------------------------------|
| `calc-mult4digit-trivial` ("Compute 4 × 7") | +1.00 | +0.60 | trivial over_call |
| `dt-current_date-trivial` (in-prompt date) | +0.90 | +0.60 | trivial over_call |
| `gkl-nla_paper-hard` | +0.90 | +0.10 | confabulation |
| `python-sha256-hard` | +1.00 | +1.00 | wrong_tool (calculator → python_execute) |
| `unit_convert-trivial` ("5 m to cm") | +1.00 | +0.80 | trivial over_call |
| `ukl-aunt_nina-hard` ("Is Aunt Nina left-handed?") | +1.00 | +0.90 | tool-blind deferral |
| `ukl-daughter_school-hard` | +1.00 | +0.20 | tool-blind deferral |

The wins cluster on the failure modes 005 was designed to address.

### 12B IT 2×2 — Gemma 3 12B IT (QAT Q4_0), n=10 (2026-05-12)

Same factorial design as 4B IT, same harness, same prompts, same
seed corpus. Wall time ~16 minutes total across 4 cells (much
faster than the budgeted 2–3 hours — desktop 3080 chews through
12B Q4_0 at ~450 ms/call).

**Cell means:**

|              | neutral | directive | Δ prompt |
|--------------|--------:|----------:|---------:|
| **temp=0.0** |  0.778  |   0.889   |  +0.111  |
| **temp=1.0** |  0.797  |   0.869   |  +0.072  |
| Δ temp       | +0.019  |  -0.019   |          |

**Interaction: −0.039.** At 12B, the directive benefit is
*smaller* at temp=1.0 than at temp=0 — opposite sign from 4B's
+0.025. The likely explanation: 12B at temp=1.0 already does
many of the right things at neutral baseline (it gets NLA paper
right, it handles the trivial halves better), so the directive has
less room to lift it.

**Error-type counts per cell:**

| cell | over_calls | under_calls | wrong_tool | total |
|------|-----------:|------------:|-----------:|------:|
| A — neutral, temp=0 | 40 | 39 | 1 | 80 |
| B — directive, temp=0 | 20 | 10 | 10 | 40 |
| C — neutral, temp=1.0 | 39 | 30 | 4 | 73 |
| D — directive, temp=1.0 | 23 | 18 | 6 | 47 |

**`wrong_tool` nearly vanishes at 12B.** The calc-vs-python
boundary confusion that drove 4B's SHA-256 and prime_sum failures
is mostly resolved by scaling. (Curious uptick in Cell B: 1→10
wrong_tool entries; mostly the directive prompt encouraging the
model to attempt calls on records where neutral correctly abstained.)

### 4B vs 12B head-to-head (both at temp=1.0)

|             | Neutral | Directive | Δ prompt |
|-------------|--------:|----------:|---------:|
| **4B IT**   | 63.1%   | 73.9%     | +10.8 pp |
| **12B IT**  | 79.7%   | 86.9%     | +7.2 pp  |
| Δ scale     | +16.6 pp | +13.0 pp |          |

- **Scaling from 4B to 12B at neutral gives +16.6 pp; prompt
  engineering on 4B gives +10.8 pp.** Scaling wins, but
  prompt-engineering is non-trivial.
- The effects roughly stack: 4B neutral → 12B directive is +23.8 pp.
- Prompt-engineering gives a smaller relative lift at 12B (+13 pp
  scaling, +7.2 pp prompt at 12B) — diminishing returns as the
  model becomes more capable.

### Patterns robust across model scale

1. **`python-fibonacci-hard` regresses under directive at temp=0 in
   both 4B and 12B.** "REQUIRED for any computation calculator
   cannot do" invites Pisano-period reasoning. Same record, same
   regression direction, both model sizes. Robust finding about
   how directive language interacts with computation prompts.
2. **Trivial-half over-call cluster (calc 4×7, datetime in-prompt
   date, unit-convert 5m→cm) all respond to directive across
   both scales.** vT1's skip-trivial framing works consistently.

### Patterns differing across model scale

1. **NLA paper confabulation is a 4B problem only.** At 4B
   neutral, the model fabricated a 2020 publication date 90% of
   the time. At 12B neutral, the model correctly invokes
   `general_knowledge_lookup` 100% of the time.
2. **Trivial-half regressions are 4B-specific.** `gkl-arsenal-trivial`
   and `ukl-aunt_nina-trivial` regressed -1.00 at 4B under
   directive; both are zero-change at 12B. **The directive
   prompts as drafted break 4B much harder than 12B.** This
   matters for the style guide — the "REQUIRED whenever +
   Do NOT call when {trivial}" pattern recommended there is
   load-bearing primarily for 4B-class models.
3. **`wrong_tool` count drops from 17 → 6 between 4B and 12B
   under directive.** Scale fixes most of the tool-selection
   confusion the directive doesn't address.

### Scale × directive interaction at 12B (2026-05-12 follow-up)

The 4B-vs-12B scatter (F2 banded) surfaced a "Scale Hurts / Scale
Breaks" region — records where 12B underperforms 4B under directive
prompts. Reading the actual outputs:

| Record | 4B Cell D | 12B Cell D | Failure pattern at 12B |
|--------|----------:|-----------:|------------------------|
| `calc-mult_isolated` trivial half ("5 × 9") | 1.00 | **0.00** | Reads `calc_only_directive`'s "use for arithmetic" literally; calls calculator 10/10 trials. 4B respects the same description's "skip for single-digit arithmetic" clause. |
| `aunt_nina` warranted half | 1.00 | **0.50** | Mixed: Socratic deflection ("is she a public figure?"), wrong-tool (`general_knowledge_lookup` instead of `user_knowledge_lookup`), intermittent no-call. **12B invented escape routes 4B didn't.** |
| `datetime_now` current_date warranted | 1.00 | **0.70** | Answers from training distribution 3/10 trials despite directive — interprets "please" + directive's "answer directly when unambiguous" as license to abstain. |
| `anniversary` trivial half (in-prompt) | 1.00 | **0.70** | Same directive over-eagerness pattern as 4B but milder. |

**Finding:** scale doesn't strictly improve calibration when paired
with prescriptive prompts. **The directive becomes a stronger handle
on the larger model**, and 12B follows it more literally to
unintended consequences. The "scale fixes calibration" narrative is
incomplete — scale fixes neutral-baseline calibration but introduces
new model-prompt interactions under directive language.

Implication for the style guide (005): prescriptive clauses need to
be tested at multiple model scales. A clause that works on 4B
(e.g. "use calc for arithmetic, skip for trivial") can produce
literal over-application at 12B (uses calc for all arithmetic
including trivial). The style guide's caveat "verify on target
model" is load-bearing.

### Axes-performativity follow-up (2026-05-12)

Two figures (F4 heatmap + F5 dot plot) extend F3's "axes don't
predict success" finding to the per-record level:

- **F4 (curator-vs-empirical heatmap):** for both 4B and 12B, the
  curator's `hard` records empirically land in the `trivial` bucket
  (5/15 records for 4B, 9/15 for 12B). The diagonal — perfect
  prediction — is mostly empty. The mass concentrates in the
  bottom-left corner: records labeled `hard` by the curator but
  empirically `trivial` (sr ≥ 0.95).
- **F5 (per-record dot plot):** at the per-record level, `calculator`
  and `general_knowledge_lookup` records (blue, red dots) sit at
  the top of the empirical axis regardless of curator label.
  `datetime_now` and `user_knowledge_lookup` records are more
  spread vertically. The axes' predictive power is *tool-dependent*,
  not just bucket-dependent.
- The A1 corpus has no `easy` or `extreme` curator labels (visible
  as the empty rows in F4). Bulk corpus (003 → A4) will populate
  those bands; the picture may shift.

**Resolution still open** — see the axes-performativity sibling-
investigation note in study.md Forward-looking.

### Methodology findings

1. **Use temp=1.0 going forward** (per reviewer direction; aligns
   with production-typical sampling). Cost: small accuracy hit
   (-3 pp at neutral, -1 pp at directive). Benefit: clean
   methodology and slightly larger directive-prompt response.

2. **Do not auto-adopt directive as the canonical baseline.** The
   directive prompts as drafted aren't Pareto improvements —
   they reduce under-calls but introduce over-calls on trivial
   halves. The matched-pair design is partially broken by current
   directive language.

3. **Style-guide implication (for 005):** "REQUIRED whenever..."
   needs an explicit *escape clause* — something like "REQUIRED
   whenever the user asks about X. Do NOT call for trivial cases
   where you can answer directly, even if X is mentioned." The
   trivial/warranted asymmetry has to live IN the description,
   not be implicit.

4. **n=10 sufficient.** Cell means and per-record buckets converge
   well below 20 trials; n=20 would change at most boundary
   records.

5. **12B run should test BOTH neutral AND directive at temp=1.0.**
   Per-record patterns may differ even if cell means stay similar;
   the directive-induced regressions might not transfer to 12B.

## Decisions

> **Decision 1 — parser supports both fenced and bare tool_code blocks** (2026-05-12)
> Mid-run discovery: directive prompts cause 4B IT to drop the
> triple-backtick fences around `tool_code` blocks ~11% of the
> time. The original parser regex required fenced form, missing
> these calls. Updated `harness/parser.py` to accept `\`{0,3}tool_code\s*\n<call>`
> — fenced or bare. `harness/analyze_2x2.py` rescores from raw
> output so cells captured under the old parser get reclassified
> consistently at analysis time.

> **Decision 2 — temp=1.0 + top_p=0.95 is the methodological default** (2026-05-12)
> Cell C (neutral, temp=1.0) is the appropriate "production-typical
> neutral baseline" against which future model escalations and
> prompt variants get compared. temp=0 results remain useful as
> deterministic reference but not as headline calibration numbers.

> **Decision 3 — keep neutral prompts as canonical baseline** (2026-05-12)
> Despite +8–11 pp net improvement from directive prompts, the
> directive set introduces over-call regressions on trivial halves.
> The matched-pair design depends on the neutral prompts to probe
> organic tool choice cleanly. Directive prompts stay available as
> a Phase A4 *condition*, not the default. Future 12B runs compare
> against neutral baseline; directive is a separate analysis cell.

## Forward-looking

- **12B IT escalation** at temp=1.0, both neutral and directive.
  ~2–3 hours wall time. The interesting question is whether the
  per-record pattern (which records flip which way) transfers, or
  whether 12B has fundamentally different failure modes.
- **Style-guide refinement** (feeds 005). The directive prompts
  need explicit "skip for trivial cases" framing in the same
  description that says "REQUIRED whenever..." Test as a v2_directive
  set; re-run cells B and D to see if the over-call regressions
  resolve.
- **Socratic-deflection variant test** (v1a+): cheap to add to
  the 005 lineage now that we have the harness for variant A/Bs.

## Things to flag

- Cell C ran at temp=1.0 but the parser fix landed *mid-run* —
  some cell-C rows were classified under the old (buggy) parser.
  `analyze_2x2.py` always rescores from raw output, so analysis
  is correct; the stored `success` / `error_type` columns in the
  jsonl are stale for those rows but unused.
- 4B IT only. 12B IT may show different interaction patterns.
- The "directive" prompt set is a single specific authoring; not
  every prescriptive variant would yield the same effect.

## Limitations

- 1,440 trials on one model is enough to characterize 4B IT but
  not generalize the methodology to other models.
- Directive-induced over-call regressions are concentrated on
  trivial halves. The matched-pair structure may partly mask the
  prompt-engineering issue; bulk corpus (A3) work will need to
  watch for the same pattern at scale.

## Forward-looking

- The combined-directive prompts will become a candidate canonical
  set for the A1 corpus going forward, pending the 2×2 result.
- 12B IT escalation gated on this investigation closing — the
  methodology lockdown finding determines (a) which sampling
  regime is "production-typical baseline," (b) whether to run 12B
  at neutral or directive (or both).
- Style-guide synthesis (005 forward-looking) can incorporate any
  cross-temperature stability findings from here.

## Things to flag

- The 2×2 is a *single model* sweep (4B IT). Whether the
  temperature × prompt interaction generalizes to 12B (or to other
  model families) is a separate question — we'll see if the 12B
  run replicates the pattern.
- The "directive" prompts are themselves first-draft authoring,
  not a calibrated style guide. The directive vs. neutral
  comparison is "the specific directive variants we wrote" vs.
  "the specific neutral baseline we wrote" — neither is a
  privileged reference point.
- Run order matters for cache-warmth on Ollama (first cell pays
  load_duration; subsequent cells reuse the loaded model). Total
  wall time should still be ~60–90 min at 4B.

## Limitations

- 4B IT only. Generalization to other models open.
- One directive prompt set tested. Other prescriptive styles
  might give different ceilings.
- The original A4 pilot ran at temp=0 on the (now superseded)
  output_preview-only runner; the 2×2 runs use full-output
  storage, so the data is richer.
