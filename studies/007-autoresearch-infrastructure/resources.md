# Resources

Resources first; constraints derive from resources (Tyler, 2026-07-27).
Agents drafting plans or tickets must receive this file — agent knowledge
of our hardware, budgets, and fleet is assumed stale. Maintained by
conversational elicitation from Tyler for now; a dedicated elicitation
Skill is backlogged (`plans/backlog.md`).

Scope: study 007; promote to repo root when another study consumes it.
Updated: 2026-07-27. Drafted by claude-fable-5, human-unreviewed.

## Compute

- **RTX 3080 12GB** in the Windows desktop (WSL2), reached from the Mac
  via Tailscale SSH; ollama serves local models. **Primary resource** —
  its 12GB VRAM is the binding hardware constraint on local model size.
- **Modal, $30/month** serverless GPU budget. **Secondary** — an
  escalation path when the 3080 cannot do the job, not a default; using
  it is a gate-worthy decision.
- This MacBook (Apple Silicon): orchestration, CPU-scale work.

## Model access

- **Claude Code subscription**: frontier-agent work and Haiku subagents;
  no marginal dollar cost, bounded by usage limits.
- **Anthropic API credits**: $17.58 remaining (verified 2026-07-30) of a
  $25 credit grant issued 2026-04-22, expiring 2027-04-23. Not a monthly
  allotment — periodic grants; monthly invoices are $0 (no pay-as-you-go,
  no auto-reload). For direct API calls the subscription can't cover
  (programmatic meta-agent or judge calls); expires unused.
- **Gemini API key**: flash-lite-class models for judge roles (small real
  API cost).
- **Local ollama fleet** on the 3080: 4B-class models (nemotron-4b,
  qwen3.5:4b family) verified in past studies; the current installed list
  must be measured at execution time, not assumed.

## Money

- Study 007 replication budget: ~$20 total; derisk phase compute ceiling
  $5 (tickets/plan.yaml).
- Modal $30/month (above), separate pool.
- Anthropic API credit balance $17.58 (above), separate pool with a
  2027-04-23 expiry.

## Human attention (scarcest resource)

- One researcher. Review bandwidth at gates is title + one-sentence
  summary per unit, detail on demand; human-authored documentation is a
  known bottleneck, so human writing obligations must be small and
  scheduled. Often reviewing from a phone, asynchronously.

## Agent streams

- Typically one interactive Claude session plus background subagents;
  local-model experiments serialize on the single GPU, so parallelism
  must come from non-GPU work.

## Time

- No fixed deadline; the study's stated horizon is ~6 months
  (2027-01).

## Derived constraints

- Max local model ≈ what measurably fits 12GB VRAM quantized (roughly:
  8B dense at Q4 fits; ~30B MoE does not fit comfortably — measure per
  model, never estimate).
- Local inference has no API price → cost claims need a documented proxy
  metric.
- Escalation ladder: 3080 → Modal ($30/mo) → anything beyond requires
  the human, explicitly.
- Subscription vs API credits (verified 2026-07-30): interactive/subagent
  work rides the subscription at $0. Programmatic calls split three ways:
  (1) our own tooling built on the Claude Agent SDK may bill the Max
  subscription via `claude setup-token` OAuth — sanctioned personal use;
  (2) third-party code (e.g. OpenHands software-agent-sdk) calling
  Anthropic must use a real API key (the finite $17.58) — subscription
  OAuth in third-party tools is banned by Anthropic policy (2026-02);
  (3) Gemini via its own key. Anthropic's announced monthly "Agent SDK
  credit" ($100/mo on Max 5x) was postponed 2026-06-16 and is NOT live —
  re-verify before relying on it.

## Things I made up to review

- The ollama fleet list is from prior-study memory, unverified today.
- Gemini judge access assumed from earlier studies' setup.
- "No fixed deadline" is my inference from the 6-month vision.
