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
updated: 2026-08-16
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

**INV1-D8 — `selection` (60) and `confirmation` (40) carved from `ft_train`,
stratified on a per-category positive floor rather than on length.** Purpose,
authorisation and the reason the stratification differs from dev's are in
`plans/splits.md`; opened by D-22/D-23. This decision records construction,
the floor and what the floor costs.

*Sizes and seeds.* `selection` n=60 seed **20260816**, `confirmation` n=40 seed
**20260817**, drawn in that order. Dev's seed 20260815 is untouched, and
`dev.txt`, `holdout.txt` and `excluded.txt` are byte-identical to the pre-carve
build — the carve is a partition of `ft_train` and nothing else.

*The floor, and why it is 5 and 4.* Primary key is a guaranteed minimum of
**5 positive contracts per subset category in `selection`** and **4 in
`confirmation`**; length bucket is secondary, matched to the 364-contract pool
(not to holdout — that is dev's job under D-13). Both are recorded in
`scripts/config/dataset.yaml` as data.

The selection floor is set by what the selection test has to be able to do. The
per-principle A/B is a paired comparison over the contracts where the
principle's category is positive, so its n *is* that positive count. Under a
paired sign test — the assumption-free floor for this design — n=4 cannot reach
p<0.05 even when the principle helps on all four contracts (one-sided p=0.0625).
**A floor of 4 would make principles scoped to Source Code Escrow untestable by
construction, not merely underpowered.** n=5 is the smallest floor where a
perfect result clears the line (p=0.031). That is the entire justification for 5:
it is the minimum at which the instrument can fire at all.

The confirmation floor is 4 rather than 5 for a supply reason, stated plainly:
Source Code Escrow has only 11 positive contracts in the whole pool. 5+5 would
leave one for Phase 2; 5+4 leaves two. Confirmation is a single directional pass
per surviving principle rather than a fresh significance hunt (`plans/splits.md`),
so it absorbs the weaker floor better than selection would.

*What the floor implies for the smallest categories — the real limit.* Achieved
positives are in the Results table. Two categories sit at or near the floor and
their principles are qualitatively weaker tests than everything else in the set:

| category | selection n | detectable paired effect (t, one-sided α=0.05) | sign test |
|---|---|---|---|
| Source Code Escrow | 5 | d ≈ 0.95 | fires only at 5/5 |
| Most Favored Nation | 8 | d ≈ 0.67 | fires at 7/8 |
| Volume Restriction | 10 | d ≈ 0.58 | — |
| Agreement Date | 52 | d ≈ 0.23 | — |

An SCE-scoped principle must produce an effect roughly **four times larger** than
an Agreement-Date-scoped one to be selected at the same threshold, and must help
on *every* contract to clear a distribution-free test. Repeated seeds per
contract do not rescue this: they shrink measurement noise, not the
between-contract variance that sets n. **Inv 006 must therefore not report an
SCE or MFN principle as "confirmed" on the same footing as the others.** The
honest options, in preference order: (a) report rare-category principles as
descriptive with the n stated inline and no significance claim; (b) pool
rare-category principles into one family-level test; (c) drop SCE-scoped
principles from the protocol entirely — which is close to what INV1-D7's flag
about SCE being near-degenerate was already pointing at. Not silently accepted;
routed to inv 006 as a design constraint.

*Is 264 enough for Phase 2?* Yes, and contract count was never the binding
constraint. `plans/phase2-outline.md` describes SFT by rejection sampling over
generations and RL with a programmatic composite reward. The unit in both is the
`(contract, category)` decision, so 264 contracts is 3,168 decision-level prompt
units before any k>1 sampling — and rejection sampling multiplies generations per
prompt while RL reuses prompts across epochs, so unique prompts are not scarce for
a LoRA-scale run. What 264 does cost is rare-category *coverage*: Source Code
Escrow falls to 2 positive contracts and Most Favored Nation to 8. SCE was already
at 11/364 (a 3% base rate) and was already flagged as near-degenerate, so the carve
converts a weak signal into effectively none rather than destroying a good one. If
Phase 2 later needs SCE positives, the correct fix is to drop SCE from the subset
at G2 — **not** to shave the selection floor below the level where the test can
fire. Recorded here rather than resolved silently.

*Near-duplicate clusters are now bound to `ft_train`, and the guard earned its
keep.* Carving three splits out of one promotes `ft_train`'s *internal*
near-duplicate clusters into *cross-split* pairs. The INV1-D7 guard caught this on
the first attempt — `ChinaRealEstateInformationCorp…Content License Agreement`
(ft_train) against `LejuHoldingsLtd…Content License Agreement1/2` (selection) at
containment 0.989 / Jaccard 0.944. This is exactly the failure `plans/splits.md`
warned about, and it was a live one: an MFN-positive twin straddling selection and
the pool. Fix: before carving, the 364-contract pool is clustered by 5-gram
containment/Jaccard (union-find), and **every contract in a multi-member cluster is
bound to `ft_train`** — clusters are indivisible and go wholesale to Phase 2. Only
singletons are eligible for selection and confirmation. 11 clusters, 23 contracts,
341 eligible.

Clustering thresholds (`split_clustering` in `dataset.yaml`: containment 0.60,
Jaccard 0.40) are deliberately **stricter than the guard's fail thresholds** (0.80 /
0.60). The guard is a fail condition; this is the preventive rule, and the gap
between the two is the headroom. Binding at the guard's own numbers would have left
a legal cross-split pair (the `BellringBrandsInc` exhibit halves) at containment
0.783 against a 0.80 fail line — a build one annotation away from breaking.

*Guard result after carving.* Passes. Worst cross-split pair is containment
**0.7365** / Jaccard 0.0635 against thresholds 0.80 / 0.60 — **unchanged from the
pre-carve build**, because it is still the pre-existing `AzulSa …Maintenance
Agreement1/2` ft_train↔dev pair documented under INV1-D7. Residual headroom is
therefore 0.064 containment, and the carve introduced no new worst pair. Full
cluster membership, edges and per-category floor traces are in
`data/processed/stats/selection_strata.json`.

*Disjointness.* All six splits are pairwise disjoint by `contract_id` and union to
510 (60+40+40+102+264+4), asserted over every pair in `build_dataset.py`. The
loader's `SPLITS` gained `selection` and `confirmation`; `CuadDataset`'s method
surface is unchanged.

## Results

Built from `data.zip` sha256 `f8161d18…b999a` (see `data/processed/manifest.json`
for the full source-file digests).

**Split sizes.** holdout 102 · dev 40 · selection 60 · confirmation 40 ·
ft_train 264 · excluded 4 · total 510. Disjoint by `contract_id` and, post-INV1-D7
and post-INV1-D8, by content. (Pre-INV1-D8 the arrangement was ft_train 364 with no
selection or confirmation; dev, holdout and excluded are unchanged across the carve.)

**Length distribution** (`data/processed/stats/length_distribution.csv`):

| split | n | median chars | median tokens | ≤4k tok | ≤8k tok | ≤16k tok | >16k tok | max tokens |
|---|---|---|---|---|---|---|---|---|
| holdout | 102 | 25,657 | 5,440 | 37 | 66 | 83 | 19 | 64,640 |
| dev | 40 | 28,237 | 6,424 | 15 | 26 | 33 | 7 | 41,703 |
| selection | 60 | 36,111 | 7,573 | 17 | 31 | 47 | 13 | 59,063 |
| confirmation | 40 | 37,826 | 7,708 | 11 | 21 | 32 | 8 | 82,345 |
| ft_train | 264 | 36,438 | 7,337 | 74 | 137 | 209 | 55 | 64,608 |
| excluded | 4 | 26,443 | 5,589 | 2 | 2 | 3 | 1 | 19,499 |
| all | 510 | 33,143 | 6,852 | 156 | 283 | 407 | 103 | 82,345 |

**Selection / confirmation length spread** (INV1-D8 secondary key; matched to the
364-contract pool, not to holdout). Every bucket lands within 1.1 percentage points
of the pool despite the floor draws going first — the floor picks are spread across
buckets where each category's positives allow, and the fill allocation is computed
against what the floor already took.

| length bucket | pool/364 | selection/60 | confirmation/40 | ft_train/264 |
|---|---|---|---|---|
| ≤4k | 102 (28.0%) | 17 (28.3%) | 11 (27.5%) | 74 |
| 4k–8k | 87 (23.9%) | 14 (23.3%) | 10 (25.0%) | 63 |
| 8k–16k | 99 (27.2%) | 16 (26.7%) | 11 (27.5%) | 72 |
| >16k | 76 (20.9%) | 13 (21.7%) | 8 (20.0%) | 55 |

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

| category | all/510 | dev/40 | holdout/102 | selection/60 | confirmation/40 | ft_train/264 |
|---|---|---|---|---|---|---|
| Agreement Date | 470 | 38 | 93 | 52 | 35 | 249 |
| Governing Law | 437 | 32 | 83 | 51 | 33 | 235 |
| Expiration Date | 413 | 33 | 78 | 49 | 34 | 216 |
| Anti-Assignment | 374 | 24 | 72 | 46 | 33 | 197 |
| Cap On Liability | 275 | 21 | 44 | 36 | 27 | 146 |
| License Grant | 255 | 16 | 50 | 27 | 23 | 137 |
| Exclusivity | 180 | 13 | 33 | 24 | 11 | 99 |
| Revenue/Profit Sharing | 166 | 13 | 35 | 18 | 12 | 87 |
| Minimum Commitment | 165 | 12 | 32 | 19 | 9 | 92 |
| Volume Restriction | 82 | 4 | 17 | 10 | 6 | 45 |
| Most Favored Nation | 28 | 4 | 3 | 8 | 5 | 8 |
| Source Code Escrow | 13 | 1 | 1 | 5 | 4 | 2 |

Both floors are met with zero violations (`selection_strata.json` →
`floor_violations`). The floor binds only on the two rare categories; every other
category clears 5/4 from the length-stratified fill alone. Selection over-draws MFN
(8, floor 5) because MFN positives are common enough in the 8k–16k bucket that the
fill picked more. **Source Code Escrow at selection 5 / confirmation 4 / ft_train 2
is the study's tightest constraint** — see INV1-D8 for what is and is not
concludable there.

The `all/510` column still counts the 4 excluded contracts, so the split
columns no longer sum to it. That is deliberate — `all` describes the CUAD
corpus, the split columns describe what the study uses.

**Artifacts.** `scripts/rebuild.sh` is the single rebuild command; a second run
reproduces every output file byte-identically (manifest differs only in
`built_at`). In git: `data/processed/instances.jsonl` (per-contract
`contract_id, title, n_chars, n_tokens, length_bucket, text_sha256, split` and
per-category gold span offsets + `is_impossible`, all 41 categories, no contract
text), `splits/*.txt` (six files), `categories.json`, `manifest.json`, `stats/*`
(including `selection_strata.json`, added at INV1-D8). The loader
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

- **Superseded in part by INV1-D8**: those clusters are now *bound* to ft_train
  (11 clusters, 23 contracts, at the stricter `split_clustering` thresholds) so
  they cannot straddle selection/confirmation. The double-weighting during
  fine-tuning is unchanged and still a Phase 2 data-loader question.

- **INV1-D8 changed what `ft_train` means, and existing work computed over it is
  now split across three splits.** Nothing here is broken, but every artifact
  below was derived from the 364-contract `ft_train` and now spans
  `ft_train` (264) + `selection` (60) + `confirmation` (40). Not fixed as part of
  INV1-D8; routed for triage:
  - `principles/pilot/` — contrastive mining and its config/summary
    (`mining_config.yaml`, `mining_summary.json`), `checkers/footprint.yaml` and
    `footprints.json`, `run_footprints.py`, `critiques.yaml`,
    `cross_source_validation.yaml`, and the whole `round2/` mirror of those.
    **This is the one that actually matters**: principles were mined from, and
    their footprints measured on, contracts that now include the very split
    those principles will be A/B tested on. A principle mined from a selection
    contract and then selected on that contract is a selection artifact of
    exactly the kind `plans/splits.md` exists to prevent. Inv 006 needs to decide
    whether to re-mine on `ft_train`-only or to record the overlap as a known
    limitation.
  - `reviews/agreement-date-check.md`, plus `calibration-controls.md`,
    `cross-source-validation.md`, `principle-claim-checks.md`,
    `principle-critiques.md`, `principle-footprints.md`, `round2-*.md`,
    `derivation-pipeline.html`, `sample-contracts.html` — all cite `ft_train`
    n=364 or counts computed over it. Numbers are still correct for "the
    364-contract pool", but the split name in them is now wrong.
  - `scripts/mine_contrastive_pairs.py` and `scripts/render_sample_contracts.py`
    — read `ft_train` and will now see 264 contracts. Reruns will not reproduce
    the checked-in outputs.
  - `apps/principle-review/` (`record_types.py`, `sample_gold.py`,
    `aggregate_audit.py`, fixtures, tests) — reference `ft_train` as a split
    literal; `sample_gold.py` defaults to dev+holdout so it is likely unaffected
    in practice.
  - `HANDOFF.md`, `plans/decisions.md`, `reviews/split-contamination-check.md`
    — prose stating ft_train n=364.
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
