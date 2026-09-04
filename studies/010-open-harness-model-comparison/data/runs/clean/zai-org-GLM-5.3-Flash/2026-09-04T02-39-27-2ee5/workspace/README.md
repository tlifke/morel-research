# Contract Category Viewer

A self-contained web app for browsing 510 SEC exhibit contracts and seeing
which of the 41 ground-truth categories appear in each one, with every
annotated span highlighted in the contract text.

## How to run

**Just open `index.html` in any web browser** (double-click it, or drag it
into a browser window). That's it — everything (all 510 contract texts and
all annotations) is embedded in the single HTML file, so it works completely
offline with no server and no setup.

Optional, functionally identical alternative — serve it over HTTP:

```
python3 -m http.server 8000
# then open http://localhost:8000
```

## Using the app

- **Left sidebar** — searchable list of all 510 contracts. Click one to open it
  (or use the Prev/Next buttons, or the `j` / `k` arrow keys).
- **Center** — the full contract text with every annotated span highlighted.
  Each category has its own color; overlapping categories are shown as split
  color bands. Hovering a highlight shows its category name(s) in a tooltip.
- **Right panel** — the categories present in the current contract
  (`is_impossible: false`), with color swatch and span count.
  - Click a category **name** to jump/cycle through its spans.
  - Click a category **swatch** to hide/show that category's highlights.
  - "Show all" re-enables every category.

## Files

| File | Purpose |
|---|---|
| `index.html` | **The app** — fully self-contained, open it in a browser |
| `app_template.html` | App source (UI + logic) without the embedded data |
| `build.py` | Rebuilds `index.html` from `contract_ground_truth` + `contract_text/` (`python3 build.py`) |
| `verify.js` | Spot-check verification in headless Chromium (sample contracts + interactions) |
| `verify_all.js` | Full sweep: renders **all 510** contracts headlessly and verifies every span exactly |
| `screenshot.png` | Screenshot of the running app |

## Verification

Both verifiers run in headless Chromium (Playwright) and check, for every
contract rendered:

1. The rendered DOM text is byte-identical to the original contract file.
2. Every ground-truth span is exactly covered by highlights tagged with the
   right category (coverage is contiguous, never leaks outside the span), with
   nested/overlapping spans in the same category handled as their union.
3. The category panel lists exactly the present categories with correct counts.

Run them with:

```
NODE_PATH=$(npm root -g) node verify.js      # sample + interaction checks
NODE_PATH=$(npm root -g) node verify_all.js  # all 510 contracts, all 13,823 spans
```

Last run result: **510/510 contracts, 13,823 spans verified exactly.**
