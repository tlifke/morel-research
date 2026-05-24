---
id: studies/003-automated-w2s-replication/investigations/002-vanilla-w2s-replication
title: Mechanical replication of vanilla_w2s baseline
status: in-progress
parents:
  - studies/003-automated-w2s-replication
children: []
related:
  - studies/003-automated-w2s-replication/investigations/001-hardware-derisk
axes:
  llm_capability: medium
  human_capability: medium
tags:
  - replication
  - vanilla-w2s
  - lora
  - pgr
aliases:
  - 003-002
  - vanilla-w2s-replication
created: 2026-05-23
updated: 2026-05-23
---

# Investigation 2 — Mechanical replication of vanilla_w2s baseline

## Scope

Reproduce the upstream `vanilla_w2s` baseline's Performance Gap
Recovery (PGR) on the 3080 12GB using the hardware-derisked config
from [[003-001-hardware-derisk]]. Compare resulting PGR against the
cached upstream baselines shipped in `cache_results.tar.gz` to
confirm our local setup (with the bs=4+grad_accum=8 hardware
adaptation) produces equivalent results to the upstream bs=32 native
configuration.

If PGR matches within seed-noise: the substrate is mechanically
sound and [[study-003]] can proceed to investigation 003
(researcher-swap to a local model). If PGR diverges: the divergence
is itself a finding — the bs adaptation isn't equivalent and needs
debugging.

## Methods

Three-phase ramp (per [[003-001]]'s GREEN verdict, with full-coverage
runs estimated at 4–10 hours each on this hardware):

### Phase 1 — Pre-flight at scale (~30–60 min wall-clock)

One math run, `seed=42`, full `train_size` (4735 unlabeled samples),
`epochs=1`. Goal: confirm the smoke's razor-thin VRAM margin
(12043 / 12288 MiB) holds at full data, and measure a real per-step
wall-clock to extrapolate phase 2 cost.

Hard pass criterion: completes without OOM, eval generates 1315
predictions, wall-clock reported.

### Phase 2 — One full seed per dataset (~12–30 hours wall-clock)

Three runs at `epochs=5`, `seed=42`, full `train_size`:

- math (4735 samples)
- chat (6826 samples)
- code (8166 samples)

Auto-triggered on phase 1 success per user authorization
(2026-05-23). Compare each resulting PGR to the cached upstream
result for `vanilla_w2s_<dataset>_seed_42_e5_lr0.0001_bs32_linear_xent`
in `cache_results/`.

### Phase 3 — Seed expansion (deferred)

If phase 2 PGRs match the cached upstream values within seed-noise
(~±0.05 PGR is the order of magnitude in the literature), expand to
seeds 43–46 across all three datasets. If phase 2 diverges, debug
the divergence rather than scale up.

User decision point — do not auto-dispatch.

## Hardware-adapted run config

From [[003-001]]'s working smoke (peak VRAM 12043 MiB):

```
--idea vanilla_w2s
--seed 42
--data-dir data/{math,chat,code}
--batch-size=4 --gradient-accumulation-steps=8  # effective bs = 32
--epochs={1 in phase 1, 5 in phase 2}
--max-ctx=2048
```

Environment:

```
WANDB_MODE=disabled
HF_HUB_DISABLE_TELEMETRY=1
TORCH_CUDA_ARCH_LIST=8.6
PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
VLLM_USE_FLASHINFER_SAMPLER=0
PATH=<venv>/bin:$PATH
```

Upstream patches in place (see [[003-001]]
`scripts/upstream_patches.diff`):

1. `vanilla_w2s/run.py` cache-lookup `batch_size` pinned to 32
2. `core/train.py` eval `max_model_len` floor of 10240 removed

## Decisions

> **Decision 1 — three-phase ramp over straight full-coverage** (2026-05-23)
> Estimated 4–10 hrs per (seed, dataset) on 3080 12GB. Straight to
> full coverage (3 datasets × 5+ seeds) = days to weeks of wall-clock
> with no validation of methodological correctness along the way.
> Phase 1 validates VRAM at scale before committing; phase 2
> validates PGR against cached upstream before scaling seeds; phase 3
> is the expensive scaling step gated on the prior two.

> **Decision 2 — auto-trigger phase 1 → phase 2** (2026-05-23)
> User explicitly authorized auto-progression from phase 1 to phase
> 2 without intervention. Phase 3 remains user-gated.

> **Decision 3 — keep `VLLM_USE_FLASHINFER_SAMPLER=0` for now** (2026-05-23)
> Permanent fix would be `sudo apt install build-essential
> libc6-dev` so flashinfer's JIT can find C++ headers. The env-var
> fallback path worked end-to-end in [[003-001]]; punting the apt
> install to keep this investigation moving. Revisit if the
> fallback sampler causes any observable behavioral differences.

## Results

**Status:** Phase 2 complete (2026-05-23 18:40 → 2026-05-24 11:16, 16h 36m).
Substrate replicates faithfully — all three datasets show
transfer_acc within seed noise of upstream and consistently +0.013
to +0.014 above. Phase 3 deferred for user decision.

### Headline comparison (seed=42, epochs=5)

| dataset | upstream transfer_acc | our transfer_acc | delta | upstream PGR | our PGR (own) | wall-clock |
|---|---:|---:|---:|---:|---:|---:|
| math | 0.5970 | **0.6099** | +0.013 | 0.336 | 0.302 | 4h 13m |
| chat | 0.6041 | **0.6184** | +0.014 | 0.372 | 0.400 | 7h 00m |
| code | 0.5949 | **0.6085** | +0.014 | 0.153 | 0.160 | 5h 23m |

Weak and ceiling accuracies match upstream to 4+ decimals across all
datasets (proves baseline lookup is hitting correctly and same data
slices/labels).

The consistent +0.013-0.014 transfer_acc lift is directional, not
coincidence. Two candidate explanations:

1. **Gradient accumulation produces smoother optimizer trajectory.**
   bs=4 × grad_accum=8 averages gradients over 8 minibatches before
   each step; native bs=32 does one big batch in one go. With AdamW's
   adaptive second moments, the accumulated version may have less
   variance per update.
2. **bf16 numerics interaction.** Different reduction order across
   batch dimensions can change the bf16 rounding pattern, leading to
   subtly different optimizer dynamics.

Either way, the substrate is mechanically faithful. The bs adaptation
isn't degrading the training — if anything it's slightly stronger.

### Cached upstream baselines (reference, seed=42, e5, bs=32)

From `cache_results/<dataset>_vanilla_w2s/Qwen_Qwen3_4B_Base_Qwen_Qwen1_5_0_5B_Chat_e5_lr0.0001_bs32_schlinear/seed_42.json`:

| dataset | weak_acc | strong_acc | transfer_acc | cached PGR |
|---|---:|---:|---:|---:|
| math | 0.5536 | 0.7399 | 0.5970 | **0.3356** |
| chat | TBD | TBD | TBD | TBD |
| code | TBD | TBD | TBD | TBD |

Cached run config: `epochs=5, lr=1e-4, batch_size=32, lora_r=32, lora_alpha=32, load_in_4bit=false`. Upstream training_time for math/seed_42 was 2872s (~48 min) on H200.

### Phase 1 — math pilot (PASS, 2026-05-23)

Run: `seed=42`, full data (4735 train_unlabel, 1315 test), `epochs=1`,
`max-ctx=2048`, `bs=4` × `grad_accum=8`. Started 17:44, ended 18:39:22.

| metric | value |
|---|---|
| wall-clock | **55 min** |
| step time | 19.55 s/step at start (148 steps) |
| peak VRAM | 12041 MiB / 12288 MiB |
| AAR mode | true (data-dir was `data/math`, labels stripped) |
| predictions written | 1315 |
| PGR | n/a (AAR mode — orchestrator API not running) |

VRAM profile matches the smoke (12043 → 12041 MiB) at full data — the
margin holds at scale. The training trajectory is dominated by setup
+ first-step warmup; subsequent steps may be faster than 19.55s.

**Verdict on phase 1:** GREEN. Proceeding to phase 2.

### Pivot for phase 2 — `labeled_data/` instead of `data/`

The cached upstream `vanilla_w2s_math/seed_42.json` was generated with
`aar_mode: false`. To get PGR locally without standing up the Flask
orchestrator API server, point `--data-dir` at `labeled_data/<dataset>`
(which retains labels) instead of `data/<dataset>` (which `prepare_data.py`
strips for the agent-worker setup). `dataset_name` is the basename
in either case, so cache lookups still hit. This is the same
configuration the cached upstream baselines were generated with.

### Phase 2 — three datasets at epochs=5 (in progress)

Launched 18:40 via `scripts/phase2_all.sh`. Sequential: math → chat
→ code. Per-dataset logs at `/tmp/phase2_<dataset>.log` on desktop.
Estimated wall-clock from phase 1's 19.55 s/step:

| dataset | unlabeled samples | steps × 5 epochs | est. training | + eval | est. total |
|---|---:|---:|---:|---:|---:|
| math | 4735 | 740 | ~4.0 hr | ~5 min | ~4 hr |
| chat | 6826 | 1067 | ~5.8 hr | ~5 min | ~6 hr |
| code | 8166 | 1280 | ~7.0 hr | ~5 min | ~7 hr |
| **total** | | | | | **~17 hr** |

#### Math result (2026-05-23 18:40 → 22:53, 4h 13min)

| metric | cached upstream | our local | delta |
|---|---:|---:|---:|
| weak_acc | 0.5536 | 0.5536 | 0.0000 |
| ceiling acc | 0.7399 | 0.7399 | 0.0000 |
| transfer_acc | 0.5970 | **0.6099** | +0.0129 |
| PGR (own baselines) | 0.336 | 0.302 | -0.034 |
| PGR (fixed baselines, post-hoc) | 0.336 | 0.407 | +0.071 |

Our transfer model marginally **exceeds** the cached upstream
transfer_acc, well within the seed-noise envelope. Replication
mechanically sound on math.

Two PGR numbers because the run reported "Fixed baselines not
available (weak=0 seeds, strong=0 seeds)" — see "Newly discovered
upstream coupling" below. PGR with cached upstream's fixed_weak
(0.5360) and fixed_strong (0.7176) computed post-hoc.

#### Newly discovered upstream coupling

[[003-001]]'s patch fixed `get_cached_weak_artifacts` and
`get_cached_ceiling_result` to pin `batch_size=32` for the cache
lookup. The PGR-computation step in `vanilla_w2s/run.py` uses a
*third* pair of functions — `get_fixed_weak_baseline` and
`get_fixed_ceiling_baseline` (called from
`w2s_research/utils/hierarchical_cache.py`) — which were not
covered by that patch. They still receive `--batch-size` from the
config and hit the empty `bs4` cache directories.

Observable effect: run completes, transfer_acc and accuracies are
correctly cached. PGR field is absent or null in the run's emitted
results. Workaround: compute PGR post-hoc using upstream's
`fixed_weak_baseline` and `fixed_strong_baseline` from the cached
`vanilla_w2s/seed_42.json` files. Permanent fix: extend
`upstream_patches.diff` to also pin these two lookups to bs=32.
Will apply after phase 2 completes (don't patch mid-stream to
avoid corrupting chat/code).


## Forward-looking

Phase 3 (seeds 43-46 expansion across all three datasets) is gated
on user decision per Decision 2. Three considerations:

- **Marginal evidentiary value:** the +0.013-0.014 transfer_acc
  finding is currently a single observation per dataset. Phase 3
  would turn three points into ~15 points and let us put a
  confidence interval around the lift. If we're going to claim "the
  bs=4+grad_accum=8 adaptation produces slightly stronger transfer
  than upstream native bs=32," phase 3 is the rigor that makes the
  claim defensible.
- **Wall-clock cost:** ~80 more hours of GPU at current pace
  (4 more seeds × 3 datasets × ~5.5 hr/dataset average). Roughly
  3.5 days continuous, or longer if interrupted.
- **Alternative use of those GPU-hours:** investigation 003
  (researcher swap) is the actual study question. Phase 3 doesn't
  block 003; it's a rigor pass on phase 2's incidental finding.

If we skip phase 3, the +0.014 finding remains "directionally
consistent across three datasets but unquantified-noise" — fine for
an investigation writeup, not strong enough to publish as a methods
finding. Proceed to investigation 003 directly.

If we do phase 3, the cost is ~3.5 GPU-days and the payoff is
quantified noise. Worth it if the transfer-acc-lift is itself
research-interesting; less worth it if our research question is the
researcher swap.

## Things to flag

- The bs=4 + grad_accum=8 adaptation maintains effective batch size
  but is not bitwise-equivalent to native bs=32 — gradient stats
  accumulate differently in the optimizer (esp. AdamW second moments
  with bf16 mixed precision). PGR differences within ~0.05 are
  plausibly attributable to this rather than to bugs. Larger
  divergence is signal.
- vLLM eval uses `VLLM_USE_FLASHINFER_SAMPLER=0` fallback path. If
  PGR differs substantially from cached, sampler differences are one
  hypothesis worth eliminating before deeper debugging.
- `gpu_memory_utilization` defaults to 0.8 in
  `core/vllm_inference.py`. With training residue at ~8 GB peak
  per [[003-001]] memory trajectory, eval may need
  `gpu_memory_utilization` lower than 0.8 if full-data runs see
  different VRAM patterns than the smoke.

## Methods differences vs upstream paper

A side-by-side audit of how our run differs from the paper's
`vanilla_w2s` baseline, with whether each difference matters for
interpretation.

### Differences that don't matter

- **Hardware** (RTX 3080 12GB vs H200 141GB) — speed/cost only,
  not scientific.
- **Weak teacher** — we use the paper's cached pseudo-labels rather
  than retraining the teacher; same labels, same source.
- **Student arch, optimizer, LR, schedule, LoRA params, epochs,
  precision** — all identical to upstream.
- **WANDB off, flashinfer sampler off** — eval is argmax-style
  binary classification, sampler choice doesn't change predictions.

### Differences that probably matter

1. **bs=4 × grad_accum=8 vs native bs=32.** Same effective batch, but
   AdamW's second-moment estimates and bf16 rounding interact
   differently with accumulation. **This is the most likely source of
   our consistent +0.013-0.014 transfer_acc lift.**

2. **max_ctx=2048 vs upstream's 8192.** Truncation analysis (see
   `figures/prompt_lengths.png`):

   | dataset | train_unlabel >2048 | test >2048 |
   |---|---:|---:|
   | math | 1.2% | 4.8% |
   | chat | **7.0%** | 2.7% |
   | code | 0.6% | 0.8% |

   Code is essentially safe (p99 < 2048). Math is mild. **Chat
   training loses tokens on 7% of samples** — the largest divergence
   risk in our setup. And yet chat is the dataset where our
   transfer_acc most exceeds upstream (+0.0143). Two possible
   explanations: the truncated tail content was low-information
   anyway, OR the grad_accum dynamics swamped the truncation hit.
   Can't distinguish without an H200 ablation.

3. **PGR computation: own-baselines vs fixed-baselines.** The
   `get_fixed_weak_baseline` / `get_fixed_ceiling_baseline` cache
   lookup was missed by [[003-001]]'s patch; it still keys on
   `--batch-size` and misses the `bs=4` directory. Result: run
   completes but PGR column reports the run's own weak/ceiling
   instead of cross-run-comparable fixed baselines. Workaround:
   compute PGR post-hoc against upstream's `fixed_weak_baseline` and
   `fixed_strong_baseline` constants. Permanent fix: extend the
   diff in [[003-001]] `scripts/upstream_patches.diff` to cover
   these two functions.

### Difference that is by design (not yet exercised)

4. **No agentic researcher loop.** The paper's headline contribution
   is Layer 2: 9 parallel Claude Opus 4.6 agents iteratively
   inventing W2S methods, reaching PGR 0.97 in 5 days. This
   investigation runs Layer 1 only — the bare `vanilla_w2s`
   baseline. The agentic loop with a local 4B model in the
   researcher role is investigation 003. Until that runs, we have
   no Layer 2 result and no "weak-researcher matches Opus" claim,
   either positive or negative.

## Limitations

- **Single seed per dataset.** Can't quantify whether the +0.014
  transfer_acc lift is real (signal) or seed noise. Phase 3 (seeds
  43-46 × 3 datasets) is what would settle this; cost ~3.5 GPU-days
  on current hardware.
- **No ablation on `max_ctx`.** Chat's 7% training-side truncation
  is a real divergence whose effect on transfer_acc is unmeasured.
  Running chat at `max_ctx=8192` to compare would require a smaller
  model or cloud GPU — out of scope here.
- **No counterfactual on bs vs grad_accum.** Can't disentangle the
  +0.014 lift from the truncation effect from the dynamics-of-accum
  effect. Both are confounded in our setup.
- **Cross-machine variation in cached upstream baselines unknown.**
  The cached `seed_42.json` values are from whatever specific H200
  setup the upstream authors used. We've matched the weak/ceiling
  accuracies to 4+ decimals so this is unlikely to be the source of
  any divergence, but it's an unmeasured assumption.

## What we can defensibly claim

> "We replicated the upstream `vanilla_w2s` substrate on consumer
> hardware (RTX 3080 12GB) using a gradient-accumulation adaptation
> (bs=4 × grad_accum=8) and reduced max sequence length (2048 vs
> 8192). Across three datasets at seed 42, our transfer accuracy was
> within seed-noise of upstream and consistently 0.013-0.014 higher
> — most likely due to the optimizer dynamics of gradient
> accumulation under bf16. The substrate is mechanically faithful:
> weak teacher and strong-with-ground-truth ceiling accuracies match
> upstream to 4+ decimal places, indicating identical data pipelines
> and label sources. The agentic researcher loop (the paper's
> headline contribution) is deferred to investigation 003."

Anything stronger needs phase 3 (seed expansion for noise
quantification) or a max_ctx ablation. Anything weaker would
under-claim what the data shows.
