# Contract Category Explorer

A local, offline app for browsing the 510 contracts in `contract_text/` with
their gold category spans (`contract_ground_truth`) rendered as highlights.

## How to run

**No setup, no network, no build step required.**

Open `index.html` in any modern web browser (double-click it, or
`open index.html` on macOS). That's it — all contract texts and annotations
are embedded in the local `data.js` file next to it, and the page works from
the `file://` protocol.

Optionally, to serve it over HTTP instead:

```
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Using the app

- **Left panel** — searchable list of all 510 contracts; click to open one
  (or use `Prev`/`Next`, the `j`/`k` or arrow keys; `/` focuses search).
- **Center** — full contract text. Every annotated span is highlighted in the
  color of its category; overlaps of multiple categories are rendered as
  stripes. Hover a highlight to see its category name(s).
- **Right panel** — the categories present in the current contract with span
  counts. Click a category to jump through its spans; click its color chip to
  hide/show that category's highlights. Hover a category to spotlight its
  spans in the text. Use "Show absent categories" to also list the 41-category
  set members that are absent (`is_impossible`).

## Files

- `index.html` — the application (self-contained UI + logic)
- `data.js` — generated data bundle: all 510 contract texts + gold annotations
- `build_data.py` — regenerates `data.js` from `contract_text/` and
  `contract_ground_truth` (only needed if the source data changes)
- `test_render.mjs` — headless test (`node test_render.mjs`) verifying that
  highlight segments tile every contract's text exactly and fully cover all
  13,823 gold spans across all 510 contracts
