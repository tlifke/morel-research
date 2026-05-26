---
id: studies/003-automated-w2s-replication
title: Automated weak-to-strong researcher replication
status: planned
parents: []
children:
  - studies/003-automated-w2s-replication/investigations/001-hardware-derisk
  - studies/003-automated-w2s-replication/investigations/002-vanilla-w2s-replication
  - studies/003-automated-w2s-replication/investigations/003-claude-sdk-shim-and-researcher-swap
  - studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor
related:
  - studies/002-principle-bootstrapped-difficulty
tags:
  - automated-research
  - weak-to-strong
  - replication
  - harness-design
  - lora-finetuning
axes:
  llm_capability: medium
  human_capability: medium
created: 2026-05-23
updated: 2026-05-23
---

# Study 3 — Automated weak-to-strong researcher replication

## Background — what the paper actually does

[Anthropic's Automated Weak-to-Strong Researcher](https://alignment.anthropic.com/2026/automated-w2s-researcher/)
is a **two-layer system**:

1. **Substrate (ML pipeline).** Qwen 1.5-0.5B-Chat as the "weak teacher"
   produces pseudo-labels on an unlabeled set. Qwen 3-4B-Base as the
   "strong student" is LoRA-fine-tuned on those pseudo-labels. The
   metric is Performance Gap Recovery (PGR) — how much of the gap
   between the weak teacher's accuracy and the strong student's
   ground-truth-trained ceiling does the pseudo-label-trained student
   recover. Tasks: chat preference, math verification, code
   verification. This whole layer runs on a single GPU per training
   run.
2. **Researcher loop (agentic).** A swarm of nine **Claude Opus 4.6
   agents** propose ideas for improving PGR, write Python implementing
   each idea (variations on the substrate's training/labeling
   pipeline), run experiments via the eval API, and share findings
   through a forum. The headline claim: agents reach PGR 0.97 in 5
   days, versus 0.23 from human researchers after 7 days, at a cost
   of ~$18,000 in Anthropic API spend.

The expensive part is **Layer 2** (Claude API tokens for the agentic
loop). Layer 1 is cheap — just GPU-hours on commodity hardware,
which the paper bought from RunPod but we have at home.

## What this study replaces

The **teacher/student weak-to-strong relationship is unchanged**:
Qwen 1.5-0.5B-Chat stays as the weak teacher and Qwen 3-4B-Base
stays as the strong student in every investigation. That's the
ML problem the paper defined and we keep it intact.

The **researcher role** is what we're varying. We are running
**Layer 1 only** for now (no researcher loop). In later investigations
we substitute a **local 4B model** (Gemma 3 4B or Qwen 3 4B Instruct)
in the researcher role where the paper used Claude Opus 4.6. The
question is whether 4B-scale agents — possibly running in parallel
like the paper's 9 Opus agents — can iteratively push PGR up from
the `vanilla_w2s` floor (~0.3-0.4) toward the Opus-achieved ceiling
(~0.97). No Anthropic API calls happen at any point in this study —
that is the whole reason it is feasible to run.

## Question

_Placeholder — fill in._ Working draft: can the substrate be
replicated faithfully on a 3080 12GB? Can a local 4B model in the
researcher role drive the loop at all — i.e., what is the capability
floor for the agent, separate from the capability floor for the
underlying ML task? What harness affordances move that floor?

## Why this study

_To be populated by the human._

Working notes from the scaffold conversation (replace or refine):

- The substrate (Qwen 0.5B teacher → Qwen 4B student, PGR metric) is
  paper-validated and 4B-feasible on consumer hardware. Confirmed in
  [[003-001]].
- The Flask eval API runs locally — no external dependency for
  scoring.
- The researcher loop is where the paper's $18k spend went. Replacing
  Claude Opus 4.6 with a local 4B model converts the paper's setup
  into a weak-researcher experiment that costs $0 in API spend. The
  research question is then about the *capability floor for the
  researcher*, with PGR as the sharp judgeable target.
- This is the "replication of a published finding" north star
  [[study-002]] surfaced: binary judgeable, methodology-focused,
  external-research-conversation relevant.

## Investigations

- `001-hardware-derisk` — Confirm 3080 12GB can run Qwen3-4B-Base
  LoRA fine-tuning via Unsloth at usable wall-clock speed. Verify
  Unsloth + vLLM + Transformers stack installs cleanly under `uv`.
  Measure VRAM ceiling, per-step time, full-epoch time. Identify
  whether researcher-inference (Gemma 4B) + training (Qwen 4B) can
  co-resident or must be sequential. **Planned (next up).**
- `002-vanilla-w2s-replication` — Run the **substrate** (`vanilla_w2s`
  baseline) on the three datasets with the seeds the paper uses;
  compare resulting PGR to the cached baselines shipped in
  `cache_results.tar.gz`. **No Layer 2 / researcher loop / Claude API
  here** — this is the pure ML pipeline that an automated researcher
  would normally drive. Output: a writeup of mechanical replication,
  with deltas and hypotheses for any divergences. **In progress.**
- `003-claude-sdk-shim-and-researcher-swap` — **First** investigation
  in which the Layer 2 agentic loop runs at all. Replaces upstream's
  Claude Agent SDK researcher in `w2s_research/research_loop/agent.py`
  with a local-model researcher (Gemma 3 4B or Qwen 4B Instruct) so
  the loop runs against a local LLM rather than calling Anthropic's
  API. Two candidate paths: (a) thin shim mimicking the SDK's
  tool-call interface, (b) honest rewrite of the agent loop around
  what the local model can actually do. Output: a working
  weak-researcher loop that produces PGR scores on the same substrate.
  **Planned.**

After investigation 003 the study reaches a natural decision point:
do we pursue **harness engineering** (what affordances raise PGR
under a weak researcher?) or **idea exploration** (what novel W2S
ideas does a weak researcher generate, and how do they compare to
the paper's idea space?). Captured as an open question below — the
right answer probably emerges only after seeing what investigation
003 produces.

## Repository policy

Default applies, with these specifics:

- W2S training output artifacts (LoRA adapters, training logs, model
  predictions) are gitignored. Re-runnable from `data/` + idea code.
- The `labeled_data.tar.gz` and `cache_results.tar.gz` archives from
  the upstream repo are large; reference them by upstream URL rather
  than checking them in.
- Anything that would be a paper-trail of *which* records the agent
  was tested against (vs. ground truth) stays out of git so the
  isolation property the upstream codebase enforces isn't accidentally
  broken on our side.
- PGR scores per (idea, seed, dataset) check in as `summary.yaml`
  under each investigation.
- If we fork the upstream `safety-research/automated-w2s-research`
  repo, it lives as a submodule at `studies/003-.../upstream/` and
  is referenced by commit hash. Modifications live in our own
  shim/adapter code rather than as patches against upstream.

## Forward-looking

- **Harness-as-research-artifact.** If the weak-researcher loop produces
  meaningfully nonzero PGR, the harness becomes a contribution in its
  own right. What's the minimum researcher capability needed to
  bootstrap? Which affordances (tool selection, retry, planning,
  result interpretation) are load-bearing and which aren't?
- **Idea-space comparison.** Opus's nine parallel AARs converged on
  what set of approaches? A weak researcher exploring the same space
  is a candidate dataset for "research-taste at scale" questions.
- **Cross-substrate transfer.** If a working weak-researcher loop exists,
  do the harness components generalize off the W2S task? This is
  where the study could connect back to [[study-002]]'s principle
  framework.
- **Researcher-capability spectrum.** Inv 004 surfaced that local 4B-class
  Qwen/Nemotron can't drive a complete PGR iteration on a single 12 GB
  GPU — substrate contention is binding. A natural follow-on is to
  hold the W2S student/teacher fixed (Qwen 0.5B / Qwen 4B per the
  paper) and vary the researcher across a capability/cost spectrum:

  - **Local-weak end:** Qwen 3.5 4B / Nemotron 3 Nano 4B (inv 004 —
    bounded by hardware on consumer GPU).
  - **API-cheap middle:** Claude Haiku 4.5, Gemini 3.1 Flash Lite,
    GPT-5 Mini equivalents. Tens-to-low-hundreds of dollars per
    24h run; high signal-to-cost ratio.
  - **API-frontier end:** Claude Opus 4.6 (paper's baseline),
    Gemini 3 Pro, GPT-5. Comparable to the paper's headline.
  - **Larger-but-local middle:** Nemotron 70B, Qwen 3 32B, Gemma 4
    27B — fit on rented A100/H100 spot capacity ($0.50-2/hr); good
    for ablations the API tier can't cheaply support.

  The reframed research question becomes: **how much of the
  Opus-4.6 PGR can each tier recover, and what's the cost
  curve?** Implementation note: build hard $-budget gates into
  the runner (max total token spend, max wall-clock per
  researcher), and treat the budget itself as a research
  parameter — different tiers will hit different walls.
- **Substrate-aware decoupling.** Inv 004 also surfaced that the
  paper's setup conflates two roles on one GPU. Splitting researcher
  and student-training across hosts (Tailscale-attached MacBook,
  cloud researcher, time-multiplexed local) is its own design space
  worth comparing.

### Operational note on Anthropic-API researcher runs

API-tier researcher cells (Haiku 4.5, etc.) are **deferred until
2026-06-15** when Anthropic Pro/Max subscriptions start including
Agent SDK API credits ($20/$100/$200 monthly on Pro/Max5x/Max20x).
That's a ~3-week wait; local-hardware work (inv 004, inv 005's
local-weak cell) continues in the meantime. Full ToS read at
[`anthropic-tos-haiku-researcher.md`](anthropic-tos-haiku-researcher.md);
verdict was yellow on one AUP clause ("utilization of inputs and
outputs to train an AI model … without prior authorization"). Plan
is to send Anthropic T&S a clarifying inquiry about whether
orchestrator-only use (Claude writes code; Qwen teacher labels;
Qwen student trains) requires authorization beyond standard ToS
acceptance, well before the credits launch so the answer is in
hand when we want to run.

## Open questions

- After mechanical replication, do we pursue **harness engineering**
  (PGR-as-yardstick for harness design) or **idea exploration**
  (PGR-as-yardstick for the agent's research taste)? Both are real
  studies on top of the same substrate. The first is more aligned
  with the MDP/action-space framing; the second is more aligned with
  a "what does a 4B researcher actually come up with" line of work.
  Decision deferred until after investigation 003.
- Is researcher-inference + student-training co-resident on 12GB, or
  must they be sequential? Determined in investigation 001. Affects
  the realistic loop wall-clock time and therefore the experiment
  budget for investigations 003+.
- If the upstream eval server expects features (e.g., MCP-style tool
  invocation patterns) that Gemma 4B can't reliably produce, do we
  patch the server to be more permissive or simplify the agent
  interface? Investigation 003 surfaces this; decision belongs to the
  human.
