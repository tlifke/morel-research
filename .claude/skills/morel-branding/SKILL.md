---
name: morel-branding
description: Apply Morel brand-consistent styling to Plotly figures AND to LaTeX one-pagers / writeups in the morel-research repo. Use whenever creating or modifying a Plotly `Figure`, OR scaffolding/editing a LaTeX writeup under `studies/.../writeups/` or `one-pagers/`. Triggers on phrases like "make a plot", "add a figure", "style this chart", "render a Plotly figure", "use Morel colors", "brand the figure", "compile the one-pager", "style the writeup", "scaffold a one-pager". Also trigger when a figure currently uses default Plotly colors (`#1f77b4` etc.) or ad-hoc hex picks, or when a LaTeX file uses Computer Modern defaults instead of the brand fonts/colors.
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

## LaTeX one-pagers and writeups

The brand also ships as a LaTeX package at `one-pagers/morel.sty`
(source of truth for typography + colors in printed/PDF artifacts).
Use it whenever you scaffold or edit a `.tex` file under
`one-pagers/` or `studies/.../writeups/`.

What the package provides:

- Brand palette as `xcolor` names: `morelprimary` (terracotta),
  `morelaccent` (forest green), `morelslate`, `morelparchment`,
  `moreldark`, `morelpage`, `morelborder`, `morelmuted`.
- Brand fonts via `fontspec`: Inter / DM Sans body, DM Serif Display
  for titles (with Helvetica Neue / Georgia fallbacks for vanilla
  TeX installs).
- Section formatting: bold forest-green sans, tight vertical rhythm.
- Caption styling: bold green "Figure N." label, period separator.
- Page footer via `fancyhdr`: terracotta **morel** • research on the
  left, `\paperRepoShort` on the right.
- `\moreltitle{TITLE}{AUTHORS}{DATE}{REPO}{STUDY-REF-SHORT}` — title
  block with serif title, muted metadata line, terracotta + cream rules.

How to use from a writeup:

```latex
\documentclass[10pt]{article}
\usepackage{morel}
\newcommand{\paperRepoShort}{tlifke/morel-research}

\begin{document}
\moreltitle
  {Title}
  {Authors}
  {YYYY-MM-DD}
  {\href{https://github.com/tlifke/morel-research}{tlifke/morel-research}}
  {studies/NNN / writeups/NNN}

\section*{Research question}
...
\section*{Context}
...
\section*{Methods}
...

\begin{figure}[h]
  \centering
  \includegraphics[width=0.95\linewidth]{path/to/figure.png}
  \caption{One-sentence caption.}
\end{figure}

\section*{Takeaways}
\begin{itemize}
  \item ...
\end{itemize}
\end{document}
```

Compile with **xelatex** (fontspec requires it). The writeup's
`Makefile` should set `TEXINPUTS` to include the repo's
`one-pagers/` directory and invoke `latexmk -xelatex`. See
`one-pagers/template/one-pager.tex` and its Makefile for the
canonical example.

### Section structure for one-pagers

Fixed order (do not reorder): **Research question · Context ·
Methods · Figure · Takeaways**. Results live in the figure and
takeaways; forward-looking notes fold into context or the closing
takeaway. Keep STUDY-REF-SHORT under ~50 characters in the title
block or it will crowd the metadata line.

### Don't (LaTeX)

- Don't re-define the brand colors locally in a writeup. Pull from
  `morel.sty` so changes propagate.
- Don't use `pdflatex` — fontspec requires xelatex.
- Don't write prose in scaffolded one-pagers. The human owns the
  prose; Claude scaffolds structure, fonts, layout, and the figure
  wiring only.
