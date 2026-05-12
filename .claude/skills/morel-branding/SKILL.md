---
name: morel-branding
description: Apply Morel brand-consistent styling (colors, typography, layout) to Plotly figures in the morel-research repo. Use whenever creating, modifying, or styling a Plotly figure — including new figures for an investigation, edits to an existing figure script under `studies/.../figures/`, the capability-map plot, or any one-off chart. Triggers on phrases like "make a plot", "add a figure", "style this chart", "update the plot", "render a Plotly figure", "use Morel colors", "brand the figure", or whenever a `plotly.graph_objects.Figure` is being built or modified. Also trigger when a figure currently uses default Plotly colors (`#1f77b4` etc.) or ad-hoc hex picks (`#5B9BD5`, `#A4C5E8`, `#C44E52`, etc.) — those should be replaced. **Do not** apply this skill to LaTeX writeups — those use vanilla LaTeX defaults by convention.
---

# morel-branding

Style Plotly figures with the Morel brand palette and typography.

## When to use

Any time Claude is creating or modifying a `plotly.graph_objects.Figure`
in this repo. The skill keeps figures visually consistent across
investigations and matches the Morel brand guide at:

`/Users/tylerlifke/Projects/morel-primordia/projects/morel-life/brand-guide/BRAND-GUIDE.md`

## What's provided

A helper module at `branding.py` (next to this SKILL.md) exports:

- `MOREL_COLORS` — dict of semantic palette names → hex.
- `MOREL_CYCLE` — ordered color cycle for grouped traces.
- `MOREL_FONT_FAMILY` / `MOREL_SERIF_FAMILY` — Plotly font strings with
  sensible fallbacks (Inter / DM Sans / system).
- `MOREL_DIVERGING_SCALE` / `MOREL_SEQUENTIAL_SCALE` — colorscales for
  heatmaps and choropleths.
- `apply_morel_template(fig, *, title=None, subtitle=None, attribution=None)`
  — applies template, fonts, colorway, axis styling, and an optional
  attribution footer to any `go.Figure`. Safe to call on any figure.
- `cycle_color(i)` / `style_bars_by_group(labels)` — utilities for
  mapping series to brand colors.

## How to use it from a figure script

The skill module isn't on `sys.path` by default. Add the path at the top
of any figure script:

```python
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[N]  # walk to repo root
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import (
    apply_morel_template,
    MOREL_COLORS,
    MOREL_CYCLE,
    cycle_color,
)
```

Where `N` is the number of `parents[]` hops from the script to the repo
root. For `studies/001-.../investigations/006-.../figures/foo.py`, that's
`parents[5]`. For `capability-map/plot.py`, that's `parents[1]`.

Then in the figure:

```python
fig = go.Figure()
# ... add traces ...
apply_morel_template(
    fig,
    title="My figure title",
    subtitle="optional smaller subtitle",
    attribution="studies/001-tool-calibration / inv 006",
)
```

## Color conventions

Follow the brand guide's product-data convention:

- **Primary metric / series 1** → Terracotta (`MOREL_COLORS["terracotta"]`).
- **Secondary metric / series 2** → Forest Green
  (`MOREL_COLORS["forest_green"]`).
- **Three or more groups** → pull from `MOREL_CYCLE` in order, or use
  `style_bars_by_group(labels)` to get a dict.
- **Reference lines / gridlines** → `MOREL_COLORS["cream_dark"]` or
  `MOREL_COLORS["axis_gridline"]`.
- **Annotations / muted callouts** → `MOREL_COLORS["muted_text"]`.
- **Errors / missed goals** → `MOREL_COLORS["error_red"]`.

## What this skill does NOT change

- Figure semantics (data, axes, what's plotted) — only styling.
- Source-data files (JSONL, schemas).
- Figures owned by humans for prose work — the user's prose stays untouched.

## Don't

- Don't hardcode default Plotly colors (`#1f77b4`, etc.) or ad-hoc hex
  values when brand colors apply. Pull from `MOREL_COLORS` /
  `MOREL_CYCLE`.
- Don't override the template after calling `apply_morel_template` —
  call it last, or use `fig.update_layout(..., overwrite=False)` for
  any further tweaks.
- Don't add Morel logos to interior figures; the logo belongs on
  one-pagers (LaTeX template), not on every chart.

## LaTeX writeups

By repo convention, LaTeX one-pagers and writeups use **vanilla LaTeX
defaults** — no brand colors, no custom fonts, no brand styling. Keep
to the standard `article` class with Computer Modern. See
`one-pagers/template/one-pager.tex` for the canonical template.

Section structure for one-pagers (fixed order): **Research question ·
Context · Methods · Figure · Takeaways**.
