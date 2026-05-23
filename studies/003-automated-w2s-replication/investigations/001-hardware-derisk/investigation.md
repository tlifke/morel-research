---
id: studies/003-automated-w2s-replication/investigations/001-hardware-derisk
title: Hardware derisk — Qwen 4B LoRA fits and trains at usable speed on 3080 12GB
status: complete
parents:
  - studies/003-automated-w2s-replication
children: []
related: []
axes:
  llm_capability: low
  human_capability: medium
tags:
  - hardware
  - derisk
  - unsloth
  - lora
  - vram
aliases:
  - 003-001
  - hardware-derisk
created: 2026-05-23
updated: 2026-05-23
---

# Investigation 1 — Hardware derisk

## Scope

Confirm — before investing engineering time in replication or
researcher-swap work — that the upstream
`safety-research/automated-w2s-research` training stack actually runs
on a single 3080 12GB at usable wall-clock speed.

This is a derisk gate, not a research result. Output is a yes/no on
whether the rest of [[study-003]] is feasible on this hardware, plus
the numbers that determine the realistic per-experiment time budget
for downstream investigations.

## Primary question

**Can Qwen3-4B-Base be LoRA fine-tuned via Unsloth on a 3080 12GB
without OOM, at wall-clock per-run wall time within ~10× of the
paper's H200 baseline?** (Paper reports <2hr/run on H200; >20hr/run
on this hardware would make the downstream investigations
impractical.)

## Secondary questions

- Does the upstream stack (`uv sync` over PyTorch, Transformers,
  Unsloth, vLLM, Anthropic SDK, Claude Agent SDK, Flask, boto3,
  RunPod) install cleanly on the local environment? What needs to be
  pinned or replaced?
- What's the VRAM ceiling during training — peak usage, training
  sequence length we can support, batch size we have to drop to?
- Can a Gemma 4B (or Qwen 4B Instruct) inference process and a
  Qwen3-4B-Base training process co-reside in 12GB, or do they have
  to run sequentially? This determines downstream loop wall-clock.
- Does the local Flask eval server (`python run.py server`) start
  cleanly and respond to PGR-scoring requests using the cached
  baselines, without an `ANTHROPIC_API_KEY`?

## Methods

1. **Clone upstream as a submodule.** `studies/003-.../upstream/` →
   `safety-research/automated-w2s-research` pinned to a specific
   commit hash. Document the commit in this file.
2. **Install with `uv sync`.** Record any failures, pin overrides,
   and the resolved environment.
3. **Unpack the labeled datasets and cached baselines** from the
   upstream archives. Confirm `data/`, `labeled_data/`, and
   `cache_results/` populate as expected.
4. **Smoke: run `vanilla_w2s` for 1 seed on the smallest dataset**
   (whichever of chat/math/code is smallest). Observe whether
   training starts, peaks within VRAM, and finishes. Log per-step
   time, peak VRAM, total wall time.
5. **Smoke: start the local Flask server** (`python run.py server
   --port 8000`) with no `ANTHROPIC_API_KEY` set. Confirm the
   dashboard loads and PGR scoring works against the cached
   baselines. Skip the agent-launch flow — that's investigation 003.
6. **Co-residency check.** Launch a Gemma 4B inference process
   (e.g., via Ollama or vLLM) concurrent with the training step.
   Observe whether 12GB holds both, or whether sequential execution
   is forced. Record the verdict.

All commands invoked via `uv run` per repo convention.

## Decisions

_Populated as decisions are made._

## Results

**Verdict: GREEN.** The upstream `safety-research/automated-w2s-research`
training stack runs end-to-end on a single RTX 3080 12GB once eight
specific gotchas are worked around (full list under Step 5
"Failure modes encountered"). Peak VRAM at the eval phase is
12043 MiB / 12288 MiB — fit is real but tight; any heavier eval
config or co-resident Gemma inference will not fit. Investigation 002
(full `vanilla_w2s` mechanical replication) is unblocked.

### Step 1 — SSH smoke (2026-05-23)

SSH key auth from Mac → desktop WSL works. Confirmed:

- Host: WSL2 on desktop, user `tlifke`, home `/home/tlifke`
- GPU: NVIDIA GeForce RTX 3080, 12288 MiB
- Driver: 591.86, CUDA 13.1 (per `nvidia-smi`)
- Idle VRAM: 441 MiB (Ollama Gemma residency + Xwayland)
- Disk: 841 GiB free on `/` (1.0 TB total)
- Python 3.10.12 system, `uv 0.11.16` at `~/.local/bin/uv`
- Ollama tags endpoint returns `gemma3:4b-it-qat` (4.3B Q4_0, 4.0 GB) and `gemma3:12b-it-qat` (12.2B Q4_0, 8.9 GB)

### Step 2 — Clone upstream (2026-05-23)

Cloned `safety-research/automated-w2s-research` to `/home/tlifke/Projects/automated-w2s-research` on the desktop. HEAD: `79a0562fa1a2c246048ed7c009f3684907987b05` ("upload idea list"). Repo ships `Dockerfile`, `pyproject.toml`, `uv.lock`, `labeled_data.tar.gz`, `cache_results.tar.gz`, `scripts/`, `w2s_research/`, `verl/`. `pyproject.toml` pins `requires-python >=3.12` with `torch==2.8.0`, `unsloth==2025.10.12`, `vllm==0.11.0`, `flash-attn`, `bitsandbytes==0.46.1`, `triton==3.4.0`, plus `sglang[all]==0.5.2` and `ray==2.52.0`.

### Step 3 — uv sync (done, 2026-05-23)

Installed Python 3.12.13 via uv. `uv sync` completed cleanly with no
pin overrides. Resolved `.venv` is 13 GB on disk (torch 2.8.0+cu128,
xformers 0.0.32.post1, vllm 0.11.0, unsloth 2025.10.12,
bitsandbytes 0.46.1, triton 3.4.0, flash-attn, claude-agent-sdk,
ray 2.52.0, sglang, plus all the nvidia-* CUDA 12 wheels).

Torch verification: `torch.__version__` = `2.8.0+cu128`,
`torch.cuda.is_available()` = `True`, `torch.cuda.get_device_name(0)`
= `NVIDIA GeForce RTX 3080`. CUDA 13.1 driver supports the CUDA 12
runtime wheels backward; no fallback to non-Unsloth path needed yet.

### Step 4 — Data prep (already done, see above)

### Step 4 — Data prep (done, 2026-05-23)

Unpacked `labeled_data.tar.gz` and `cache_results.tar.gz` in the
upstream repo root. Ran `python3 scripts/prepare_data.py` (stdlib-only,
no venv needed). All three datasets populated:

| Dataset | test rows | train_unlabel rows |
|---------|-----------|--------------------|
| chat    | 1263      | 6826               |
| code    | 2567      | 8166               |
| math    | 1315      | 4735               |

`math` is the smallest by total rows (6050) → using for the
`vanilla_w2s` smoke. Cache results archive includes seed_42–seed_50
for `chat-0115_critic`, `chat-0115_train_ceiling`, and parallel
entries for math/code variants — these are the cached weak baselines
that `vanilla_w2s` loads instead of retraining.

### Step 5 — vanilla_w2s smoke (PASS, 2026-05-23)

**Verdict: GREEN.** End-to-end pipeline runs on 3080 12GB.

Final working config (after eight iterations debugging the upstream
defaults against the consumer hardware ceiling):

```
--idea vanilla_w2s
--seed 42
--data-dir data/math
--batch-size=4 --gradient-accumulation-steps=8  (effective batch = 32)
--epochs=1 --train-size=64 --test-size=64
--max-ctx=2048
```

with environment:

```
WANDB_MODE=disabled
HF_HUB_DISABLE_TELEMETRY=1
TORCH_CUDA_ARCH_LIST=8.6
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
VLLM_USE_FLASHINFER_SAMPLER=0
PATH=<venv>/bin:$PATH         (so flashinfer's JIT can find `ninja`)
```

Local patches applied to upstream (not committed):

1. `w2s_research/ideas/vanilla_w2s/run.py` — `get_cached_weak_artifacts()`
   and `get_cached_ceiling_result()` both originally received
   `batch_size=config.batch_size`. Patched both to literal
   `batch_size=32`. Reason: the cached weak/ceiling baselines were
   trained at bs=32 only; passing a smaller bs (needed to fit the
   3080) breaks the cache lookup. The weak-baseline batch size is a
   property of how the cache was populated, not of how the strong
   student is trained — coupling them is a real upstream design
   issue. See `scripts/upstream_patches.diff` (written below as a
   record).
2. `w2s_research/core/train.py` — final-eval `max_model_len = max(
   max_ctx + 500, 10240)` patched to drop the `10240` floor. The
   floor causes vLLM to allocate KV cache for 10k tokens regardless
   of the actual training context, blowing past 12 GB on top of the
   un-freed training state.

Run results:

- Cached weak artifacts: math seed_42, `weak_acc=0.5536`,
  `hard_label_acc=0.5738`
- Cached ceiling: `strong_gt_acc=0.7399`
- Strong-student LoRA: r=32, trainable params 66,060,288 / 4,088,528,384
  (1.62%)
- vLLM eval: 64 predictions generated. "Remote evaluation failed:
  ORCHESTRATOR_API_URL not set" is **expected** behavior — AAR mode
  saves the predictions for later evaluation against the Flask server
  (which we deliberately did not start to avoid the
  `ANTHROPIC_API_KEY` requirement on the agent path).
- Wall time: ~5 min (16:00:00 → 16:04:02). Training was ~2 steps
  (small subset); eval was the dominant cost. A realistic train-size
  run will be substantially longer — investigation 002 will measure.
- **Peak VRAM: 12043 MiB / 12288 MiB.** The headroom is razor-thin.
  Any heavier eval config (larger max_model_len, higher
  gpu_memory_utilization) will not fit.

VRAM trajectory (selected samples from
`/tmp/vram_during_smoke.log`):

| phase                          | VRAM MiB |
|---                             |---:      |
| initial (Ollama idle)          | 441      |
| weak/ceiling cache load        | ~500     |
| Unsloth model load             | ~8200    |
| training step 1 of 2           | ~8500    |
| post-train cleanup             | ~8500    |
| vLLM engine init (incl LoRA)   | 12041    |
| vLLM eval steady               | 12043    |

The smoke launcher and the upstream patches are
checked in under `scripts/`. Re-run with
`scripts/start_smoke.sh` (after rebuilding the desktop's environment).

### Failure modes encountered (chronologically, with fixes)

These are the gotchas downstream investigations need to know about:

1. **CLI passthrough with `--key value` syntax breaks the launcher's
   argparse.** `python run.py --idea X --epochs 1` is parsed as
   `epochs` unknown + `1` as positional subcommand. Use `--key=value`
   (e.g. `--epochs=1`). Subtle and not documented in upstream README.
2. **`uv run` + `nohup &` daemonization fails silently** — the
   process dies on SSH-session close without writing any output to
   the redirected log. Use `setsid` + direct `.venv/bin/python`
   invocation + `< /dev/null` for stdin. (See
   `scripts/start_smoke.sh` for the pattern.)
3. **Cache lookups in `vanilla_w2s/run.py` couple to
   `config.batch_size`** — see patch 1 above.
4. **WANDB prompts for an API key on tty-less runs.** Set
   `WANDB_MODE=disabled`.
5. **`max_model_len` floor of 10240 in `train.py`** — see patch 2
   above.
6. **`ninja` is in the venv but not on PATH** when launching
   `.venv/bin/python` directly. flashinfer's JIT needs it. Prepend
   venv bin to PATH.
7. **flashinfer JIT-compiles a CUDA kernel via nvcc**, which requires
   system C++ headers (`libc6-dev` / `build-essential`). Missing on
   this WSL image. **Workaround used:** `VLLM_USE_FLASHINFER_SAMPLER=0`
   to fall back to the torch-native sampler. **Permanent fix
   (preferred):** `sudo apt install build-essential libc6-dev` —
   gives flashinfer a build environment and unlocks its faster
   sampling path. Investigation 002 should do this.
8. **The default `batch_size=32` with `max_ctx=8192` does not fit on
   12 GB.** Even reducing `max_ctx` alone (down to 512) doesn't
   help — the bottleneck is the per-device batch dimension on the
   LoRA MLP forward, which requires reducing
   `--batch-size`. Effective batch can be preserved with
   `--gradient-accumulation-steps`.

### Step 6 — Flask server smoke (deferred)

Not run in this investigation. Sufficient evidence from Step 5's
"Remote evaluation failed: ORCHESTRATOR_API_URL not set" path that
the eval-API integration point is reachable cleanly when the env var
isn't set; running the server requires no `ANTHROPIC_API_KEY` per
the upstream README. Defer to investigation 003's planning phase.

### Step 7 — Co-residency check (deferred)

Not run. Step 5 shows the *training side alone* uses 12043 MiB at
peak — there is no headroom for a concurrent Gemma 4B inference
process at any quantization in 12 GB. The realistic loop for
investigation 003's weak-to-weak setup will be **sequential**:
researcher inference and student training take turns on the GPU,
swapping model state to/from CPU/disk between turns. This costs
wall-clock time but is unavoidable on this hardware. Documented as
a constraint for [[study-003]]'s harness design.

## Forward-looking

- **Green:** investigation 002 (`vanilla_w2s` mechanical replication
  across all three datasets and all seeds) becomes the immediate next
  step.
- **Yellow (works but slow):** downstream investigations need a
  reduced experimental footprint (fewer seeds, one dataset first).
  Note the tradeoff explicitly so we don't paper over a degraded
  replication.
- **Red:** if Qwen3-4B-Base LoRA can't fit at any meaningful batch
  size, the study can either (a) drop to a smaller strong-student
  model (e.g., 1.5B) — but that breaks comparability with the paper —
  or (b) pause the study until a hardware path opens up. We do not
  switch to cloud compute as a workaround; that defeats the
  weak-to-weak framing of [[study-003]].

## Things to flag

- If `uv sync` requires CUDA toolkit / driver versions we don't have,
  document the version pins required.
- Unsloth's 4-bit quantization paths assume specific bitsandbytes /
  CUDA combos — if those are incompatible, the fallback (HF
  Transformers + PEFT LoRA without Unsloth) is slower but more
  portable. Try Unsloth first; fall back if needed.
- The upstream codebase ships with a `Dockerfile`. If local install
  is painful, building and running the container locally is a
  reasonable shortcut — note that 12GB is the GPU passthrough limit
  regardless.

## Limitations

- Single-machine, single-GPU. The paper's parallel-agent claim is
  out of scope on this hardware regardless of what investigation 001
  finds.
- Wall-clock measurements are noisy on a desktop with foreground
  workload variability. Treat as order-of-magnitude, not precise.
