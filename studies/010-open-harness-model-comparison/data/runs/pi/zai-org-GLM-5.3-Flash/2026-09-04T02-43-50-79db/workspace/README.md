# Contract Category Viewer

A self-contained web app for browsing 510 contracts and seeing, for each one,
which of the 41 categories are present, with every ground-truth span rendered
as a color-coded highlight inside the contract text.

## How to open

**No setup, no server, no network needed.** Just open `index.html` in any
modern browser (double-click it, or e.g. `open index.html` on macOS).

All 510 contract texts and the ground-truth annotations are embedded in that
single file, so everything works offline from a plain `file://` URL.

## Using the app

- **Left panel** — searchable list of all 510 contracts (with the number of
  categories present in each). Click one to open it, or use the
  **Prev/Next** buttons or the **←/→ arrow keys**.
- **Center** — the full contract text. Every annotated span is highlighted;
  the color identifies the category. Hover a highlight to see its category
  name and character offsets (overlapping spans from different categories
  show a blended color and list all of them).
- **Right panel** — all 41 categories. Present ones show a color swatch and
  span count; absent ones are greyed out and struck through. Click a present
  category to jump to its first highlight. Hovering a category emphasizes all
  of its highlights in the text. Uncheck "show highlights" to read the plain
  text.

## Files

| File | Purpose |
|---|---|
| `index.html` | The app (all data embedded — this is all you need) |
| `app_template.html` | App source with a `/*__DATA__*/` placeholder |
| `gen_app.py` | Regenerates `index.html` from `contract_text/` + `contract_ground_truth` |
| `verify_app.py` | Headless-browser (Playwright) end-to-end verification |

## Verification performed

`verify_app.py` drives headless Chromium against `index.html` and checks, for
a sample of 9 contracts, that: the right text is shown, present/absent
category sets match the ground truth, and every gold span is rendered as a
highlight whose DOM position and text exactly match the ground-truth
substring. A separate full pass verified **all 510 contracts**: for every
category, the union of highlighted DOM ranges exactly equals the union of the
gold spans (character-for-character), with no highlights for absent
categories. Run it yourself with `python3 verify_app.py` (requires
`playwright` with Chromium).
