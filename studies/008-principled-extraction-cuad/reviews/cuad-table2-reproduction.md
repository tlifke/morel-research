# CUAD Table 2 reproduction — released checkpoints, CPU-only, zero GPU time

**GATE: PASS.** All three released checkpoints reproduce their published Table 2
row to within 0.05 percentage points on every reported figure — AUPR, P@80%R and
P@90%R — scoring the authors' own shipped `nbest_predictions_.json` against the
authors' own `test.json` with `evaluate.py` completely unmodified.

Run date 2026-08-16, on the desktop at `/home/tlifke/Projects/cuad-baseline`,
CPU only, 35 s wall for all three models including the 41-category breakdown. No
inference was run. Our `test` split contracts were never loaded; the only gold
read is the CUAD repo's own `repo/test.json` (checked in by the authors,
2021-03-10).

AI Assistant Used: Claude Code

---

## 1. Recovered vs published

Pooled micro over all 41 categories, 4,182 questions (102 test contracts × 41),
`assert sorted(pred.keys()) == sorted(gt.keys())` passing for all three.

| model | metric | published | recovered | Δ (pp) |
|---|---|---|---|---|
| RoBERTa-base | AUPR | 42.6 | **42.586** | −0.01 |
| | P@80%R | 31.1 | **31.131** | +0.03 |
| | P@90%R | 0.0 | **0.000** | 0.00 |
| RoBERTa-large | AUPR | 48.2 | **48.250** | +0.05 |
| | P@80%R | 38.1 | **38.128** | +0.03 |
| | P@90%R | 0.0 | **0.000** | 0.00 |
| DeBERTa-v2-xlarge | AUPR | 47.8 | **47.793** | −0.01 |
| | P@80%R | 44.0 | **44.032** | +0.03 |
| | P@90%R | 17.8 | **17.828** | +0.03 |

Every delta is smaller than the rounding step of the published table. There is
nothing here to dig into: this is the same computation on the same bytes, and
the paper's numbers are these numbers rounded to one decimal. No
evaluation-script version drift, no gold-file ambiguity, no category-set
question arises.

Two structural facts confirmed in passing, both consistent with the paper:

- **P@90%R is 0.0 for both RoBERTas because they never reach 90% recall.** Max
  recall at `conf = 0` is 0.899 (base) and 0.905 (large); DeBERTa reaches 0.917,
  which is why it is the only model with a non-zero P@90%R. The published `0.0`
  for RoBERTa-large is therefore "recall threshold unreachable", not "precision
  collapsed to zero" — worth knowing before anyone quotes it.
- **The gold is absence-dominated.** Of the 4,182 test questions, **2,938 (70.3%)
  have zero gold answers** and 1,244 have at least one; there are **2,643 gold
  spans** total, which is the recall denominator. Their metric awards nothing for
  the 2,938 correct absences — the point made in
  `cuad-baseline-comparability.md` §1.4, now with the counts.

### What was run

`scripts/cuad-baseline/reproduce_table2.py`, which imports the upstream
`evaluate.py` module and calls `get_answers` / `get_precisions_recalls` /
`get_prec_at_recall` / `get_aupr` / `process_precisions` with no modification of
any kind. It must be run with cwd set to the CUAD repo (`evaluate.py` reads
`category_descriptions.csv` at module scope). Invocation:

```
cd repo && python ../scripts/reproduce_table2.py \
  --repo . --gold ./test.json --ckpt-root ../ckpt \
  --out ../out/table2 --per-category
```

The script asserts the gold filename is `test.json`; it has no path to our
splits and loads no contract text of ours.

---

## 2. Operating points and PR curve data

**Location: `studies/008-principled-extraction-cuad/data/cuad-baseline/table2/`**
(also on the desktop at `/home/tlifke/Projects/cuad-baseline/out/table2/`).

| file | contents |
|---|---|
| `table2_reproduction.json` | all metrics, deltas, operating points, 41-category breakdown per model |
| `pr_curve_roberta-base.csv` | 102 points: `conf, precision, recall, interpolated_precision` |
| `pr_curve_roberta-large.csv` | same |
| `pr_curve_deberta-v2-xlarge.csv` | same |

The curve is the upstream sweep: `np.arange(0.99, 0, -0.01)` plus `0.001` and
`0`, prepended with the seeded `(P=1, R=0)` anchor — 102 rows, recall increasing.
`interpolated_precision` is `process_precisions` applied, i.e. the running max
from the high-recall end; that is the curve `get_aupr` integrates and the one our
committed-decision point must be plotted against.

Exact operating points at the 80% and 90% recall thresholds:

| model | thresh | conf | recall | precision |
|---|---|---|---|---|
| RoBERTa-base | 80% | 0.02 | 0.8093 | 0.3113 |
| RoBERTa-large | 80% | 0.02 | 0.8154 | 0.3813 |
| RoBERTa-large | 90% | 0.00 | 0.9054 | 0.0343 |
| DeBERTa-v2-xlarge | 80% | 0.05 | 0.8025 | 0.4403 |
| DeBERTa-v2-xlarge | 90% | 0.001 | 0.9039 | 0.1783 |

At all of these the interpolated precision equals the raw precision, so the
published P@R figures are real measured points, not artifacts of interpolation.

**The `conf` off-by-one in `evaluate.py` is confirmed and quantified.**
`get_prec_at_recall` zips a 102-long `precisions` against a 101-long `confs`, so
the `conf` it *returns* is one sweep step below the one that actually produced
the reported precision (e.g. RoBERTa-base: returns 0.01, true threshold 0.02).
The JSON records both — `conf_at_80_recall_reported` is upstream's value,
`operating_point_at_80_recall.conf` is the correct one. **Use the latter.** No
reported precision, recall or AUPR is affected.

Curve shape, for planning where our point will land: at `conf = 0.99` precision
is only 0.72–0.76 at recall 0.09–0.12, and the curve descends smoothly. There is
no near-vertical segment above recall ~0.1, so the
`cuad-baseline-comparability.md` §2.1 worry (comparison uninformative below
recall 0.2) is milder than feared — but the pre-registration should stand.

### Category-level breakdown

`table2_reproduction.json` carries per-model, per-41-category AUPR, P@80%R,
max recall and question counts. Computed by **subsetting `gt` and `pred` on
exact category match** (`key.rsplit("__", 1)[-1] == category`) rather than using
`evaluate.py`'s `category` argument, which is a substring test. The smoke's
finding replicates exactly on the test split: **`Insurance` is the only leaking
category — 102 exact questions vs 142 substring matches**; all other 40 partition
cleanly. Upstream's filter would inflate `Insurance`'s question pool by 39%.

Shape of the breakdown (AUPR, DeBERTa): best are `Document Name` 0.966,
`Governing Law` 0.961, `Agreement Date` 0.948, `Expiration Date` 0.915,
`Parties` 0.914; worst are `Non-Disparagement` 0.191, `Competitive Restriction
Exception` 0.142, `Warranty Duration` 0.139, `Affiliate License-Licensor` 0.134.
**`Price Restrictions` scores AUPR 0.000 for all three models** — no model
retrieves it at any threshold. Note the pooled Table 2 numbers use no category
filter at all, so none of this affects §1; and a 12-category recomputation is a
different quantity that must never be printed beside the 41-pooled figures.

---

## 3. Did they ship train-set predictions? No.

**They did not.** There are no predictions over CUAD's train split in the Zenodo
bundles, the GitHub repo, or the HuggingFace artifacts. What ships is one
prediction set per model, over the test split only.

Checked exhaustively:

- **Zenodo record 4599830 ("CUAD Finetuned Models")** holds exactly three files —
  `roberta-base.zip`, `roberta-large.zip`, `deberta-v2-xlarge.zip`. Each zip
  contains exactly **11 entries**, listed in full (not just the obvious ones):
  `config.json`, `pytorch_model.bin`, `training_args.bin`, tokenizer files
  (`vocab.json` + `merges.txt`, or `spm.model` + `added_tokens.json` for
  DeBERTa), `special_tokens_map.json`, `tokenizer_config.json`, and the three
  prediction files `nbest_predictions_.json`, `predictions_.json`,
  `null_odds_.json`. Nothing else. No second prediction directory, no
  train-named file, no `.tar` inside the zip.
- **Each `nbest_predictions_.json` has 4,182 keys and those keys equal the
  `test.json` gold key set exactly** (the reproduction's own assertion passed).
  So the shipped predictions are unambiguously test-only — they are not a
  superset from which train keys could be sliced out. A train set would be
  ~408 × 41 = 16,728 keys; nothing of that size exists.
- **GitHub `TheAtticusProject/cuad`**: one branch (`main`, `67faa0e`), zero
  releases, and the full recursive tree is nine files —
  `category_descriptions.csv`, `contract_review.png`, `data.zip`, `evaluate.py`,
  `readme.md`, `run.sh`, `scrape.py`, `train.py`, `utils.py`. `data.zip` contains
  three files only: `CUADv1.json`, `test.json`, `train_separate_questions.json` —
  i.e. gold, not predictions.
- **HuggingFace**: `theatticusproject` publishes **no model repos at all** (the
  checkpoints were never mirrored to the Hub) and four datasets. `cuad-qa` is a
  three-file loader repo; `cuad` is the raw corpus (PDFs, txt, label xlsx,
  `master_clauses.csv`, `CUAD_v1.json`). No prediction files in either. The
  third-party re-finetunes (`akdeniz27/*`) are independent training runs and
  irrelevant here regardless.
- **`HF_TOKEN` was not needed** — every artifact is public. It was not used.

### What this costs us, and the one thing that would have been worth having

The diagnostic use Tyler had in mind is real but unavailable. To be precise about
what we lose: their train predictions would **not** have been an evaluative
reference point — their models were fine-tuned on those 408 contracts, so any
score there is memorisation-inflated. The smoke already measured the size of that
inflation on `harness_val` (AUPR 0.85–0.91 against a test-split 0.43–0.48, with
the model ordering scrambled). Nobody was ever going to quote those numbers.

The honest use, now foreclosed, was **qualitative error analysis on the contracts
we actually develop on**: every non-`test` split of ours (`harness_val`,
`model_train`, `principle_train`, `principle_val`, `scratch`) was carved from
CUAD's official train pool, so their train predictions would have let us put
their spans beside ours on the same contracts — same category, same document —
without touching `test`, purely to sanity-check our pipeline's output shape and
to see which clauses a fine-tuned extractor picks where we differ.

**That is still obtainable, at GPU cost rather than for free.** The checkpoints
and the working environment are both in place, so running their models over a
non-`test` split ourselves produces exactly the artifact the shipped files would
have been. Cost, from the smoke's measured throughput: roughly 0.4 h for all
three over the 40-contract `harness_val` at 12 categories, scaling linearly with
contracts and categories. It is a legitimate pre-G4 action — the smoke already
did it on 4 categories — provided the resulting scores are recorded as wiring
evidence and never as results. Whether that diagnostic is worth the GPU hour is a
call for Tyler; it is not on the critical path for the Table 2 gate, which has
now passed.

---

## 4. Consequences for the plan

1. **The hard gate in `cuad-baseline-comparability.md` §6 option 1 is cleared.**
   Item 10 of that document's "things I made up" list — "that the released Zenodo
   checkpoints reproduce Table 2" — is now settled affirmatively, and settled
   more strongly than a re-run would have settled it: we reproduced their
   *reported numbers from their own inference output*, which isolates the scoring
   path completely.
2. **What it does not establish**: that *our* re-run of their weights reproduces
   their inference. That is the second, stronger check the smoke identified —
   diff our n-best against theirs question-by-question. It still requires the
   GPU pass, and it is now the only remaining reproduction risk. It distinguishes
   "we reproduced the number" from "we reproduced the computation", and the
   shipped files make it a free byproduct of the run we were going to do anyway.
3. **The 41-category GPU run is no longer needed as a sanity check.** Its only
   remaining purpose is (2) above plus the 12-category recomputation. If GPU time
   is tight, the 12-category run alone is defensible now that the pooled
   41-category figures are confirmed from the shipped files.
4. **Plot against `interpolated_precision`, not `precision`.** That is the curve
   their AUPR integrates and their P@R reads off, so it is the curve our
   committed-decision point belongs on.

---

## Artifacts

| path | what |
|---|---|
| `scripts/cuad-baseline/reproduce_table2.py` | the reproduction (new; CPU-only, imports upstream `evaluate.py` unmodified) |
| `data/cuad-baseline/table2/table2_reproduction.json` | metrics, deltas, operating points, 41-category breakdown |
| `data/cuad-baseline/table2/pr_curve_*.csv` | full 102-point PR curves, per model |

Nothing was committed. Desktop state at `/home/tlifke/Projects/cuad-baseline` is
unchanged apart from `scripts/reproduce_table2.py` and the new `out/table2/`.

## Things I made up that you should review

1. **The claim that the deltas are "smaller than the rounding step".** Checked:
   every recovered value rounds to its published value at one decimal place
   (largest raw delta is RoBERTa-large's AUPR, 48.2497 vs 48.2, i.e. +0.0497 pp,
   interior to the bin). The table shows deltas rounded to 2 dp, which makes that
   one read as exactly 0.05; it is not on the boundary.
2. **The 0.4 h estimate** for a `harness_val` diagnostic run is a linear rescale
   of the smoke's measured per-window timings, not a measurement.
3. **"HuggingFace publishes no `theatticusproject` model repos"** is from the Hub
   API author listing. A model repo under a different owner that mirrors the
   Zenodo zips verbatim would not have been caught by that query — I checked the
   plausible `akdeniz27` re-finetunes only by reputation, not by listing their
   files.
4. **The absence-rate figures (2,938 / 1,244 / 2,643)** come from
   `evaluate.py`'s own `get_answers`, so they are the gold as their scorer sees
   it, which is not necessarily the gold as our pipeline parses `CUADv1.json`.
5. **The recommendation in §4.3 that a 12-category-only GPU run is now
   defensible** is my inference from the gate passing, not a decision. It trades
   away the n-best diff on 29 categories.
