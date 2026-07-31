---
id: studies/007-autoresearch-infrastructure/investigations/002-distributed-hello-world
title: Distributed hello world through an OpenCode drain
status: in-progress
parents:
  - studies/007-autoresearch-infrastructure
children: []
related:
  - studies/007-autoresearch-infrastructure/investigations/001-better-harnesses-derisk
  - studies/000-research-organization
axes:
  llm_capability: low
  human_capability: medium
tags: [drain, opencode, small-agent, routing, derisk]
created: 2026-07-30
updated: 2026-07-30
---

# Investigation 2 — Distributed hello world through an OpenCode drain

## Scope

Derisk the parallel drain that `plans/ticket-system.md` deferred ("parallel
drain, cron/background draining") and the small-agent dispatch that
`scripts/drain.py` left as a stub, using the OpenCode SDK as the agent
substrate — the "more modifiable harness" fork flagged in study 000's
framework-drift evidence. Five v1.1 tickets (three Python, two TypeScript),
each a hello-world program with machine-runnable checks, are drained in
parallel onto separate git worktrees/branches of a throwaway sandbox repo,
routed across two backends: the desktop 3080 (Ollama over Tailscale,
qwen3.5:9b) and the Gemini API (gemini-3.1-flash-lite).

The drain engine lives in `morel-primordia/projects/drain` (deployment
plumbing per the split-of-concerns contract); this investigation holds the
ticket set and the empirical record. Per resources.md, OpenCode is a
third-party harness: routes use real API keys (Gemini) or local models
(Ollama) — never Claude subscription OAuth.

Schema note: tickets here extend v1.1 with two additive fields consumed only
by the new drain — `route` (named model route in the drain config) and
`checks` (machine-executable acceptance). `drain.py check` tolerates both.

## Methods

- Tickets validated with `uv run scripts/drain.py --dir <tickets> check`.
- Drain run record: `morel-primordia/projects/drain/runs/<ts>/` —
  per-task `result.json` (schema drain-result/v1), `events.jsonl`,
  `agent.md`, `server.log`, plus `report.md`.
- Verification ladder before spending: unit tests → validate → dry-run →
  per-route smoke → single-task Ollama run → full Ollama rehearsal →
  mixed milestone run.

## Decisions

> **Decision 1 — OpenCode SDK as small-agent substrate** (2026-07-30)
> Small-agent dispatch goes through `opencode serve` + `@opencode-ai/sdk`
> (one server per worktree, per-prompt providerID/modelID) rather than
> extending drain.py's subprocess dispatch. Chosen because OpenCode's
> provider config natively expresses every routing target we need
> (Ollama over Tailscale, Gemini, corporate gateways with custom
> baseURL/headers) and the SDK returns per-message cost/token metadata.
> Alternative considered: claude_agent_sdk shim against Ollama's
> Anthropic-compatible endpoint (study 003 inv 003) — rejected for this
> use because it hardcodes one provider shape.

> **Decision 2 — qwen3.5:9b over 4B-class for the GPU route** (2026-07-30)
> First proof prioritizes tool-calling reliability over the weakest-capable
> principle; 4B-class floor probing is Part 3 territory once the drain
> itself is proven.

> **Decision 3 — pre-dispatch resource guards** (2026-07-30)
> Mid-build, the first GPU smoke test was aborted because the desktop 3080
> was running a game. Added per-provider guards to the drain config: a shell
> command (exit 0 = free) checked before dispatch; busy providers get their
> tasks skipped — not failed, no ticket write-back — so a later run drains
> them. The bundled `gpu-free.sh` queries nvidia-smi over Tailscale SSH.
> Validated live against the occupied GPU (39% util, 10.5 GiB VRAM → BUSY).

## Results

**Run 1 — 2026-07-31T02-51-48-282Z** (mixed config, GPU guarded-busy):

| Ticket | Route | Verdict | Duration | Tokens | Cost |
|---|---|---|---|---|---|
| 002-hello-python-args | gemini-3.1-flash-lite | pass 2/2 | 7.2s | 3025in/52out | $0.0011 |
| 003-hello-python-tested | gemini-3.1-flash-lite | pass 2/2 | 11.4s | 4072in/63out | $0.0015 |
| 005-hello-ts-json | gemini-3.1-flash-lite | pass 2/2 | 8.8s | 3304in/6out | $0.0014 |
| 001-hello-python-plain | desktop qwen3.5:9b | skipped (GPU busy) | — | — | — |
| 004-hello-ts-plain | desktop qwen3.5:9b | skipped (GPU busy) | — | — | — |

- All three API-routed tickets passed every check on the first attempt,
  in parallel on separate worktrees/branches, total metered cost $0.0039
  against the $0.50 phase budget. Per-route smoke (create-a-file tool-loop
  test) passed for gemini-3.1-flash-lite at $0.0009.
- The two GPU-routed tickets remain `ready`; rerunning the drain when the
  guard reports free will complete the distributed half of the milestone.
- Run record: `morel-primordia/projects/drain/runs/2026-07-31T02-51-48-282Z/`.
- Operational finding: OpenCode's built-in google provider reads
  `GOOGLE_GENERATIVE_AI_API_KEY`, not the repo-conventional `GEMINI_API_KEY`;
  mapped in drain config via `options.apiKey: "{env:GEMINI_API_KEY}"`.
- Hygiene finding (fixed): first commits included the generated
  `opencode.json` and `__pycache__`; the drain now excludes configured junk
  patterns at commit time and the three branches were amended clean.

**Run 2 — 2026-07-31T04-23-03-836Z** (GPU free, remaining two tickets):

| Ticket | Route | Verdict | Duration | Cost |
|---|---|---|---|---|
| 001-hello-python-plain | desktop qwen35-9b-32k | pass 1/1 | 7.2s | $0 |
| 004-hello-ts-plain | desktop qwen35-9b-32k | pass 1/1 | 7.1s | $0 |

**Milestone complete: 5/5 tickets passed across two backends** (3 on
gemini-3.1-flash-lite at $0.0039 total, 2 on local qwen at $0), each on its
own `drain/*` branch with a clean single commit.

Getting the local model working surfaced two findings that ARE the derisk
payoff:

- **`tool_call: true` is mandatory** on custom-provider model entries in
  opencode config; without it opencode never offers tools and the model
  narrates shell commands as prose. Failure mode is silent (session
  "completes" normally).
- **Ollama's default 4096 context silently breaks agent harnesses**: opencode's
  system prompt + tool schemas exceed it, Ollama truncates, and the model
  never sees its tools — while qwen3.5:9b tool-calls perfectly when hit
  directly with a small prompt. Fix: a derived model with `num_ctx 32768`
  (`qwen35-9b-32k`, created over the HTTP API, mirroring the existing
  `qwen35-4b-32k` recipe). Both failure modes produced zero errors anywhere —
  only the drain's acceptance checks caught them, which validates
  checks-as-verdict as a design choice.

> **Decision 4 — 32k derived model for agent work** (2026-07-31)
> Agent harnesses require the 32k-context derived models on the desktop
> (`qwen35-9b-32k`), never the stock tags with 4096 default context.
> Delegation-floor probes of 4B-class models (Part 3) should use
> `qwen35-4b-32k` for the same reason.

## Things made up that you should review

- The `route`/`checks` schema extension is used here without a blessed
  v1.3; if it survives contact, fold into the ticket-system spec.
- The drain writes provenance back into these ticket files from
  morel-primordia code, bending the one-way contract rule for derisk
  convenience.
- The `hello-world-approval` gate was marked approved by tyler on the basis
  of the explicit request for this milestone in conversation; no separate
  gate review happened.
