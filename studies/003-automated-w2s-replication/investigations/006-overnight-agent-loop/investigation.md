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

### Run 1 — 2026-05-31 22:25 → 2026-06-01 07:45 (SIGKILL)

**Setup:** math dataset, seed 42, nemotron-3-nano:4b researcher on Mac
M2 via Tailscale, vanilla_w2s SFT + vLLM eval on desktop 3080.
Defaults from the patch: train 500 / test 200 / 2 epochs (agent
allowed to vary).

**Iterations completed: 11 sessions** (renumbered iteration_00–10 in
inv 006's `logs/handoff_math_seed42/.agent_handoff/` after migrating
out of upstream's default workspace — see "Things to flag" finding 1).

**Valid PGR measurements: 3**

| Iter | exit | elapsed | predictions | transfer_acc | PGR    | notes |
|------|------|---------|-------------|--------------|--------|-------|
| 02   | —    | —       | 116/200     | 0.5800       | **0.2422** | first medium-scale success |
| 03   | 1    | 11.33s  | 123/200     | **0.6150**   | **0.4350** | best of the night |
| 08   | 1    | 9.2s    | 160/300     | 0.5333       | -0.0148 | regression (training step failed) |

Reference baselines (from orchestrator's fixed cache, same every
iteration): `fixed_weak_acc = 0.5360`, `fixed_strong_acc = 0.7176`.

**Best PGR: 0.435 at iteration 03.** On N=200 with SE ≈ 19pp on PGR,
this is a single observation in a noisy distribution — not a
calibrated measurement. But the central estimate sits in the
ballpark of Burns 2023 / AAR baselines, and demonstrates a 4B local
researcher can reach that ballpark in a single iteration on this
substrate.

**The 5-hour stall (iteration 18, retrying after a Bash timeout):**
At 03:20 UTC the agent emitted a second Bash tool_call after
acknowledging the first had timed out at the agent's self-imposed
180s limit. The second call produced no result for the remaining
~5 hours. No `bash_0016.log` was ever created on the desktop. The
agent loop hung between emitting the tool_use block and receiving
back a tool_result. Logged as "Things to flag" finding 2.

**Migrated state:** all 11 iteration yamls live at
`results/iteration_yamls/` for archival + downstream analysis.

## Forward-looking

- Patched `run_smoke.py` to pass `workspace=` to
  `AutonomousAgentLoop` so future runs write to inv 006's persistent
  dir natively (no migration needed).
- Run 2 (a few hours, post-fix): re-fire and verify the persistent
  dir is now populated by the loop itself. Confirms the fix
  end-to-end.
- Investigate the 5-hour stall. Was it the shim's `_run_turn`
  waiting on an inflight tool_use that never closed? Or the queue
  pattern that bit us in inv 005 sprint 1? Add a per-iteration
  liveness check.
- Multi-seed validation for the iteration_03 config (best PGR
  candidate): re-run train 500 / test 200 / 2 epochs across seeds
  42–46, no agent in the loop, to get a confidence interval on PGR
  for that hyperparameter setting. Compare central estimate to
  Burns table.
- A longer cleaner run (24h) after the stall is understood, ideally
  with structured per-iteration logging (iterations.csv: timestamp,
  config, exit, PGR) so analysis isn't a yaml grep.

## Things to flag

> **Finding 1 — workspace plumbing missed `AutonomousAgentLoop`'s
> `workspace=` arg** (2026-06-01)
> Run 1's `.agent_handoff/` landed in upstream's default workspace
> instead of inv 006's persistent dir. Root cause: `run_smoke.py`
> built the agent loop without passing `workspace=`, so it fell
> back to upstream's `WORKSPACE_DIR` constant. The persistent dir
> we wired in `run_overnight.sh` was unused by the agent (though
> still used for bash_subprocess_logs, vram_samples.csv, etc.).
> Symptom: 11 iteration yamls written to wrong location +
> `HANDOFF_RESUME` picked up 7 stale inv 005 smoke iterations as
> "prior" so session_count started at 7. Fix: `workspace=workspace`
> added to the `AutonomousAgentLoop(...)` call. Tested locally;
> next run will validate.

> **Finding 2 — 5-hour stall after a self-imposed Bash timeout** (2026-06-01)
> At session 018, after the agent's `timeout=180` Bash call returned
> "timed out" (the SFT job needs ~20 min, agent's bound was too
> short), the agent emitted a retry Bash call with `--batch-size 2`.
> That second tool_use produced no tool_result for the remaining
> ~5 hours. `bash_0016.log` was never created — the Bash tool
> handler never started running it. Hypothesis: the shim's
> `_run_turn` got into a state where the second tool_call didn't
> reach the tool dispatcher, or a queue was stuck. Same family of
> bug as inv 005 sprint 1's findings 8 + 12 (silent contract
> failures around the tool_call ⇄ tool_result hand-off in the
> shim).  Needs a focused repro at the shim layer — not blocking
> Run 2 but a real shim bug.

> **Finding 3 — agent set unrealistically short Bash timeouts** (2026-06-01)
> Sessions 015 + 017 + 018 used `timeout: 180` for full SFT+eval
> jobs that need ~10–20 min. The patch text didn't tell the agent
> what timeouts to use; it picked 180 from somewhere (default? prior
> handoff context?). Each timeout wastes an iteration. The patch
> should explicitly say "use `timeout: 1800` (30 min) for Bash
> calls that run training" for Run 2.

- The agent's prompt patch tells it the medium-scale defaults; nothing
  *enforces* them. Nemotron may try larger configs that take longer
  or OOM. Acceptable as exploration data; OOM iterations should
  recover cleanly (orchestrator returns error, agent moves on).
- Upstream `automated-w2s-research` is currently a sibling clone,
  not a git submodule of this repo. Inv 005 + 006 maintain deltas
  as apply-scripts under `scripts/upstream_w2s_patches/`. The
  parent `study.md` already states the intent to convert to a
  submodule at `studies/003-.../upstream/`. Tracking as inv 006
  follow-up.
- Mac ollama keeps nemotron loaded between sessions
  (`keep_alive` default). Mac power state matters: if Mac sleeps,
  the loop stalls until Mac wakes. Recommend wired-power + caffeinate
  for the overnight window.
- Tailscale flakiness during the night would manifest as the agent
  loop hanging on the next nemotron call. The shim has no resilient
  retry. If the user observes the loop stalled, kill it and resume.

## Limitations

_To be populated._
