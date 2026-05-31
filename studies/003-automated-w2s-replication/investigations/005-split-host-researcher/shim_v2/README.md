# Shim v2 — OpenAI-compat wire, Anthropic-shape facade

Design doc for the v2 replacement of the inv 003/004/005 Claude-shim.

The v1 shim coerces Ollama into the Anthropic Messages API surface (via
Ollama's `/v1/messages` Anthropic-compat layer). Inv 005 findings 5–7 show
that path is structurally costly: every model bug we hit was a translation
fault between the Anthropic-shape request and the model's native tool format,
mediated by Ollama's less-tested Anthropic-compat translator. We replaced
about a week of investigation cycles chasing translator quirks (Hermes vs
XML for Qwen3.5; thinking-block signature pairing; client-side hang after
large tool_result).

The v2 design talks **OpenAI-compat (`/v1/chat/completions`)** to Ollama
while preserving the **Anthropic-shape facade upstream** so `agent.py` and
`AutonomousAgentLoop` are unchanged.

## Goals

- Reduce the translation surface by talking to Ollama on its better-trodden
  endpoint. Nemotron-3 is natively OpenAI-shape; the Anthropic-compat layer
  was doing an extra round trip we did not need.
- Eliminate the anthropic SDK from the request path entirely (the inv 005
  finding 7 hang correlates with anthropic SDK 0.78 client-side state under
  thinking blocks). Talk to Ollama with raw `httpx`.
- Keep the upstream API surface identical so `agent.py` imports (
  `ClaudeAgentOptions`, `ClaudeSDKClient`, `AssistantMessage`,
  `ResultMessage`, `TextBlock`, `ThinkingBlock`, `ToolUseBlock`) and the
  `async with`/`query`/`receive_response` shape do not change.
- Make per-model adapters a small, explicit registry rather than implicit
  behavior of Ollama's renderer.

## Non-goals

- Not a general Anthropic SDK reimplementation. Only the subset
  `AutonomousAgentLoop` consumes is in scope.
- Not a streaming implementation. Non-streaming `chat/completions` is
  sufficient for the research loop and removes a large failure surface.
- Not multi-provider. OpenAI-compat-to-Ollama only. Adding real Anthropic or
  OpenAI later is a follow-on.
- Not a fix for vLLM-side issues, prior-work tools, or `findings.json`
  semantics. Those are upstream concerns.

## Wire format choice: OpenAI-compat

`POST /v1/chat/completions` against Ollama. Why:

- Ollama's OpenAI-compat layer predates the Anthropic-compat layer and is
  the one most upstream Ollama users hit; it has more bug-fix mileage.
- Nemotron-3 Nano is natively trained on OpenAI `tool_calls`. The
  translation through Anthropic-compat was identity-ish but added a layer.
- Qwen3.5's renderer bug (`ollama/ollama#14601`) affects the shared final
  prompt construction; the workaround (embed Hermes-style tool defs in the
  system prompt) is straightforward in an OpenAI-compat client because we
  can simply not pass `tools` and instead include them as system text. We
  do not need the Anthropic-compat path to do this for us.
- The OpenAI shape lacks a few Anthropic features we depend on lightly
  (`thinking` blocks with signatures, `cache_control`, `betas`). The
  facade absorbs that asymmetry: see "Features dropped" below.

## Upstream API surface: Anthropic-shape facade

The upstream consumer (`w2s_research/research_loop/agent.py`) imports these
names from `claude_agent_sdk`:

```python
from claude_agent_sdk import (
    ClaudeSDKClient, ClaudeAgentOptions,
    AssistantMessage, ResultMessage,
    TextBlock, ThinkingBlock, ToolUseBlock,
)
```

It uses them in this shape:

```python
options = ClaudeAgentOptions(
    allowed_tools=[...], system_prompt=..., model=..., mcp_servers={...},
    permission_mode="bypassPermissions", cwd=..., setting_sources=["project"],
    betas=["context-1m-2025-08-07"],
)
async with ClaudeSDKClient(options=options) as client:
    await client.query(task)
    async for message in client.receive_response():
        # AssistantMessage with .content of TextBlock | ThinkingBlock | ToolUseBlock
        # ResultMessage with .stop_reason / .result
        ...
```

v2 preserves all of this. `ClaudeAgentOptions` keeps the same fields (some
become no-ops: `permission_mode`, `setting_sources`, `betas`, `cli_path`).
`ClaudeSDKClient.__aenter__/__aexit__`, `.query`, `.receive_response`, and
the message dataclasses are unchanged. The internal turn loop, request
construction, and history bookkeeping are all rewritten.

## Per-model adapters

Each adapter is a tiny object with two responsibilities: (a) shape the
outgoing request (system prompt, tool definitions, parameters); (b) parse
the incoming response into Anthropic-shape content blocks.

Adapter list, kept deliberately small:

| Adapter             | When picked                   | Tools delivered via       | Tool calls parsed from                          |
|---------------------|-------------------------------|---------------------------|-------------------------------------------------|
| `OpenAINative`      | `nemotron-3-nano:4b` (default) | `tools` param             | OpenAI `message.tool_calls`                     |
| `Qwen35HermesEmbed` | `qwen3.5:4b`                  | system-prompt JSON block  | `<tool_call>{...}</tool_call>` regex in content |
| `Generic`           | anything else                 | `tools` param             | `message.tool_calls`, falls back to regex       |

`Qwen35HermesEmbed` is the workaround for `ollama/ollama#14601`. Adapter
selection is by `options.model` prefix match in a registry; unknown models
fall back to `Generic`.

## Features dropped

- **Extended thinking signatures across turns.** Anthropic's `thinking`
  blocks carry signed `signature` fields that the SDK uses to validate
  multi-turn reasoning consistency. OpenAI-compat has no equivalent. v2
  preserves thinking *text* in `ThinkingBlock` for logging, but does not
  round-trip a signature in history. Acceptable because Ollama's
  Anthropic-compat layer did not provide a real signature anyway (inv 005
  finding 7), and the consumer (`agent.py._format_message`) only reads
  `.thinking`/`.text` for logging.
- **`betas` and `cache_control`.** No-ops. The research loop does not depend
  on either; the option is accepted and ignored.
- **`permission_mode`, `setting_sources`, `cli_path`.** No-ops.
- **Streaming.** Single non-streaming POST per turn. Iteration latency in
  this study is dominated by Bash subprocesses (~94 s SFT), not researcher
  generation (~10–20 s).
- **`tool_choice="auto"` enforcement.** Default behavior of OpenAI-compat
  endpoints is already "auto"; we pass it explicitly.

## Testing plan

### Unit (CI-able, in this prototype)

`prototype/test_conversion.py` covers:

1. `_anthropic_tools_to_openai_tools` — input_schema preserved verbatim as
   `function.parameters`; no semantic loss; `tool_choice` passed through.
2. `_openai_response_to_anthropic_blocks` — three cases: text only,
   tool_calls only, mixed content + tool_calls. Verifies block ordering,
   `ToolUseBlock.input` is a parsed dict (not the JSON string), and IDs are
   propagated.
3. `_make_tool_result_payload` — Anthropic tool_result block → OpenAI
   `{role: "tool", tool_call_id, content}` message; multi-block content
   collapses to a string deterministically.
4. Adapter selection — `nemotron-3-nano:4b` picks OpenAI-native;
   `qwen3.5:4b` picks Hermes-embed; unknown picks Generic.

Run with `uv run pytest prototype/test_conversion.py`.

### Smoke (sharp criterion)

**A 4-iteration nemotron smoke against the inv 005 split-host substrate
produces 4 valid `evaluate_predictions` submissions accepted by the
orchestrator.** This is sharper than inv 005 Q1's "one submission" because
it tests both (a) the v1 turn-1 hang is gone and (b) the loop is stable
across multiple Bash + eval cycles. Anything less than 4 is a failure mode
worth diagnosing; 4 closes Q1 and unblocks Q2.

Smoke harness lives outside this prototype (in the inv 005 scripts dir) and
is not run from this skill scope per the task constraints.
