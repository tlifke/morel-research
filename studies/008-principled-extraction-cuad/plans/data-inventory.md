# Data inventory — what exists, where, and how to regenerate it

Written 2026-08-17. **Not everything is in git.** This file records what lives
outside it, why, and the exact command to rebuild each piece. Anything
gitignored is one machine failure away from gone, so treat regeneration cost as
the real backup policy.

## In git — safe

| path | what |
|---|---|
| `data/processed/` | instance manifest (gold offsets, no contract text), all six `splits/*.txt`, `manifest.json`, `stats/*` |
| `data/cuad-baseline/table2/` | reproduced Table 2, PR curves for all three models (102 points each, with the interpolated-precision column their AUPR integrates), n-best depth and dedup analyses |
| `data/cuad-baseline/baseline_on_train_splits.json` | their models' scored results on `harness_val` + `principle_train` |
| `data/cuad-baseline/c2c3_cuad_scored.json` | our C2/C3 scored through their `evaluate.py` |
| `data/cuad-baseline/expiration_gold_taxonomy.json` | gold Expiration Date spans classified calendar / duration / event / other |
| `data/cuad-baseline/c2c3_absence_profile.json`, `paper_figure4_category_order.json` | supporting figure data |
| `principles/`, `harness/`, `apps/`, `scripts/`, `reviews/` | all code and all review artifacts |

## Not in git — regenerate as needed

### `data/cuad-baseline/split-preds/` — 45 MB, the highest-value gap

**What it is.** Their three checkpoints' raw predictions over `harness_val` and
`principle_train`, 18 shards. Per question, 21 candidates (20 + null) carrying
`text`, `probability`, `start_logit`, `end_logit`, `token_doc_start`,
`token_doc_end`, plus `null_odds_.json` per shard.

**Why it matters.** This is the raw material for **exploring alternative
scoring methods** — the logits are present, not just softmaxed probabilities, so
you are not locked into their normalisation. Different aggregations, thresholds,
dedup rules, span merging, and absence rules can all be tried offline against
it, with no GPU.

**Cost to regenerate.** ~1.49 GPU-hours on the desktop RTX 3080, plus
environment setup if that machine has been rebuilt. Gzips to 5.3 MB if it is
ever worth committing.

```bash
# on the desktop, env at /home/tlifke/Projects/cuad-baseline
# use the desktop-gpu-access skill — the ssh RemoteCommand trap
scripts/cuad-baseline/setup_desktop_env.sh     # only if the env is gone
scripts/cuad-baseline/make_split_shards.py     # refuses --split test by design
scripts/cuad-baseline/run_split_shards.sh
scripts/cuad-baseline/score_split_runs.py
```

Traps that will bite on a rebuild, both already paid for once:
- **Cache-key collision** — `cached_dev_{model}_{seq_len}` omits the predict
  file, so a per-category loop sharing one `--cache_dir` silently scores every
  shard against shard one's features. Use a distinct cache dir per shard.
- **RAM** — DeBERTa peaks at ~10 GB per shard, flat; sharding is required.
- Pins: `torch==1.13.1+cu117`, `transformers==4.17.0`, `numpy==1.23.5`.
  `transformers==4.12.5` is *uninstallable* on py3.10; `numpy>=1.24` breaks
  DeBERTa-v2 on `np.int`.

### Their shipped `test`-split predictions — not local at all

**Where they are.** Inside the three Zenodo checkpoint bundles (record
**4599830**), currently unpacked only on the desktop at
`/home/tlifke/Projects/cuad-baseline`. Each ships
`nbest_predictions_.json` (4,182 keys = 102 × 41), `predictions_.json`, and
`null_odds_.json` — the authors' own released inference output over the
official test split.

**Why they matter.** These are the **honest** predictions, not
memorisation-inflated, and they are what any G4 comparison uses. They also make
the Table 2 reproduction free: `scripts/cuad-baseline/reproduce_table2.py` runs
CPU-only in ~35 s against them, no inference.

**Cost to regenerate.** A download. No GPU, no inference. Nothing in this repo
currently records them as a dependency living on another machine — hence this
entry.

### `data/traces/` — 21 MB, our own trial traces

Per-trial, per-attempt records: the exact prompt as sent, raw response before
parsing, `reasoning_content`, finish reason, usage, latency, and any repair
message. Currently `2026-08-16-c2c3-harness-val` (240 trials, 8 shards),
`2026-08-16-c2c3-budget-probe`, and the smoke runs.

**These cannot be regenerated.** Tinker does not honour seeds, so re-running
produces different samples. Deleting a run's traces discards that experiment —
the scored records in `trials.jsonl` / `decisions.jsonl` survive as the audit
trail, but the reasoning text does not. Regenerating costs ~$5.49 and yields
*different* data, not the same data.

### `data/raw/` — 96 MB, CUAD source

```bash
uv run scripts/fetch_raw.py    # sha256-pinned; rebuild is deterministic
uv run scripts/build_dataset.py
```

### Other ignored paths

- `data/responses/` — raw proposer responses from principle derivation.
- `data/fake_e2e/` — fake-env harness output, disposable.
- `principles/applicability/work/` — labelling prompts and raw responses; they
  embed contract text, hence ignored.
- `principles/pilot/{controls,controls_key,round2_key}.yaml` — the calibration
  instrument. Untracked **deliberately** so the curator cannot read them; they
  go back into git once the instrument is retired, since the key is part of the
  methodological record.
- `assets/*.pdf` — the Atticus Labeling Handbook. **Purchased, copyrighted,
  non-redistributable.** Must never enter this public repo. Not regenerable
  without buying it again.

## The rule

**A number in a review is only as durable as the data behind it.** Anything
above that is gitignored and expensive to rebuild should be regenerated *before*
a result depending on it is published, not after — and the traces in particular
can never be reproduced, only replaced.
