# Calibration cost estimate — Gemma 3 4B/12B (IT and base)

Computed for the A1 seed corpus (18 pairs / 36 records) at the
default `n=20` trials per record (per `calibration_methodology.md`).

## Per-model trial count

```
36 records × 20 trials = 720 inferences per model
```

For the initial four target models:

| Model               | Trials | Notes                                              |
|---------------------|--------|----------------------------------------------------|
| Gemma 3 4B IT       | 720    | API or local                                       |
| Gemma 3 4B base     | 720    | Local only — base models not commonly hosted       |
| Gemma 3 12B IT      | 720    | API or local (Q4_0 QAT)                            |
| Gemma 3 12B base    | 720    | Local only                                         |
| **Total**           | 2,880  |                                                    |

## Token-volume assumption

Per inference: roughly **150 input tokens** (system prompt + user
prompt) and **300 output tokens** (typical short response with at
most one tool call + its result). These are conservative; the
seed corpus user prompts run ~10–25 tokens and system prompts ~50–100.

Per model:
- 720 × 150 = 108,000 input tokens
- 720 × 300 = 216,000 output tokens

## API option: pricing (USD)

### Gemma 3 4B IT

Google AI Studio / Vertex AI baseline: $0.040 / M input, $0.080 / M
output (also available on the Gemini API free tier within rate limits).

- Per-model cost = 108,000 × $0.040/M + 216,000 × $0.080/M
  = $0.0043 + $0.0173 = **~$0.022**

### Gemma 3 12B IT

Provider spread is large (up to 6.4×). Cheap end (DeepInfra): $0.040 / M
input, $0.130 / M output. Expensive end (Cloudflare): $0.40 / M flat.

- DeepInfra per-model cost = 108,000 × $0.040/M + 216,000 × $0.130/M
  = $0.0043 + $0.0281 = **~$0.032**
- Cloudflare per-model cost = 324,000 total × $0.40/M = **~$0.130**

### Base (non-IT) variants

Gemma 3 4B-pt / 12B-pt are not commonly available on commercial APIs.
Locally hosted only. See "Local option" below.

### API total (IT-only round)

| Provider        | 4B IT  | 12B IT | Total       |
|-----------------|--------|--------|-------------|
| Google (4B) + DeepInfra (12B) | $0.022 | $0.032 | **~$0.05** |
| Cloudflare (12B) end | $0.022 | $0.130 | ~$0.15      |

API cost is negligible for an IT-only first round. Base-model comparison
requires the local option regardless.

## Local option: RTX 3080 12GB

### What fits

| Model              | Format               | VRAM est. | Fits 12GB? |
|--------------------|----------------------|-----------|------------|
| Gemma 3 4B IT      | FP16                 | ~8 GB     | ✓          |
| Gemma 3 4B IT      | Q4_K_M / Q4_0 QAT    | ~3 GB     | ✓          |
| Gemma 3 4B base    | FP16                 | ~8 GB     | ✓          |
| Gemma 3 12B IT     | BF16                 | ~24 GB    | ✗          |
| Gemma 3 12B IT     | Q4_0 QAT GGUF        | ~7 GB     | ✓          |
| Gemma 3 12B IT     | Q4_K_M GGUF          | ~7 GB     | ✓          |
| Gemma 3 12B IT     | Q8_0 GGUF            | ~13 GB    | ✗ (tight)  |
| Gemma 3 12B base   | Q4_K_M GGUF          | ~7 GB     | ✓          |

KV-cache also consumes memory; for long contexts on 12B Q4 setting
`OLLAMA_KV_CACHE_TYPE=q8_0` recovers a few GB.

### Tooling options

**Easiest — Ollama** (single binary, automatic GGUF management):

```
ollama pull gemma3:4b
ollama pull gemma3:12b-it-qat        # Q4_0 QAT, fits 12GB cleanly
```

Base (non-IT) models are not natively packaged in Ollama. For those:

**Direct GGUF — llama.cpp / LM Studio**:
- `bartowski/google_gemma-3-4b-pt-GGUF` (and 12b-pt-GGUF) — community
  GGUF conversions of the base weights.
- `unsloth/gemma-3-12b-pt-GGUF` is another reliable converter.

**Native PyTorch — transformers + bitsandbytes**:
- `google/gemma-3-4b-pt` / `google/gemma-3-12b-pt` from HuggingFace
  (license-gated; requires accepting Google's terms in HF UI).
- For 12B, load with `load_in_4bit=True` (bnb-nf4) for the 12GB card.
- Slowest to set up but most flexible for grading hooks.

### Tool-calling support — IT vs base

- **IT models** are trained with a specific chat template (`<bos>`,
  `<start_of_turn>user/model<end_of_turn>`). Tool calls are emitted
  as ```` ```tool_code ```` blocks containing JSON-like function
  invocations; tool returns wrap in ```` ```tool_output ````. The
  Hugging Face `tokenizer.apply_chat_template(..., tools=...)` produces
  the right input format.
- **Base models** are NOT trained on the chat template or tool-call
  format. Grading them on the same seeds requires a different prompt
  formatter (probably a few-shot tool-call demonstration in the system
  prompt) and a more permissive output parser. This is meaningful
  scope; flag for A4 design.

### Throughput estimate (RTX 3080 12GB)

Approximate single-stream inference speed for Q4_K_M GGUF on a 3080:
- 4B: ~80–120 tok/s output
- 12B: ~20–35 tok/s output

At ~300 output tokens per call:
- 4B: ~2.5–3.75s/call; 720 calls = **30–45 min wall time per model**
- 12B: ~8.5–15s/call; 720 calls = **1.7–3 hours wall time per model**

Total for all four models (4B IT, 4B base, 12B IT, 12B base): roughly
**5–8 hours** of GPU time, plus setup.

## Recommended order

1. **Set up local first**, even if APIs would be cheaper for IT
   models. Base-model comparison requires local; getting the harness
   working locally first means a single inference path for all four
   models. The 4B IT model is the cheapest to iterate on while the
   harness is being written.
2. **Use Ollama for the IT models initially**; switch to direct GGUF /
   llama.cpp once the base models are needed.
3. **Validate the harness end-to-end against the dispatch dry-run**
   (`check_tool_dispatch.py`) before committing to a full run — a
   broken parser on 720 trials wastes hours.
4. **First serious run on 4B IT**: cheapest, fastest, sanity-checks
   thresholds and parsing. Expected: ~30–45 min.
5. **Then 12B IT** on the same harness (~2–3 hours).
6. **Then base models** after the base-model prompting strategy is
   designed (separate doc to come; see "Tool-calling support" above).

## What needs the human

- **Confirm target model list.** Currently planned: 4B IT, 4B base,
  12B IT, 12B base. Add or remove?
- **API or local for the initial run.** API is trivially cheap
  (~$0.05 for 4B+12B IT round) but local is needed for base models
  regardless. Recommendation above: start local for path uniformity.
- **Authorize local setup** (Ollama install, ~15 GB model downloads).
  These are reversible and on the user's hardware, but worth
  surfacing before doing them.
