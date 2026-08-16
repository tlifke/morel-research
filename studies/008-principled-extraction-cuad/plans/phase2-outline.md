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

## Open — how much data does the fine-tuning actually need?

Noted 2026-08-16, deliberately **not** worked through yet. Flagged now so it is
answered before the training pool is committed rather than discovered during a
run.

What is already known and does not need re-deriving:

- The pool is **264 contracts** (`model_train`), ~3,168 `(contract, category)`
  decision units before any k>1 rejection sampling.
- INV1-D8 concluded contract *count* was never the binding constraint: SFT is
  rejection-sampled per decision, and RL reuses prompts across epochs, so unique
  prompts are not scarce. **Reward signal per rare category is.**
- The concrete casualty: `Source Code Escrow` has **2 positive contracts** in
  the pool. Any per-category claim about it after fine-tuning is unsupportable.

What still has to be decided, when Phase 2 opens:

- SFT: how many accepted samples per decision are needed, and at what
  rejection-sampling k — which sets the real generation cost, not the contract
  count.
- RL: episodes to convergence at the chosen LoRA rank, and whether 3,168
  distinct prompts is enough diversity to avoid memorising the pool.
- Whether the composite reward's β term needs *more* data than the answer term,
  since citation correctness is a sparser signal than span overlap.
- Whether rare categories should be **excluded from per-category claims** or
  the pool **rebalanced toward them** — the second means re-carving splits,
  which is a G1-class change, so it must be decided before the freeze hardens.
- Whether Phase 2 needs its **own validation split** for early stopping and
  hyperparameters, or borrows `harness_val`. It currently has neither.

## Phase-1 obligations this creates

- The results store must retain enough per-decision structure to build SFT
  targets and compute citation F1 as a reward, not just as an analysis metric.
- The principle set must support "held-out" and "edited" variants — so
  `Principle` records need stable ids and the prompt assembler needs to take a
  principle subset as a parameter.
