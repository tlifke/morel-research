---
id: studies/000-research-organization/investigations/002-plotly-migration
title: Plotly migration
status: complete
parents:
  - studies/000-research-organization
children: []
related: []
axes:
  llm_capability: high
  human_capability: medium
tags:
  - figures
  - plotly
  - infrastructure
created: 2026-05-11
updated: 2026-05-11
---

# Investigation 2 — Plotly migration

## Scope

Migrate `capability-map/plot.py` from matplotlib to Plotly so the
figure aligns with the repo's stated preference (see `CLAUDE.md`
"Figures" section). Produces both an interactive HTML view and a
static PNG export, and updates dependent docs/skills.

## Methods

Direct rewrite. `plot.py` was small (~85 lines) so no migration tooling
was needed. The new module uses `plotly.graph_objects.Scatter` with one
trace per status (for legend grouping), hover text composed from each
task's metadata, and a fixed legend order. Static PNG export goes
through kaleido. The HTML output uses CDN-hosted `plotly.js` so the
checked-in file stays small (~14 KB).

## Decisions

> **Decision 1 — emit both HTML and PNG** (2026-05-11)
> The HTML view is the primary artifact (interactive, hoverable); the
> PNG is for embedding in Markdown and one-pagers. Check both in.
> Alternative considered: HTML only, regenerate PNG ad hoc — rejected
> because the PNG is the artifact a casual reader sees first on GitHub.

> **Decision 2 — kaleido v1 + Chrome** (2026-05-11)
> kaleido 1.x dropped the bundled renderer and now drives Chrome via
> the DevTools protocol. One-time `plotly_get_chrome -y` is required.
> Alternative considered: pin kaleido <1.0 — rejected because the old
> bundled renderer is on a deprecation path and we'd be locking
> ourselves to it.

> **Decision 3 — `include_plotlyjs="cdn"`** (2026-05-11)
> HTML loads `plotly.js` from a CDN rather than inlining it (~4 MB
> savings per HTML file). Tradeoff: the HTML needs network to render
> interactively. Acceptable for a public research repo; if we ever
> need offline-first, switch to `include_plotlyjs="inline"`.

## Results

- `capability-map/plot.py` rewritten using `plotly.graph_objects`.
- New outputs: `capability-map.html` (interactive, ~14 KB) and
  `capability-map.png` (static export via kaleido).
- `capability-map/README.md` updated with new install steps
  (`pip install plotly kaleido pyyaml` plus `plotly_get_chrome -y`).
- `.claude/skills/capability-map-entry/SKILL.md` updated; removed
  the "Future" section that predicted this migration.

## Forward-looking

- Label overlap in the static PNG is unresolved (same issue under
  matplotlib). Possible fix: per-task `label_offset_x` / `label_offset_y`
  fields in `tasks.yaml`. Defer until it's an actual annoyance.
- The HTML view doesn't show the legend symbols (`circle`, `triangle-up`,
  etc.) at the same size they appear in markers. Plotly legend symbol
  sizing is a known wart; not worth chasing for a v1 figure.
- Future figures in this repo should follow the same pattern: Plotly
  module that emits HTML + PNG, hover text composed from underlying
  data, fixed color/symbol mapping for categorical groupings.

## Things to flag

- Kaleido's dependency on Chrome means CI environments need either
  Chrome installed or to skip PNG export (the HTML still renders).
  Worth documenting in any future CI setup.
- `tasks.yaml` is still hand-edited. Once the schema stabilizes,
  consider a JSON Schema and a validator. Not blocking.

## Limitations

- The capability map remains a *visualization*, not a *measurement*.
  Coordinates are eyeball priors. The migration changes how it's
  drawn, not how it's calibrated.
- Plotly's static export depends on a headless Chrome binary
  managed outside this repo (~150 MB), which is heavier than
  matplotlib's pure-Python rendering path. The tradeoff is
  interactivity in the HTML view.
