# CUAD baseline smoke test — all three released checkpoints, on the 3080

Companion to `cuad-baseline-comparability.md`. That document was an assessment
with no models run. This one is the execution: environment built, all three
released checkpoints run end to end on the desktop GPU, and every quantitative
claim in the assessment checked against measurement.

Run date 2026-08-16. Desktop: RTX 3080 12 GB (sm_86), driver 591.86, WSL2,
12 CPU cores, 23 GB RAM visible, 750 GB free. Nothing was run on `test`.

AI Assistant Used: Claude Code

---

## Verdict

**Go.** All three checkpoints run end to end on the 3080 under a pinned
2021-era stack, produce structurally sane n-best output exactly as the
assessment describes, and score cleanly through unmodified `evaluate.py`. The
environment took one real fight (`np.int`) and one substitution
(`transformers` 4.17 rather than 4.12) and was working inside an hour. Modal is
not needed.

Three findings change the plan for the full run:

1. **The Table 2 reproduction gate costs zero GPU time.** Every released
   checkpoint ships the authors' own `nbest_predictions_.json`,
   `predictions_.json` and `null_odds_.json` — 4,182 questions each
   (102 test contracts × 41 categories). The gate is `evaluate.py` on those
   files against `test.json`. It is still G4-gated because it reads `test`, but
   it is a five-minute CPU job, not part of the inference run, and it should be
   the *first* thing done at G4 — before spending a single GPU-hour.
2. **The full 41-category run must be sharded, and not for the reason given.**
   Feature-conversion CPU time is not the bottleneck the assessment feared; RAM
   is worse than it feared. Measured peak RSS grows at 93 KB per feature, which
   puts an unsharded 41-category run at ~18 GB peak on a 23 GB box. Per-category
   sharding drops that to under 5 GB and is trivial to script.
3. **`train.py` has no fp16 eval path at all**, so the assessment's headline
   ~3.4 h figure (which assumed fp16) is unreachable without patching. Measured
   fp32 wall-clock for all three at 41 categories is **~5.6 h**, which sits
   between the assessment's two estimates and is an overnight job as it said.

---

## 1. What was installed, and what fought back

Working directory on the desktop: `/home/tlifke/Projects/cuad-baseline`.

```
repo/    github.com/TheAtticusProject/cuad @ 67faa0e (2021-10-21)
ckpt/    roberta-base 521M, roberta-large 1.4G, deberta-v2-xlarge 3.4G
.venv/   uv-managed, Python 3.10.12
```

Final environment:

| package | version | note |
|---|---|---|
| `torch` | **1.13.1+cu117** | as the assessment recommended; works on sm_86 |
| `transformers` | **4.17.0** | *not* 4.12.x — see below |
| `tokenizers` | 0.13.3 | pulled by the above |
| `numpy` | **1.23.5** | hard pin, see below |
| `huggingface-hub` | 0.4.0 | 4.17 rejects modern hub |
| `sentencepiece` | 0.2.2 | DeBERTa-v2 tokenizer |
| `protobuf` | 3.20.3 | pinned `<4` |
| `scikit-learn` / `pandas` | 1.7.2 / 2.3.3 | `evaluate.py` only |

Setup is scripted at `scripts/cuad-baseline/setup_desktop_env.sh` and is
idempotent.

### What broke

**(a) `transformers==4.12.5` is not installable on Python 3.10.** It requires
`tokenizers<0.11`, whose newest release (0.10.3, Aug 2021) predates CPython
3.10 and ships no cp310 wheel. `uv` fell through to a source build and died on
`error: can't find Rust compiler`. Two ways out — drop to Python 3.9, or move
transformers forward to a version whose `tokenizers` floor has cp310 wheels.
I took the second: **4.17.0**. It keeps the entire API surface `train.py`
touches (`AdamW`, `WEIGHTS_NAME`, `is_main_process`, top-level
`squad_convert_examples_to_features`, `transformers.models.bert.BasicTokenizer`,
`SquadV2Processor`), so `train.py` and `utils.py` ran **completely unmodified**
— no import patches, no `weights_only` accommodation, no source edits of any
kind. This is a correction to the assessment's §3.5, which expected the
"pin old" path to require 4.12.x specifically and the "modernise" path to
require ~5 import patches. Neither is true: 4.17 is a free lunch.

**(b) `np.int` — the only real fight.** DeBERTa-v2 fails on the first forward
pass:

```
transformers/models/deberta_v2/modeling_deberta_v2.py:537, in make_log_bucket_position
    bucket_pos = np.where(abs_pos <= mid, relative_pos, log_pos * sign).astype(np.int)
AttributeError: module 'numpy' has no attribute 'int'.
```

`np.int` was removed in numpy 1.24. Fix is `numpy==1.23.5` (the last release
that still carries the alias). Both RoBERTas run fine on modern numpy, so this
bites only on the third model — which is exactly the sort of thing that would
have burned an hour if discovered mid-run rather than in a smoke test.

**(c) `evaluate.py` is not importable from an arbitrary cwd.** It calls
`get_questions_from_csv()` at module scope, which reads
`./category_descriptions.csv` relative to cwd. Any wrapper must `cd` into the
repo. `scripts/cuad-baseline/score_slice.py` does.

**(d) The feature cache key is unsafe for sharding.** `load_and_cache_examples`
builds `cached_dev_{model_basename}_{max_seq_length}` — the **predict file is
not in the key**. A per-category sharded loop that reuses one `--cache_dir`
will silently score every shard against shard 1's features. Use a per-shard
`--cache_dir`, or delete the cache between shards, or pass `--overwrite_cache`.
`scripts/cuad-baseline/run_smoke.sh` removes it each run.

### What did not break

- `torch 1.13.1+cu117` on sm_86: fine, first try, `torch.cuda.get_device_capability` → `(8, 6)`.
- WSL2: no measurable friction.
- No HuggingFace download was needed at any point — the Zenodo zips are
  self-contained (config, weights, tokenizer, and spm model for DeBERTa). The
  `HF_TOKEN` in `.env` was never required and never used.
- apex: never touched. `--fp16` in `train.py` only guards the *training* path;
  the eval path has no autocast anywhere, so eval is unconditionally fp32.
  Assessment item 6 in "things I made up" is confirmed — and it matters more
  than it looks (§4).

### Correction to the assessment's provenance note

The assessment says the repo's default branch was "last pushed 2023-07-13". The
cloned `main` HEAD is `67faa0e`, dated **2021-10-21**. The 2023 date is GitHub
repository metadata, not a commit on `main`. Immaterial, but worth not
repeating.

---

## 2. Smoke slices

Two slices, both built from `harness_val` only, by
`scripts/cuad-baseline/make_smoke_slice.py` (which refuses `--split test`
outright):

| slice | contracts | categories | questions |
|---|---|---|---|
| `smoke` | 2 (median + p90 by length; 30 K + 120 K chars) | Governing Law, Agreement Date, Anti-Assignment, License Grant | 8 |
| `throughput` | all 40 `harness_val` | same 4 | 160 |

All parameters from `run.sh`: `--max_seq_length 512 --max_answer_length 512
--doc_stride 256 --n_best_size 20 --version_2_with_negative`, batch 16,
`--threads 12`. Confirmed against the upstream `run.sh` — the assessment quoted
these correctly.

**Reminder, and it is load-bearing: none of the scores below mean anything.**
`harness_val` sits inside CUAD's official train split, i.e. inside these
models' fine-tuning data. They are wiring checks. The memorisation is visible
and is itself the evidence that the wiring is right (§5).

---

## 3. Per-model results

Measured on the 160-question `throughput` slice (40 contracts × 4 categories),
which gives steady-state numbers; the 8-question slice is warmup-dominated.

| | RoBERTa-base | RoBERTa-large | DeBERTa-v2-xlarge |
|---|---|---|---|
| windows (features) | 5,545 | 5,545 | 5,111 |
| GPU eval wall | 45.0 s | 140.9 s | 352.9 s |
| **s / window** | **0.00812** | **0.02541** | **0.06905** |
| effective TFLOPS | 11.9 | 13.2 | 11.5 |
| peak VRAM, total | 2,920 MiB | 3,931 MiB | 9,071 MiB |
| **peak VRAM, net of 1,168 MiB idle Ollama** | **1,752 MiB** | **2,763 MiB** | **7,903 MiB** |
| feature conversion (12 threads) | 48 s | 47 s | 40 s |
| total wall for the slice | 103 s | 202 s | 413 s |

VRAM notes. The assessment's table (fp32 weights 0.50 / 1.42 / 3.6 GB, "fits
with wide margin") is right about the weights and **low by roughly 2× on actual
footprint at batch 16** — activations and DeBERTa's disentangled-attention
score matrices cost more than the "few hundred MB transient" it estimated.
Still comfortable: DeBERTa at 7.9 GB net leaves ~3 GB headroom on a 12 GB card
with Ollama resident. Batch 32 at fp32 would be tight to impossible for
DeBERTa; batch 16 is the right default and is what the scripts use.

Structural check on the output, against the assessment's §1.3 description:
n-best lists are **20 or 21 entries deep** (21 when HF appends the null
candidate — the assessment said 20; the off-by-one is harmless but real), the
empty string participates with a probability, and `null_odds_.json` is written
separately. All exactly as described.

### Example predictions

RoBERTa-base, 2-contract slice (`probability`, text):

```
CcRealEstateIncomeFundadv_..._Marketing Agreement__Governing Law   null_odds -14.04
  0.9998  'This Agreement and the application and interpretation hereof shall be
           governed exclusively by the laws of the State of Colorado.'
  0.0001  'This'
  0.0001  '.'

CcRealEstateIncomeFundadv_..._Marketing Agreement__Agreement Date   null_odds -15.67
  0.9575  '24t h day of August 2018,'
  0.0412  'the 24t h day of August 2018,'

CcRealEstateIncomeFundadv_..._Marketing Agreement__License Grant    null_odds +5.89
  0.9971  ''
  0.0028  'S2K shall be entitled to produce materials ("Fund Materials") for use in
           marketing a Fund as described herein, ...'
```

DeBERTa-v2-xlarge, 40-contract slice:

```
MACY_S,INC_05_11_2020-EX-99.4-JOINT FILING AGREEMENT__Agreement Date   null_odds -12.41
  0.9798  'May 11, 2020.'
  0.0155  'IN WITNESS WHEREOF, the undersigned hereby execute this agreement as of May 11, 2020.'

MACY_S,INC_05_11_2020-EX-99.4-JOINT FILING AGREEMENT__Governing Law    null_odds +13.33
  1.0000  ''
  0.0000  'JOINT FILING AGREEMENT'

NETZEEINC_11_14_2002-EX-10.3-MAINTENANCE AGREEMENT__Governing Law      null_odds -10.78
  0.9955  'THIS MAINTENANCE AGREEMENT IS GOVERNED BY, AND SHALL BE SUBJECT TO, THE
           TERMS AND CONDITIONS OF THE MASTER AGREEMENT BETWEEN NETZEE AND BANKERS BANK...'
```

Three things to eyeball here, all of which match the assessment's model of the
system:

- **Spans are verbatim contract text**, extracted, never generated. Confirms
  §2.1's point that their scorer cannot see hallucination and therefore
  flatters us on that axis.
- **`24t h day of August 2018,`** — the mangled spacing is in the source
  contract, and their span carries it through. Our verbatim-fidelity metric will
  have to handle the same corpus artifacts.
- **Absence lands on the empty string with high probability and a large positive
  `null_odds`** (`+5.9`, `+13.3`, `+17.2`), while presence gives large negative
  `null_odds`. The null-score-diff signal is real, well separated, and usable
  for Direction A exactly as §2.2 proposed. This is a genuinely well-behaved
  absence signal, better separated than I expected from reading the assessment.

---

## 4. Scoring path validated; corrected extrapolation

### `evaluate.py` runs unmodified

`scripts/cuad-baseline/score_slice.py` imports the upstream module and calls
`get_answers` / `get_precisions_recalls` / `get_aupr` / `get_prec_at_recall`
with no changes. The question-id assertion
(`sorted(pred.keys()) == sorted(gt.keys())`) passes for all three models. On the
160-question `harness_val` slice:

| model | AUPR | P@80%R | max recall |
|---|---|---|---|
| RoBERTa-base | 0.850 | 0.797 | 0.970 |
| RoBERTa-large | 0.907 | 0.839 | 0.982 |
| DeBERTa-v2-xlarge | 0.884 | 0.821 | 0.988 |

Against Table 2's test-split 0.426 / 0.482 / 0.478. **These numbers are
meaningless as scores and are reported only as evidence.** A ~2× inflation over
published test performance, with the model ordering scrambled
(large > xlarge > base rather than large ≳ xlarge > base), is precisely the
memorisation signature you expect when scoring a fine-tuned model on its own
training data. It confirms both that the scoring path is wired correctly and
that the assessment's §6 governance argument is not theoretical — there is no
non-`test` split on which these models are honest.

### The substring category filter — resolved

The assessment flagged that `compute_precision_recall`'s category filter is
`if category and category not in key`, a substring test against question ids
that embed contract titles, and asked for the 12-way partition to be verified.
Checked exhaustively over all 20,910 CUAD question ids:

- **40 of 41 categories partition exactly.**
- **`Insurance` is the sole leak**: 510 exact vs 590 substring matches — 80
  extra questions pulled in from contract titles containing the word.
- **None of our 12 subset categories leak.** `evaluate.py`'s filter can be used
  unmodified for the 12-category recomputation.

If the 41-category reproduction is ever reported per-category, `Insurance` needs
the filter tightened to `key.rsplit("__", 1)[-1] == category`. It does not
affect the pooled Table 2 numbers, which use no filter.

### Corrected sizing

The assessment's window counts come from an assumed 4.0 / 4.3 chars-per-token.
Measured on the 40 `harness_val` contracts (1,759,190 chars):

| tokenizer | assumed c/t | **measured c/t** | error |
|---|---|---|---|
| RoBERTa BPE | 4.0 | **4.342** | tokens over-counted 8.5% |
| DeBERTa-v2 SentencePiece | 4.3 | **5.323** | tokens over-counted 24% |

DeBERTa's SentencePiece is markedly more efficient on legalese than assumed.
Combining that with the *measured* HF feature counts (which run ~12% below the
`N/256 + 1` formula), and applying to `test`'s 4,778,515 characters — a figure
already published in the assessment's §3.3 from the manifest, no test text read:

| | assessment, 41 cats | **measured-basis, 41 cats** | **12 cats** |
|---|---|---|---|
| RoBERTa windows | 190,486 | **~154,400** | **~45,200** |
| DeBERTa windows | 177,079 | **~142,300** | **~41,700** |

### Corrected time

Using measured s/window, plus the measured ~11 ms/window of non-GPU overhead
(feature conversion + `torch.save` + post-processing), which was a remarkably
stable ~60 s per 5.5 K windows across all three models:

| model | GPU, 41 cats | **wall, 41 cats** | **wall, 12 cats** |
|---|---|---|---|
| RoBERTa-base | 0.35 h | **0.82 h** | 0.24 h |
| RoBERTa-large | 1.09 h | **1.56 h** | 0.46 h |
| DeBERTa-v2-xlarge | 2.73 h | **3.20 h** | 0.94 h |
| **all three** | **4.17 h** | **~5.6 h** | **~1.6 h** |

Against the assessment: its **fp16 figure of ~3.4 h is unreachable** — there is
no fp16 eval path in `train.py`, and adding one is an unforced modification of
the reference implementation right before a reproduction gate. Its fp32 figure
of ~6.9 h is 23% pessimistic. **Budget ~5.6 h fp32 for all three at 41
categories, ~1.6 h at 12.** Still an overnight job; the conclusion "feasibility
is not the constraint" survives intact.

On MFU: measured effective throughput is **11.5–13.2 TFLOPS fp32/TF32**, i.e.
~40% of the 3080's ~30 TFLOPS fp32 peak. The assessment's ~30% MFU assumption
was slightly conservative rather than optimistic — it just applied it to an fp16
peak the code cannot reach. Two errors partially cancelling is why its fp32
number came out close.

### Corrected bottlenecks — both §3.4 caveats need revising

**(a) Feature conversion is NOT the bottleneck.** Measured on 5,545 windows:

| threads | conversion time | per window |
|---|---|---|
| 1 | 62 s | 11.2 ms |
| 12 | 48 s | 8.7 ms |

Single-threaded conversion of a full 41-category run is ~29 min per RoBERTa
model — real, but a fraction of the 3.2 h DeBERTa GPU pass, not "potentially
longer than the GPU work." And `--threads` buys only **1.29×** even at 12
threads, so the assessment's recommended `--threads 8–16` fix is worth having
but is not the difference between viable and not. Set `--threads 12`; do not
expect much.

**(b) RAM is worse than estimated, and it is the reason to shard.** Measured
peak RSS at two slice sizes gives a clean line:

- 472 windows → 3.657 GB
- 5,545 windows → 4.129 GB
- **slope 93 KB per window**, intercept 3.61 GB (torch + CUDA context + model)

Extrapolated to 41 categories on `test` (~154 K windows): **~18 GB peak RSS**,
against 23 GB visible to WSL and 8 GB swap. That is not a comfortable margin —
and the assessment's ~10 GB estimate was low by roughly 2×. Its *direction* was
right and its recommendation (shard per category) is not optional, it is
required. Per-category sharding caps peak at ~3.9 GB. The on-disk feature cache
is 32.5 KB/window → ~5 GB per model unsharded; irrelevant on 750 GB free, but it
is written and re-read, so sharding also saves that I/O.

---

## 5. Blockers for reproducing Table 2

None found. Specifically checked:

1. **The checkpoints ship the authors' own predictions.** All three contain
   `nbest_predictions_.json` with **4,182 keys** = 102 × 41, plus
   `predictions_.json` and `null_odds_.json`, dated 2021-03-10. This is the
   released test-split inference output. **The reproduction gate is therefore a
   CPU job on files we already have**, and should be run first at G4. It also
   gives a second, stronger check: our own re-run's n-best can be diffed against
   theirs question-by-question, which distinguishes "we reproduced the number"
   from "we reproduced the computation".
2. n-best depth in the shipped roberta-base file varies (2–21) where
   roberta-large is uniformly 20–21. Not a defect — shallow lists occur where
   fewer distinct valid spans survive — but if a re-run produces uniformly deep
   lists where theirs are shallow, that is a signal worth chasing, not ignoring.
3. Question-id format matches between our generated slices and the released
   files (`{contract_title}__{Category}`), so the `assert sorted(keys) ==
   sorted(keys)` in `get_results` should hold on a full `test` run.
4. `evaluate.py`'s two code quirks noted in the assessment (`confs` off-by-one
   in the returned confidence, `preds[text] = prob` keeping last rather than
   max) are confirmed present in the cloned source and affect only the returned
   `conf` value, not any reported precision, recall, or AUPR.

The one residual risk the smoke cannot retire: whether the released weights
actually reproduce 42.6 / 48.2 / 47.8. Item 10 of the assessment's own
"things I made up" list. But per (1) that check is now cheap and GPU-free, so
it can be settled at G4 before any inference is scheduled.

---

## 6. Go / no-go

**Go, with these changes to the plan:**

1. At G4, **run the reproduction gate on the shipped prediction files first**
   (CPU, minutes). If Table 2 does not fall out, stop there and fall back to the
   assessment's option 3 — no GPU time spent.
2. Only then run inference, **sharded per category** (41 shards), each with its
   own `--cache_dir` or an explicit cache delete. Budget **~5.6 h** for all
   three at 41 categories on the 3080, fp32, batch 16, `--threads 12`.
3. Do not add an fp16/autocast eval path before the reproduction gate. After it
   passes, if throughput matters, it is a legitimate optimisation.
4. Keep `numpy==1.23.5` pinned. It is the only thing standing between
   DeBERTa-v2 and an immediate crash.

Modal is not needed. The environment is built, reproducible from
`scripts/cuad-baseline/setup_desktop_env.sh`, and the box has 750 GB free.

---

## Artifacts

Under `studies/008-principled-extraction-cuad/scripts/cuad-baseline/`:

| script | purpose |
|---|---|
| `setup_desktop_env.sh` | clone, venv, pinned installs, checkpoint fetch/unzip |
| `make_smoke_slice.py` | build a SQuAD-format slice from a named split; refuses `test` |
| `run_smoke.sh` | run `train.py --do_eval` with `run.sh` parameters, sampling VRAM |
| `inspect_preds.py` | dump top-k n-best entries + null odds per question |
| `score_slice.py` | run upstream `evaluate.py` on a slice, pooled and per-category |
| `collect_metrics.py` | parse windows / GPU time / wall / peak VRAM out of run logs |
| `measure_tokenization.py` | chars-per-token and window counts for a split |

Desktop state left in place at `/home/tlifke/Projects/cuad-baseline` — repo,
venv, all three unpacked checkpoints (5.3 GB), smoke and throughput slices, and
per-model outputs under `out/`.

## Things I made up that you should review

1. **Test-split window counts** are extrapolated from `harness_val`'s measured
   windows-per-character, applied to `test`'s already-published character total.
   `harness_val` and `test` were length-matched at D-13, so this should be
   tight, but it is an extrapolation, not a count — `test` was never tokenized.
2. **The 11 ms/window non-GPU overhead** is a single constant fitted to three
   runs at one slice size. It bundles conversion, `torch.save`, and
   post-processing, and post-processing may scale super-linearly in n-best
   writing at 4,182 questions. Treat ~5.6 h as ±20%.
3. **The RSS line** is fitted from two points (472 and 5,545 windows). The slope
   is probably reliable; whether it stays linear to 154 K windows is untested,
   and Python's allocator may make it worse rather than better.
4. **"transformers 4.17 needs no source patches"** is established for the
   `--do_eval` path only. `--do_train` was never exercised and may well need the
   patches the assessment predicted.
5. **The claim that Ollama's 1,168 MiB is the right baseline to subtract.** It
   was idle-resident throughout; I did not stop it to confirm the model-only
   figure.
6. **Effective-TFLOPS figures** reuse the assessment's per-sequence FLOP counts
   (97 / 335 / 792 GFLOP), including its guessed 2.5× DeBERTa attention
   multiplier. The wall-clock numbers are measured; the MFU commentary inherits
   that guess.
