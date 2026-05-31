# Handoff-artifact design (proposed)

Scratch design for the context-reset / handoff-artifact pattern that
inv 005 will try after the reference-returning Bash tool is verified.
Based on Anthropic's harness-design-long-running-apps essay
([link](https://www.anthropic.com/engineering/harness-design-long-running-apps)),
specifically the "communication via files" + "context resets with
structured handoffs" patterns.

This is not yet implemented. Document this here so it's reviewable
before we touch the agent loop.

## What problem this solves

Today's `AutonomousAgentLoop`:

- Runs one `ClaudeSDKClient` session.
- Inside the session, each `_run_turn` iteration adds the previous
  assistant message and the previous tool result to `self._history`.
- The full history is sent on every POST.

By iteration N:

- Turn 0 prompt: ~4,300 tokens (system + tools + user kickoff)
- Turn 1: +reference-bash result (~1,500 tokens) → ~5,800
- Turn 2: +next assistant + next bash result → ~7,500
- Turn 5–10: somewhere between 15K-30K tokens depending on what the
  agent does

That's *much* better than 30K+ at turn 1 with raw stdout. But it
still grows linearly with iteration count, and the next
weak-to-strong investigation Tyler has in mind (inv 006+: 24-hour
multi-iteration runs with anchored baselines) will explode that.

## What the handoff pattern looks like

After every completed iteration (one valid `evaluate_predictions`
submission landing on the orchestrator), the agent:

1. **Writes a handoff artifact** to disk (YAML or JSON).
2. **Ends the session.**
3. The outer `AutonomousAgentLoop` **starts a fresh
   `ClaudeSDKClient`** with a clean `_history`.
4. The new session's first user message is a small bootstrap that
   references the prior artifact: "Continuing from iteration N. Prior
   handoff at `<path>`. Read it first, then propose iteration N+1."
5. The new model `Read`s the artifact, has the load-bearing facts,
   and can decide what to try next without any of the prior turn's
   tool-result bloat in context.

Cost stays roughly constant across iterations because the prior
history is replaced by a small handoff reference.

## Artifact schema (proposal)

```yaml
# .agent_handoff/iteration_N.yaml
schema_version: "1"
iteration: 3
timestamp: 2026-06-02T14:33:51Z
parent_iteration_path: .agent_handoff/iteration_2.yaml

idea:
  uid: "vanilla_w2s_v3"
  name: "vanilla_w2s with mid-layer LR scaling"
  source_code:
    path: w2s_research/ideas/autonomous_vanilla_w2s_v3
    commit: 4a8f...  # if applicable
  hypothesis: "Reducing LR on middle layers improves transfer recovery
               by preserving the strong model's pretrained representations
               in the layers that do the heavy reasoning."

attempted_command:
  argv: ["python", "-m", "w2s_research.ideas.vanilla_w2s.run", "..."]
  cwd: /home/tlifke/Projects/automated-w2s-research
  full_log: results/.../bash_0017.stdout

result:
  ran_to_completion: true
  exit_code: 0
  elapsed_sec: 96.4
  metrics:
    transfer_acc: 0.6112
    weak_acc: 0.5536
    strong_acc: 0.7399
    pgr: 0.31
  predictions_file: results/.../eval_output.json
  evaluate_predictions:
    submitted: true
    server_ack:
      correct: 654
      total: 1315
      transfer_acc: 0.497

artifacts:
  sft_log: bash_0016.stdout
  vllm_log: bash_0017.stdout
  lora_adapter: results/.../checkpoint-16/adapter_model.safetensors

learnings:
  - "Mid-layer LR scaling did NOT improve PGR vs vanilla_w2s baseline."
  - "Training was stable; no OOM, no flashinfer issues."
  - "Mid-layer scaling reduced final loss but transfer_acc stayed flat."

next_action_hints:
  - "Try selective unfreezing of attention layers only."
  - "The redis remote-cache warning is benign; ignore it next time."
  - "Don't pass --load-in-4bit if running with researcher on Mac;
     SFT now has full headroom and 4-bit slows it down."

failure_log: []  # populated only when ran_to_completion is false
```

The structure has three jobs:
- **What was tried** (`idea`, `attempted_command`) — recoverable
  reasoning context for the next iteration.
- **What was learned** (`result`, `learnings`) — the facts that
  influence the next idea.
- **What to fix or carry forward** (`next_action_hints`, `failure_log`).

The artifact is small (a few hundred lines max) but load-bearing.

## Bootstrap message shape

The new session's first user message:

```
You are autonomous-research-agent iteration N+1. The previous
iteration's handoff artifact is at:

  .agent_handoff/iteration_N.yaml

Read it first, then decide whether to:
  (a) Iterate on the same idea with a refinement
  (b) Try a new idea informed by the prior result
  (c) Stop because the search has converged

Recent history of all prior iterations is in .agent_handoff/. Read
those you find relevant. Do not assume context from earlier turns.

Begin.
```

That's it. ~120 tokens. The model `Read`s the handoff, gets the load-
bearing state, decides, and emits the next `Bash` call.

## Where this lives in the code

Two pieces:

1. **`AutonomousAgentLoop.run()`** (upstream `agent.py`): currently
   loops sessions but each session shares state in some way. Change
   the loop to:
   - After every session that lands an `evaluate_predictions`
     submission, write the handoff YAML.
   - Then `break` out of the inner-session loop, create a fresh
     `ClaudeSDKClient`, bootstrap with the message above.
2. **Handoff writer**: a small module that
   `(prior_history, tool_calls, server_acks) → YAML`. Extracts
   metrics from `evaluate_predictions` tool calls, finds the most
   recent `Bash` result path, etc. No model in the loop — just code.

The first piece is the real change. The second is straightforward.

## What gets harder

A few honest tradeoffs:

- **Cross-iteration reasoning** ("I noticed across iterations 2-5
  that lower LR helped only on math; not on code") is *gone* unless
  the agent re-derives it by `Read`ing multiple prior handoffs. The
  Anthropic essay accepts this tradeoff explicitly — *context anxiety
  beats context bloat*.
- **The handoff artifact becomes the contract.** If it's missing a
  field the next agent needs, the next agent can't compensate. So
  the schema needs to actually capture the load-bearing state. We'll
  iterate it.
- **No memory of dead ends.** If iteration 4 tried X and failed,
  iteration 5 needs to see that in `learnings` or it might re-try X.
  This is mostly a write-side discipline question.

## When to do this

After the reference-returning Bash tool is verified (inv 005 immediate
work). The handoff design only makes sense once each iteration has a
clean "I succeeded / I failed" state to write out — which the new
Bash tool's markers + `evaluate_predictions` ack make tractable.

If we wired the handoff before fixing the tool-result bloat, every
handoff would carry 30K of unused stdout into the artifact too.
Order matters.

## Smaller-than-the-Anthropic-essay scope

We're not replicating their whole pattern. Specifically:

- **One agent at a time, not parallel specialists.** Their game-maker
  example had distinct planner / coder / QA agents communicating via
  files. Our researcher is a single role.
- **No mid-iteration reset.** They reset between major stages
  (planning → coding → QA). We only reset between iterations
  (between evaluate_predictions submissions). Each iteration is
  short enough that mid-iteration context bloat is bounded.
- **No structured prompt-rewrite step.** They sometimes rewrite the
  bootstrap message based on prior agents' outputs. Ours is fixed.

If single-reset doesn't carry far enough, we can add finer-grained
reset boundaries later (e.g. between "propose" and "implement"
phases inside one iteration). Premature for now.

## Sharp criterion to evaluate this design

After implementing:

> A 4-iteration smoke run lands all 4 submissions on the orchestrator
> AND the agent's wall-clock-per-iteration stays within 20% of the
> first iteration's wall-clock. (Without handoffs, we expect later
> iterations to slow down as the message history grows.)

If we hit that, it's the right design. If iteration wall-clock grows
substantially anyway (because the handoff artifact gets too big, or
because the agent over-reads prior handoffs), revise.
