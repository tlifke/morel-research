---
id: studies/003-automated-w2s-replication/investigations/003-claude-sdk-shim-and-researcher-swap
title: Claude Agent SDK shim and local-researcher swap
status: in-progress
parents:
  - studies/003-automated-w2s-replication
children: []
related:
  - studies/003-automated-w2s-replication/investigations/001-hardware-derisk
  - studies/003-automated-w2s-replication/investigations/002-vanilla-w2s-replication
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - automated-research
  - agent-sdk-shim
  - local-researcher
  - gemma-3-4b
  - capability-floor
aliases:
  - 003-003
  - sdk-shim-researcher-swap
created: 2026-05-24
updated: 2026-05-24
---

# Investigation 3 — Claude Agent SDK shim and local-researcher swap

## Scope

First investigation in which the agentic researcher loop runs at all
in [[study-003]]. Replaces the paper's Claude Opus 4.6 researcher
with a single local **Qwen 3 4B** instance (renamed from the
originally-planned Gemma 3 4B; see Decision 2), served via Ollama's
Anthropic-compatible endpoint (Ollama v0.14+). Uses the upstream
`safety-research/automated-w2s-research` agent harness with minimal
adaptations: a tight shim for the `claude_agent_sdk` import surface
backed by `anthropic.Anthropic(base_url='http://...:11434')`. Time-boxed
at 24 wall-clock hours after a feasibility gate.

The teacher (Qwen 1.5-0.5B-Chat) and student (Qwen 3-4B-Base)
remain unchanged from upstream and from [[003-002]]. Only the
**researcher** role is varied.

## Primary research question

**Can a Qwen 3 4B agent, given the upstream agent harness through
a tight `claude_agent_sdk`-compatible shim, drive `vanilla_w2s` PGR
above its baseline floor on at least one dataset within 24 wall-clock
hours? If yes, by how much? If no, what specifically broke —
capability, harness integration, hardware, or coherence?**

Binary-judgeable with a known floor (PGR ~0.30 vanilla) and a
published ceiling (~0.97 from the paper's 9-Opus-agent run, not
reproduced here).

## Why this question

- **Floor first.** Establishes whether a 4B researcher can sustain
  coherent multi-turn agentic behavior on this task before testing
  parallelism, harness affordances, or model substitutions.
- **Informative negative results.** "Loop fails because of X" is as
  useful as "loop succeeded with PGR Y" — it scopes what
  investigations 004+ should explore.
- **Aligned with [[study-003]]'s North Star.** Capability floor for
  the researcher role is the central study question.
- **One variable at a time.** We hold harness, student, teacher,
  dataset, and hardware fixed; only the researcher LLM changes from
  Opus to Gemma.

## Methodology

### Researcher LLM

- **Qwen 3 4B** (Ollama tag `qwen3:4b`, ~2.5 GB on disk, Q4 quant)
  via Ollama at `localhost:11434` (`100.97.4.17:11434` from the Mac).
  Ollama capabilities tag: `['completion', 'tools', 'thinking']`.
  Pulled on 2026-05-24; smoke-tested through shim gates 1, 2, 3.
- One agent instance, sequential GPU access. No parallelism in this
  investigation — see "Hardware constraints" below.
- Single seed for the researcher's stochasticity (Ollama default
  sampling); separate from the student's training seed (42, locked).
- Symmetry note: researcher and student now share the Qwen base
  (researcher: `qwen3:4b` instruct-class, student: `Qwen3-4B-Base`
  trained via LoRA). Convenient for behavioral interpretation; an
  unintended bonus of the model switch.

### Shim approach — tight, minimal coverage

Replace `claude_agent_sdk` with a compatibility layer backed by the
bare `anthropic` Python SDK pointed at Ollama. Cover only the
surface the upstream `agent.py` actually uses:

- `ClaudeSDKClient(options)` async context manager
- `await client.query(prompt)` and `client.receive_messages()`
- `ClaudeAgentOptions` dataclass (only the fields upstream sets)
- Message types: `AssistantMessage`, `ResultMessage`, `TextBlock`,
  `ToolUseBlock`
- `@tool(name, desc, schema)` decorator + `create_sdk_mcp_server`

Ollama v0.14+ exposes an Anthropic Messages-API-compatible endpoint
with native tool calling, so the wire protocol matches the SDK's
expectations.

Estimated shim scope: ~400-700 lines. Lives at
`scripts/claude_agent_sdk_shim/` under this investigation. Not 100%
SDK coverage — just what works for our agent flow.

Why tight shim over honest rewrite of the loop:

- Preserves the upstream agent's prompt and behavioral structure.
  Any divergence in outcome from a hypothetical Opus run is
  attributable to the model, not to harness redesign.
- Decoupled investment: the shim works for any Ollama-served
  Anthropic-compatible model, so investigations 004+ (smaller models,
  Qwen-as-researcher, parallel agents) get the shim for free.

### Test gates (build incrementally)

Subagent builds and tests in this order. Halt at each gate failure
for human review.

1. **Basic client** — single `query("say ok")` returns parseable
   text from Gemma 4B via Ollama.
2. **Multi-turn** — two-turn dialogue where turn 2 references turn 1.
3. **Single tool round-trip** — register `add(a, b)`, ask "what's
   5+3?", confirm tool invoked + result returned. **Human-review
   checkpoint.**
4. **Multi-tool** — full upstream tool surface (`evaluate_predictions`,
   `share_finding`, `get_leaderboard`) against the running Flask
   server.
5. **Full loop micro-iteration** — shim drives upstream `agent.py`
   for one short cycle (math, train_size=64, epochs=1, ~15 min) —
   one full idea proposed, trained, evaluated, reasoned about.

### Feasibility gate (before the 24-hour run)

A 10-20 minute pre-flight that runs gate 5's micro-iteration
end-to-end. Pass criterion: at least one full iteration completes
without harness crash or agent incoherence. If pass, proceed to the
24-hour run. If fail, triage and document.

### 24-hour run

- Wall-clock budget: 24 hours from launch.
- Dataset: agent chooses, OR we set one — TBD per upstream agent
  flow (see open questions).
- Logging: see "Logging structure" below.
- No human intervention during the run.

### Logging structure

```
investigations/003-.../runs/<timestamp>-<model>-<seed>/
├── config.yaml               # model, time budget, dataset, seed
├── timeline.jsonl            # ordered turn-by-turn record
├── ideas/
│   └── <NNN>-<slug>/
│       ├── proposal.md       # agent's text proposing this idea
│       ├── run.py            # the Python the agent wrote
│       ├── train.log         # training stdout
│       ├── train_summary.json
│       ├── eval_request.json # what was sent to evaluate_predictions
│       ├── eval_response.json
│       └── retrospective.md  # agent's reasoning after seeing the result
├── notebook.json             # agent's running memory file
├── notebook_snapshots/       # per-turn version history
├── findings/                 # share_finding outputs
└── summary.json              # final aggregate
```

`timeline.jsonl` records each turn as a JSON object: timestamp,
turn index, phase (system/agent/tool/subprocess), reasoning text,
tool calls, tool results, file writes (with content hashes), and
subprocess invocations.

### Comparison reporting

Final results table:

| dataset | vanilla floor (003-002) | our Gemma 4B agent | paper Opus AAR ceiling |
|---|---:|---:|---:|
| math | 0.30-0.34 | TBD | 0.97 (cited, not reproduced) |
| chat | 0.37-0.40 | TBD | (TBD from paper) |
| code | 0.15-0.16 | TBD | (TBD from paper) |

Opus column is cited from the alignment forum post (parallel 9-agent
× 5 days). We explicitly note non-reproduction.

## Hardware constraints

From [[003-001]]'s verdict:

- Student training uses ~12 GB of the 12 GB GPU. No co-residency
  possible.
- Researcher inference (Gemma 4B Q4 in Ollama) uses ~4 GB when
  active; Ollama idles models out of VRAM when not in use.
- Single agent only — multiple agents would have to serialize on the
  GPU anyway. We could run logically-parallel agents that share a
  findings forum, but they wouldn't speed up wall-clock; their value
  would be idea-diversity. Deferred to investigation 004.
- Smaller models (Gemma 1B, Qwen 0.6B) wouldn't unlock parallelism —
  student training alone fills the GPU. Smaller models could be a
  capability-floor characterization in investigation 005.

### GPU usage timeline per iteration

| phase | duration | VRAM | resident |
|---|---|---|---|
| agent reasoning + code gen | ~5-10 min | ~3-4 GB | Qwen 3 4B (Ollama) |
| transition | <30 sec | ~441 MB idle | (Qwen swapped to disk) |
| student LoRA training | ~3-5 hr | ~12 GB | Qwen 3 4B Base + LoRA |
| transition | ~30 sec | ramps | — |
| student eval (vLLM) | ~5-10 min | ~12 GB | Qwen 3 4B Base in vLLM |
| transition | ~30 sec | drops then ~3-4 GB | — |
| agent reads result, plans | (next iter) | — | — |

Strictly sequential, never parallel. 24 hours ≈ 5-8 full iterations.

## Decisions

> **Decision 1 — tight shim over honest rewrite** (2026-05-24)
> The upstream agent harness uses `claude_agent_sdk` imports.
> Replacing those with a compatibility shim backed by
> `anthropic.Anthropic(base_url=ollama)` preserves the upstream
> prompt and behavioral structure, isolating "model capability" as
> the only changed variable. Honest rewrite was the alternative;
> rejected for the first investigation because it confounds harness
> redesign with model substitution.

> **Decision 2 — Qwen 3 4B over Gemma 3 4B IT (revised 2026-05-24)** (2026-05-24)
> **Originally:** Gemma 3 4B IT QAT, on grounds of consistency with
> prior repo work (studies 001, 002).
> **Revised after gate 3 failure:** Ollama's Anthropic-compatible
> endpoint rejects tool-call requests for `gemma3:4b-it-qat` and
> `gemma3:12b-it-qat` at the API layer — the registry tag is missing
> the `tools` capability (`['completion', 'vision']` only). This
> isn't a model-capability issue (study 001 confirmed Gemma 3 4B can
> do tool calling effectively via text-mode prompt formatting), but
> it does block our specific Anthropic-SDK-shaped harness without
> additional shim engineering. Switched to **`qwen3:4b`**, which is
> the smallest-on-disk (~2.5 GB) and most-battle-tested 4B-class
> tool-tagged Ollama model. The "instruct" designation has been
> folded into the base tag in recent Qwen releases.
>
> **Why not Qwen 3.5 4B?** Also pulled and smoke-tested — all three
> gates pass cleanly. But released ~9 minutes before our smoke
> screenshot was taken (2026-05-24), so production behavior is
> unstudied. Held as the easy-swap follow-on once we have a working
> baseline.
>
> **Smoke comparison (2026-05-24, gate 3 wall-time):**
>
> | model | gate 1 | gate 2 | gate 3 (tool call) | gate 3 wall |
> |---|---|---|---|---|
> | gemma3:4b-it-qat | PASS | PASS | **FAIL (server gate)** | 0.13s |
> | qwen3:4b | PASS | PASS | **PASS** | 2.5s |
> | qwen3.5:4b | PASS | PASS | **PASS** | 1.7s |
>
> Symmetry bonus: researcher and student now share the Qwen base
> (researcher = `qwen3:4b`, student = `Qwen3-4B-Base`). Originally
> identified as a weak preference; gate 3 made it the load-bearing
> consideration.

> **Decision 3 — feasibility gate before 24-hour run** (2026-05-24)
> 10-20 minute micro-iteration smoke before committing GPU-day to a
> 24-hour run. Catches loop-coherence and harness-integration issues
> early.

> **Decision 4 — single agent in this investigation** (2026-05-24)
> Hardware forces sequential GPU access. Multi-agent value would
> come from idea-diversity, not parallelism. Deferred to
> investigation 004 (or later) to keep this investigation's variable
> count low.

## Results

### Gate 1 — basic client (PASS, 2026-05-24)
- wall-time: 4.24 sec
- response text: `'ok\n'`
- key observation: `anthropic.AsyncAnthropic(base_url=ollama)` against
  `gemma3:4b-it-qat` round-trips cleanly via the shim's
  `ClaudeSDKClient`/`receive_response()` surface. No protocol surprises.

### Gate 2 — multi-turn (PASS, 2026-05-24)
- wall-time: 1.08 sec (combined two turns)
- turn-2 response: `'Your name is Tyler! You told me earlier.'`
- key observation: shim-side conversation history (appending each turn's
  `{role, content}` to `self._history`) is sufficient — Ollama's
  Anthropic-compatible endpoint correctly conditions on prior turns.

### Gate 3 — single tool round-trip (FAIL, 2026-05-24)
- wall-time: 0.13 sec (server rejected the request before any inference)
- root cause: **server-side, not shim, not model-capability.** Ollama's
  Anthropic-compatible endpoint returns HTTP 400 for
  `gemma3:4b-it-qat`:
  `registry.ollama.ai/library/gemma3:4b-it-qat does not support tools`.
  Confirmed via `/api/show`: the model's capabilities are
  `['completion', 'vision']` — no `tools` capability. Same is true of
  `gemma3:12b-it-qat`. Gemma 3 is not tool-tagged in Ollama's registry
  even though the model can in principle follow tool-calling schemas.
- shim behavior: the shim correctly serialized the `tools` argument,
  surfaced the server error through `ResultMessage(stop_reason='error')`,
  and did not corrupt state. Tool-call code path is untested by this
  gate because the request never reached inference.
- implication for the investigation: the planned Gemma 3 4B IT
  researcher cannot drive the upstream W2S agent harness against
  Ollama's Anthropic-compat endpoint as currently configured. Options
  for human review before continuing:
    1. **Pull a tool-tagged Ollama model** (e.g. `qwen3:4b`,
       `llama3.1:8b`, `mistral:7b-instruct`) and re-run gate 3. Breaks
       Decision 2 (Gemma-first) but keeps the investigation alive on a
       comparable scale.
    2. **Bypass Ollama's Anthropic-compat layer.** Call Ollama's native
       `/api/chat` (which does support tool calls for Gemma 3 per
       Ollama's own docs) and translate to/from Anthropic types
       inside the shim. Larger shim scope; preserves Gemma.
    3. **Drop tool calling for the researcher** and have the agent
       emit structured text the harness parses. Major harness
       deviation; breaks the "tight shim" framing of Decision 1.

Stopping here for human review per the spec's "Ollama behaves
unexpectedly" trigger. Gates 1 and 2 confirm the shim's text-only
surface is sound; the tool surface is blocked behind a server/model
compatibility issue.

### Gates 1–3 re-run with Qwen 3 4B (PASS, 2026-05-24)

After model-switch decision (see revised Decision 2), the existing
shim was re-tested against `qwen3:4b` and `qwen3.5:4b` with zero code
changes — only the model string differs.

| gate | qwen3:4b | qwen3.5:4b | observation |
|---|---|---|---|
| 1 — basic client | PASS (27.5s) | PASS (9.8s) | both round-trip cleanly |
| 2 — multi-turn | PASS (5.6s) | PASS (23.8s) | context retained across turns; turn-2 correctly recalled "Tyler" |
| 3 — tool round-trip | PASS (2.5s) | PASS (1.7s) | `add` tool invoked with `{a:5, b:3}`; both reported "8" |

Headline observations:

- Both models pass cleanly via Ollama's Anthropic-compat endpoint.
  No text-mode hacks needed; native `tools=[...]` API works.
- Qwen 3 4B is selected for the rest of the investigation (Decision 2).
- The shim is model-agnostic by construction — easy comparative
  studies in later investigations.

Proceeding to gate 4 (full upstream tool surface against the Flask
server).

### Gate 4 — multi-tool against running Flask server (PASS, 2026-05-24)

- wall-time: 37.1 sec
- model: `qwen3:4b` (thinking enabled, native)
- tool calls invoked, in order:
  1. `get_leaderboard` (no args)
  2. `evaluate_predictions` with `{predictions:[0,1,0,1,0], dataset:'math', weak_model:'Qwen/Qwen1.5-0.5B-Chat', strong_model:'Qwen/Qwen3-4B-Base'}`
- final synthesized text: noted the server returned HTTP 404 for the
  math evaluation (no pre-cached baselines for math/Qwen on the server
  at gate-4 time), and that the leaderboard entries were chat-only.
  Final answer correctly cited the 404 rather than fabricating a PGR.
- pass criteria: both tools invoked at least once each, final response
  includes a numeric value from the server. Met.
- caveats:
  - Required `max_tokens` ≥ 8192 for Qwen 3 4B in thinking mode; the
    initial run at 4096 exhausted the budget entirely on
    `<think>...</think>` reasoning before any tool call was emitted.
    Shim default raised from 2048 → 8192 to absorb this.
  - First attempt with `/no_think` (thinking disabled) produced
    confident hallucinated tool-result narration *without* actually
    calling the tools. Thinking is load-bearing for tool selection
    here. Re-enabling thinking + a stronger "you MUST call tools, do
    not guess" system prompt fixed it.
- shim behavior: multi-tool sequencing worked first try once token
  budget and thinking were correct. Tool-result-injection into the
  conversation is sound at multi-tool scale; the assistant correctly
  conditioned on the prior tool result when choosing the next call.
- ran on the desktop (`/home/tlifke/inv003_shim/`) because port 8000
  isn't forwarded to the Tailnet. Mac → desktop runs are only
  reachable for Ollama (11434).

Proceeding to gate 5.

### Gate 5 — full loop micro-iteration (FAIL, 2026-05-24)

- wall-time: ~90 sec elapsed (killed early; failure mode confirmed in
  first 4 sessions; no point burning more GPU time)
- sessions completed: 4 (each ~27-30 sec)
- evaluate_predictions hits on Flask server: **0**
- stop reason: manually terminated; would have run to 25-min timeout
  with the same per-session failure mode repeating
- model: `qwen3:4b` via shim, `local_mode=True`, dataset=math, smoke
  task targeting train_size=64 etc.

**Specific failure mode: tool-call format mismatch.**

The shim correctly serializes the upstream tools, sets
`tools=[...]` on the Anthropic-compat request, and Ollama accepts it
(gate 3 + gate 4 confirmed this round-trip). But on the
full-system-prompt agent run, Qwen 3 4B chose to emit tool calls
**as free-form JSON text** inside its response body rather than via
native Anthropic `tool_use` blocks. Three of four sessions produced
text like:

```
{
  "name": "evaluate_predictions",
  "arguments": {
    "dataset": "math",
    "predictions": [0,1,0,1,...],
    ...
  }
}
```

(One session also wrapped this in a `<function_call>...</function_call>`
tag, the Qwen-native fine-tuned format.) The shim sees only
`TextBlock`, no `ToolUseBlock`, so no tool actually fires. The Flask
server received zero requests across the entire run.

Session 0 was silent — empty `AssistantMessage` after 27s. Consistent
with the gate-4-observed pattern where thinking consumes the full
output budget on first contact with a complex prompt.

**This is not a shim bug.** Gates 3 and 4 both invoked native tool_use
correctly under shorter / more prescriptive prompts. The behavior is
the model's: the upstream agent prompt is dense, Claude-tuned, and
asks the agent to "consult /research-thinking skill" and read/write
files via `Read`/`Write`/`Bash` tools that the shim does not provide
(because they're built-in tools of the real `claude` CLI, not MCP
servers). With no `Bash` to actually run the smoke training command,
Qwen falls back to its template-native function-call text format and
calls it a turn.

**What this reveals about the integration:**

1. **Built-in tool gap.** The upstream agent assumes `Read`, `Write`,
   `Bash`, `Glob`, `Grep`, `WebSearch`, `WebFetch` are available — they
   are provided by the `claude` CLI binary, not by `claude_agent_sdk`.
   The shim, pointed at Ollama, has no way to expose these to Qwen.
   Without `Bash` the agent cannot actually run the smoke training
   command — the loop is uncloseable as currently constructed.
2. **Tool-format hallucination.** Even for the MCP tools that *are*
   wired up, Qwen 3 4B under this prompt prefers its instruction-tuned
   text-format function-call output over the native tool_use API. The
   Ollama Anthropic-compat layer faithfully forwards whatever the
   model produces; it does not retrofit text-format calls into
   `tool_use` blocks.
3. **Thinking-budget pressure.** Even at `max_tokens=8192`, the
   first-contact session burned the whole budget thinking and
   produced an empty response. Later sessions reached an output;
   per-iteration latency is dominated by reasoning, not action.

Gate 5 verdict: **harness-integration failure, predictable in
hindsight.** The shim's surface is sound. The upstream agent harness
assumes capabilities (Bash, Read/Write, native Anthropic tool_use)
that don't transfer to a 4B Ollama-served model without additional
shim engineering. The 24-hour run is not authorized.

**What would unblock gate 5 (not done here — for human review):**

- (a) Add MCP-backed `Bash`/`Read`/`Write` tools to the shim so the
  agent has *some* execution surface. Substantial scope creep — these
  are non-trivial to do safely.
- (b) Switch the shim to use Ollama's native `/api/chat` and parse
  text-format function calls into `ToolUseBlock`s before yielding them
  upstream. Catches Qwen's preferred format but requires per-model
  parsing rules.
- (c) Rewrite the upstream agent loop to use only MCP tools (drop the
  built-in dependency). Breaks the "tight shim" framing of Decision 1
  but is honest about what the harness actually needs.
- (d) Use a model that more reliably emits native `tool_use` under
  long prompts (Qwen 3 8B+, Llama 3.1 8B). Bigger model → can't
  co-reside with training → loop becomes serialized differently.

Recommend (b) then (a) as the next investigation's scope. (c) is
philosophically cleanest but discards the bulk of the upstream prompt
engineering, which is the thing we wanted to study.

### Gate 5 retry — paths A + B implemented (PARTIAL, 2026-05-24)

After (a) and (b) were both authorized, the shim was extended:

- **Path A (text-format tool call parsing).** `parser.py` synthesizes
  `ToolUseBlock` instances from `TextBlock` content when the model
  emits tool calls as `<function_call>{...}</function_call>`,
  `<tool_call>{...}</tool_call>`, fenced ```json blocks, or bare
  JSON objects (gated on the known tool-name set). Recognises `name`,
  `function`, `function_name`, `tool`, `tool_name` as the name key
  and `arguments`, `parameters`, `input`, `args` as the argument key.
  Synthesized turns are treated as `stop_reason='tool_use'` so the
  agent loop continues. 13 unit tests under
  `scripts/tests/test_text_format_parser.py`.
- **Path B (MCP-backed built-ins).** `builtins.py` exposes an
  `SdkMcpServer` named `builtin` containing `Bash`, `Read`, `Write`,
  `Edit`, `Glob`, `Grep` (`WebSearch`/`WebFetch` stubbed to a clear
  error). Bash runs via `asyncio.create_subprocess_shell` in a
  configurable cwd with default timeout 1800s for training commands.
  The server is registered through the existing
  `loop.mcp_servers["builtin"] = ...` plumbing — no new public API on
  `ClaudeSDKClient`. Filtering also accepts bare tool names in
  `allowed_tools` so the unqualified upstream entries (`Bash`,
  `Read`, ...) match. 8 unit tests under
  `scripts/tests/test_builtins.py`.

Both unit-test suites pass locally and on the desktop.

**Retry run** (`logs/gate_5_run_20260524_203736_pathAB/`):
qwen3:4b, smoke config, 7 sessions in ~6.5 min before manual stop.

| metric | gate 5 first attempt | gate 5 retry (A+B) |
|---|---:|---:|
| sessions completed | 4 | 7 |
| `evaluate_predictions` tool calls fired | 0 | 8 |
| Bash/Read/Write tool calls fired | 0 | 0 |
| training command actually executed | no | no |

**What improved.** Path A is working: the shim now reliably
synthesizes tool_use blocks from Qwen's text-format emissions across
multiple variants (`{"name":...}`, `{"function":...}`,
`{"function_name":..., "arguments":...}`, naked
`<function_call>` tags). 8 of 7 sessions produced at least one
genuine tool call hitting the Flask server (gate-5 first attempt had
zero). The agent reads tool results and reasons about them.

**Where it still fails.** A third class of issue surfaces, distinct
from paths A and B: even with Bash now available and listed in
`allowed_tools`, the model **never emits a Bash tool call**. It
instead writes the shell commands it wants to run as markdown code
blocks inside its narration (`\`\`\`bash mkdir -p ...\`\`\``). Across
all 7 sessions the agent called only `evaluate_predictions`
(repeatedly, with dummy 0..63 predictions), never `Bash`, `Read`, or
`Write`. The workspace remained empty. So the loop still cannot
close: no training command runs, so there is nothing real to
evaluate, so PGR cannot be produced.

This is a model-behavior failure under a long Claude-tuned system
prompt, not a shim gap. Possible interventions, in increasing scope:

1. Prompt patch — append an explicit "you must call the Bash tool to
   execute commands; do not write commands in markdown" instruction
   to the system prompt. Cheapest; may simply not stick on a 4B
   model.
2. Force-loop scaffold — if a session produces no tool calls, inject
   a user-turn nudge ("you wrote shell commands but did not invoke
   Bash; please call Bash to execute them"). Slightly heavier; biases
   the loop further from the upstream behavior.
3. Model swap — Qwen 3 8B or larger; sacrifices GPU-co-residency
   with the student (see [[003-001]] hardware verdict, the training
   phase will need to fully swap out the researcher).

Per the operating constraint ("don't fix more than one new class of
issue without checking back"), stopping here. The 24-hour run remains
not-authorized.

**Gate 5 verdict update.** Paths A + B unblock the shim-side
failures. The loop-closure failure is model-side
(commands-as-narration). Recommend a follow-on investigation 004
scoped narrowly to: (i) try prompt patch (1), (ii) if that fails,
swap to 8B and re-test gate 5. Skip the scaffold (2) unless both
fail.



## Forward-looking

After this investigation, depending on outcome:

- **If Qwen 3 4B drove PGR meaningfully above the vanilla floor:**
  investigation 004 could test multi-agent with shared findings,
  smaller models for capability-floor characterization, or harness
  affordance ablations. Direct Qwen 3.5 4B comparison becomes the
  easiest swap.
- **If Qwen 3 4B failed at the loop-coherence level:** investigation
  004 becomes "what harness affordances help a 4B agent maintain
  coherence" — directly the MDP/action-space framing.
- **If Qwen 3 4B kept the loop alive but didn't improve PGR:**
  investigation 004 explores whether the failure is in idea
  selection, code-writing reliability, or reasoning about results
  — each a different harness fix.
- **Gemma 3 4B revisit (any outcome):** Once a working loop exists,
  building a text-mode-tools shim variant lets us put Gemma 3 4B
  back in the running. Study 001 showed Gemma 3 4B can do text-mode
  tool calls; the only blocker was the Anthropic-compat endpoint
  gate. Worth a follow-on if we want a non-Qwen-family comparison.

The shim is the durable contribution. Once built and tested, it
makes future investigations (Qwen-researcher, smaller-model
floors, parallel-agent diversity) drop-in.

**Post-gate-5 update (2026-05-24):** Gate 5's first run surfaced
two shim-side gaps (text-format tool calls; missing built-in tools).
The retry implemented both (paths A and B above). Result:

- Both shim gaps are closed. Tool calls now fire correctly, including
  against the Flask server (8 `evaluate_predictions` invocations
  across the 7-session retry). The shim is no longer the blocker.
- A third gap emerged that is **not** shim-side: even with Bash
  exposed and listed in `allowed_tools`, Qwen 3 4B writes shell
  commands as markdown code blocks in its narration and never
  actually invokes Bash. The loop cannot close because no training
  command runs.

Investigation 004 should target this directly: prompt-patch first
(cheap), then an 8B+ model swap if needed (accepts GPU-serialization
cost per [[003-001]]). The 24-hour Qwen 3 4B run as originally
scoped remains not viable.

## Open questions

- The upstream agent flow expects a `target_idea_content` — a
  research direction provided to the agent. For investigation 003,
  do we leave this empty (let the agent pick) or pre-fill with a
  specific direction (e.g., "explore unsupervised elicitation
  refinements")? Defaulting to empty for the first run; revisit if
  the agent flounders on direction selection.
- Dataset choice for the 24-hour run: pick one (math is fastest per
  iteration), let the agent pick, or rotate. Default: math only,
  for tightest iteration loop.
- How tightly should the shim mimic `claude_agent_sdk`'s
  conversational continuity? The SDK retains session state across
  `query()` calls; Ollama via the Anthropic-compat layer also
  supports multi-turn. Verify in gate 2.

## Things to flag

- **The shim is the largest novel-code investment in this study.**
  ~400-700 LOC of glue. Worth thinking carefully about ownership and
  maintenance — it'll be used in investigations 004+.
- **Ollama Anthropic-compatibility is new (v0.14+).** Edge cases in
  tool-call format are possible. Gate 3 specifically tests this.
- **The agent's prompt is dense and Claude-tuned.** It expects
  certain reasoning patterns (e.g., "consult /research-thinking
  skill"). Qwen 3 4B may interpret some directives literally
  ("consult X" → tries to invoke X as a tool) or ignore them. Watch
  for this in gate 5.

## Limitations

- Single seed for the researcher; can't characterize researcher-side
  stochasticity.
- Single 24-hour budget; can't characterize how PGR scales with
  more time.
- Single agent; no multi-agent diversity comparison.
- The Opus ceiling is cited, not reproduced. Any "Qwen 4B vs Opus"
  comparison is against published numbers from a different setup
  (parallel 9-agent over 5 days vs our single agent over 24 hours).
