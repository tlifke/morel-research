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

### Phase 1 — C1×C4 factorial (2026-06-08)

nemotron-4b · Env A · reasoning=low · 20 seeds/arm · 120 runs · figure
`assets/fig_phase1.png`, data `data/phase1_runs.csv`.

| arm | finished | finish_kind | regret med / mean / max | reach-opt | sec |
|---|---|---|---|---|---|
| A0 minimal | 11/20 | clean 11 | 0.0016 / 0.0060 / 0.038 | 2 | 31 |
| A1 +C4 | **20/20** | nudged 10, clean 9, forced 1 | 0.0016 / 0.0074 / 0.026 | 3 | 34 |
| A2 +C1self | 11/20 | clean 11 | 0.0021 / 0.0059 / 0.042 | 2 | 33 |
| A3 +C1self+C4 | **20/20** | clean 10, nudged 8, forced 2 | 0.0016 / 0.0038 / 0.016 | 1 | 34 |
| A4 +C1fresh | 8/20 | clean 8 | 0.0016 / 0.0034 / **0.014** | **5** | 88 |
| A5 +C1fresh+C4 | **20/20** | nudged 8, clean 9, forced 3 | **0.0002** / **0.0036** / 0.019 | **5** | 78 |

**Main effects.**
- **C4 (actuation) is a clean, decisive win on finishing:** stall rate
  ~45–60% → **0%** across *all* C1 levels (finished-rate Δ ≈ +50%). The rescue
  is real: ~8–10/20 finished only after the re-prompt (`nudged`), 1–3 needed the
  harness force-submit (`forced`). As predicted, C4 does **not** change the
  median regret of runs that already finished — it fixes *finishing*, not search.
- **C1 (reflection) doesn't move the saturated median but tightens the tail,
  and fresh > self:** worst-case regret falls from `off` ~0.026–0.038 to `fresh`
  ~0.014–0.019; mean from ~0.006–0.007 (`off`) → ~0.0035 (`fresh`). Fresh
  reflection also reaches the **exact optimum 5/20** (vs 2–3 elsewhere) — its
  "explore both axes / unexplored regions" advice works.
- **Interaction:** the C4 nudge ("run another experiment OR finish") extracts ~1
  extra experiment on average (A3 13.7 vs A2 12.7 exp), so C4 *slightly* helps
  regret in combination, not just finishing. Self-reflection is noisy **alone**
  (A2) but clean **with C4** (A3).
- **Cost:** fresh reflection ≈ 2.3× wall-clock (78–88s vs 31–34s) — the
  per-step advisor call.

**Best harness:** **A5 (fresh + C4)** — 100% finished, lowest mean regret,
most optimum-reaches — for quality; **A3 (self + C4)** is ~as good on the tail
at **half the time** (no advisor calls), the quality/cost pick.

### Why it fails — converged/close/far deep-dive (2026-06-08)

Subagent read A3/A5 traces across tiers (converged / close / far). Root cause
is **specific and nameable**, not generic weakness:

- **The model does not reason about the lr×bs *interaction*.** It treats the two
  as independently optimizable, **freezes one axis early (almost always batch
  size)** — often off a misleading low-lr slice — and sweeps the other. The
  optimum needs the *joint* high-lr + large-bs setting, so freezing bs small
  caps regret at ~0.016. Worse, the bs=128 lr-sweep has a **clean, confident,
  wrong minimum** (at low lr=1.38e-3, loss 2.358), so the agent gets an
  internally-consistent "answer" it has no reason to doubt.
- **Success discriminator = did it reach bs ≥ 736 paired with high lr.** Effort
  doesn't separate tiers — far misses (s11 12-exp, s16 13-exp) used *more*
  budget than converged runs (s8 6-exp). It's *which* corner, not how hard.
- **Failure is COVERAGE, not perception or stamina.** The shallow-basin worry
  didn't materialize — when agents reach the basin they correctly stop on a
  near-best cell (no found-it-then-walked-away cases). Extra budget wouldn't
  help the misses; they'd keep sweeping lr at bs=128. (One exception: A5 s19, a
  genuine stamina+bad-steering give-up at n=5.)
- **The A5 fresh advisor is net-unreliable.** When it names the high-lr/high-bs
  corner it's golden (s8 → exact optimum). But it's the *same 4B*, and in both
  A5 far misses it produced sustained **low-lr advice in the wrong direction**
  (s18, s19), plus off-grid values (1.5e-2, 2.2e-2) and truncated lines
  ("Try lr≈8.0e-"). As likely to cause a far miss as a convergence. A3's
  *self*-reflection produced the single cleanest run (s13's deliberate bs-sweep)
  with no advisor.

### All-six-arms behavioral comparison (2026-06-08) — corrects the A3>A5 read

Second subagent analyzed A0/A1/A2/A4 against the axis-freezing hypothesis. The
result **overturns the prior turn's "A3 self+C4 is the better base, drop the
advisor" conclusion.** Which intervention touches the *root cause* (axis-freezing)
vs merely cleans up finishing:

- **C4 / actuation (A1): finishing only, zero effect on search.** A1's far misses
  are identical low-lr bs-freezes to A0's; the wrapper fires once, at the stop
  step (A1 s5 wrote a prose "Finish." with a *hallucinated* loss 1.945, got
  re-prompted, then called finish). Necessary for clean measurement, not a cure.
- **C1self / inline reflection (A2): does NOT structurally unfreeze.** It makes
  the agent more *methodical inside* whatever region it anchored — A2 s18 spent
  20 experiments crawling lr 2.4e-4→9.8e-4, reflecting "128 best" the whole way.
  Changes flavor, not the freeze.
- **C1fresh / fresh advisor (A4): the ONLY lever that actually breaks
  axis-freezing.** By injecting new (lr,bs) *pairs* each step it mechanically
  prevents single-axis sweeps → highest joint 2-axis movement, lowest freezing
  of all six arms. **But** it trades freezing for (a) direction-unreliability
  (off-grid "bs=7", dead-zone low-lr pushes) and (b) **non-termination** — A4
  converged runs (s4, s16) *reached the optimum then walked away* because the
  advisor kept proposing corners; they ended `stalled`.

**Reframe:** A4 is **less problematic than its regret suggests** — its *search*
is the best of the set; its deficit is termination/selection, exactly what C4
fixes. A2 **looked better than it is** — clean joint narration on wins, but its
misses are pure unbroken freezes. So the implied combination is **C1fresh + C4
(= A5)**: the advisor breaks the freeze, C4 stops the advisor-induced wandering
and commits. **Neither alone suffices** — C4-alone fixes nothing about search;
fresh-alone finds the corner but won't commit. My prior-turn "drop the advisor"
was wrong: self-reflection cannot break the freeze; only the fresh observer can.

**Corrected highest-leverage path (→ Phase 2):** keep **C1fresh + C4**, but fix
the advisor's *reliability* (its only real flaw): (i) **on-grid validation** —
snap/reject its suggestions to real grid points before injection; (ii) **reframe
it as a general anti-freezing monitor** — "you've held one axis fixed for N
steps; vary it / check whether your best lr changes at other batch sizes" —
rather than naming specific configs/corners (which leaks env-specific answers and
is the source of its bad low-lr pushes). C4 already handles the termination flaw.
This keeps the *generalizable* mechanism (detect freezing, prompt joint coverage,
no assumption about where the optimum is) and removes the env-specific noise.

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
