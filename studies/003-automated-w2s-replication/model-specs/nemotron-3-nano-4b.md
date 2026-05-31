# nemotron-3-nano:4b (Ollama tag)

## Identity

- **Ollama tag**: `nemotron-3-nano:4b`
- **HF underlying**: [`nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF`](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF)
- **Architecture**: Mamba-2 and MLP hybrid with 4 attention layers
  (Nemotron-H family — NVIDIA's hybrid SSM design).
- **Parameters**: 3.97B.
- **Context**: up to 262K tokens per the model card; runner registers
  4096 KV by default in Ollama unless overridden.
- **Quantization on disk**: Q4_K_M, ~2.84 GB.
- **VRAM resident**: ~4.86 GiB on a 3080 with default settings, ~5.25
  GiB on M2 (verified 2026-05-31). Higher than the on-disk size because
  Ollama allocates KV cache + activation buffers.
- **Capabilities** (Ollama reports): `completion`, `tools`, `thinking`.

## Ollama state (verified 2026-05-31 against this machine)

```
template:   {{ .Prompt }}     # pass-through, no chat template at modelfile layer
system:     (none)
parameters:
  temperature  1
  top_p        1
```

Same pass-through template as qwen3.5. Endpoint-specific layers
(`/api/chat`, `/v1/messages`, etc.) construct the model-native prompt
before invoking the runner.

## Tool-calling format the model was trained on

**OpenAI-convention JSON tool calls**. Per NVIDIA's NIM docs the model
expects/emits the standard OpenAI `tool_calls` structure:

```json
{
  "tool_calls": [{
    "id": "call_id_here",
    "type": "function",
    "function": {
      "name": "tool_name",
      "arguments": "{\"arg1\": \"value1\"}"
    }
  }]
}
```

Tool definitions in the system prompt match the OpenAI tools array
shape:

```json
{
  "type": "function",
  "function": {
    "name": "...",
    "description": "...",
    "parameters": {"type": "object", "properties": {...}}
  }
}
```

`tool_choice` is supported (`auto` or `none`).

## How Ollama renders tools

Ollama's Anthropic-compat `/v1/messages` layer translates Anthropic
input_schemas → Ollama Parameters (JSON Schema), and `tool_use` blocks
from the model → internal `api.ToolCall` entities. For Nemotron 3,
which natively emits OpenAI-style `tool_calls`, this translation path
is the same one OpenAI-compat uses — generally well-tested.

**No documented Ollama renderer bug specific to Nemotron 3 Nano 4B** as
of 2026-05-31. The bug tracker
([discussion #3 on the 30B-A3B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B-BF16/discussions/3))
notes "tool calling with reasoning parsing broken" for the larger MoE
variant, but that's a vLLM reasoning-parser issue, not an Ollama tool
renderer issue, and it affects a different SKU.

**However**: an n8n community thread reports
`nvidia/llama-3.1-nemotron-nano-4b-v1.1` tool-calling problems with
some clients. That's the *older* Llama-3.1-based Nemotron Nano, not
the Nemotron-3 (Nemotron-H) generation we're using. Separate model;
separate behavior.

## Sampling recommendations

**Authors' Ollama defaults**: `temp=1, top_p=1`. The Nemotron-3 paper
doesn't pin specific decoding params for tool use; NVIDIA NIM docs
treat tool calling as deterministic-ish via `tool_choice` semantics
rather than via sampling.

**Reasoning toggle**: the model's reasoning capability is controllable
via system prompt (e.g. instructing it to skip the `<think>` trace).
"Disable Reasoning" returns final answers without intermediate
reasoning at a slight accuracy cost — relevant if we want tool calls
on the first turn for latency-sensitive cycles, since the reasoning
trace adds 100s-1000s of tokens.

**Study 003 default**: until we test more, keep `temp=1, top_p=1`
(modelfile defaults) and let the model use its reasoning mode unless
that creates latency problems in inv 005's Q2.

## Known issues

- **n8n thread on the prior-generation `llama-3.1-nemotron-nano-4b`**:
  not our model, but flag here in case the symptom looks similar in
  inv 005.
- **30B MoE variant's vLLM reasoning-parser bug**: not relevant for the
  4B SSM-hybrid; flagged here for completeness.

## What we've observed in this study

- **Inv 004 nemotron drop-in** (per inv 004's results section):
  prompt-fit was "fine" — canonical training command fired immediately
  on first action with no preamble. **Caveat under inv 005's
  retroactive read**: same SdkMcpServer identity bug present; those
  "Bash calls" may have been intent that bounced off `_invoke_tool`,
  not real subprocess runs.
- **Inv 005**: not yet tested with the harness fixes applied. Up next
  per the inv 005 Q4 plan.

## Why nemotron may behave better than qwen3.5 in this harness

The Ollama Anthropic-compat layer's translation path is:
`Anthropic tool_use ↔ internal api.ToolCall ↔ model-native format`.
For Nemotron-3 the model-native format is OpenAI `tool_calls`, which
shares the same JSON-as-arguments shape as Anthropic's `tool_use.input`
— translation is essentially identity. For Qwen3.5 the model-native
format is the Qwen3-Coder XML tag wrapper, which Ollama allegedly
renders incorrectly (see qwen3.5-4b.md).

So **nemotron is the lower-risk researcher choice on this harness
until the Qwen3.5 renderer bug is fixed upstream or worked around in
the shim**.

## References

- [Nemotron-3-Nano-4B-GGUF on Hugging Face](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF)
- [NVIDIA NIM Function (Tool) Calling docs](https://docs.nvidia.com/nim/large-language-models/latest/function-calling.html)
- [NVIDIA Nemotron 3 — How To Run Guide (Unsloth)](https://unsloth.ai/docs/models/nemotron-3)
- [Inside NVIDIA Nemotron 3 — NVIDIA Tech Blog](https://developer.nvidia.com/blog/inside-nvidia-nemotron-3-techniques-tools-and-data-that-make-it-efficient-and-accurate/)
- [Nemotron 3 Nano Technical Report (PDF)](https://research.nvidia.com/labs/nemotron/files/NVIDIA-Nemotron-3-Nano-Technical-Report.pdf)

## TODO before relying on this model

- [ ] Run the inv 005 Q3/Q4 smoke against nemotron-3-nano:4b under the
  fixed harness. If structured `tool_use` blocks fire and Bash
  subprocess logs land in `BASH_DEBUG_LOG_DIR`, that's our baseline.
- [ ] Verify the reasoning trace doesn't eat the 4K context window in
  long sessions. If yes, consider a "skip reasoning" system prompt
  per the model card guidance.
- [ ] Compare wall-clock per iteration vs qwen3.5:4b on the same
  hardware so Q2's speed-cost measurement has both data points.
