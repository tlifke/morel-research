---
id: studies/001-tool-calibration/investigations/006-temperature-prompt
title: Temperature × prompt interaction (methodology lockdown)
status: in-progress
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

_To be populated after the 2×2 run completes._

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
