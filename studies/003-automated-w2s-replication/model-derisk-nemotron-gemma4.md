# Model derisk — Nemotron 3 Nano 4B + Gemma 4 E4B

Gate-1/2/3 derisk for two candidate weak-researcher models, sibling to 4a. Live
verification against the desktop RTX 3080 via Ollama Anthropic-compat endpoint,
through the existing `claude_agent_sdk_shim` (no shim modifications).

Date of run: 2026-05-25. Shim commit: state of
`studies/003-automated-w2s-replication/investigations/003-claude-sdk-shim-and-researcher-swap/scripts/claude_agent_sdk_shim/`
at branch tip.

## Verdict per model

| Model | Ollama tag | On-disk | Gate 1 (pull) | Gate 2 (hello) | Gate 3 (add tool) | Native shape |
|---|---|---|---|---|---|---|
| **Nemotron 3 Nano 4B** | `nemotron-3-nano:4b` | 2.8 GB | PASS (2m42s pull) | PASS (~15s incl. 14s cold load; 162 eval tokens) | **PASS** (1.51s, native `tool_use`, correct args, correct final answer "8") | Native Anthropic `tool_use` block; reasoning content in a separate `thinking` field on the raw Ollama API (does not leak into final text) |
| **Gemma 4 E4B** | `gemma4:e4b` | 9.6 GB | PASS (10m04s pull) | PASS (~26s incl. 25.6s cold load; 9 eval tokens) | **PASS** (1.85s, native `tool_use`, correct args, correct final answer "8") | Native Anthropic `tool_use` block; emits an explicit `thinking` block in the response content array which the shim currently ignores |

Both pass all three gates on first attempt with the unmodified shim. No Path A
parser invocation was necessary; in both cases Ollama emitted Anthropic-shaped
`tool_use` blocks directly.

Cross-reference: `qwen3.5:4b`, the current 4a default, is 3.4 GB on disk and
clears gate 3 in similar wall time. Nemotron is *smaller* on disk than the
current default; Gemma4 E4B is ~3x larger — material for memory pressure.

## What each model emits

### Nemotron 3 Nano 4B

Raw Ollama `/api/chat` response (Gate 2, lightly elided):

```
"message": {
  "role": "assistant",
  "content": "Hello friends, how are you?",
  "thinking": "We need to respond with hello in 5 words: ... Count: Hello(1) friends,(2) how(3) are(4) you?(5)"
}
```

Reasoning is in a sidecar `thinking` string, not the main `content`. Through the
Anthropic-compat layer in our gate 3, the shim's `SHIM_DEBUG` log showed exactly
one `tool_use` block and no `thinking` block surfaced — Ollama appears to drop or
collapse the thinking sidecar into the Anthropic translation for this model.
Final-turn text was clean ("The result of 5 + 3 is 8.") with no narration of the
tool call.

### Gemma 4 E4B

Through the Anthropic-compat layer, the gate-3 first turn produced **two**
content blocks: a `thinking` block followed by a `tool_use` block. Excerpt from
the thinking block (≤200 chars shown by SHIM_DEBUG):

```
"The user wants to compute 5 + 3 using the available `add` tool.
The `add` tool requires two integer arguments, `a` and `b`.
I need to call the function with `a=5` and `b=3`.

Plan:
1. Call the `add` t..."
```

Then a clean `tool_use` block with `{a:5,b:3}`. Stop reason `tool_use`. Second
turn: single text block "The result is 8.", stop reason `end_turn`. No
`<|tool_call|>` token text was observed at the Anthropic-compat surface — Ollama
translates the special-token protocol into native `tool_use` for us.

## Shim changes needed

### Nemotron 3 Nano 4B — none required

Gate 3 passed unmodified. The Mamba-2-hybrid architecture does not leak through
the API surface; from the shim's perspective Nemotron behaves identically to
Qwen 3.5 4B. No Path A patterns needed, no system-prompt patching change, no
MCP layer change.

Watch-items (not gating, but worth confirming in 4b-style follow-on):

- **Multi-turn with thinking sidecar.** Ollama may or may not preserve the
  `thinking` sidecar in the assistant message we feed back as history. If it
  requires the field to be echoed, multi-turn tool loops could degrade. The
  shim currently rebuilds assistant history as plain `text`/`tool_use` blocks
  and discards anything else. This is the same risk profile as qwen3.5 with its
  `<think>` blocks (no observed problem there). Probable cost: zero. Risk if
  hit: small — add a `thinking` passthrough in `_run_turn`'s history rebuild.
- **Tool-name pinning.** Not tested here; 4a/4b's findings on tool-name drift
  may or may not generalize. Nemotron's stated tool-use focus suggests it will
  be at least as good as Qwen 3.5 4B with the `tool_invocation_hint` patch.

### Gemma 4 E4B — modest, one likely-needed change

Gate 3 passed unmodified, but the model emits **explicit `thinking` blocks** in
the response content array. Currently `client.py` only branches on `text` and
`tool_use` block types (parser.py lines 111-143); `thinking` blocks are
silently discarded and not appended to `assistant_content_for_history`.

For single-turn-then-tool flows like gate 3, this is fine — the tool_use block
still fires. **For multi-turn flows where the assistant needs its own prior
thinking re-supplied (some Anthropic-shaped backends require this), gemma4 will
likely break on the second-or-later turn.** Concrete diff-in-prose for
`client.py::_run_turn` block-loop:

1. Add an `elif btype == "thinking"` branch alongside `text`/`tool_use`. Decide
   one of: (a) pass-through as a `ThinkingBlock` analogue and append to history
   verbatim; (b) drop from surfaced content but preserve in history; (c) drop
   entirely and rely on the model regenerating chain-of-thought. Anthropic
   semantics suggest (a); current shim de facto does (c).
2. If gemma4's protocol requires `signature` / `cache_control` style metadata
   on thinking blocks (Anthropic Claude does for extended thinking), the shim
   may need to forward those — verify by inspecting the raw Anthropic-compat
   response from Ollama (`SHIM_DEBUG` only shows preview text). Not gating for
   gate-3 single-turn; gating for gate-5 (full automated-w2s loop).
3. The `<|tool_call|>` token protocol described in Gemma 4's docs is **not
   visible at the Anthropic-compat surface** — Ollama translates it. Therefore
   no `tool_invocation_hint` reshape and no new Path A pattern is needed at
   the shim level. (If we ever drop the Anthropic-compat wrapper and talk
   `/api/chat` directly with `tools=[]`, the token protocol re-emerges and
   Path A would need a `<|tool_call|>...<|tool_call_end|>` family.)

No MCP-builtin layer changes needed for either model. The MCP layer is
schema-driven and both models honor the schemas as observed.

### New failure modes not caught by gates 1-3

- Cold load times: Nemotron 14s, Gemma4 26s. For full-loop runs these are
  one-shot, but warmup-blind concurrency or premature unload could re-cost
  these. Gate 5 wall-time budgets should add ~30s headroom per cold spin-up.
- Gemma4 E4B's 9.6 GB on-disk is meaningful on a 12 GB card once KV cache is
  factored in. Gate 5 should re-verify the model stays loaded under long
  contexts; we may need to drop to `e4b` quant beyond `latest` or accept
  context-length caps. Nemotron at 2.8 GB has no such pressure.
- Tool-call *quality* under longer multi-turn agentic prompts (the actual 4a
  failure mode for qwen3:4b) is not tested by gate 3's add(5,3) probe.
  Whatever 4b discovers about tool-name pinning likely needs to be re-checked
  for each model individually.

## Recommendation

**Nemotron 3 Nano 4B is meaningfully closer to drop-in.** Gate 3 passed with
zero shim changes, the model is *smaller* than the current Qwen 3.5 4B default,
and NVIDIA's tool-use framing held up on the smoke. The shim work to support
it is **trivial** (zero changes needed for the gates we ran; one optional
defensive change for `thinking` sidecar passthrough in multi-turn).

Gemma 4 E4B's shim-change effort is **modest**. The only material change is
handling the explicit `thinking` blocks in the response content array — one
new branch in `client.py::_run_turn` (and a corresponding history-rebuild
update). The `<|tool_call|>` special-token protocol that the landscape doc
flagged as needing a different `tool_invocation_hint` shape **is invisible at
the Anthropic-compat layer** — Ollama handles the translation, so the patched
hint stays the same. The on-disk footprint (9.6 GB) is the bigger cost than
the shim work.

Order of preference for an alternative-to-Qwen run:

1. Nemotron 3 Nano 4B — different architecture (Mamba-2 hybrid), smaller
   memory footprint, native tool calling clean through our shim. Best
   architectural-diversity datapoint of the three.
2. Gemma 4 E4B — works, costs one small shim patch + more VRAM, gives a
   Google-lineage datapoint distinct from Alibaba/NVIDIA.
3. Stay on Qwen 3.5 4B (status quo).

## Things I made up that you should review

- "Ollama appears to drop or collapse the thinking sidecar into the Anthropic
  translation for Nemotron" is inferred from one SHIM_DEBUG run showing no
  `thinking` block surfaced. Could also be that Nemotron didn't emit one on
  that particular prompt. Worth a second probe with a harder reasoning task.
- The "drop-in" claim for Nemotron is single-task gate-3 evidence only. The
  tool-name-drift failure modes from 4a may or may not generalize; could be
  better or worse than Qwen.
- Gemma4 E4B's 9.6 GB size on disk is from `ollama list` — I haven't verified
  what quant level Ollama is serving by default for the `e4b` tag. The MLX
  variants in the registry suggest different quants exist; if VRAM pressure
  hits, switching tag is the first lever.
- Whether Ollama's Anthropic-compat layer requires `thinking` blocks to be
  echoed in history for gemma4 multi-turn is *untested* — flagged as a likely
  failure mode, not a confirmed one.
