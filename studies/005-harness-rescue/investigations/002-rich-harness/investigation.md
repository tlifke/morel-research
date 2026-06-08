---
id: studies/005-harness-rescue/investigations/002-rich-harness
title: Rich-harness build + ablation
status: planned
parents:
  - studies/005-harness-rescue
children: []
related:
  - studies/005-harness-rescue/investigations/001-steplaw-substrate
axes:
  llm_capability: medium
  human_capability: high
tags:
  - harness
  - context-engineering
  - ablation
  - reflexion
  - long-horizon
created: 2026-06-07
updated: 2026-06-07
---

# Inv 002 — Rich-harness build + ablation

## Scope

Build a **rich harness** around the *same* prompted weak model
(nemotron-3-nano:4b) on the *same* StepLaw substrate from inv 001, and
**ablate its components** to measure how much of the minimal-harness gap each
one closes. The gap to close is the inv 001 baseline:

- nemotron stalls **~45%** of runs (never actuates `finish`),
- median regret **0.006** (vs gemini ≈ 0), max 0.073,
- only **10/20** runs ever reach the optimum region (basin-trapping),
- yet its per-step search is competent (66% coordinate moves, 46% improving).

The question: **can context engineering substitute for training** to lift
this 4B toward gemini-flash-lite — and toward the *trained* 4B of
AutoLLMResearch — with no weight updates?

## Background — the interaction hypothesis (two anchor papers)

This investigation is positioned by two results that point in **opposite
directions**, which is exactly what makes the question live:

- **AutoLLMResearch** ([arXiv 2605.11518](https://arxiv.org/abs/2605.11518)) —
  *weak model + TRAINING*. A Qwen3-4B trained with policy distillation +
  multi-turn GRPO on a regret reward, over an LLMConfig-Gym that is nearly our
  exact task (propose config → get performance → minimize regret over a long
  horizon). The trained 4B **beats frontier reasoning models used zero-shot**
  (regret ~0.01–0.03 vs >0.2). Their ablation: PD-alone 0.144, RL-alone 0.190,
  combined 0.035 — both training stages needed. Crucially, one failure they
  fix with **harness, not training** — malformed Gym calls in later turns
  (~32% of rollouts) — via **Most-Similar-Configuration Matching** (redirect a
  bad call to the nearest valid config). That is a direct existence proof that
  *some* of the trained advantage is recoverable by scaffolding alone.
- **Automated Weak-to-Strong Researcher** (Anthropic, alignment.anthropic.com,
  2026) — *strong model + MINIMAL harness*. Nine Claude Opus 4.6 agents, three
  MCP tools (submit/score, share-findings, upload/download), **no prescribed
  scaffolding**. They tested a fixed workflow and it **underperformed** full
  autonomy: *"less imposed structure leads to better performance."*

So: **rich scaffolding HURTS an Opus-class model, while TRAINING is what a 4B
needs to win.** Our hypothesis is a **crossover/interaction with model scale**:
the structure that is dead weight at Opus is *load-bearing* at 4B — i.e. a
rich harness can stand in for some of the training a 4B would otherwise need.
This is consistent with study 004's finding that nemotron's bottleneck is
**actuation + stamina, not capability** (`project_researcher_stamina_bottleneck`),
and with inv 001 here (competent search, but stalls + basin-trapping).

## What "rich harness" means — literature-grounded components

A "rich harness" is **context engineering**: structured context, externalized
state, in-loop reflection, and recovery scaffolding — all at inference time,
no weight updates. Each component below is tied to its literature and to the
specific inv-001 failure it targets. (Grading = strength of literature
support.)

| Component | Targets (inv 001 failure) | Literature | Operationalization on StepLaw |
|---|---|---|---|
| **R1. Verbal reflection** (per-step "what did that result teach me") | loose search; basin-trapping | **Reflexion** ([2303.11366](https://arxiv.org/abs/2303.11366)) — verbal RL; the training-free analog of AutoLLMResearch's GRPO credit assignment | After each `run_config`, force a 1-line reflection ("lr too low, loss flat → jump lr up") appended to an episodic buffer that conditions the next proposal |
| **R2. Structured handoff-with-state** | stamina; context rot | **Generative Agents** ([2304.03442](https://arxiv.org/abs/2304.03442)), **MemGPT** ([2310.08560](https://arxiv.org/abs/2310.08560)), Anthropic *Effective Context Engineering* (2025) | Re-inject a curated **config→loss→note table** (best-K + recent), not the raw transcript; drop failed-call cruft to kill self-conditioning ([2605.02572](https://arxiv.org/abs/2605.02572)) |
| **R3. Results-playbook** | basin-trapping; aimless wandering | **Plan-and-Solve** ([2305.04091](https://arxiv.org/abs/2305.04091)); branch/backtrack framing from **ToT** ([2305.10601](https://arxiv.org/abs/2305.10601)) — synthesis, not a single citation | A revisable strategy in context: coarse-sweep → find region → exploit → "if you haven't tried high lr × high bs, do it"; explicit heuristics (diverge → halve lr) |
| **R4. Recovery + finish scaffolding** | **~45% stall**; off-grid loops | AutoLLMResearch Most-Similar Matching ([2605.11518](https://arxiv.org/abs/2605.11518)); MAST failure taxonomy ([2503.13657](https://arxiv.org/abs/2503.13657)) — *premature termination*, *failure-to-commit*, *missing termination cues* | On yield-without-finish, detect the prose conclusion and **re-prompt to actuate `finish`** (or auto-submit best); on stall/loop, steer. Already partly in inv 001 (consec-reject guard) |
| **R5. Bounded episodes / compaction** | stamina; meltdown | Anthropic **compaction**; meltdown detection ([2603.29231](https://arxiv.org/abs/2603.29231)); agent drift ([2601.04170](https://arxiv.org/abs/2601.04170)) | Cap an episode at N steps, **compact** (summarize best configs + lessons), re-init a fresh window — reset *before* coherence collapse |

**Components added on the literature's advice (not in the original four):**

- **R1 (verbal reflection) promoted to first-class.** The survey is emphatic:
  Reflexion-style verbal feedback is *the* training-free substitute for the RL
  credit assignment AutoLLMResearch buys with GRPO. If a 4B can't
  reflect-then-improve, no other scaffold saves it — so it is the highest-value
  lever and is tested first / alone.
- **Self-consistency** ([2203.11171](https://arxiv.org/abs/2203.11171)) as an
  optional knob: sample k candidate next-configs, pick by agreement — cheap
  variance reduction for a noisy 4B. Held as a stretch arm.

**Honest support grading** (from the survey): R1, R2, R4 are **well-cited**;
R3 (playbook) is a **composite/synthesis**, not a single paper; R5 is
**weakest-cited head-on** — justify it *as compaction* (which is well-supported)
rather than as "bounded episodes." The degradation cluster (2603.29231,
2605.02572, 2601.04170) is search-verified (titles/abstracts), not deep-read —
verify against PDFs before leaning on them in a writeup.

## Design space to review together (DO NOT IMPLEMENT YET)

_Tyler's framing: be super clear about everything we *could* test before
committing to a first rich harness. This is the menu; decisions are made
together after the inv-001 reasoning sweep lands. Each dimension is a knob,
and many are orthogonal (combinatorial — we will not test all)._

- **Reflection locus** — who writes the per-step reflection: (a) the agent
  itself, inline in its own turn (cheap, but a weak model reflecting on its own
  context); (b) a *separate fresh agent* that reads the trajectory and writes
  the reflection back (clean window, possibly stronger/other model); (c) a
  curated/templated reflection the harness fills in. [Reflexion 2303.11366]
- **Results tracking** — the externalized config→loss→note table (R2): raw vs
  curated; who maintains it (the agent, a meta-agent, or harness code).
- **Handoff cadence** — `num_iterations` before compaction/handoff to a fresh
  agent (R5/R2): every N steps, or triggered (plateau / meltdown signal).
- **Research-principle scaffolding** — give the agent a list of good-research
  principles (vary one axis at a time, probe extremes first, don't stop while
  improving…) and have it **name which principle it's applying each step**.
  That self-tag is itself context that could be (i) agent-generated, (ii)
  meta-agent-assigned, or (iii) human-curated — and becomes a measurable trace.
- **Reflection/curation owner** generalizes the above: for each piece of
  injected context (reflection, results table, principle-tag), decide
  self-generated vs meta-agent vs curated — a cross-cutting axis.
- **Reasoning level** (from inv 001 sweep) — off/low/medium as a knob that
  interacts with all of the above.

## Methods (draft — ablation design)

_Drafted for review; the human owns the final call on arms + metrics._

- **Same protagonist + substrate as inv 001**: nemotron-3-nano:4b, StepLaw
  Env A (and B/C for generalization), `BUDGET=50`, single-conversation Pi
  harness, regret + outcome (finished/stalled/ceiling) metrics, ≥20 seeds/cell
  to match inv 001's variance characterization.
- **Arms** (add one component at a time onto the inv-001 minimal baseline):
  `minimal` → `+R1` → `+R1+R2` → `+R1+R2+R3` → `+R1..R4` → `+R1..R5` (full).
  Plus single-component arms (`minimal+R4` alone) to separate the stall fix
  from the search fix.
- **Headline metric**: fraction of the nemotron→gemini regret gap closed, and
  the stall-rate reduction, per arm.
- **Controls**: run the *full* rich harness on **gemini** too — to test the
  interaction prediction that the same scaffolding helps the 4B but is neutral
  or harmful to the stronger model (the Anthropic finding).
- **Cost discipline**: nemotron local/free; gemini control arms metered (inv
  001 showed ~$0.02–0.03/run, with a guard against the off-grid loop bug).

## Decisions

_Populate as work proceeds._

## Results

_To be populated._

## Forward-looking

_To be populated — the winning harness graduates to inv 003 (real-W2S desktop
transfer)._

## Things to flag

- **R3 and R5 are the soft spots.** The playbook risks Anthropic's
  "rigid-script underperforms" failure — keep it revisable. Bounded-episodes
  is the least literature-supported of the five; if it doesn't earn its place
  in the ablation, cut it.
- The **interaction control** (full harness on gemini) is the load-bearing
  test of the whole study's thesis — don't skip it.
- AutoLLMResearch is the *trained* ceiling for this exact task; if we can get
  their environment or numbers, "harness vs training" becomes a direct,
  quantitative comparison rather than a qualitative one.
- Reflexion/playbook add tokens every step → on a 4B's context this competes
  with R2/R5 (compaction). Watch the context budget; the components interact.

## References

- Reflexion — Shinn et al. 2023 — [2303.11366](https://arxiv.org/abs/2303.11366)
- Generative Agents — Park et al. 2023 — [2304.03442](https://arxiv.org/abs/2304.03442)
- MemGPT — Packer et al. 2023 — [2310.08560](https://arxiv.org/abs/2310.08560)
- Plan-and-Solve — Wang et al. 2023 — [2305.04091](https://arxiv.org/abs/2305.04091)
- Tree-of-Thoughts — Yao et al. 2023 — [2305.10601](https://arxiv.org/abs/2305.10601)
- Self-Consistency — Wang et al. 2022 — [2203.11171](https://arxiv.org/abs/2203.11171)
- ReAct — Yao et al. 2022 — [2210.03629](https://arxiv.org/abs/2210.03629)
- MAST (why multi-agent systems fail) — [2503.13657](https://arxiv.org/abs/2503.13657)
- AutoLLMResearch — [2605.11518](https://arxiv.org/abs/2605.11518)
- Anthropic, *Effective Context Engineering for AI Agents* (2025-09-29)
- Anthropic, *Automated Weak-to-Strong Researcher* (alignment.anthropic.com, 2026)
- Long-horizon degradation (search-verified, verify before citing): meltdown
  [2603.29231](https://arxiv.org/abs/2603.29231), self-conditioning
  [2605.02572](https://arxiv.org/abs/2605.02572), agent drift
  [2601.04170](https://arxiv.org/abs/2601.04170)
