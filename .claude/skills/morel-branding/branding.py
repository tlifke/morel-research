"""Morel brand-consistent styling for Plotly figures in morel-research.

Source of truth for the brand palette and typography:
  morel-primordia/projects/morel-life/brand-guide/BRAND-GUIDE.md

Use:
    from branding import apply_morel_template, MOREL_COLORS, MOREL_CYCLE

    fig = go.Figure(...)
    apply_morel_template(fig, title="My figure", subtitle="optional")
"""

from __future__ import annotations

from typing import Iterable, Optional

import plotly.graph_objects as go

MOREL_COLORS: dict[str, str] = {
    "terracotta": "#C1694F",
    "terracotta_light": "#D4957E",
    "terracotta_dark": "#A3523A",
    "forest_green": "#2D5016",
    "green_light": "#4A7A2E",
    "parchment": "#F5E6D3",
    "cream_dark": "#E8D5BF",
    "dark_earth": "#3B2F2F",
    "off_white": "#FAFAF8",
    "error_red": "#C14F4F",
    "muted_text": "#6B5E5E",
    "axis_gridline": "#E8D5BF",
}

MOREL_FONT_FAMILY = (
    "Inter, 'DM Sans', -apple-system, BlinkMacSystemFont, "
    "'Segoe UI', Helvetica, Arial, sans-serif"
)

MOREL_SERIF_FAMILY = (
    "'DM Serif Display', Georgia, 'Times New Roman', serif"
)

MOREL_CYCLE: list[str] = [
    MOREL_COLORS["terracotta"],
    MOREL_COLORS["forest_green"],
    MOREL_COLORS["terracotta_dark"],
    MOREL_COLORS["green_light"],
    MOREL_COLORS["terracotta_light"],
    MOREL_COLORS["dark_earth"],
    MOREL_COLORS["error_red"],
]

MOREL_DIVERGING_SCALE: list[list] = [
    [0.0, MOREL_COLORS["forest_green"]],
    [0.5, MOREL_COLORS["parchment"]],
    [1.0, MOREL_COLORS["terracotta"]],
]

MOREL_SEQUENTIAL_SCALE: list[list] = [
    [0.0, MOREL_COLORS["parchment"]],
    [0.5, MOREL_COLORS["terracotta_light"]],
    [1.0, MOREL_COLORS["terracotta_dark"]],
]


def cycle_color(i: int) -> str:
    """Return the i-th color in the Morel cycle (wraps)."""
    return MOREL_CYCLE[i % len(MOREL_CYCLE)]


def apply_morel_template(
    fig: go.Figure,
    *,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    attribution: Optional[str] = "morel-research",
    show_attribution: bool = True,
) -> go.Figure:
    """Apply Morel brand styling to a Plotly figure.

    Mutates and returns the figure. Safe to call on any figure without
    breaking the data. Existing layout fields are preserved unless they
    conflict with brand styling (title/font/colors/template).

    Args:
      fig: plotly Figure to style.
      title: if given, replaces the title text.
      subtitle: optional small line beneath the title.
      attribution: short label rendered as a footer annotation.
      show_attribution: set False to omit the footer.
    """
    existing_title = fig.layout.title.text if fig.layout.title else None
    title_text = title if title is not None else existing_title

    title_html = None
    if title_text:
        title_html = f"<span style='color:{MOREL_COLORS['dark_earth']}'>{title_text}</span>"
        if subtitle:
            title_html += (
                f"<br><span style='font-size:13px;color:{MOREL_COLORS['muted_text']};"
                f"font-weight:400'>{subtitle}</span>"
            )

    fig.update_layout(
        template="plotly_white",
        font=dict(
            family=MOREL_FONT_FAMILY,
            color=MOREL_COLORS["dark_earth"],
            size=13,
        ),
        title=dict(
            text=title_html,
            font=dict(
                family=MOREL_FONT_FAMILY,
                size=18,
                color=MOREL_COLORS["dark_earth"],
            ),
            x=0.02,
            xanchor="left",
            y=0.97,
            yanchor="top",
        ),
        paper_bgcolor=MOREL_COLORS["off_white"],
        plot_bgcolor="#FFFFFF",
        colorway=MOREL_CYCLE,
        margin=dict(l=72, r=36, t=90 if subtitle else 72, b=72),
        legend=dict(
            font=dict(family=MOREL_FONT_FAMILY, size=12,
                      color=MOREL_COLORS["dark_earth"]),
            bgcolor="rgba(255,255,255,0.92)",
            bordercolor=MOREL_COLORS["cream_dark"],
            borderwidth=1,
        ),
        hoverlabel=dict(
            font=dict(family=MOREL_FONT_FAMILY,
                      color=MOREL_COLORS["dark_earth"]),
            bgcolor=MOREL_COLORS["parchment"],
            bordercolor=MOREL_COLORS["terracotta"],
        ),
    )

    axis_style = dict(
        gridcolor=MOREL_COLORS["axis_gridline"],
        linecolor=MOREL_COLORS["cream_dark"],
        zerolinecolor=MOREL_COLORS["cream_dark"],
        tickfont=dict(family=MOREL_FONT_FAMILY,
                      color=MOREL_COLORS["dark_earth"], size=12),
        title=dict(font=dict(family=MOREL_FONT_FAMILY,
                             color=MOREL_COLORS["dark_earth"], size=13)),
    )
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)

    if show_attribution and attribution:
        fig.add_annotation(
            text=f"<span style='color:{MOREL_COLORS['muted_text']}'>"
                 f"{attribution}</span>",
            xref="paper", yref="paper",
            x=1.0, y=-0.12,
            xanchor="right", yanchor="top",
            showarrow=False,
            font=dict(family=MOREL_FONT_FAMILY, size=10),
        )

    return fig


def style_bars_by_group(
    labels: Iterable[str],
) -> dict[str, str]:
    """Map an iterable of group labels to brand colors in cycle order."""
    return {label: cycle_color(i) for i, label in enumerate(labels)}
