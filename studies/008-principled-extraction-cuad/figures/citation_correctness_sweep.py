from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import MOREL_COLORS, MOREL_SEQUENTIAL_SCALE, apply_morel_template

HERE = Path(__file__).resolve().parent
DEFAULT_SWEEP = HERE / "data" / "citation_sweep_fixture.json"

CELLS = [
    ("right_answer_wrong_citation", "Right answer \u2192 wrong reason", "terracotta", 4.0),
    ("right_answer_right_citation", "Right answer \u2192 right reason", "forest_green", 2.0),
    ("wrong_answer_right_citation", "Wrong answer \u2192 right reason", "mustard", 2.0),
    ("wrong_answer_wrong_citation", "Wrong answer \u2192 wrong reason", "muted_text", 2.0),
]

ATTRIBUTION = "studies/008-principled-extraction-cuad / WS5 harness"


def load_sweep(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _subtitle(sweep: dict) -> str:
    n = sweep.get("n_decisions")
    rule = sweep.get("citation_rule", {})
    citation_rule = (
        "citation correct = exact set match"
        if rule.get("requires_exact_set")
        else f"citation correct = F1 >= {rule.get('citation_f1_correct')}"
    )
    base = f"{n} decisions · {citation_rule}"
    if sweep.get("__fixture__"):
        return base + " · SYNTHETIC FIXTURE, NOT EXPERIMENTAL DATA"
    return base


def build_curve_figure(sweep: dict, as_rate: bool = False) -> go.Figure:
    thresholds = sweep["span_f1_thresholds"]
    points = sweep["points"]
    key = "rates" if as_rate else "counts"

    fig = go.Figure()
    for cell, label, color, width in CELLS:
        fig.add_trace(
            go.Scatter(
                x=thresholds,
                y=[p[key][cell] for p in points],
                name=label,
                mode="lines+markers",
                line=dict(color=MOREL_COLORS[color], width=width),
                marker=dict(size=7 if width > 3 else 5),
                hovertemplate=(
                    f"<b>{label}</b><br>threshold t=%{{x}}<br>"
                    + ("rate" if as_rate else "decisions")
                    + "=%{y}<extra></extra>"
                ),
            )
        )

    headline = sweep.get("headline_span_f1_threshold")
    if headline is not None:
        fig.add_vline(
            x=headline,
            line=dict(color=MOREL_COLORS["dark_earth"], width=1.5, dash="dot"),
        )
        fig.add_annotation(
            x=headline,
            y=1.02,
            yref="paper",
            text=f"headline t = {headline}",
            showarrow=False,
            font=dict(color=MOREL_COLORS["muted_text"], size=11),
            xanchor="left",
            xshift=6,
        )

    fig.update_xaxes(
        title_text="span-F1 threshold t for &#8220;answer correct&#8221;",
        tickmode="array",
        tickvals=thresholds,
        range=[min(thresholds) - 0.03, max(thresholds) + 0.03],
    )
    fig.update_yaxes(
        title_text="share of decisions" if as_rate else "decisions",
        rangemode="tozero",
    )
    apply_morel_template(
        fig,
        title="Citation quality by answer correctness, swept over t",
        subtitle=_subtitle(sweep),
        attribution=ATTRIBUTION,
    )
    fig.update_layout(
        legend=dict(
            orientation="h",
            y=-0.24,
            x=0.5,
            xanchor="center",
            font=dict(size=12),
            entrywidthmode="fraction",
            entrywidth=0.42,
        ),
        margin=dict(l=80, r=40, t=110, b=150),
        width=1120,
        height=620,
    )
    return fig


def build_surface_figure(sweep: dict) -> go.Figure | None:
    surface = sweep.get("surface")
    if not surface:
        return None
    thresholds = sweep["span_f1_thresholds"]
    citation_axis = [row["citation_f1_threshold"] for row in surface]
    z = [
        [p["counts"]["right_answer_wrong_citation"] for p in row["points"]]
        for row in surface
    ]
    fig = go.Figure(
        go.Heatmap(
            x=thresholds,
            y=citation_axis,
            z=z,
            colorscale=MOREL_SEQUENTIAL_SCALE,
            colorbar=dict(title="decisions"),
            hovertemplate=(
                "span-F1 t=%{x}<br>citation-F1 t=%{y}<br>"
                "right answer, wrong reason=%{z}<extra></extra>"
            ),
        )
    )
    fig.update_xaxes(title_text="span-F1 threshold t", tickvals=thresholds)
    fig.update_yaxes(title_text="citation-F1 threshold", tickvals=citation_axis)
    apply_morel_template(
        fig,
        title="Right answer, wrong reason across both thresholds",
        subtitle=_subtitle(sweep),
        attribution=ATTRIBUTION,
    )
    fig.update_layout(width=860, height=520)
    return fig


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sweep", type=Path, default=DEFAULT_SWEEP)
    parser.add_argument("--out-dir", type=Path, default=HERE)
    parser.add_argument("--stem", default="citation_correctness_sweep")
    parser.add_argument("--rates", action="store_true")
    parser.add_argument("--html", action="store_true")
    args = parser.parse_args()

    sweep = load_sweep(args.sweep)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    fig = build_curve_figure(sweep, as_rate=args.rates)
    png = args.out_dir / f"{args.stem}.png"
    fig.write_image(str(png), engine="kaleido", scale=2)
    written = [png]
    if args.html:
        html = args.out_dir / f"{args.stem}.html"
        fig.write_html(str(html), include_plotlyjs="cdn")
        written.append(html)

    surface = build_surface_figure(sweep)
    if surface is not None:
        surface_png = args.out_dir / f"{args.stem}_surface.png"
        surface.write_image(str(surface_png), engine="kaleido", scale=2)
        written.append(surface_png)

    for path in written:
        print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
