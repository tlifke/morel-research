# Task: Build a contract visualization application

You are working in the directory you were started in. Everything you need is
already there. Do not access files outside this directory.

## Data

- `contract_text/` — 510 plain-text files, one per contract. Filenames are
  contract IDs (e.g. `FuseMedicalInc_20190321_10-K_EX-10.43_11575454_EX-10.43_Distributor Agreement.txt`).
- `contract_ground_truth` — JSONL, one record per contract. Each record has:
  - `contract_id` — matches a filename in `contract_text/` (plus `.txt`)
  - `gold` — an object mapping category names to
    `{ "is_impossible": bool, "spans": [string, ...] }`
  - There are 41 possible categories. `is_impossible: true` means the
    category is absent from the contract; in that case `spans` is empty.
  - Each span is an exact substring of that contract's text. A contract may
    have zero or more spans per category.

## What to build

Build something for viewing contracts. It should show a contract's text and
which categories are present in it.

## Constraints

- Use only the data in this directory.
- It must handle all 510 contracts, not a sample.

## Deliverable

The working application inside this directory.
