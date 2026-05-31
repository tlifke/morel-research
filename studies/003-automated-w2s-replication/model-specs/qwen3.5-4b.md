# qwen3.5:4b (Ollama tag)

## Identity

- **Ollama tag**: `qwen3.5:4b`
- **HF underlying**: part of the Qwen3.5 series released by Alibaba in
  early 2026. The Small series is 0.8B, 2B, 4B, 9B; the 4B is the one
  Ollama serves here.
- **Architecture**: dense transformer, multimodal hybrid reasoning
  ("thinking" + "non-thinking" modes).
- **Capabilities** (Ollama reports): `completion`, `vision`, `tools`,
  `thinking`.
- **Context**: 256K tokens per the family announcement; Ollama
  registers the loaded runner at 4096 KV by default unless overridden
  (verified 2026-05-31).
- **Quantization on disk**: Q4_K_M.
- **VRAM resident**: ~5.4–5.7 GiB at runtime with 4K KV cache.

## Ollama state (verified 2026-05-31 against this machine)

```
template:   {{ .Prompt }}     # pass-through, no chat template applied at modelfile layer
system:     (none)
parameters:
  top_k             20
  top_p             0.95
  presence_penalty  1.5
  temperature       1
```

`{{ .Prompt }}` means the Ollama Modelfile does **not** wrap the
incoming prompt in any chat template. Whichever endpoint serves the
request (`/api/chat`, `/api/generate`, `/v1/chat/completions`,
`/v1/messages`) is responsible for constructing the model-native prompt
before calling the runner.

## Tool-calling format the model was trained on

**Qwen3-Coder XML format**, the same format the Qwen3-Coder family was
trained on. Tool calls are emitted as:

```
<tool_call>
{"name": "tool_name", "arguments": {"arg1": "value1"}}
</tool_call>
```

Tool definitions in the prompt are also expected in JSON, embedded into
the system message in Hermes style (the Qwen3-family convention).

Qwen3 (the prior generation) used the Hermes JSON wire format, also
with `<tool_call>` tags but a slightly different definition shape in
the system prompt. **Qwen3.5 inherited the tag wrapper but the
definition shape changed to the Qwen3-Coder XML variant.**

## How Ollama renders tools (and the bug)

**Ollama as of mid-2026 renders Qwen3.5 tool prompts using the Qwen3
Hermes JSON renderer, not the Qwen3-Coder XML renderer the model was
trained on.** This is a known issue tracked in `ollama/ollama#14601`
("Qwen3 tool calling via /api/chat tools parameter: malformed tool
definitions"), reported 2026-03-03; the bug was found to also affect
the Anthropic-compat `/v1/messages` endpoint by extension since the
final prompt construction is shared.

Symptoms reported (and seen here in inv 005's first split-host smoke,
log `q3_smoke_qwen3.5_4b_p4_20260531_123958`):

- Tool definitions arrive at the model malformed (Go struct repr leaks
  into the JSON in some paths).
- The model emits **markdown ```bash fences** instead of `<tool_call>`
  tags because it doesn't recognize the tool definitions in the prompt.
- The shim's `parser.synthesize_tool_use_blocks` does not synthesize
  from markdown bash, so the harness gets zero executable tool calls.

## Workaround

The accepted community workaround (per the GitHub issue and
LangChain forum threads): **bypass the `tools` parameter and embed
tool definitions directly in the system prompt as JSON strings in the
Hermes-style wrapper Qwen3 expects**. The model will then emit
`<tool_call>{...}</tool_call>` tags — which the shim's parser already
synthesizes (`_TOOL_CALL_TAG_RE` at `shim_pkg/claude_agent_sdk/
parser.py:11`).

Concretely, the agent prompt should include something like:

```
# Tools

You have access to the following functions. Use them by emitting
<tool_call>{"name": ..., "arguments": ...}</tool_call> on its own line.

<tools>
{"type": "function", "function": {"name": "Bash", "description": "...",
 "parameters": {"type": "object", "properties": { ... }}}}
{"type": "function", "function": {"name": "Read", ...}}
...
</tools>
```

Tooling-side this means **stop passing the Anthropic `tools` array
through to Ollama for Qwen3.5; serialize it into the system prompt
text instead**. The shim's `_anthropic_tools` array would be moved
from the `tools` API field into the `system` field as JSON text.

## Sampling recommendations

**Authors' defaults (Ollama modelfile)**: `temp=1, top_p=0.95, top_k=20,
presence_penalty=1.5`. Note the unusually high presence_penalty — this
appears to be a Qwen3.5-specific tuning to reduce repetition under the
thinking-mode hybrid generation.

**Study 003 default**: keep the authors' defaults until we have
evidence to change them. (Inv 004's `temp=1.0 + top_p=0.95` memory was
specifically for the *judge* model, not necessarily the researcher;
the modelfile defaults already include that pair.)

## Known issues

- **Tool renderer mismatch** — `ollama/ollama#14601`, fix in progress
  via PR `#14695` as of 2026-03. Re-check on every Ollama upgrade.
- **`/think` and `/no_think` instruction leaks** — Ollama appends
  thinking-mode toggle text into prompts in some paths; can leak into
  later conversation history. Custom modelfile can strip.
- **Prior tool-call history stripped** — Ollama strips prior assistant
  tool calls from history before sending to the model; the model sees
  only the tool *results* but not its own prior *invocations*. This
  breaks multi-turn reasoning that depends on seeing what you tried.

## What we've observed in this study

- **Inv 003 gate-5 single PASS** (claimed 58 canonical Bash calls under
  the gate-5 `tool_invocation_hint` patch): retroactively suspect.
  Under the SdkMcpServer identity bug present at that time, those
  "Bash calls" were `tool_use` blocks that bounced off `_invoke_tool`
  with `"unknown tool: Bash"`. Whether the model was actually emitting
  structured `tool_use` or text-mode that got matched on the literal
  string `Bash` is unknown without re-running.
- **Inv 004 patches 1–4**: same retroactive caveat. Tool-call counts
  in the v1 patch-ladder figure measure intent, not execution.
- **Inv 005 first split-host smoke** (2026-05-31, run dir
  `q3_smoke_qwen3.5_4b_p4_20260531_123958`): with the identity bug
  fixed, the model emits markdown ```bash and zero `<tool_call>`
  tags. The renderer mismatch documented above is the most likely
  cause.

## References

- [Qwen Function Calling docs](https://qwen.readthedocs.io/en/latest/framework/function_call.html)
  — Hermes-style framing, sampling recommendations.
- [Function Calling and Tool Use — QwenLM/Qwen3 DeepWiki](https://deepwiki.com/QwenLM/Qwen3/4.3-function-calling-and-tool-use)
- [ollama/ollama#14601 — Qwen3 tool calling malformed JSON](https://github.com/ollama/ollama/issues/14601)
- [Qwen3.5 — How to Run Locally (Unsloth)](https://unsloth.ai/docs/models/qwen3.5)
- [vLLM Tool Calling docs](https://docs.vllm.ai/en/latest/features/tool_calling/) — `--tool-call-parser hermes` for the Qwen Hermes path.

## TODO before relying on this model

- [ ] Verify the renderer mismatch hypothesis directly by capturing
  the exact prompt Ollama constructs for a tool-using request (e.g.
  via the Ollama `OLLAMA_DEBUG=1` env var or a wireshark trace) and
  comparing against the Qwen3.5 official template in `tokenizer_config.json`.
- [ ] If confirmed, implement the system-prompt-embedding workaround
  in the shim's client.py: when model family is `qwen35`, serialize
  `_anthropic_tools` into the system prompt instead of passing via
  the API tools array.
- [ ] Re-run inv 005's Q3 behavioral parity smoke under the workaround.
