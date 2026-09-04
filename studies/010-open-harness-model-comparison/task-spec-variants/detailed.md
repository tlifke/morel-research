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

A single-page static web application (no build step, no frameworks, no
external CDNs — vanilla HTML/CSS/JavaScript only) that renders contracts
with their ground-truth category highlights.

### Architecture

- `index.html` (plus any `.js`/`.css` files you create) in the current
  directory. The app must work when served with `python3 -m http.server`
  from this directory; load all data with `fetch` from relative paths
  (do not rely on `file://` — browsers block XHR/fetch there).
- On startup: fetch `contract_ground_truth`, parse it as JSONL
  (split on newlines, `JSON.parse` each line), and build the contract list
  from it. Fetch a contract's text from `contract_text/<contract_id>.txt`
  when it is selected (do not preload all 510).

### UI requirements

1. **Contract selector**: a searchable dropdown or list of all 510
   contracts (show the `contract_id`; support text search over it).
2. **Contract text pane**: the full text of the selected contract,
   HTML-escaped, monospaced or serif, with line wrapping.
3. **Highlights**: every span of every present category is highlighted in
   the text. Assign each of the 41 categories a distinct, stable color (a
   fixed palette indexed by category name). Wrap each occurrence of a span
   substring in the text with its category's background color. If spans
   overlap, the inner one wins visually (e.g. rendered with a border or
   darker shade) so both remain visible.
4. **Category panel**: for the selected contract, list the categories
   present (`is_impossible: false`), each with its color swatch, its number
   of spans, and a toggle to show/hide that category's highlights.
5. **Span list**: clicking a category in the panel shows its spans as
   snippets; clicking a snippet scrolls the text pane to that highlight.
6. **Status line**: display the selected contract's `contract_id`, its
   character count, and the count of present categories.

## Constraints

- Use only the data in this directory. Do not download anything.
- The application must handle all 510 contracts, not a sample.
- Verify your work before finishing: open or run the application yourself,
  render at least one contract end-to-end, and check that the highlights
  match the spans in the ground truth.

## Deliverable

The working application inside this directory, plus a short `README.md`
saying how to start and use it.
