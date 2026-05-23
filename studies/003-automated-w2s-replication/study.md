---
id: studies/003-automated-w2s-replication
title: Automated weak-to-strong researcher replication
status: planned
parents: []
children:
  - studies/003-automated-w2s-replication/investigations/001-hardware-derisk
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

## Question

_Placeholder — fill in. Working draft from the scaffold conversation:_
_Can the Anthropic Automated Weak-to-Strong Researcher (alignment.anthropic.com,_
_2026) be replicated on consumer hardware (3080 12GB) using a local 4B-class_
_model in the researcher role instead of Claude Opus 4.6? If so, what does the_
_capability floor look like — does a weak-to-weak loop bootstrap at all, and_
_what harness affordances move PGR?_

## Why this study

_To be populated by the human._

Working notes from the scaffold conversation (replace or refine):

- The W2S substrate (Qwen 0.5B teacher → Qwen 4B student, PGR metric)
  is paper-validated and 4B-feasible.
- The local Flask eval API removes the only external-cost vector that
  isn't the Claude researcher itself.
- Substituting Gemma 4B (or Qwen 4B) as the researcher converts the
  paper's setup into a weak-to-weak experiment with a sharp judgeable
  target (PGR vs. published `vanilla_w2s` baseline ≈ 0.23 human / 0.97
  Opus AAR).
- This is the kind of "replication of a published finding" that
  [[study-002]]'s research-methodology focus called for: binary
  judgeable, methodology-focused, external-research-conversation
  relevant.

## Investigations

- `001-hardware-derisk` — Confirm 3080 12GB can run Qwen3-4B-Base
  LoRA fine-tuning via Unsloth at usable wall-clock speed. Verify
  Unsloth + vLLM + Transformers stack installs cleanly under `uv`.
  Measure VRAM ceiling, per-step time, full-epoch time. Identify
  whether researcher-inference (Gemma 4B) + training (Qwen 4B) can
  co-resident or must be sequential. **Planned (next up).**
- `002-vanilla-w2s-mechanical-replication` — Run `vanilla_w2s` on the
  three datasets (chat, math, code) with the seeds the paper uses;
  compare resulting PGR to the cached baselines shipped in
  `cache_results.tar.gz`. No agent involved; pure ML pipeline.
  Output: a writeup of mechanical replication, with deltas and
  hypotheses for any divergences. **Planned.**
- `003-claude-sdk-shim-and-researcher-swap` — Replace the Claude
  Agent SDK researcher in `w2s_research/research_loop/agent.py` with
  a local-model researcher (Gemma 3 4B or Qwen 4B Instruct). Two
  candidate paths: (a) thin shim mimicking the SDK's tool-call
  interface, (b) honest rewrite of the agent loop around what the
  local model can actually do. Output: a working weak-to-weak loop
  that produces PGR scores on the same substrate. **Planned.**

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

- **Harness-as-research-artifact.** If the weak-to-weak loop produces
  meaningfully nonzero PGR, the harness becomes a contribution in its
  own right. What's the minimum researcher capability needed to
  bootstrap? Which affordances (tool selection, retry, planning,
  result interpretation) are load-bearing and which aren't?
- **Idea-space comparison.** Opus's nine parallel AARs converged on
  what set of approaches? A weak researcher exploring the same space
  is a candidate dataset for "research-taste at scale" questions.
- **Cross-substrate transfer.** If a working weak-to-weak loop exists,
  do the harness components generalize off the W2S task? This is
  where the study could connect back to [[study-002]]'s principle
  framework.

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
