---
id: studies/003-automated-w2s-replication/investigations/004-qwen-researcher-floor
title: Qwen researcher floor — machinery, prompt induction, harness shape
status: in-progress
parents:
  - studies/003-automated-w2s-replication
children: []
related:
  - studies/003-automated-w2s-replication/investigations/003-claude-sdk-shim-and-researcher-swap
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - harness-design
  - tool-calling
  - qwen
  - weak-researcher
  - capability-floor
created: 2026-05-25
updated: 2026-05-25
---

# Investigation 4 — Qwen researcher floor

## Scope

Investigation 003 closed the harness gaps and produced a single gate-5
PASS (qwen3.5:4b + `tool_invocation_hint`) — but the longer-smoke run
showed the loop closes mechanically while never completing a single
end-to-end vanilla_w2s training iteration. This investigation answers
the next question the matrix surfaced:

**What does it take to get a 4B-class Qwen researcher to perform one
complete training-and-evaluation iteration on the vanilla_w2s substrate,
and is the remaining gap machinery, model behavior, or harness shape?**

Three sub-parts, sequenced. The sequencing matters — machinery before
prompt induction is a precondition for the prompt work being
interpretable; QwenCode reading runs in parallel because it's research,
not implementation, and informs the conditional 4d decision.

### 4a — Machinery

The longer-smoke agent in 003 constructed the correct training command
on the first try (`python -m w2s_research.ideas.vanilla_w2s.run
--train-size 64 ...`) but the command failed because workspace cwd was
outside the upstream `.venv`. Fix the harness so the agent's `Bash` tool
runs in an environment where the constructed command actually executes.

Concretely: workspace cwd, PATH plumbing (or `uv run` wrapper), env vars
the upstream agent expects (`ORCHESTRATOR_API_URL`, etc.). One end-to-end
training+eval iteration must complete from a clean workspace before 4b
starts.

Sharp success criterion: a single `Bash` invocation of the constructed
training command produces a model checkpoint and `evaluate_predictions`
accepts the resulting integer-list submission against the real target
idea.

### 4b — Prompt induction (gated on 4a)

Even with machinery fixed, the longer smoke showed the agent emits 40
hallucinated `share_finding` calls, drifts onto invented tool names
(`terminal`, `get_file`), and submits free-text prose to
`evaluate_predictions` instead of an integer list. These are model
behaviors the patch text in 003 did not address.

Iterate prompt patches targeting these failure classes. Each patch
plumbed through `ClaudeAgentOptions` so it can be stripped for the
unpatched control. Treat each patch as an experimental condition with
its own gate-5-style smoke before composing with the next.

**Stopping criterion** (required — this is the tar-pit prevention):
iterate until the agent completes one end-to-end iteration with a
valid `evaluate_predictions` submission against the real target idea,
OR until 5 distinct patches have been tried without progress on that
specific gate. Either outcome is the result. "Ineffective researcher
that mechanically completes one iteration" is a publishable finding;
so is "no prompt patch in 5 attempts gets a 4B-class Qwen to a valid
submission."

### 4c — QwenCode wrapping read

In parallel with 4a (web reading; no GPU or implementation). The cell
4 and 5 results from 003 pressure-test an assumption baked into our
shim: that the Claude Agent SDK protocol shape is a neutral substrate
that any model can be coerced into. Two readings of that data are
live:

- **Reading A:** Qwen with enough prompting can be coerced into the
  Claude-shaped protocol. Our job is to find the right coercion. (4b
  pursues this.)
- **Reading B:** The Claude-shaped protocol isn't neutral; forcing
  Qwen through it depresses its measured capability. The right
  comparison would wrap Qwen in its native idiom.

Half a day of reading QwenCode's open-source wrapping (and Qwen's own
tool-call documentation) is the cheapest way to know whether Reading B
is worth taking seriously. Output: short writeup contrasting QwenCode's
LLM-wrapping shape against our shim's, with a recommendation on whether
4d should exist.

### 4d — Qwen-native harness spike (conditional)

If 4b's stopping criterion fires with no progress AND 4c's read
suggests Qwen's native tool-call idiom is structurally different from
the Claude SDK's, spike a small Qwen-native wrapper and re-run gate 5.
If 4b succeeds, 4d collapses to a paragraph in the writeup
acknowledging the harness-shape question without spending GPU on it.

This is a decision point, not work to schedule up front.

## Methods

_To be populated as 4a starts. Will track per-sub-part: changes
landed, smoke logs, success-criterion status._

## Decisions

_Populate as work proceeds. Format:_

> **Decision N — short title** (date)
> What was chosen, alternatives considered, why this won.

## Results

### 4a — Machinery

**Plumbing changes (landed).**

- `ClaudeAgentOptions` gained `bash_cwd: Optional[str]` and
  `bash_env: Optional[Dict[str, str]]` fields (shim `types.py`). Both
  default to `None` so the control run is byte-identical when neither
  is set.
- `create_builtin_tools_server(...)` accepts `bash_cwd` and `bash_env`
  kwargs (shim `builtins.py`). The `Bash` tool now starts subprocesses
  with `cwd=bash_cwd` (falls back to the general `cwd`) and an env
  built from `os.environ` merged with `bash_env`. Read/Write/Edit/Glob
  /Grep still use the general `cwd` so workspace isolation is
  preserved.
- `tests/test_gate_5_full_loop.py` plumbs the upstream-venv PATH plus
  the env vars upstream `agent.py`, `config.py`, `http_utils.py` and
  `train.py` read: `VIRTUAL_ENV`, `WORKSPACE_DIR`,
  `ORCHESTRATOR_API_URL`, `SERVER_URL`, `DATASET_NAME`, `DATA_DIR`,
  `GROUND_TRUTH_DIR`, `WEAK_MODEL`, `STRONG_MODEL`, `IDEA_UID`,
  `IDEA_NAME`, `RUN_ID`, `LOCAL_MODE`, plus `WANDB_MODE=offline`
  (training imports wandb unconditionally; `WANDB_DISABLED=true`
  conflicts with `transformers`' `report_to='wandb'`).

**Verification.** Direct shim-tool test on the desktop invoked the
exact training command the gate-5 agent constructed in the 003 longer
smoke: `python -m w2s_research.ideas.vanilla_w2s.run --data-dir ...
--weak-model Qwen/Qwen1.5-0.5B-Chat --strong-model Qwen/Qwen3-4B-Base
--train-size 64 --test-size 64 --epochs 1 --seed 42 --batch-size 4
--load-in-4bit`.

- `which python` → resolves to `.venv/bin/python` ✓
- `import w2s_research` → ok ✓
- training executes the full SFT loop, **writes a LoRA checkpoint** at
  `results/math_vanilla_w2s/.../seed_42/checkpoint-16/adapter_model.safetensors`
  ✓ (84 s wall, 16 SFT steps, weights + tokenizer + scheduler +
  optimizer state all on disk).

The plumbing has done its job. The agent's command, plus the right
env, plus the right cwd, actually trains and produces a checkpoint.

**What's still in the way of an end-to-end iteration** (not 4a's
scope; flagging for 4b/005+):

1. *`--load-in-4bit` required on a 12 GB 3080*: without it, unsloth's
   fused CE loss hits `ZeroDivisionError` because
   `_get_chunk_multiplier` reads zero free VRAM at the call site (the
   model fills VRAM before the loss computes). The agent's first-try
   command in the 003 longer smoke did **not** pass `--load-in-4bit`.
   So even with all plumbing right, on this GPU the command-as-
   constructed fails on first call. 4b should weigh whether to nudge
   the prompt toward 4-bit hyperparams or treat this as a real
   inductive challenge for the researcher.
2. *flashinfer JIT*: vLLM's first call into `flashinfer.sampling`
   triggers a ninja-driven nvcc compile that errors `fatal error:
   math.h: No such file or directory` even though `/usr/include/math.h`
   exists — nvcc on this WSL2 host isn't picking up the standard C
   include path. Setting `VLLM_USE_FLASHINFER_SAMPLER=0` +
   `VLLM_DISABLE_FLASHINFER_PREFILL=1` +
   `VLLM_ATTENTION_BACKEND=FLASH_ATTN` bypasses flashinfer.
3. *KV-cache OOM*: with flashinfer bypassed, vLLM init fails because
   "1.20 GiB KV cache is needed; 0.50 GiB available." The SFT model
   isn't released before vLLM allocates strong-model weights for
   inference; upstream `train.py` lacks an explicit `gc.collect()` /
   `torch.cuda.empty_cache()` between SFT and inference. Either an
   upstream tweak or `--gpu-memory-utilization` / `--max-model-len`
   overrides plumbed through.

**Verdict (sharp criterion: a single `Bash` invocation produces a
model checkpoint AND `evaluate_predictions` accepts the integer-list
submission).** *Partial.* Checkpoint is produced from a clean
workspace via the shim's Bash tool with the new plumbing. The
integer-list submission to `evaluate_predictions` is not reached, but
the remaining gap is upstream environment / GPU-budget issues
(flashinfer JIT, SFT→vLLM memory handoff), not the Claude-SDK harness
the shim is responsible for. 4a's plumbing change unblocks 4b: the
agent now has a tool that can actually execute the training pipeline
rather than spiraling on broken `python` resolution.

**Upstream patch attempt — SFT → vLLM memory handoff (2026-05-25).**
Issue #3 from 4a (KV-cache OOM at vLLM init) was the precondition for
4b. Patched upstream `w2s_research/core/train.py`:

- `import gc`
- After `trainer.train()`: `del trainer; del model; gc.collect();
  torch.cuda.empty_cache()` (was: `del model; torch.cuda.empty_cache()`,
  i.e. trainer + gc.collect were missing).
- `gpu_memory_utilization` plumbed into both `generate_predictions` and
  `evaluate_model` call sites in `train.py`.

The patch was appended to
`studies/003-automated-w2s-replication/investigations/001-hardware-derisk/scripts/upstream_patches.diff`
and applied on the desktop. Three direct-Bash verification runs of
`python -m w2s_research.ideas.vanilla_w2s.run --train-size 64
--test-size 64 --epochs 1 --batch-size 4 --load-in-4bit` (with the
4a env vars + `VLLM_USE_FLASHINFER_SAMPLER=0` etc.) at
`gpu_memory_utilization` ∈ {0.5, 0.85, 0.95}:

| util | result                              | KV available reported by vLLM |
|------|-------------------------------------|-------------------------------|
| 0.5  | Engine core init fail               | −4.33 GiB                     |
| 0.85 | Engine core init fail               | −1.98 GiB                     |
| 0.95 | Engine core init fail (pre-load)    | "Free 10.81 GiB < 11.4 GiB"   |

Each run completed SFT cleanly (`[Memory] GPU memory freed`, parent
process reporting 0.83 GiB allocated / 0.94 GiB reserved). vLLM
loaded Qwen3-4B-Base weights (7.63 GiB) in its spawned child every
time. The deficit is in the **child-process budget**, not the
parent's reported allocations: vLLM's spawned worker needs its own
CUDA context (~500 MB) + cached kernels + library state, and the
combination plus the model weights overruns whatever the parent didn't
hand back to the driver. `nvidia-smi` shows ~10.8 GiB free immediately
before vLLM launches; vLLM's per-process budget after subtracting
its own init overhead leaves ~−2 to −4 GiB for KV cache at any util
that doesn't trip the "Free < desired util" guard.

The prior agent's plan (`gpu_memory_utilization=0.5`, in-place `del +
gc.collect`) was the canonical fix shape but doesn't clear the
structural barrier on a 12 GB 3080: there is no util value that
simultaneously (a) stays below `free_memory_at_startup` and (b) leaves
enough headroom after vLLM loads the strong-model weights. Two
viable structural fixes, both larger than 4a scope:

1. Spawn vLLM evaluation in a fresh Python subprocess so the SFT
   parent's CUDA context is fully released. (`subprocess.run` invoking
   a small `python -m w2s_research.core.eval_only` entrypoint.)
2. Switch the strong-model inference path to a 4-bit quantized vLLM
   load (`--quantization bitsandbytes` or similar), trading runtime
   for a much smaller weight footprint.

**Sharp criterion not met.** Per inv 4 anti-stall protocol the run
stopped here without proceeding to 4b. Recommendation in Forward-
looking.

### 4c — QwenCode wrapping read

Verdict: **Reading A.** QwenCode (`QwenLM/qwen-code` @ `331f45e9`) is
structurally isomorphic to our shim modulo OpenAI-vs-Anthropic wire
dialect — both bet on native tool-call tokens emitted by the model and
translated by the endpoint. The only material delta is the system
prompt: QwenCode names canonical tool identifiers (`Shell`, `ReadFile`,
`WriteFile`) constantly, in canonical case, with worked examples and an
explicit "Tools vs. Text" anti-narration clause. The upstream
automated-w2s prompt names them once. That maps 1:1 onto our cell-2/3
result where the `tool_invocation_hint` patch (which names canonical
tools) was the only thing that landed `qwen3.5:4b`. The Claude-SDK
protocol shape is not depressing Qwen's measured capability; the
prompt density is. Qwen-Agent's nous `<tool_call>{json}</tool_call>`
text-mode template is the only structurally different idiom and (a)
lives outside qwen-code, (b) is a fallback for when native tool_calls
aren't available, and (c) our shim's Path A already covers it.

**Recommendation: collapse 4d to a paragraph.** Right follow-on is a
prompt-side extension of 4b (lift QwenCode's name-pinning + worked
examples + anti-narration clause) rather than a Qwen-native harness
spike. Revisit only if 4b exhausts its 5-patch budget *and* failures
look shape-coupled rather than prompt-coupled.

Full writeup: [`qwencode-wrapping-read.md`](qwencode-wrapping-read.md).

## Forward-looking

The 4a SFT→vLLM upstream patch did not pass its direct-Bash
verification on this 12 GB 3080 at any `gpu_memory_utilization`
setting. 4b is blocked until the SFT→vLLM memory handoff is resolved.
Two next moves, in priority order:

1. **Subprocess vLLM eval.** Smallest structurally-different fix:
   move the `generate_predictions` / `evaluate_model` call sites to
   a fresh Python subprocess that the SFT parent exits before
   launching. Releases the CUDA context fully. Suggested as an
   upstream patch under inv 001 with the same diff-append pattern.
2. **Quantized vLLM load.** Pass `--quantization` (bnb-int4 or
   awq-int4) so the strong model weights occupy ~2 GiB in vLLM
   instead of 7.63. Cheaper to plumb (one kwarg) but may impact
   prediction quality vs. the Claude/Opus baseline.

Either resolves 4a's sharp criterion. Once 4a is green, 4b's
QwenCode-style prompt patches (per `qwencode-wrapping-read.md`) run
as originally scoped. If both 4a fixes prove costly enough that the
research question shifts, pivot to 4d (Qwen-native harness spike) or
inv 005's Nemotron swap — the prompt-induction question becomes
secondary to the substrate question.

If 4a and 4b both succeed with a 4B-class Qwen reaching one valid
end-to-end iteration, investigation 005 measures the 24-hour run with
the anchored baselines (vanilla_w2s, Opus 4.6, human, student-start).
That investigation is single-agent at 24h; multi-agent / longer-budget
runs are gated on that single-agent run showing nonzero PGR movement.

If 4d ends up needed, the resulting Qwen-native harness becomes a
fork of the shim — to be decided whether it lives alongside the
Claude-shaped shim (two harnesses, model-typed) or replaces it.

## Things to flag

- The 49-min longer-smoke result from 003 is the load-bearing data
  for this investigation's framing. If on closer inspection the
  agent's command was wrong rather than the environment, 4a's premise
  collapses and we restart from "what is the agent actually trying
  to do."
- `tool_invocation_hint` is currently a single string. As 4b composes
  multiple patches it may need to become a list-of-named-patches so
  stripping is per-condition. Surfacing this as expected refactor,
  not a scope change.

## Limitations

- 4B-class only. If nothing in 4a+4b+4d gets a Qwen to a valid
  submission, the right next move may be to test 8B/14B Qwen, but
  that's investigation 005+ territory and out of scope here.
- Single-agent only. Multi-agent dynamics are deferred to inv 005.
- Smoke-sized configs throughout (`train_size=64`, `epochs=1`). Real
  PGR measurement belongs to inv 005.
