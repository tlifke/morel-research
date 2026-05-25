# Open-Source ~4B-Class Model Landscape — May 2026

Reference scan for the weak-researcher experiment (RTX 3080 12GB, Q4_K_M-ish quant,
agentic tool-calling role). Focus: families competitive *as of late May 2026* whose
small members fit in ~10GB VRAM.

## Top-line recommendation

- **Qwen 3.5 small series (4B / 9B)** — current default; native multimodal, 262K
  context, Hermes-style tool-call template recommended. 4B reportedly matches the
  last-gen Qwen3-VL-30B-A3B on agent tasks and tops some peers on TIRE-Bench.
  ([MarkTechPost](https://www.marktechpost.com/2026/03/02/alibaba-just-released-qwen-3-5-small-models-a-family-of-0-8b-to-9b-parameters-built-for-on-device-applications/),
  [Qwen docs](https://qwen.readthedocs.io/en/latest/framework/function_call.html))
- **Gemma 4 E4B / 12B** — April 2026, Apache 2.0, dedicated function-calling
  protocol (`<|tool_call|>` tokens). The 12B variant explicitly carries the "full
  multimodal + function-calling stack." Realistic 12GB candidate with aggressive
  quant. ([Google blog](https://blog.google/innovation-and-ai/technology/developers-tools/gemma-4/),
  [function-calling docs](https://ai.google.dev/gemma/docs/capabilities/text/function-calling-gemma4))
- **Ministral 3 8B** — December 2025, Apache 2.0, edge-optimized single-GPU,
  base/instruct/reasoning variants with vision. Mistral-shaped tool-call template
  is well-documented and the family is back to being competitive after the Small 4
  refresh. ([Mistral changelog](https://docs.mistral.ai/getting-started/changelog),
  [TechCrunch](https://techcrunch.com/2025/12/02/mistral-closes-in-on-big-ai-rivals-with-mistral-3-open-weight-frontier-and-small-models/))
- Worth a *light* read but probably not primary: **Phi-4-mini (3.8B)** —
  strong per-param, native function-calling, but reputation as a benchmark-tuned
  small model persists; sanity-check on agent eval before committing.
- DeepSeek-V4 has no first-party small dense checkpoint as of May 2026; only
  community R1-style Qwen/Llama distills exist. Not a primary candidate.

## Families

| Family | Best ~10GB fit | Released | Maintainer | Tool calling | Reputation (May 2026) |
|---|---|---|---|---|---|
| **Qwen 3.5** | 4B, 9B (Q4) | 2026-03-02 | Alibaba / Qwen | Native, Hermes/Nous template; Qwen-Agent canonical impl | Flagship 397B leads BFCL-V4 (0.729); small series widely deployed; Apache 2.0; 262K ctx |
| **Gemma 4** | E4B, possibly 12B Q4 | 2026-04 | Google DeepMind | Native, dedicated special tokens; documented per-family | Apache 2.0 (new); large jump over Gemma 3 (AIME 21% → 89%); strong default for "startups in 2026" per third-party comparisons |
| **Ministral 3** | 3B, 8B | 2025-12 | Mistral AI | Native, Mistral tool template, well-supported in vLLM/llama.cpp | Apache 2.0; positioned for single-GPU; "matches/exceeds comparable models with fewer tokens" |
| **Phi-4-mini** | 3.8B | early 2026 (refresh) | Microsoft | Native function-calling per HF card | Strong on MMLU/IFEval per-param; lingering "benchmark-leaning" skepticism |
| **DeepSeek (small)** | community 7B/8B distills only | ongoing | DeepSeek + community | Inherits base (Qwen/Llama) tool-call format | V4 itself is 284B+ MoE; no first-party small dense. Distills exist but are not a coherent agent family |
| **Cohere Command R7B** | 7B | 2024 era | Cohere | Native, well-documented | Older; Cohere's energy is on Command A+ (218B). R7B has not been refreshed at this scale |

Sources for table: per HF model cards (Qwen, Gemma, Ministral, Phi),
[BFCL V4](https://gorilla.cs.berkeley.edu/leaderboard.html),
[Cohere models overview](https://docs.cohere.com/docs/models).

## Skip list

- **Llama 4** — community reception "decidedly mixed," Maverick trails DeepSeek V4
  and Qwen 3.6 on SWE-bench Verified and LiveCodeBench; the small Scout sibling is
  17B-active (too big for our budget). Per user instruction, deprioritized; this
  scan agrees. ([Medium / Brahma](https://dinmaybrahma.medium.com/metas-llama-4-revolution-or-disappointment-c52d491e5a39))
- **Qwen 2.5** — superseded by Qwen 3 (April 2025) and Qwen 3.5 (Feb–Mar 2026).
  Skip.
- **Cohere Command R7B** — not refreshed; Cohere's open-weights momentum is on
  the 218B Command A+. Not in the running at our scale.
- **DeepSeek V4** — flagship is 284B / 1.6T (MoE). No first-party small dense
  variant; community distills are heterogeneous and not a *family* to evaluate.

## Open questions

- **BFCL small-model rankings (≤10B):** main BFCL V4 page surfaces frontier
  models; per-size slice was not retrievable in this scan. Confirming Qwen 3.5 4B
  vs Gemma 4 E4B vs Ministral 3 8B head-to-head on BFCL V4 would need the raw
  CSV. ([BFCL](https://gorilla.cs.berkeley.edu/leaderboard.html))
- **Gemma 4 dense intermediate sizes:** sources disagree on whether a 12B dense
  variant ships at GA or only E4B + 26B-A4B + 31B. The function-calling docs
  reference "4B, 12B, 27B" — possibly leftover Gemma 3 wording. Verify on HF
  before planning a 12B run.
- **Qwen 3.6 timing:** a `Qwen3.6` repo exists (35B-A3B referenced). Whether a
  3.6 small series is imminent affects whether 3.5-4B has a short shelf life.
- **Tool-calling format details per family** — deliberately out of scope for this
  scan; that's the next read.

## Follow-up: families flagged by the LMArena-style tier list

Quick scan of GLM, StepFun, MiMo, GPT-OSS, MiniMax, Kimi, and Nemotron for
~4B-class siblings that fit our budget.

- **NVIDIA Nemotron 3 Nano 4B** — *strong fit, add to primary candidates.*
  Released ~March 2026. Hybrid Mamba-2 + MLP + 4 attention layers; compressed
  from Nemotron-Nano-9B-v2 via NVIDIA's "Nemotron Elastic" framework. Unified
  reasoning + non-reasoning model with explicit "excellent tool-use" framing
  from NVIDIA. Runs in **5GB** RAM/VRAM. Open weights + open training data +
  open recipes on HF. This is the most agentic-focused 4B in the scan.
  ([HF blog](https://huggingface.co/blog/nvidia/nemotron-3-nano-4b),
  [HF GGUF](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF))
- **GLM-4.6V-Flash (9B)** — *fits at Q4, worth a deeper read.* MIT-licensed,
  native multimodal **function calling** baked into the architecture, 128K
  context. The 4.6V series explicitly markets "tools can consume and return
  images, video frames, document pages." No GLM model below 9B as of May 2026;
  GLM-5 itself is 744B MoE, out of budget.
  ([VentureBeat](https://venturebeat.com/ai/z-ai-debuts-open-source-glm-4-6v-a-native-tool-calling-vision-model-for),
  [MarkTechPost](https://www.marktechpost.com/2025/12/09/zhipu-ai-releases-glm-4-6v-a-128k-context-vision-language-model-with-native-tool-calling/))
- **Step-3.5-Flash** — *does not fit.* 196B total / 11B active sparse MoE. The
  "Flash" name is misleading at our scale — 11B active is the *routing* cost,
  but you still need to hold the full ~196B of weights in memory. Apache 2.0,
  agentic-focused, but skip for the 3080.
  ([HF model card](https://huggingface.co/stepfun-ai/Step-3.5-Flash))
- **MiniMax M2.5 / Kimi K2.5 / MiMo-V2-Flash** — *no first-party 4B siblings
  located.* All three labs ship 200B+ MoE flagships. Earlier-generation small
  variants (e.g. MiMo-7B) exist but aren't part of the current strong release.
  Skip for now; revisit if these labs ship small siblings.
- **gpt-oss-20b** — *does not fit at Q4.* 20B dense, OpenAI's open-weights
  model. ~12GB at Q4_K_M is tight on a 12GB card and leaves no headroom for KV
  cache at meaningful context. Mentioned for completeness; not a primary
  candidate.

### Revised top picks for the weak-researcher role

1. **Qwen 3.5 4B** (current default — keep)
2. **Nemotron 3 Nano 4B** (new addition — NVIDIA's stated tool-use focus +
   5GB VRAM + Mamba hybrid is a genuinely different architectural sample than
   the Qwen/Gemma transformer baseline)
3. **Gemma 4 E4B** (fallback)
4. **GLM-4.6V-Flash 9B** at Q4 if we want a multimodal tool-calling
   datapoint with a different lineage

## Things I made up that you should review

- Treated several 2026-dated third-party blog posts as authoritative for release
  dates and benchmark numbers. The Qwen 3.5 small-series 2026-03-02 date and the
  Gemma 4 2026-04 date appear in multiple sources but I did not cross-check
  against the official Qwen/Google blogs directly.
- "Top 3" ranking (Qwen 3.5 / Gemma 4 / Ministral 3) is my judgment call from
  the search material, not a measured comparison.
- Phi-4-mini "benchmark-leaning skepticism" is a vibes summary from the
  per-source language, not a cited consensus.
