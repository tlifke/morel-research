---
id: studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor
title: Qwen researcher floor — machinery, prompt induction, harness shape
status: planned
parents:
  - studies/003-automated-w2s-replication
children: []
related:
  - studies/003-automated-w2s-replication/investigations/003-claude-sdk-shim-and-researcher-swap
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - harness-design
  - tool-calling
  - qwen
  - weak-researcher
  - capability-floor
created: 2026-05-25
updated: 2026-05-25
---

# Investigation 4 — Qwen researcher floor

## Scope

Investigation 003 closed the harness gaps and produced a single gate-5
PASS (qwen3.5:4b + `tool_invocation_hint`) — but the longer-smoke run
showed the loop closes mechanically while never completing a single
end-to-end vanilla_w2s training iteration. This investigation answers
the next question the matrix surfaced:

**What does it take to get a 4B-class Qwen researcher to perform one
complete training-and-evaluation iteration on the vanilla_w2s substrate,
and is the remaining gap machinery, model behavior, or harness shape?**

Three sub-parts, sequenced. The sequencing matters — machinery before
prompt induction is a precondition for the prompt work being
interpretable; QwenCode reading runs in parallel because it's research,
not implementation, and informs the conditional 4d decision.

### 4a — Machinery

The longer-smoke agent in 003 constructed the correct training command
on the first try (`python -m w2s_research.ideas.vanilla_w2s.run
--train-size 64 ...`) but the command failed because workspace cwd was
outside the upstream `.venv`. Fix the harness so the agent's `Bash` tool
runs in an environment where the constructed command actually executes.

Concretely: workspace cwd, PATH plumbing (or `uv run` wrapper), env vars
the upstream agent expects (`ORCHESTRATOR_API_URL`, etc.). One end-to-end
training+eval iteration must complete from a clean workspace before 4b
starts.

Sharp success criterion: a single `Bash` invocation of the constructed
training command produces a model checkpoint and `evaluate_predictions`
accepts the resulting integer-list submission against the real target
idea.

### 4b — Prompt induction (gated on 4a)

Even with machinery fixed, the longer smoke showed the agent emits 40
hallucinated `share_finding` calls, drifts onto invented tool names
(`terminal`, `get_file`), and submits free-text prose to
`evaluate_predictions` instead of an integer list. These are model
behaviors the patch text in 003 did not address.

Iterate prompt patches targeting these failure classes. Each patch
plumbed through `ClaudeAgentOptions` so it can be stripped for the
unpatched control. Treat each patch as an experimental condition with
its own gate-5-style smoke before composing with the next.

**Stopping criterion** (required — this is the tar-pit prevention):
iterate until the agent completes one end-to-end iteration with a
valid `evaluate_predictions` submission against the real target idea,
OR until 5 distinct patches have been tried without progress on that
specific gate. Either outcome is the result. "Ineffective researcher
that mechanically completes one iteration" is a publishable finding;
so is "no prompt patch in 5 attempts gets a 4B-class Qwen to a valid
submission."

### 4c — QwenCode wrapping read

In parallel with 4a (web reading; no GPU or implementation). The cell
4 and 5 results from 003 pressure-test an assumption baked into our
shim: that the Claude Agent SDK protocol shape is a neutral substrate
that any model can be coerced into. Two readings of that data are
live:

- **Reading A:** Qwen with enough prompting can be coerced into the
  Claude-shaped protocol. Our job is to find the right coercion. (4b
  pursues this.)
- **Reading B:** The Claude-shaped protocol isn't neutral; forcing
  Qwen through it depresses its measured capability. The right
  comparison would wrap Qwen in its native idiom.

Half a day of reading QwenCode's open-source wrapping (and Qwen's own
tool-call documentation) is the cheapest way to know whether Reading B
is worth taking seriously. Output: short writeup contrasting QwenCode's
LLM-wrapping shape against our shim's, with a recommendation on whether
4d should exist.

### 4d — Qwen-native harness spike (conditional)

If 4b's stopping criterion fires with no progress AND 4c's read
suggests Qwen's native tool-call idiom is structurally different from
the Claude SDK's, spike a small Qwen-native wrapper and re-run gate 5.
If 4b succeeds, 4d collapses to a paragraph in the writeup
acknowledging the harness-shape question without spending GPU on it.

This is a decision point, not work to schedule up front.

## Methods

_To be populated as 4a starts. Will track per-sub-part: changes
landed, smoke logs, success-criterion status._

## Decisions

_Populate as work proceeds. Format:_

> **Decision N — short title** (date)
> What was chosen, alternatives considered, why this won.

## Results

_To be populated. One section per sub-part. Each section ends with
"verdict" against its sharp criterion._

## Forward-looking

If 4a and 4b both succeed with a 4B-class Qwen reaching one valid
end-to-end iteration, investigation 005 measures the 24-hour run with
the anchored baselines (vanilla_w2s, Opus 4.6, human, student-start).
That investigation is single-agent at 24h; multi-agent / longer-budget
runs are gated on that single-agent run showing nonzero PGR movement.

If 4d ends up needed, the resulting Qwen-native harness becomes a
fork of the shim — to be decided whether it lives alongside the
Claude-shaped shim (two harnesses, model-typed) or replaces it.

## Things to flag

- The 49-min longer-smoke result from 003 is the load-bearing data
  for this investigation's framing. If on closer inspection the
  agent's command was wrong rather than the environment, 4a's premise
  collapses and we restart from "what is the agent actually trying
  to do."
- `tool_invocation_hint` is currently a single string. As 4b composes
  multiple patches it may need to become a list-of-named-patches so
  stripping is per-condition. Surfacing this as expected refactor,
  not a scope change.

## Limitations

- 4B-class only. If nothing in 4a+4b+4d gets a Qwen to a valid
  submission, the right next move may be to test 8B/14B Qwen, but
  that's investigation 005+ territory and out of scope here.
- Single-agent only. Multi-agent dynamics are deferred to inv 005.
- Smoke-sized configs throughout (`train_size=64`, `epochs=1`). Real
  PGR measurement belongs to inv 005.
