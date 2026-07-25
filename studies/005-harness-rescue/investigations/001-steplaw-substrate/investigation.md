---
id: studies/005-harness-rescue/investigations/001-steplaw-substrate
title: StepLaw lookup substrate + minimal-harness baseline
status: complete
parents:
  - studies/005-harness-rescue
children: []
related:
  - studies/004-researcher-diagnostics/investigations/001-mock-substrate-harness
axes:
  llm_capability: medium
  human_capability: high
tags:
  - steplaw
  - substrate
  - regret
created: 2026-06-05
updated: 2026-07-25
---

# Inv 001 — StepLaw lookup substrate + minimal-harness baseline

## Scope

Stand up a real-data research environment behind the Pi harness: the
StepLaw lr/bs loss landscape as a lookup substrate (`SUBSTRATE=steplaw`).
Establish the **minimal-harness baseline** (prompted nemotron, no extra
scaffolding) and the **regret + coverage** metrics. Answer the gating
question for the whole study: does the long-horizon coherence failure
from study 004 reproduce in a *rich* space (~118 configs/env), or was it
an artifact of the toy 12-config landscape?

## What StepLaw is

**StepLaw** = *Predictable Scale, Part I: Optimal Hyperparameter Scaling
Law in LLM Pretraining* ([arXiv 2503.04715](https://arxiv.org/abs/2503.04715),
[step-law/steplaw](https://github.com/step-law/steplaw)). The authors ran a
brute-force empirical study of how the **optimal learning rate and batch
size** depend on model size and data budget: they pretrained **~3,700 LLMs
from scratch** (≈1M H800 GPU-hours, ~100T tokens total), sweeping a grid of
learning rates × batch sizes at many fixed `(N, D)` points, and recorded the
final smoothed validation loss for each run.

Their headline product is the **Step Law** — a fitted scaling rule giving
the optimal `lr` and `bs` as smooth power-law functions of `(N, D)`:
`lr* = f(N, D)`, `bs* = g(D)` (their public tool predicts these to within
~0.1% of the exhaustive-search optimum). Two facts make this an ideal
**substrate** for us:

1. The loss surface they measured is a **real, dense, discrete grid** with a
   **known per-cell loss** — so we can hand an agent an *actual* "train with
   this lr/bs → here's the validation loss" oracle, backed by real GPU runs,
   for **zero compute** (it's a CSV lookup).
2. Each `(N, D)` has a **known optimum** (the grid-min loss), giving a clean
   **simple-regret** signal without us having to define a reward.

What the agent's task is, concretely: it is dropped into **one** `(N, D)`
pretraining setup (model size + token budget fixed) and must find the
`lr, bs` that minimize validation loss, by repeatedly proposing a config and
reading back the measured loss. The cross-`(N, D)` scaling structure (could
the agent *infer* the Step Law itself?) is a richer long-horizon target we
**defer** — inv 001 is single-env tuning.

## The environment

`data/dense_lr_bs_loss.csv` — the vendored dense-model loss grid from
StepLaw (1911 rows; columns include `N`, `D`, `lr`, `bs`, `smooth loss`):

- **17 `(N, D)` environments** (param-size × token-budget). Within each, the
  action space is **lr × bs**, typically **12 lr × 10 bs ≈ 120 configs**
  (range 47–120). The global counts (26 lr, 13 bs) are *not* the per-env axis
  sizes: each env sweeps its own **window** of a shared 14-value √2 lr ladder,
  and some envs record the same physical lr at 3 s.f. and others at 4 s.f.
  (`0.00276` vs `0.002762`, 0.07% apart) — so 14 physical values appear as 26
  distinct strings. Per env the grid is clean. See "Environment catalogue".
- Per-env **known optimum** (grid-min loss) → **simple-regret**.
- This is ~10× the study-004 toy (12 configs). A 50-experiment run touches
  ~40% of a dense env: real room to explore, so repeats signal incoherence,
  not pigeonholing.

**Three envs swept in the baseline** (chosen to span the scaling structure):

| label | N (params) | D (tokens) | D/N | grid | optimum |
|---|---|---|---|---|---|
| Env A (default) | 215M | 100B | 466 (most over-trained env in the CSV) | 12×10 dense (120/120) | 2.342 |
| Env B | 537M | 50B | 93 | 12×10 (119) | 2.217 |
| Env C | 1.07B | 57B | 53 (least over-trained *of these three*) | **5×10 sparse (47)** | 2.121 |

Bigger model + more tokens → lower achievable loss (2.34→2.12). Env C only
swept **5 low learning rates** (≤2e-3) — a real Step-Law signature (optimal
lr falls as N grows), making it a narrower, lower-lr search.

A/B/C are **our labels**; StepLaw names no environments, and the letters
appear nowhere in the CSV or the paper. The canonical identity of an env is
its `(N, D)` pair. Env A is the harness **default** (`src/researcher.ts:14-15`,
`src/society.ts:52-53`), so any run whose command did not set `N`/`D` is Env A.
Three of 17 were swept because seeds-per-env buys statistical power and
17×n=1 does not — not because the substrate is limited to three
(`scripts/steplaw_query.py list-envs` enumerates all of them, and `N`/`D` are
plain env vars). Note `D/N ≈ 18.6` is the compute-balanced (Chinchilla-ish)
family across the full 17; on that scale Env C's 53 is already ~3×
over-trained.

The substrate (`scripts/steplaw_query.py`) is a CSV lookup over the **real
measured grid**: a requested `(lr, bs)` is matched to a grid point within 3%
(log space); **off-grid requests are rejected** (no fabricated loss — StepLaw
has no interpolation), with the nearest valid values returned for recovery.
Dead-simple guts, rich behavior. No AutoLLMResearch / verl dependency.

## Environment catalogue

Every table in this section is generated from the vendored CSV by
`harness/scripts/env_catalogue.py` (stdlib only, no pandas). Regenerate with
`python3 scripts/env_catalogue.py`; `--check` re-asserts the invariants the
prose below relies on and exits non-zero if the data stops supporting them.

### Env A, precisely

| property | value |
|---|---|
| N | 214,663,680 (~215M) **non-embedding** parameters |
| D | 1.0e11 tokens (100B) |
| D/N | 465.8 |
| architecture | `d_model=960`, `ffn_hidden=9368`, 15 heads, 7 layers (fixed across all 120 cells) |
| sequence length | 2048 |
| lr axis | 12 values, 2.441e-4 → 1.105e-2, √2-spaced |
| bs axis | 10 values (sequences): 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| grid | 12 × 10 = **120 cells, all measured** — no holes |
| metric | the `smooth loss` column (smoothed final val loss), not raw `loss` |
| optimum | **2.342014** at lr = 7.812e-3, bs = 1024 |
| worst cell | 2.5332 at lr = 7.812e-3, bs = 32 (spread 0.191) |

The optimum sits at lr index 11/12 and bs index 9/10 — *diagonally adjacent*
to the high-lr/large-bs corner, not at it. The log entries below use "corner"
as shorthand for that region; read it as the region, not the extreme cell.

Env A's flatness is in the **tight** band: only 3/120 cells are within 0.001
of the optimum and 13/120 within 0.005, but 41% are within 0.02 and the median
cell is just 0.029 above optimum. By the wide band Env C is flatter (62%), so
claims that "Env A is the flat env" should cite the 0.005 column, not 0.02.

### All 17 environments

`lr*`/`bs*` are the argmin cell; `med−opt` is the median cell's gap to the
optimum; the last two columns are the fraction of cells within 0.005 and 0.02
of it.

| label | N (non-emb) | D | D/N | cells | grid | lr* | bs* | optimum | med−opt | <.005 | <.02 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| — | 214.7M | 4.0B | 18.6 | 119/120 | 12×10 | 0.00276 | 128 | 2.6214 | 0.098 | 3% | 12% |
| — | 214.7M | 11.4B | 53.1 | 119/120 | 12×10 | 0.00276 | 192 | 2.4847 | 0.063 | 3% | 14% |
| — | 214.7M | 20.0B | 93.2 | 118/120 | 12×10 | 0.00391 | 256 | 2.4401 | 0.059 | 3% | 18% |
| **A** | 214.7M | 100.0B | 465.8 | 120/120 | 12×10 | 0.00781 | 1024 | 2.3420 | 0.029 | 11% | 41% |
| — | 268.3M | 5.0B | 18.6 | 118/120 | 12×10 | 0.00195 | 128 | 2.5577 | 0.094 | 3% | 14% |
| — | 268.3M | 14.2B | 52.9 | 120/120 | 12×10 | 0.00391 | 192 | 2.4319 | 0.055 | 6% | 19% |
| — | 268.3M | 25.0B | 93.2 | 119/120 | 12×10 | 0.00391 | 352 | 2.3849 | 0.049 | 4% | 22% |
| — | 268.3M | 80.0B | 298.2 | 120/120 | 12×10 | 0.00391 | 512 | 2.3050 | 0.032 | 9% | 34% |
| — | 429.3M | 8.0B | 18.6 | 120/120 | 12×10 | 0.00195 | 128 | 2.4373 | 0.069 | 2% | 15% |
| — | 429.3M | 22.7B | 52.9 | 118/120 | 12×10 | 0.00195 | 192 | 2.3226 | 0.042 | 6% | 25% |
| — | 429.3M | 40.0B | 93.2 | 100/110 | 11×10 | 0.00276 | 256 | 2.2749 | 0.041 | 10% | 33% |
| — | 429.3M | 50.0B | 116.5 | 113/120 | 12×10 | 0.00195 | 256 | 2.2566 | 0.031 | 7% | 32% |
| — | 536.9M | 10.0B | 18.6 | 106/120 | 12×10 | 0.000977 | 128 | 2.3833 | 0.065 | 4% | 19% |
| — | 536.9M | 28.4B | 52.9 | 117/120 | 12×10 | 0.00195 | 192 | 2.2629 | 0.043 | 4% | 23% |
| **B** | 536.9M | 50.0B | 93.1 | 119/120 | 12×10 | 0.00276 | 352 | 2.2171 | 0.038 | 7% | 30% |
| — | 1073.7M | 20.0B | 18.6 | 118/120 | 12×10 | 0.00138 | 256 | 2.2255 | 0.042 | 6% | 25% |
| **C** | 1073.7M | 56.9B | 53.0 | 47/50 | 5×10 | 0.00138 | 256 | 2.1206 | 0.015 | 21% | 62% |

### How a row-group is derived

An "environment" is exactly `groupby(N, D)` over the CSV
(`steplaw_query.py:24`). Three things follow:

**N is an architecture, not a knob.** Each of the 5 distinct N values maps to
exactly one shape, and N is that shape's non-embedding parameter count —
`numl × (4·d_model² + 3·d_model·ffn_hidden)`, i.e. attention plus a 3-matrix
(SwiGLU-style) FFN, with embeddings and head excluded. All five reproduce
exactly:

| N (non-emb) | d_model | ffn hidden | heads | layers | recomputed |
|---|---|---|---|---|---|
| 214,663,680 | 960 | 9368 | 15 | 7 | 214,663,680 |
| 268,304,384 | 1024 | 9552 | 16 | 8 | 268,304,384 |
| 429,260,800 | 1280 | 9472 | 10 | 10 | 429,260,800 |
| 536,872,960 | 1280 | 9048 | 10 | 13 | 536,872,960 |
| 1,073,741,824 | 2048 | 8192 | 16 | 16 | 1,073,741,824 |

Note 429M and 537M share `d_model=1280` and differ only in depth — the size
axis is not a clean rescale. Because the shape is fixed within a group, lr and
bs really are the only free variables.

**D comes in ratio families.** The base design is 5 model sizes × 3 token
multiples, `D/N ∈ {18.6, ~53, ~93}` — 15 points less the missing 1074M/~100B
cell = 14 — **plus 3 over-trained extensions**: 429M/50B (117), 268M/80B
(298), and 215M/100B (466), which is Env A.

**Sequence length is 2048, and bs counts sequences.** `bs × ti × 2048` lands
within 0.4% of D for all 17 groups (exactly, for the 13 whose D isn't rounded
to 3 s.f.). The token budget is held fixed across the bs axis by varying step
count: in Env A, `ti` runs 1,525,878 at bs=32 down to 23,841 at bs=2048.

### Axis windows slide (the Step Law, visible in the raw grid)

Envs do **not** share an action space. There are 14 physical lr values
globally, √2-spaced from 2.441e-4 to 2.21e-2; each env sweeps a 12-value
*window* of that ladder, and the window shifts down as N and D grow:

| N | D | lr window (12 unless noted) | bs values |
|---|---|---|---|
| 214.7M | 4.0B | 0.000488 … 0.0221 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 214.7M | 11.4B | 0.000488 … 0.0221 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 214.7M | 20.0B | 0.000488 … 0.0221 | 16, 24, 32, 64, 96, 128, 192, 256, 512, 1024 |
| 214.7M | 100.0B | 0.000244 … 0.0111 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 268.3M | 5.0B | 0.000488 … 0.0221 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 268.3M | 14.2B | 0.000488 … 0.0221 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 268.3M | 25.0B | 0.000488 … 0.0221 | 16, 32, 64, 96, 128, 192, 256, 352, 512, 1024 |
| 268.3M | 80.0B | 0.000244 … 0.0111 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 429.3M | 8.0B | 0.000345 … 0.0156 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 429.3M | 22.7B | 0.000345 … 0.0156 | 32, 64, 96, 128, 192, 256, 352, 512, 1024, 2048 |
| 429.3M | 40.0B | 0.000488 … 0.0156 (11 values) | 32, 64, 96, 128, 192, 256, 352, 512, 1024, 2048 |
| 429.3M | 50.0B | 0.000244 … 0.0111 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 536.9M | 10.0B | 0.000345 … 0.0156 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 536.9M | 28.4B | 0.000345 … 0.0156 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 536.9M | 50.0B | 0.000345 … 0.0156 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 1073.7M | 20.0B | 0.000244 … 0.0111 | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |
| 1073.7M | 56.9B | 0.000488 … 0.00195 (5 values) | 32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048 |

Env A's window is the *lowest* of the 215M envs (shifted two notches below
215M/4B), yet its optimum sits near the window's top at 7.812e-3 — the largest
`lr*` of all 17. bs is usually `32…2048`, except three envs that swap in
16/24/96. Reading the `lr*`/`bs*` columns of the catalogue: `lr*` falls with N
at fixed ratio (2.76e-3 → 9.77e-4 across the 18.6 family) and rises with D at
fixed N (2.76e-3 → 7.81e-3 across the 215M family), while `bs*` tracks D almost
alone (128 at ≤10B → 1024 at 100B). That is StepLaw's fitted
`lr* = f(N, D)`, `bs* = g(D)` showing up before any fitting.

### Holes, and what they mean for the agent

Only 4 of 17 grids are complete (Env A, 268M/14.2B, 268M/80B, 429M/8B). The
rest carry 1–14 unmeasured cells, scattered rather than structured — worst are
537M/10B (14 holes across 7 different lr values) and 429M/40B (10, including
the whole lowest-lr row). There are **no** duplicate `(N,D,lr,bs)` keys
anywhere in the 1911 rows.

Holes surface to the agent as `pair_not_measured` — a rejection distinct from
`off_grid`, carrying the batch sizes actually measured at that lr. **Env A has
zero holes**, so no Env A run ever exercised that path; any claim about
rejection-handling behavior rests on Env B/C evidence only.

### What the CSV is not

`dense_lr_bs_loss.csv` is 1911 rows = the **dense** joint lr×bs sweep at 17
`(N, D)` points. StepLaw's headline "3,700 LLMs / ~1M H800-hours / ~100T
tokens" covers their whole program: their repo also ships a **MoE** smooth-loss
CSV (not vendored here) and `1004_fitted_lr_bs_scaling_model_parameters.csv`
(1,000 bootstrap fits), on top of runs behind other parts of the paper. The
exact decomposition of the 3,700 should be cited from the paper, not inferred
from this file.

## Metrics

- **simple_regret** = best-found-loss − per-env optimum loss.
- **coverage** = unique grid points tried / configs available in env.
- **redundant rate** (kept for continuity with study 004) — but now read
  against a non-exhaustible space.
- regret-vs-budget curve.

## Methods

**Substrate.** `scripts/steplaw_query.py` — per-(N,D) lookup over the vendored
CSV. The action space is the **real measured grid** (≈12 lr × 10 bs, ~99%
complete per env). Off-grid requests are **rejected** (3% log-tolerance match),
returning the nearest valid lr/bs — no loss is fabricated. This follows
StepLaw's own convention: the dataset is an exhaustive discrete grid with no
interpolation; their public tool is a *formula predictor*, not a loss lookup.
`optimum_loss` = per-env grid-min (the regret denominator).

**Minimal-harness baseline.** `src/researcher.ts` — a single Pi `agent.prompt()`
(Pi's internal loop runs experiments until the agent stops). Two tools:
`run_config(lr, bs)` → val_loss (or an off-grid rejection that costs no budget),
and `finish(best_lr, best_bs)` → returns `terminate:true`. Guards: an
experiment-count ceiling (`BUDGET`, default 50; hard stop at +10) as the primary
bound, plus a **total-call cap** and a **consecutive-rejection guard** (stop
after 8 invalid requests in a row — added after a gemini run looped on one
unmeasured pair 694× until the wall-clock), and a wall-clock timeout (`WALL_MS`,
default 5 min in sim) as insurance that transfers to the real-W2S run. The agent
is told the budget once, in the system prompt — **no per-turn counting**.

**Model configs.** nemotron-3-nano:4b via desktop ollama; gemini-3.1-flash-lite
via API ($0.25/$1.50/$0.025 per 1M in/out/cache — matches the pi-ai catalog).
The baseline gemini runs ran with **reasoning off** (the Pi Agent defaults
`thinkingLevel: "off"`, and the model object must set `reasoning: true`); a
`REASONING`/`THINK` toggle now enables gemini thought-summaries (flash-lite
supports minimal/low/medium/high). nemotron exposes its chain-of-thought as
`thinking` blocks regardless. This was a config choice, **not** a tracing bug —
the tracer captures every content block the model emits.

**Three terminal outcomes** fall out and are the core coherence signal:
`finished` (called `finish`), `stalled` (yielded without finishing, before the
cap), `ceiling` (still exploring when a guard fired). We also log
`invalid_requests` (off-grid attempts) and `claim_matches_best` (did the config
the agent reported at `finish` match its actual best trajectory point).

**Renderer.** `scripts/render_compare.py` → self-contained side-by-side HTML of
two traces (move-coded steps + outcome banner), in the agent-trace-report style.

## Differences from the W2S task (be explicit)

- Metric: StepLaw minimizes **loss**; W2S maximizes **PGR**.
- Levers: StepLaw = lr, bs (2D, dense). W2S = train/test-size, epochs, lr,
  batch (higher-D). So StepLaw is a *narrower, denser* recipe-tuning
  problem — appropriate as the cheap development proxy.
- No weak-teacher dynamic; deterministic lookup (no real errors / OOM /
  timeouts) — so this env tests the **coherence/exploration** half of the
  harness, not the **actuation** half (that's the real-W2S run, inv 003).

## Status / log

- 2026-06-05 — Investigation scaffolded; StepLaw CSV vendored. Building
  the lookup substrate + minimal-harness baseline.
- 2026-06-06 — **First clean baseline (n=1 each, env N=214663680
  D=1e11, budget 50, temp default).** Earlier external-loop harness
  produced confounded behavior (nemotron "front-loaded" + "confabulated");
  root-caused to a harness bug — an external N-of-8 re-prompt loop wrapped
  around Pi's *own* internal agent loop, plus a silent nearest-neighbor
  snap. Rebuilt as single-conversation + finish-tool + off-grid rejection.
  On the fixed harness, with identical prompts:
  - **gemini-3.1-flash-lite → `finished`**: 13 experiments, found the
    **true optimum** (regret ≈ 0), 0 invalid, 0 repeats, reported config
    matched its actual best.
  - **nemotron-3-nano:4b → `stalled`**: 21 coherent experiments (no
    front-load, no confabulation, 0 invalid, 0 repeats), correctly stated
    its best **in prose** — but **never called `finish`**. Also
    basin-trapped at lr=2.76e-3/bs=512 (regret 0.0016); never escaped to
    the high-lr/high-bs corner gemini reached.
  - Read: the study-004 pathologies were substantially *harness artifacts*.
    The residual weak-model failure in a rich space is an **actuation gap**
    (has the answer + intent to stop, fails to emit the terminal tool) and
    **basin-trapping**, not front-loading/confabulation. n=1 — needs
    replication across seeds/envs before claiming the pattern.
- 2026-06-06 — **Replication sweep: nemotron ×20 (default env) + gemini
  ×5 across 3 envs.** Substrate bug found+fixed mid-sweep: a degenerate
  retry loop (gemini re-requested one *unmeasured* pair 694× on the sparse
  env) was bounded only by the 15-min wall-clock → 1.4M tokens, $1.08, one
  run. Fix: consecutive-rejection guard (stop at 8), total-call cap, sim
  wall-clock 15→5 min, and rejection messages now return the batch sizes
  actually measured at that lr. Re-verified: same env+seed then finished at
  the true optimum for $0.028. Clean results:

  | model | env | n | outcomes | regret min/med/max | mean exp |
  |---|---|---|---|---|---|
  | gemini-flash-lite | dense 214M/1e11 | 5 | fin 3 / stall 2 | 0.000/0.0003/0.0049 | 18 |
  | gemini-flash-lite | 537M/5e10 | 5 | fin 5 | ~0 / ~0 / ~0 | 29 |
  | gemini-flash-lite | sparse 1.07B/5.7e10 | 5 | fin 5 | ~0 / ~0 / ~0 | 38 |
  | nemotron-4b | dense 214M/1e11 | 20 | fin 11 / **stall 9** | 0.000/**0.0060**/0.0730 | 15 |

  - **Reliability:** gemini finishes 13/15 (87%); nemotron 11/20 (**55%**) —
    it stalls ~45% of the time (fails to call `finish`).
  - **Quality:** gemini median regret ≈ 0 (finds the optimum); nemotron
    median 0.006, max 0.073 — far worse and high-variance / basin-trapped.
  - **Claim fidelity:** *both* are 100% claim-correct when they finish
    (13/13, 11/11). So nemotron's problem is **not** mis-reporting its best —
    it knows its best; it fails to (a) *emit* `finish` and (b) explore widely.
  - gemini also churns (mean 8–16 repeats/run) — not perfectly efficient.
  - Cost: gemini sweep ≈ $0.23 (+$1.08 wasted pre-fix); nemotron free (local).
- 2026-06-07 — **Behavior deep-dive + artifacts + docs.** Figures in
  `assets/`: `fig_baseline` (regret + outcome, from checked-in
  `data/baseline_runs.csv`), `fig_trajectories` (20 nemotron runs over the
  real Env A loss surface), `nemotron_cases.html` (stall / lucky-win /
  early-bad-finish traces with reasoning). Behavior stats (20 runs): search is
  competent — **66% coordinate moves, 46% improving steps**, ~7.5/12 lr and
  ~5.2/10 bs touched — but **only 10/20 reach the optimum corner**. Refinement
  from the figure: on the flat over-trained Env A, **both** models stall ~40%
  (gemini 2/5, nemotron 9/20) — *stalling tracks landscape flatness*, not just
  model weakness; gemini's 87% overall finish rate comes from the easier
  Envs B/C. Spun up **inv 002** (rich-harness ablation, literature-grounded).

- 2026-06-07 — **First-round strategy analysis (subagent, 20 nemotron
  traces) sharpens the failure modes.** (1) The **"stall" is mostly an
  actuation artifact**: 6 of 8 stalls (s6,s9,s12,s17,s18,s19) reached a
  confident conclusion and wrote a final answer **in prose** but never called
  `finish` — including s19, which had found the *exact optimum*. Only s1
  (generation cutoff) and s16 (malformed tool call) are true loop breakdowns.
  So search competence and termination competence are **decoupled**. (2)
  **Opening batch size is the single strongest predictor of regret**: seeds
  that placed bs≈1024 early (s3,s11,s20) reached the optimum; seeds that
  **froze one axis** in round 1 (bs=2048: s2,s13; bs=128: s4,s7,s17) capped
  out at regret ~0.014–0.016. (3) Acknowledging the combinatorial space
  ("130>50") is **NOT** predictive — good and bad seeds both noted it. Four
  ranked harness nudges fall out → inv 002 (force tool-actuated finish; forbid
  early axis-locking; seed the high-lr/large-bs corner; don't stop while
  improving with budget left). Charts now mark reported-best (pink ◇) and
  optimum-reach step.

- 2026-06-07 — **Reasoning-level sweep (off/low/medium × {nemotron, gemini}
  × Env A × 15 seeds = 90 runs).** Control: nemotron via `reasoning_effort`
  none/low/medium (true-off routed through the model config — Pi's stock `/v1`
  has no off, so `thinkingLevelMap` maps a sentinel level → `reasoning_effort:"none"`);
  gemini via `thinkingLevel` off/low/medium. Result (`assets/fig_reasoning`,
  from `data/reasoning_runs.csv`):

  | model | level | finished | regret med | mean exp |
  |---|---|---|---|---|
  | nemotron-4b | off | 8/15 | **0.0256** | **5.7** |
  | nemotron-4b | low | 9/15 | 0.0016 | 13.6 |
  | nemotron-4b | medium | 10/15 | 0.0016 | 13.3 |
  | nemotron-4b | high | 7/15 | 0.0016 | 15.1 |
  | gemini | off | 14/15 | 0.0003 | **33.6** |
  | gemini | low | 15/15 | ~0 | 12.6 |
  | gemini | medium | 15/15 | ~0 | 14.1 |

  (nemotron mean regret: off 0.0255, low 0.0076, medium 0.0085, **high 0.0043**;
  max: off 0.073 → high **0.028**. So past "low", more reasoning doesn't move the
  median but **tightens the bad tail** — high is the most *consistent*, fewest
  disaster runs — at no stall-rate benefit, 53% stalled.)

  - **Reasoning is load-bearing for exploration, and the weak model is far more
    sensitive** — nemotron off→on ≈ **16× better median regret** (0.0256→0.0016)
    and doubles exploration (5.7→13.6 exp); gemini is already near-perfect but
    reasoning removes its last stall and its churn. Supports the scale-sensitivity
    thesis on the *reasoning* axis [[project_harness_scale_interaction]].
  - **Opposite off-failure by scale:** reasoning-off makes the *weak* model
    **under-explore / give up** (5.7 exp) and the *strong* model **over-explore
    inefficiently** (33.6 exp, churning) — same near-optimal answer, 6× the work.
  - **low ≈ medium** for both — diminishing returns; minimal reasoning suffices.
  - **Reasoning does NOT fix the stall** — nemotron stays ~33–47% stalled across
    levels. The actuation gap is orthogonal to reasoning; it needs the harness
    (R4), not more thinking.

## Things to flag

- Off-grid requests are **rejected** (no fabricated loss), matching StepLaw's
  discrete-grid reality. Earlier nearest-neighbor *snapping* fabricated a
  neighbor's loss and confused the weak model — dropped.
- The baseline is **n=20 (nemotron) / n=5 (gemini)** per env; gemini Env A
  (n=5) is thin for the "both stall on flat envs" claim — worth more seeds.
- Gemini baseline ran **reasoning-off** (unintended). A reasoning-on arm would
  be a fairer "natural config" comparison and would expose its reasoning for
  the artifacts.
- **Env A/B/C are repo-local labels** — StepLaw names no environments. Cite
  envs by `(N, D)` in anything external. Two earlier phrasings were corrected
  against the data when the catalogue was added: Env C's `D/N=53` was called
  "compute-balanced" (the compute-balanced family across the full 17 is
  `D/N≈18.6`; 53 is ~3× over-trained), and the global "26 lr / 13 bs" counts
  were called float-precision duplicates (they are *sliding per-env windows*
  over a 14-value ladder, plus a 3-vs-4-s.f. recording difference).
