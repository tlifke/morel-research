---
id: studies/008-principled-extraction-cuad/investigations/001-dataset-and-splits
title: Dataset and splits (WS1)
status: complete
parents:
  - studies/008-principled-extraction-cuad
children: []
related: []
axes:
  llm_capability: high
  human_capability: high
tags: [cuad, data, splits]
created: 2026-08-15
updated: 2026-08-15
---

# Investigation 1 — Dataset and splits (WS1)

## Scope

Turn the raw Atticus CUAD release into instance records, pick the ~12-category
subset, and build the frozen dev / FT-train / holdout splits everything
downstream depends on.

## Methods

**Input.** Clone of `github.com/TheAtticusProject/cuad` — `data.zip` →
`CUADv1.json`, `test.json`, `train_separate_questions.json`; plus
`category_descriptions.csv` and `evaluate.py`.

**Steps.**

1. Parse the SQuAD-format JSONs into instance records:
   `{contract_id, title, text, n_tokens, split, gold}` where `gold` carries
   per-category spans and the `is_impossible` absence flag. `n_tokens` via a
   real tokenizer, not a character heuristic.
2. Select the ~12-category subset. Must include the Savelka confusable trio
   (Minimum Commitment / Volume Restriction / Revenue-Profit Sharing); the
   rest a spread of frequent and structural categories. **Provisional here —
   final pick lands after inv 002 reads the Atticus guidelines.**
3. Build splits per the study's D-3: official test (102 contracts) = holdout;
   ~40 contracts sampled from official train, stratified by length and by
   positive-category count, = dev; remainder of official train reserved for
   Phase 2. Seeded and persisted as files, not recomputed at read time.
4. Emit the dataset manifest and summary stats, including the
   length-distribution table.

**Reference distribution to reproduce** (official test set, as stated at
planning time): median ~25.7k chars ≈ 6.4k tokens; 27 contracts ≤4k tokens,
63 ≤8k, 79 ≤16k, max ~75k. **The character figure held; the token figures did
not, and were retired — see Results.** Kept here as written so the correction
is legible.

## Acceptance

- Deterministic rebuild from the raw upstream repo.
- Per-instance gold loadable through the harness env interface (a) and (d).
- Length-distribution table reproduced.
- Splits disjoint and frozen; nothing downstream may resample.

## Decisions

**INV1-D1 — source of record is `CUADv1.json`, not the train/test JSONs.** All 510
contracts and all 41 categories are parsed from `CUADv1.json`;
`test.json` supplies only the 102 holdout *titles*.
`train_separate_questions.json` is fetched (it is the SQuAD-format training
file and splits each category into multiple questions) but is not used for
gold, because its per-contract question list is 68 entries rather than 41 and
would not line up with the category axis. Verified programmatically: the 102
test titles are a subset of `CUADv1.json`, contexts and gold match byte-for-byte,
and test ∩ train = ∅, test ∪ train = 510.

**INV1-D2 — tokenizer: `Qwen/Qwen3-8B` (HF `Qwen2Tokenizer`), no special tokens.**
Chosen because the ~8B arm of the model axis is `qwen3.5:8b` and the Qwen3 BPE
tokenizer is shared across the family; `n_tokens` therefore measures the same
thing the local backend will see. Special tokens are excluded so the count
measures the contract, not a particular prompt template. Empirical rate on CUAD
contract text: **4.70 chars/token**.

**INV1-D3 — the manifest carries all 41 categories, not just the subset.** The
12-category pick is provisional and changes at G2; storing all 41 means a
subset change is a config edit, not a dataset rebuild.

**INV1-D4 — category subset selection criteria** (recorded in
`scripts/config/category_subset.yaml`, which is the source of truth, not this
list):

1. mandatory inclusion of the Savelka confusable trio;
2. frequency spread across near-universal / frequent / mid / uncommon / rare,
   so absence decisions are non-trivial and answer scores are not dominated by
   one base rate;
3. answer-format spread (date, jurisdiction name, yes/no-with-span) taken from
   `category_descriptions.csv`;
4. at least one confusable pair beyond the trio whose boundary is decided by a
   rule rather than a lexical cue (Exclusivity vs Non-Compete/No-Solicit;
   Expiration Date vs Effective Date/Renewal Term);
5. whole-contract properties alongside single-clause properties, since the two
   induce different search behaviour over a long document;
6. target size ~12.

Document Name (510/510) and Parties (509/510) were deliberately excluded as
trivial / multi-span-inflating. Ranked alternates are in the config;
Uncapped Liability is the strongest single addition.

**INV1-D5 — split construction.** Seed **20260815**. Holdout = the 102 official test
contracts. Dev = 40 contracts drawn from the 408 official-train contracts.
FT-train = the remaining 368, less the INV1-D7 exclusions (364). Disjointness
and the 510-way union are asserted in
`build_dataset.py`; splits are written to `data/processed/splits/*.txt` and read
back by id, never recomputed.

Dev stratification follows **D-13** (rationale there, not restated here).
Implementation: length bucket is the **primary** key and its per-bucket targets
are holdout's bucket proportions scaled to n=40 with largest-remainder rounding;
positive-count tercile is the **secondary** key, allocated *within* each length
bucket in proportion to that bucket's tercile composition in the official-train
pool, again largest-remainder. Sampling inside a `(bucket, tercile)` cell is
uniform without replacement under the seed. The priority ordering is declared in
`scripts/config/dataset.yaml` (`priority: primary | secondary` plus an explicit
`priority_rule`), so it is data, not a property of the code. Allocation is
capacity-clamped: if a bucket's target exceeded the train pool available in that
bucket the shortfall would be recorded in
`data/processed/stats/dev_strata.json` → `bucket_shortfall` rather than silently
absorbed. It is empty for this build.

**INV1-D6 — stratification keys use all 41 categories, not the 12-category subset.**
Positive-count terciles over all 41 (edges: <11 / 11–15 / ≥16) keep the dev
split valid if inv 002 changes the subset. Since D-13 demoted positive count to
a within-bucket secondary key, the terciles now balance inside each length
bucket rather than across the whole dev set. Two cells draw zero contracts —
`<=4k|T3` (only 2 such contracts exist in the entire train pool) and
`8k-16k|T1` (8 exist, but the bucket's 7 slots round to T2/T3) — so tercile
balance is approximate by construction. Length buckets are token-based
(≤4k / 4k–8k / 8k–16k / >16k).

**INV1-D7 — four contracts dropped from ft_train for content-duplication with
holdout and dev; a content-based guard now enforces it.** Approved by Tyler at
G1 and executed. Evidence, similarity figures and the alternatives considered
are in `reviews/split-contamination-check.md` — not restated here.

Implementation detail:

- The four ids live in `scripts/config/dataset.yaml` under `exclusions`, each
  with a reason and the split its twin sits in. Data, not code.
- Exclusions are applied **after** dev sampling, so the seed, the sampling
  procedure, dev's membership and the D-13 length profile are all bit-identical
  to the pre-fix build. Only the ft_train pool shrinks: 368 → 364. Asserted in
  code that no exclusion targets holdout or dev.
- The dropped contracts are **not** deleted from `instances.jsonl`. They keep a
  row with `split: "excluded"` plus `exclusion_reason` and
  `exclusion_twin_split`, and get their own `splits/excluded.txt`. The corpus
  stays auditable at 510 and code that scans all contracts still sees them.
  `"excluded"` was added to the loader's `SPLITS`.
- The standing guard is `assert_no_cross_split_duplicates` in
  `build_dataset.py`, run over the final assignment: normalized content hashes
  for exact matches, then 5-gram shingle containment/Jaccard for near matches,
  thresholds from `dataset.yaml` (`contamination_guard`). It runs **in addition
  to** the `contract_id` disjointness assertion — that assertion is not wrong,
  it is just blind to identical content filed under two titles, which is the
  whole lesson here. Failure messages name both contracts, both splits and the
  containment, so a future failure is diagnosable without re-running the scan.
  Verified by reverting the exclusions in a scratch run: the exact-hash path
  fires on ADURO and the containment path names the other three with their
  figures.
- Guard cost is ~5s on the full corpus. Post-fix headroom: the worst remaining
  cross-split pair is containment 0.737 against a 0.80 threshold.

## Results

Built from `data.zip` sha256 `f8161d18…b999a` (see `data/processed/manifest.json`
for the full source-file digests).

**Split sizes.** holdout 102 · dev 40 · ft_train 364 · excluded 4 · total 510.
Disjoint by `contract_id` and, post-INV1-D7, by content.

**Length distribution** (`data/processed/stats/length_distribution.csv`):

| split | n | median chars | median tokens | ≤4k tok | ≤8k tok | ≤16k tok | >16k tok | max tokens |
|---|---|---|---|---|---|---|---|---|
| holdout | 102 | 25,657 | 5,440 | 37 | 66 | 83 | 19 | 64,640 |
| dev | 40 | 28,237 | 6,424 | 15 | 26 | 33 | 7 | 41,703 |
| ft_train | 364 | 36,820 | 7,580 | 102 | 189 | 288 | 76 | 82,345 |
| excluded | 4 | 26,443 | 5,589 | 2 | 2 | 3 | 1 | 19,499 |
| all | 510 | 33,143 | 6,852 | 156 | 283 | 407 | 103 | 82,345 |

**Dev-to-holdout length-profile match** (D-13; from
`data/processed/stats/dev_strata.json`). No bucket was capacity-constrained —
the official-train pool had at least 5× the needed contracts in every bucket.

| length bucket | holdout n (%) | dev target | dev n (%) | train pool available |
|---|---|---|---|---|
| ≤4k | 37 (36.3%) | 15 | 15 (37.5%) | 119 |
| 4k–8k | 29 (28.4%) | 11 | 11 (27.5%) | 98 |
| 8k–16k | 17 (16.7%) | 7 | 7 (17.5%) | 107 |
| >16k | 19 (18.6%) | 7 | 7 (17.5%) | 84 |

Every bucket lands within 1.2 percentage points of holdout — the residual is
integer rounding at n=40, not a pool constraint. Dev median length is now 6,424
tokens against holdout's 5,440 (was 8,248 under the pool-mirroring scheme): a
gap of 984 tokens, down from 2,808. The remaining gap is *within-bucket* — dev
contracts sit slightly higher inside each bucket than holdout's do — and closing
it would require matching on a finer length statistic than the four buckets H5
reports on.

**Reference-distribution check.** The character figure reproduces exactly:
holdout median 25,657 chars vs the stated ~25.7k. The token figures do **not**
match, and the cause is identified rather than adjusted around. Dividing the
holdout character counts by 4 reproduces the reference numbers to the digit:

| quantity | reference | n_chars / 4 | Qwen3-8B tokenizer |
|---|---|---|---|
| median tokens | ~6.4k | 6,414 | 5,440 |
| contracts ≤4k tokens | 27 | 27 | 37 |
| contracts ≤8k tokens | 63 | 63 | 66 |
| contracts ≤16k tokens | 79 | 79 | 83 |
| max tokens | ~75k | 75,192 | 64,640 |

The reference token figures were produced by a 4-chars-per-token heuristic. CUAD
contract text actually runs at 4.70 chars/token under the Qwen3 tokenizer, so
the heuristic overstates length by ~18%. The tokenizer-derived column is the one
carried forward; the reference token figures should be retired.

**Category subset** (positive contracts, out of the split size):

| category | all/510 | dev/40 | holdout/102 | ft_train/364 |
|---|---|---|---|---|
| Agreement Date | 470 | 38 | 93 | 336 |
| Governing Law | 437 | 32 | 83 | 319 |
| Expiration Date | 413 | 33 | 78 | 299 |
| Anti-Assignment | 374 | 24 | 72 | 276 |
| Cap On Liability | 275 | 21 | 44 | 209 |
| License Grant | 255 | 16 | 50 | 187 |
| Exclusivity | 180 | 13 | 33 | 134 |
| Revenue/Profit Sharing | 166 | 13 | 35 | 117 |
| Minimum Commitment | 165 | 12 | 32 | 120 |
| Volume Restriction | 82 | 4 | 17 | 61 |
| Most Favored Nation | 28 | 4 | 3 | 21 |
| Source Code Escrow | 13 | 1 | 1 | 11 |

The `all/510` column still counts the 4 excluded contracts, so the four split
columns no longer sum to it. That is deliberate — `all` describes the CUAD
corpus, the split columns describe what the study uses.

**Artifacts.** `scripts/rebuild.sh` is the single rebuild command; a second run
reproduces every output file byte-identically (manifest differs only in
`built_at`). In git: `data/processed/instances.jsonl` (per-contract
`contract_id, title, n_chars, n_tokens, length_bucket, text_sha256, split` and
per-category gold span offsets + `is_impossible`, all 41 categories, no contract
text), `splits/*.txt`, `categories.json`, `manifest.json`, `stats/*`. The loader
is `scripts/cuad_dataset.py` (`CuadDataset.load_instances`, `.get_instance`,
`.gold`, `.categories`, `.contract_ids`), satisfying env-interface (a) and (d);
it reconstructs contract text from `data/raw/CUADv1.json`, which stays
gitignored.

## Forward-looking

_To be populated._

## Things to flag

Assumptions and open calls from the WS1 build, for review at G1:

- **The reference token figures in this doc's Methods section are wrong**, not
  the build (see Results). They came from `n_chars / 4`. Every downstream use of
  "27 contracts ≤4k tokens" — including feasibility planning against an 8B
  context window — should be re-derived from the tokenizer column.
- **Dev is now a deliberately non-representative sample of official-train** —
  the accepted cost of D-13. It cannot be used to characterize the training
  pool; FT-train is the pool of record for Phase 2. The ≤4k bucket in particular
  draws 15 of 119 available short contracts, so its effective diversity is
  narrower than 15 independent draws from official-train would suggest.
- **Residual cross-split overlap sits at containment 0.737**, below the 0.80
  threshold and therefore not excluded:
  `AzulSa_20170303_F-1A_EX-10.3_9943903_EX-10.3_Maintenance Agreement1`
  (ft_train, 233k chars) and `…Maintenance Agreement2` (dev, 17k chars) are two
  CUAD entries carved from the same SEC exhibit, and 74% of the shorter one's
  5-grams appear in the longer. It is the closest thing to a survivor and the
  reason the guard's headroom is 0.06 rather than 0.15. Judged acceptable
  because dev is not trained on; it would matter more if the pair straddled
  ft_train and holdout.
- **ft_train-internal duplicates are untouched.** Five near-duplicate clusters
  remain inside ft_train (see the review). They double-weight the same contract
  during fine-tuning, which is a Phase 2 data-loader question, not a split-safety
  one. Deliberately not bundled into INV1-D7.
- **Byte-identical contracts carry disagreeing gold labels.** The ADURO pair is
  byte-identical at 12,020 chars yet labeled differently on Anti-Assignment and
  Exclusivity; the WOMENSGOLF and NETGEAR near-twins likewise. This is a direct
  measurement of CUAD annotation noise on categories the study scores, and it
  bounds achievable agreement independently of model or prompt. For inv 003's
  reliability section and the study's limitations.
- **The two rare categories are near-degenerate for extraction on holdout.**
  Source Code Escrow has 1 positive in holdout and 1 in dev; Most Favored Nation
  has 3 and 4. They are excellent absence-calibration targets and give almost no
  extraction signal. Keeping both may be redundant.
- **`train_separate_questions.json` is fetched but unused.** Kept because the
  investigation spec names it as an input; drop from `fetch_raw.py` if it stays
  unused after inv 002.
- **Stratifying on all-41 positive counts** trades dev balance on the *subset*
  for stability under subset change. Subset-positive counts per dev contract are
  in `instances.jsonl` as `n_positive_subset` if a re-check is wanted.
- **`contract_id` is the CUAD title string** (spaces, slashes and all). It is
  unique across all 510 and matches the `component-contracts.md` example, but it
  is not filesystem-safe. Checked and left as is: nothing in WS1 puts a
  `contract_id` in a path. It is used only as a JSON key, a dict key, and a
  newline-delimited line in `splits/*.txt` — all of which tolerate the raw
  string. Downstream code that wants per-contract *files* (e.g. cached raw
  responses) must slugify or hash the id itself; the manifest's `text_sha256`
  is a ready-made stable key for that.
- **Tokenizer pinning is by model id, not by file digest.** A silent upstream
  retokenizer change on the HF repo would change `n_tokens`. The manifest records
  the tokenizer class and vocab size as a weak check.

## Limitations

- CUAD is public and present in pretraining corpora. Condition comparisons are
  valid under shared contamination; absolute numbers are not
  leaderboard-comparable. This note travels with every downstream result.
