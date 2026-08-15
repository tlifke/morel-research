# Phase 2 outline — Tinker fine-tuning

Not scheduled. Opens only after inv 005 returns Phase-1 results. Carried
forward unchanged from the reference plan; recorded here so Phase-1 design
choices stay compatible with it.

## Shape

1. **SFT bootstrap** — deliberative-alignment pattern: principles in prompt →
   generate → filter by grader → chat-SFT recipe.
2. **RL** — composite reward `α·answer + β·citation_F1` via a custom cookbook
   Env, with `rl_basic.py`'s loop as the reference implementation.
   - **β=0 ablation is the key comparison.**
   - F1, not recall, so cite-everything doesn't win.
   - Fully programmatic reward. No judge.
3. **Faithfulness check** — ablate a cited principle from the prompt-time set
   and verify behavior changes (TTS-adjacent).

## Headline experiments

- Composite vs answer-only reward at matched compute.
- OOD: held-out and edited principles.
- Post-FT size grid vs frontier (H3).
- Rule-ablation faithfulness.

## Data

FT training data comes from the official-train remainder only. The official
test split stays untouched until final results.

## Phase-1 obligations this creates

- The results store must retain enough per-decision structure to build SFT
  targets and compute citation F1 as a reward, not just as an analysis metric.
- The principle set must support "held-out" and "edited" variants — so
  `Principle` records need stable ids and the prompt assembler needs to take a
  principle subset as a parameter.
