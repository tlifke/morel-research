---
id: studies/008-principled-extraction-cuad/investigations/001-dataset-and-splits
title: Dataset and splits (WS1)
status: planned
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

**Reference distribution to reproduce** (official test set): median ~25.7k
chars ≈ 6.4k tokens; 27 contracts ≤4k tokens, 63 ≤8k, 79 ≤16k, max ~75k.

## Acceptance

- Deterministic rebuild from the raw upstream repo.
- Per-instance gold loadable through the harness env interface (a) and (d).
- Length-distribution table reproduced.
- Splits disjoint and frozen; nothing downstream may resample.

## Decisions

_Populate as work proceeds._

## Results

_To be populated._

## Forward-looking

_To be populated._

## Things to flag

_Surface assumptions explicitly here when drafting._

## Limitations

- CUAD is public and present in pretraining corpora. Condition comparisons are
  valid under shared contamination; absolute numbers are not
  leaderboard-comparable. This note travels with every downstream result.
