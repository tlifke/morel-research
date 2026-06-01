---
id: studies/003-automated-w2s-replication/investigations/006-overnight-agent-loop
title: Overnight agent loop on the split-host substrate
status: in-progress
parents:
  - studies/003-automated-w2s-replication
children: []
related:
  - studies/003-automated-w2s-replication/investigations/005-split-host-researcher
  - studies/003-automated-w2s-replication/investigations/002-vanilla-w2s-replication
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - agentic-loop
  - overnight
  - pgr-trajectory
  - resumable
  - vanilla-w2s
  - math
created: 2026-05-31
updated: 2026-05-31
---

# Investigation 6 — Overnight agent loop on the split-host substrate

## Scope

Run the working inv 005 split-host substrate as an automated researcher
loop for ~12 hours unattended. One seed, math dataset, medium scale
(train 500 / test 200 / 2 epochs default). The question: starting from
the vanilla_w2s baseline, how far does a 4B local researcher
(nemotron-3-nano:4b on Mac) climb in PGR over ~40-50 iterations? What
kinds of variations does it try?

The loop must be **interruptible**: SIGTERM at any time → finishes the
current session boundary cleanly, persists state to handoff yaml,
exits. **Resumable**: re-firing the launcher with the same
`HANDOFF_DIR` picks up at `iteration_{N+1}` from the latest yaml.

## Methods

### Substrate

Identical to inv 005:

- Researcher: nemotron-3-nano:4b on Mac M2, served by Ollama over
  Tailscale at `100.106.241.33:11434`.
- Agent harness: shim_v2 + handoff_writer (see inv 005).
- SFT + vLLM eval on desktop 3080 12 GiB (Unsloth + LoRA).
- Orchestrator on desktop port 8000 (Flask, `evaluate_predictions`
  endpoint with subset support from inv 005 patch).

### Default scale

Agent's default Bash command (overridable per-iteration):

```
python -m w2s_research.ideas.vanilla_w2s.run \
  --data-dir /home/tlifke/Projects/automated-w2s-research/data/math \
  --weak-model Qwen/Qwen1.5-0.5B-Chat \
  --strong-model Qwen/Qwen3-4B-Base \
  --train-size 500 --test-size 200 --epochs 2 --seed 42 \
  --batch-size 4 --load-in-4bit
```

Expected per-iteration cost: ~12–18 min (Bash ~8–12 min, agent
thinking ~3–5 min). Budget 12 hours → ~40–50 iterations.

### Resume + interruption

- **Resume**: launcher reads `$HANDOFF_DIR/iteration_*.yaml`, picks
  highest N, agent loop initialises `session_count = N+1` and seeds
  the prompt from `make_bootstrap_message(latest, N)` instead of the
  patch text.
- **Interruption**: agent loop registers SIGTERM handler. On signal,
  set `_should_stop_after_session = True`. The session-loop checks
  the flag after `_maybe_handoff` runs and exits cleanly. SIGTERM
  mid-Bash kills the SFT subprocess and *loses that iteration's
  work* — but durable state from prior iterations is intact.

### Comparison baseline

The orchestrator's cached `fixed_weak_acc` and `fixed_strong_acc`
(from inv 005: 0.5360 and 0.7176 for math) define the PGR denominator
on every iteration. Agent's PGR per iteration is directly comparable.

5-seed validation of the *best* idea(s) the agent finds is queued as a
post-overnight follow-up (not part of this 12-hour run).

## Decisions

> **Decision 1 — single seed during exploration, multi-seed validation at the end** (2026-05-31)
> Running each idea on 5 seeds inside the loop makes iterations 5×
> slower for no exploration benefit. Better: 1 seed (42) during the
> 12-hour exploration, then re-run top 3–5 candidates across 5 seeds
> in a follow-on for a clean PGR confidence interval. The agent
> sees fixed_weak_acc / fixed_strong_acc per iteration regardless.

> **Decision 2 — medium scale defaults** (2026-05-31)
> train 500 / test 200 / 2 epochs. Smoke (64/64/1) under-samples to
> the point that PGR is dominated by noise (±34 absolute PGR points
> at N=64). Paper-faithful (5K+/1315/3+) takes 35–50 min per
> iteration → only 14–20 iterations in 12 hours. Medium gives
> ~40–50 iterations with each PGR carrying meaningful signal
> (test_size=200 → SE on transfer_acc ≈ 3.5pp).

> **Decision 3 — resume via handoff dir, not checkpoint file** (2026-05-31)
> The handoff yaml is already the source of truth for inter-iteration
> state. Adding a second checkpoint file would duplicate that with
> drift risk. Resume = pick the highest iteration_NN.yaml + bootstrap
> from it.

## Results

_To be populated as the run progresses._

## Forward-looking

_To be populated after the run completes._

## Things to flag

- The agent's prompt patch tells it the medium-scale defaults; nothing
  *enforces* them. Nemotron may try larger configs that take longer
  or OOM. Acceptable as exploration data; OOM iterations should
  recover cleanly (orchestrator returns error, agent moves on).
- Mac ollama keeps nemotron loaded between sessions
  (`keep_alive` default). Mac power state matters: if Mac sleeps,
  the loop stalls until Mac wakes. Recommend wired-power + caffeinate
  for the overnight window.
- Tailscale flakiness during the night would manifest as the agent
  loop hanging on the next nemotron call. The shim has no resilient
  retry. If the user observes the loop stalled, kill it and resume.

## Limitations

_To be populated._
