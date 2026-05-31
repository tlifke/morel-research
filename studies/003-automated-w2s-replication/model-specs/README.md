# Model specs

Per-model documentation for the local Ollama models used as researchers
in study 003. Each spec captures **how the model wants prompts and tools
specified**, so we don't keep guessing across investigations.

These are living documents — update them whenever a new investigation
discovers something material about a model's behavior, format, or
quirks.

## Files

- [qwen3.5-4b.md](qwen3.5-4b.md) — Qwen3.5 4B Instruct, served via Ollama
- [nemotron-3-nano-4b.md](nemotron-3-nano-4b.md) — NVIDIA Nemotron 3
  Nano 4B, served via Ollama

## What every spec should answer

1. **Identity** — what model is this *really*? (HF model card; underlying
   architecture; training cutoff.)
2. **Ollama state** — modelfile template, system prompt, sampling
   parameters as Ollama reports them today.
3. **Tool-calling format the model was trained on** — XML tags
   (`<tool_call>...</tool_call>`)? JSON in fences? OpenAI-style? Custom?
4. **How Ollama renders tools** — and whether that matches (3). If it
   doesn't, the workaround.
5. **Sampling recommendations** — author defaults + study-003 chosen
   defaults if they differ, with rationale.
6. **Known issues** — Ollama-specific bugs, broken renderers, version
   gates.
7. **What we've observed** — directly observed behavior in this study's
   investigations, with run references.
8. **References** — links to model card, function-calling docs, Ollama
   bugs, and any other ground truth we should re-verify.

## Why this exists

Inv 005's first split-host smoke ran a fully-fixed harness against
qwen3.5:4b and got zero tool executions because Ollama's tool-template
renderer for qwen3.5 mismatches what the model was actually trained on.
The behavior was invisible at the agent-loop level and could only be
diagnosed by reading the Ollama docs + GitHub issues. That cost real
hours. Documenting per-model conventions up front means the next
investigation doesn't pay that cost again.
