# Plan — Open-Harness Model Comparison

Status: draft · Owner: TBD · Last updated: 2025-01-01

## Goal

Build a static, reproducible web app for comparing model outputs across the
contract-extraction evaluation arms (base model vs +principles), one tab per
option, with all data served as plain files (no backend).

## Pages / tabs

| Tab | Path | Purpose |
|---|---|---|
| Grid | `/grid` | Category × Source agreement matrix (A) |
| Span track | `/span-track` | Offset-aligned span lane track (B) |
| Diff | `/diff` | Side-by-side contract diff with highlight layers (C) |
| Drilldown | `/drilldown` | Per-category drilldown table (D) |

Shared assets live in `data/` (JSON artifacts) and `style.css`. A small
`app.js` handles tab switching; each tab folder is self-contained so tabs can
be built or replaced independently.

## Repository layout

```
studies/010-open-harness-model-comparison/
├── plan.md                  # this file
├── data/                    # gold segments, model outputs, step1-4 intermediates
├── app/                     # index.html, app.js, style.css
└── scripts/                 # one-off regeneration / verification scripts
```

## Milestones

1. **M1 — Data inventory.** Emit gold span list, empty-arm outputs, and the
   41-category target set to `data/`. (Done: gold segments + step1.json.)
2. **M2 — Static shell.** `index.html` + tab router + shared CSS. Each tab
   renders from its own JSON, no cross-tab state.
3. **M3 — Diff + drilldown.** Wire the side-by-side diff pane and the
   per-category drilldown to the same JSON sources.
4. **M4 — Verification.** `verify_scores.py` runs clean; span offsets in
   `data/` match the model predictions used in the drilldown.

## Open questions

- Span-level offsets for model predictions: only text exists today; add an
  offset-matching pass before M4.
- Whether the +principles arm needs a separate tab or folds into `/diff`.

## Non-goals

- No backend/server component — everything served as static files.
- No model training or fine-tuning in this repo.
