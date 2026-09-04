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

An application that lets a person read one contract at a time and see which
categories are present in it, with every span rendered as a highlight inside
the contract text. Specifically:

1. The user can select any contract from the 510 and view its full text.
2. The application shows the categories present in the selected contract
   (i.e. those with `is_impossible: false`).
3. Every span for the selected contract is visually highlighted in the
   contract text, identifiable by its category.
4. The user can inspect the application themselves — it must run locally
   with no network access and no setup steps beyond opening/starting it.

## Constraints

- Use only the data in this directory. Do not download anything.
- The application must handle all 510 contracts, not a sample.

## Deliverable

The working application inside this directory, plus whatever minimal
instructions a person needs to open and use it.
