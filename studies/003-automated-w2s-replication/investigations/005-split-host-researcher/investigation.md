---
id: studies/003-automated-w2s-replication/investigations/005-split-host-researcher
title: Split-host researcher — does evicting the researcher from the GPU let the loop close end-to-end?
status: planned
parents:
  - studies/003-automated-w2s-replication
children: []
related:
  - studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - harness-design
  - substrate
  - split-host
  - tool-calling
  - qwen
  - nemotron
created: 2026-05-31
updated: 2026-05-31

---

# Investigation 5 — Split-host researcher

## Scope

Investigation 004 closed at a sharp result: **prompt induction at 4B is
solved (patch 4); substrate contention is the residual wall** on a
single 12 GB GPU. Inv 004 tried three on-host workarounds — patch 4 +
GPU-contention tolerance, time-multiplex unload-on-long-bash, and a
nemotron-3-nano:4b drop-in — and all three failed to cross inv 4b's
stopping criterion (one valid `evaluate_predictions` submission). The
captured VRAM traces in inv 004's `figures/` directory show why:
co-resident runs peg the 12 GiB cap to within ~76-234 MiB of OOM at
smoke scale (`test_size=64`) and exceed it at production scale
(`test_size=1315`).

This investigation tests the first structural fix that does not fight
the GPU: **serve the researcher model from Ollama on the MacBook Air
M2 over Tailscale, while keeping the agent loop and Bash subprocess
local to the desktop**. The only thing that moves is the ~5.7 GiB
researcher-model resident allocation; everything else (orchestrator,
agent loop, Bash, SFT, vLLM eval) stays on the desktop. The Mac is
just an HTTP server for the researcher API at
`http://<mac-tailscale>:11434/api/generate`.

This topology has a useful property for the human-in-the-loop case:
if the Mac sleeps mid-run (lid closed, walked away), only the next
researcher `generate` call fails — the desktop's in-flight Bash
subprocess (SFT or vLLM eval) keeps running to completion, and a
small agent-loop retry can resume once the Mac is back. Bench numbers captured during scaffolding (2026-05-31) put the
researcher at ~12 tok/s for qwen3.5:4b and ~16.6 tok/s for
nemotron-3-nano:4b on the MacBook (vs ~129 and ~193 on the desktop) —
a ~10× generation slowdown that translates to roughly 2× wall-clock
per research-loop iteration once SFT+eval is the dominant cost.

### Research questions

Four questions, sequenced. Each is a distinct unit of evidence; do not
collapse them into a single end-to-end "did it work" verdict.

#### Q1 — Substrate sharp criterion (mirrors inv 4a)

Does the split-host topology let the loop produce **one valid
`evaluate_predictions` submission against the real target idea at
production scale** (`test_size=1315`)? This is the threshold inv 004
could not cross. Direct repro of the inv 4a `train_eval` verification
with the researcher served from the Mac is the canonical sharp test.

Success criterion: a single agent-loop session (qwen3.5:4b + patch 4,
Mac-hosted) produces a model checkpoint and the upstream orchestrator
accepts the integer-list submission.

#### Q2 — Researcher speed cost

How much does the iteration wall-clock change vs the inv 004 desktop-
resident pattern? Two measurements:

- **Per-iteration wall time** — researcher reasoning latency + Bash
  subprocess wall time. Compare to the captured direct-Bash control
  (~94 s end-to-end SFT+eval) and the inv 004 patch-4 co-resident
  retries (~5-7 s per Bash, but never crossing the substrate).
- **Iterations per smoke window** — at a fixed `MAX_RUNTIME_SECONDS`
  (e.g. 1500 s like inv 4b), how many full
  (think → Bash → eval) cycles complete? Compare to inv 4b patch 4
  (49 retries inside one task) and the time-multiplex run (208 retries
  inside one task).

The hypothesis carried in from inv 004 + today's benches:
researcher-side latency rises ~10× but loop wall-clock rises ~2×
because SFT+eval is the dominant cost. Q2 measures whether that holds
in practice.

#### Q3 — Behavioral parity of tool-calling shape

Does the researcher's tool-calling shape stay consistent under split-
host conditions? Patch 4's measured shape on the desktop (inv 4b) was:
**10 canonical `Bash`, 29 lowercase `bash`, 4 `Write`, ~6 invented
names** across one 3-minute session — a pattern dominated by
GPU-contention-induced fast-fail retries. Predicted under split-host:
each canonical `Bash` actually runs ~80 s, so retry pressure
disappears; expect **5-15 calls per session, predominantly canonical
`Bash`, with `evaluate_predictions` firing exactly once at end**.

Three sub-checks against the inv 004 patch-4 baseline:

- Canonical-`Bash` share (target: ≥80% of Bash invocations canonical;
  inv 004 was ~26%)
- Lowercase / hallucinated tool fraction (target: ≤10%; inv 004 was
  ~75% of Bash invocations were lowercase)
- `evaluate_predictions` invocation count (target: 1; inv 004: 0)

#### Q4 — Researcher choice (qwen3.5:4b vs nemotron-3-nano:4b)

Inv 004's nemotron diagnostic showed equivalent prompt-fit but
substrate failure. Today's MacBook benches show nemotron ~35% faster
generation than qwen3.5:4b. Under split-host, does that translate to:

- Lower Q2 wall-clock cost (expected: yes, ~25-30% faster
  per-iteration)?
- Equivalent or better Q3 tool-calling shape (expected: yes per inv
  004's nemotron drop-in)?
- The same Q1 result (expected: yes, since substrate is no longer
  binding)?

A clean answer here picks the inv-005-and-beyond researcher.

### Why this scoping

Inv 004's anti-stall protocol explicitly named the harness-vs-model
distinction (see [[feedback_harness_vs_model_floor]]): when floor
evidence points at the harness, scope harness redesign as its own
investigation. The MacBook-as-researcher path is that redesign. It is
**not** a study because the parent question — "can we replicate the
w2s automated-researcher paper on consumer hardware" — has not
changed; only the hardware topology under test has. If Q1-Q4 close
cleanly, the next unit (inv 006+) is the 24-hour single-agent run
with anchored baselines, which is the long-deferred study-003 goal.

### What this investigation is NOT

- Not the 24-hour PGR-measurement run. That is gated on Q1 succeeding.
- Not a multi-agent dynamics test (deferred to inv 006+).
- Not a comparison of harness shapes (QwenCode-native vs Claude-shaped
  SDK shim) — inv 4c closed that question on Reading A. The shim is
  the substrate.
- Not an attempt to reduce the on-host VRAM footprint via fp8 KV-cache
  or quantized vLLM weights — those are independent levers worth
  testing **after** Q1, when they can be evaluated without
  substrate-contention confounding the measurement.

## Methods

### Pre-Q1 — Harness bugs surfaced while wiring split-host (2026-05-31)

Q1 setup uncovered two long-standing bugs in the
`/home/tlifke/inv003_shim/` infrastructure that the agent loop in inv
004 was running on. Documented here before the fix because they
materially change how inv 004's tool-call-count narrative should be
read.

#### Bug 1 — `SdkMcpServer` identity mismatch silently drops every builtin tool

The shim ships two parallel copies of the same package:

- `/home/tlifke/inv003_shim/shim_pkg/claude_agent_sdk/` — imported by
  `w2s_research/research_loop/agent.py` as `claude_agent_sdk`.
- `/home/tlifke/inv003_shim/scripts/claude_agent_sdk_shim/` — imported
  by the inv 003/004 test runner
  (`scripts/tests/test_gate_5_full_loop.py`) as
  `claude_agent_sdk_shim`.

The two `builtins.py` and `tools.py` files are byte-identical. But
because they're loaded as different modules, the two `SdkMcpServer`
classes have different class identity. The test runner calls
`create_builtin_tools_server(...)` from `claude_agent_sdk_shim`, which
returns a server typed `claude_agent_sdk_shim.tools.SdkMcpServer`. The
agent loop wraps it in `ClaudeAgentOptions(mcp_servers={"builtin": ...})`,
and `client.py._build_tool_index` does:

```python
for server_key, server in (self.options.mcp_servers or {}).items():
    if not isinstance(server, SdkMcpServer):  # claude_agent_sdk.tools.SdkMcpServer
        continue                              # ← always skipped
    for tool_name, t in server.tools.items():
        self._tool_index[t.name] = t
```

So `_tool_index` is empty. When the model emits a `tool_use` block
naming `Bash`, `_invoke_tool` returns `{"content": [{"type": "text",
"text": "unknown tool: Bash"}], "is_error": True}`. The agent receives
"unknown tool" instantly and retries.

**Verification.** Direct repro:

```python
from claude_agent_sdk_shim import create_builtin_tools_server as cbts
from claude_agent_sdk.tools import SdkMcpServer as ExpectedCls
srv = cbts(cwd='/tmp')
print(type(srv).__module__)   # claude_agent_sdk_shim.tools
print(ExpectedCls.__module__) # claude_agent_sdk.tools
print(isinstance(srv, ExpectedCls))  # False
```

**Retroactive read of inv 004.** Inv 4b patches 1-4 reported "Bash
fires" by counting `Tool: Bash` lines in the agent's session log.
Those entries log the model's *intent* to call Bash (the `tool_use`
block emitted by the model), not the result of calling the handler.
Under this bug, every one of those calls returned `"unknown tool:
Bash"` from `_invoke_tool` without ever reaching the shim's
`_make_bash_tool` handler. The "Bash returns in 5-7s" pattern
attributed to GPU contention via Ollama keep-alive is, in retrospect,
almost certainly *"`_invoke_tool` returns 'unknown tool: Bash'
instantly; the 5-7s is the qwen3.5:4b response latency on Tyler's
desktop, not subprocess wall time."* Same explanation fits the
time-multiplex option 3a's 208 retries inside one task: the Bash
subprocess never ran, the unload-on-long-Bash heuristic never fired,
the model just kept emitting `tool_use` blocks that bounced off
`_invoke_tool`.

**What inv 004 findings still hold.** The VRAM measurements
(`figures/vram_*.csv` and the v5/v6 figures) were captured running
direct-Bash (no agent loop), so those numbers and the substrate-
contention conclusion are independent of this bug. The patch-trajectory
*tool-call-shape* observations (canonical-Bash share, lowercase-bash
share, `share_finding` hallucination) reflect the model's output shape
when faced with an empty tool list, not the underlying capability. The
v1 patch-ladder chart's verdict labels (e.g. "right first action, 49
retries — Bash returns in ~5s on 84s task") should be re-read as
*"agent emits 49 `tool_use(Bash)` blocks that all bounce off
`_invoke_tool` returning 'unknown tool'"* — patch 4 may actually have
been *more* successful at prompt induction than reported, but we
couldn't tell because no tool ever actually ran.

**Fix landing in inv 005.** Two options:

1. **Caller-side**: import `create_builtin_tools_server` from
   `claude_agent_sdk` instead of `claude_agent_sdk_shim`. The single
   import path keeps the `SdkMcpServer` class identity consistent.
   Already applied in `005-split-host-researcher/scripts/run_smoke.py`.
2. **Upstream**: remove the duplicate `scripts/claude_agent_sdk_shim/`
   package and have it re-export from `shim_pkg/claude_agent_sdk/`, OR
   change `client.py._build_tool_index` to duck-type instead of
   isinstance-check (look for `.tools` and `.name` attributes).

Caller-side fix is in for inv 005. Upstream fix is the right
permanent thing — flagged to inv 003's `001-hardware-derisk` upstream-
patch tracker for inclusion alongside the existing diffs.

#### Bug 2 — `OLLAMA_ANTHROPIC_BASE_URL` captured at import time

`/home/tlifke/inv003_shim/shim_pkg/claude_agent_sdk/client.py` line
21:

```python
DEFAULT_BASE_URL = os.getenv("OLLAMA_ANTHROPIC_BASE_URL", "http://100.97.4.17:11434")
```

This is module-level, evaluated once when `client.py` is first
imported. Setting `OLLAMA_ANTHROPIC_BASE_URL` in `os.environ` *after*
`from claude_agent_sdk import ...` runs has no effect — the agent
silently falls back to the hardcoded desktop URL.

**Observed effect today.** The smoke runner set
`os.environ["OLLAMA_ANTHROPIC_BASE_URL"]` inside `main_sync()`, after
the import chain had already evaluated `DEFAULT_BASE_URL`. The agent
loop's `ClaudeSDKClient` then used the captured default, talked to the
desktop's Ollama (which auto-loaded qwen3.5:4b at 6088 MiB on the
desktop GPU), and our "split-host" run was never actually split-host.
Mac's Ollama log showed zero requests during the run.

**Fix landing in inv 005.** Export `OLLAMA_ANTHROPIC_BASE_URL` in
`run_smoke.sh` *before* invoking the Python entry point. Upstream fix
is to change `DEFAULT_BASE_URL` from a module-level constant to a
function call evaluated per-`ClaudeSDKClient`-instance — also flagged
for inv 001's upstream-patch tracker.

#### Finding 3 — Ollama's qwen3.5 tool renderer is mismatched

After bugs 1 and 2 were fixed and a v5 split-host smoke ran cleanly
(Mac Ollama getting traffic, 8 tools registered in `_tool_index`,
patch-4 hint injected into the system prompt), qwen3.5:4b still
emitted **markdown ```bash code fences** rather than structured
`tool_use` blocks or any of the patterns the shim's
`parser.synthesize_tool_use_blocks` recognizes (`<function_call>`,
`<tool_call>`, fenced JSON).

Cause traced to a known Ollama upstream issue:
[`ollama/ollama#14601`](https://github.com/ollama/ollama/issues/14601),
filed 2026-03-03. Ollama renders Qwen3.5 tool prompts using the
**Qwen3 Hermes JSON renderer** instead of the **Qwen3-Coder XML
renderer** the Qwen3.5 family was actually trained on. The result is
that tool definitions arrive at the model in a format it doesn't
recognize, so it falls back to writing example commands as markdown
inside narration text. Inv 005 confirms the bug also affects the
Anthropic-compat `/v1/messages` path (shared final prompt
construction).

Full details, the workaround (embed tool definitions in the system
prompt as Hermes-style JSON), and references are in
[`../../model-specs/qwen3.5-4b.md`](../../model-specs/qwen3.5-4b.md).

**Why this changes inv 004's read again.** Inv 004's substrate-
contention conclusion was based on the assumption that the model's
patch-trajectory `Tool: Bash` log lines represented structured
`tool_use` blocks being dispatched and failing. We now think most of
those were narration-text matches on the string `Bash` (in markdown
fences), not structured calls. The substrate conclusion may still be
right — vLLM eval needing >12 GiB co-resident is independent
arithmetic — but the *path* by which inv 004 reached it (counting
"Bash fires" per patch) was measuring something else entirely.

**Path forward for inv 005's Q3**: switch to nemotron first (per Q4),
since its native format (OpenAI `tool_calls`) is well-supported by
Ollama's translator. If nemotron emits structured `tool_use` and Bash
subprocess logs appear in `BASH_DEBUG_LOG_DIR`, that's a clean Q3
baseline. The Qwen3.5 path then becomes a separate work item:
implement the system-prompt-embed workaround in the shim's client.py.

#### Finding 4 — Ollama context length and tool-result size

Two related discoveries while running the nemotron smoke:

- **Ollama default context (4096 tokens) is too small for any
  w2s-loop turn.** Even turn 0 (system prompt + tool definitions +
  user kick-off) hit 4,336 tokens. Ollama silently truncates with a
  WARN in the runner log; the API still returns 200 OK so the agent
  sees a malformed response. Verified at 4K (truncates turn 0), 16K
  (turn 0 succeeds, turn 1 truncates), and 64K (both turns succeed in
  inv 005's nemotron smoke). `OLLAMA_CONTEXT_LENGTH=65536` is the
  inv 005 minimum.
- **Bash tool results in this codebase are huge.** A single
  `python -m w2s_research.ideas.vanilla_w2s.run --train-size 64
  --test-size 64 --load-in-4bit` returns ~31,250 chars (~7K tokens)
  of unsloth boilerplate + training progress + vLLM logs. With the
  system prompt + tools + assistant history, turn 1 lands at ~30K
  tokens. By turn 3 we'd be at 50K+.

The right long-term fix is shim-side truncation of `Bash` tool
results (return only the last N lines + `...truncated...`), with the
agent's session log preserving the full output via
`BASH_DEBUG_LOG_DIR`. Tracked separately. For now, 64K context is the
operating floor for any w2s-loop research model.

Both findings are documented in
[`../../model-specs/nemotron-3-nano-4b.md`](../../model-specs/nemotron-3-nano-4b.md).

#### Finding 5 — Nemotron + split-host produces a real end-to-end Bash cycle (but the agent hangs after the result)

The 2026-05-31 nemotron split-host smoke (run dir
`q3_smoke_nemotron-3-nano_4b_p4_20260531_131319`) achieved the
following on a single agent-fired Bash:

- **Q3 behavioral parity at turn 0**: 1 canonical `Tool: Bash`, 0
  lowercase variants, 0 invented names, 0 markdown narration. No
  preamble. Exact match for the predicted Q3 shape, contrasting
  sharply with inv 004's reported numbers (which are now suspected
  to have measured rejected tool_use blocks).
- **Real subprocess**: shim's patched Bash tool ran for 94.56 s,
  exit_code 0. SFT 16 steps completed, LoRA adapter on disk.
  `os.execv` → vLLM eval phase, 64 prompts processed, `eval_output
  .json` with `pred_distribution {1: 59, 0: 5}` on the math dataset.
- **VRAM trace as predicted by inv 004's figures**: idle 537 MiB →
  SFT peak 9.3 GiB → vLLM peak 10.6 GiB. No co-resident researcher
  consuming desktop VRAM; comfortable headroom throughout.

**Then the agent went idle after `_invoke_tool` returned the 31K-char
tool result.** Process state: `S (sleeping)` in `do_epoll_wait`, 0%
CPU, no second POST to Mac in 138+ seconds. Mac Ollama TCP connection
established but Recv-Q=0, Send-Q=0, no new bytes sent. Not a hang
inside the shim's Bash handler (which returned with the result on
disk); not a hang on Mac (which is idle); appears to be an async
client/queue interaction with very large tool results.

**Q1 sharp criterion status**: not yet met (no `evaluate_predictions`
submission against the orchestrator), but every structural piece up
to and including the eval cycle is verified. The remaining gap is a
localized client-side bug, not a substrate/model question.

**Next work**:

1. Debug the agent's post-tool-result async hang. Hypotheses to test:
   (a) anthropic AsyncClient body-serialization issue with very large
   tool_result blocks; (b) queue.put deadlock in the shim's
   `_run_turn`; (c) the upstream agent.py consumer broke silently on
   message_callback or `_format_message`.
2. Implement the shim-side `Bash` tool-result truncation (e.g. last
   2K chars + `...truncated, full log at <path>...`). This both
   removes the hang's trigger and reduces context cost for later
   turns — the model rarely needs unsloth progress bars to decide
   next action.
3. With (1) or (2) in place, complete the Q1 cycle:
   `evaluate_predictions` call → orchestrator accepts integer-list
   submission → session ends with a real result.

#### Finding 6 — Reference-returning Bash patch landed, hang still reproduces (2026-05-31 PM)

Implemented the Anthropic-style "tools return small structured
summaries; full artifacts live on disk" pattern as planned. The shim's
`_make_bash_tool` now returns a body containing exit_code, elapsed,
stdout/stderr byte counts, path to the full log, detected event
markers via regex, and the last 40 lines of stdout — typically ~1,500
chars instead of 31K+. Implementation verified in isolation: markers
detect correctly (`LORA_ADAPTER_WRITTEN`, `EVAL_PREDICTIONS_WRITTEN`,
`VLLM_EVAL_COMPLETE`, etc.); summary length scales as expected.

**The turn-1 hang reproduced with the small-summary payload.** That
falsifies the "tool-result size triggers an anthropic-SDK
serialization issue" hypothesis (finding 5's hypothesis (a)). The
root cause is something else.

#### Finding 7 — Thinking-block handling in shim was incomplete; fixing it did NOT resolve the hang

Captured via `SHIM_DEBUG=1` that nemotron's first response is two
blocks: `thinking` then `tool_use`. The shim's `_run_turn` response
loop had no branch for `btype == "thinking"`, so thinking blocks were
silently dropped from both `blocks_out` (session log) and
`assistant_content_for_history` (what goes into the next POST).
Theory: anthropic SDK 0.78 client-side validates the history shape
and rejects/hangs on tool_use that isn't paired with the preceding
thinking block + signature.

Patched: added a `thinking` branch that captures the block text +
signature into both the session-log Frontier and the history dict.
Added `ThinkingBlock` to `types.py` and re-exported from
`__init__.py`. Patches captured in
[`scripts/upstream_shim_patches/`](scripts/upstream_shim_patches/).

**Hang still reproduces with the thinking-preservation fix landed.**
So the thinking-handling bug was real (and worth fixing on its own
merits — reasoning models lose information without it), but it's not
the trigger for the turn-1 async hang.

Remaining open hypotheses for the turn-1 hang:

- **anthropic SDK 0.78 thinking-feature gating**: the SDK may require
  a specific beta header (e.g. `extended-thinking-2025-XX-XX`) to
  send thinking blocks; without it the SDK silently drops or
  validation-fails. Worth checking the SDK source for `thinking`
  handling on the request side.
- **httpx connection pool semantics**: the first request's response
  may not be fully released, leaving the pool empty when turn 1's
  POST tries to acquire a connection. Worth inspecting via
  `httpx` event hooks or by setting `limits=httpx.Limits(...)`.
- **Ollama Anthropic-compat output shape**: maybe Ollama's thinking
  block omits a field the anthropic SDK depends on at deserialize
  time, leaving the SDK's internal state inconsistent.
- **Shim coercion vs. native protocol** (tracked separately):
  Tyler's question of whether the whole shim approach is the
  problem. The Anthropic Messages API is rich (signatures, betas,
  rich content blocks) and Ollama's Anthropic-compat layer is newer
  than its OpenAI-compat layer. A shim that talks OpenAI-compat to
  Ollama and presents Anthropic-shape upstream might dodge an entire
  class of these bugs. Worth scoping as inv 006 candidate before any
  reliable 24-hour run.

**Q1 sharp criterion status**: still not met. We have a clean
end-to-end turn-0 → real Bash subprocess → real eval_output.json
on disk, captured ground-truth. We don't have the agent's
`evaluate_predictions` submission because the agent hangs after the
Bash tool result returns.

**Files committed for this iteration**:

- `scripts/upstream_shim_patches/builtins_summary.diff` — reference-
  returning Bash tool
- `scripts/upstream_shim_patches/client_thinking.diff` — thinking
  block branch in response handler
- `scripts/upstream_shim_patches/types_thinking.diff` —
  `ThinkingBlock` added
- `scripts/upstream_shim_patches/init_thinking.diff` — re-export
- `handoff-artifact-design.md` — proposed context-reset / handoff
  pattern, to be tried after the hang is unblocked

The per-model specs at
[`../../model-specs/`](../../model-specs/) document both models'
conventions and quirks so the next investigation doesn't pay this
diagnostic cost again.

#### Bug 4 — debug instrumentation for future agent-loop runs

The shim's `_make_bash_tool` handler was patched (in both shim_pkg/
and scripts/ copies) to write subprocess `stdout`/`stderr`/`exit_code`/
`elapsed` to `${BASH_DEBUG_LOG_DIR}/bash_NNNN.log` when the env var is
set. No-op when unset. Strictly additive — does not change handler
return shape. The inv 005 `run_smoke.sh` plumbs the log dir into
`bash_env` so every agent-fired Bash subprocess in this investigation
leaves a ground-truth log alongside the session transcript.

This instrumentation was added because the inv 004 session logs only
contained the model's `tool_use` blocks (`AssistantMessage`), not the
`tool_result` content (`UserMessage`). Without it, we'd be guessing at
what the subprocess actually did — exactly the gap that hid bug 1.

### Q1 — Substrate sharp criterion

_To be populated once bugs 1 and 2 are fixed and we have one clean
end-to-end run on the split-host substrate._

## Decisions

_Populate as work proceeds. Format:_

> **Decision N — short title** (date)
> What was chosen, alternatives considered, why this won.

## Results

_To be populated._

## Forward-looking

_To be populated._

## Things to flag

- The MacBook benches captured 2026-05-31 used a generic reasoning
  prompt, not the actual w2s system prompt + tool definitions. Real
  tool-call latency under the inv 4a env may differ. Q2's first
  measurement should re-validate the tok/s numbers under a real
  agent-loop step.
- Tailscale latency between Mac and desktop was not measured under
  load. If the agent loop becomes latency-bound rather than
  generation-bound, that's a Q2 finding worth surfacing.
- Mac-side Ollama must listen on the Tailscale interface (not just
  `127.0.0.1`). Homebrew's default is loopback-only; the launchd
  plist needs `OLLAMA_HOST=0.0.0.0:11434` (or the Tailscale IP
  directly) to be reachable from the desktop. Mirrors the override
  pattern already used on the desktop side.
- Researcher-side latency under the real agent loop (with the full
  inv 4a system prompt + tool definitions, not the generic bench
  prompt used 2026-05-31) is not yet known. Q2's first measurement
  re-validates the ~12-17 tok/s benches under realistic conditions.
- Tailscale latency between Mac and desktop has not been measured
  under load. If the agent loop becomes latency-bound rather than
  generation-bound, that's a Q2 finding worth surfacing.
- Lid-close / Mac-sleep mid-run: a small retry-on-connection-failure
  policy in the agent loop is probably needed to make this topology
  human-friendly. Not yet implemented.

## Limitations

- Single hardware pair (M2 MacBook Air + RTX 3080 desktop). Findings
  do not directly generalize to other split-host topologies.
- Two researcher models (qwen3.5:4b, nemotron-3-nano:4b). The 8B/9B
  options from inv 003 are not in scope.
- Smoke-sized and one production-sized configuration. Multi-iteration
  convergence behavior is inv 006+ territory.
