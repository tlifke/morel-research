# Contract Category Viewer

A fully offline, zero-setup web app for browsing 510 contracts and their
ground-truth category annotations. Every annotated span is highlighted in the
contract text and color-coded by its category.

## How to run

Open `index.html` in any modern web browser (double-click it, or drag it onto a
browser window). No server, no network access, no installation — all data is
embedded in `data.js` next to it.

    open index.html      # macOS

## Using the app

- **Left sidebar** — searchable list of all 510 contracts (each shows how many
  categories are annotated). Click to open, or type to filter by name.
- **Category bar** — chips for every category present in the open contract,
  with the number of spans. Click a chip to hide/show that category's
  highlights; hover to spotlight its spans in the text.
- **"Show all" button** — re-enables all hidden categories.
- **Prev / Next buttons** (or `←` / `→` / `j` / `k` keys) — move between
  contracts. Press `/` to jump to the search box.
- Hover any highlight to see its category name(s) in a tooltip.

## Files

| File | Purpose |
|---|---|
| `index.html` | The application (UI + logic) |
| `data.js` | All 510 contract texts + ground-truth spans, generated from the source data |
| `build_data.py` | Regenerates `data.js` from `contract_text/` and `contract_ground_truth` (run `python3 build_data.py`) |
| `contract_text/`, `contract_ground_truth` | Original source data (unchanged) |
