import sys
from datetime import date
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))
sys.path.insert(0, str(HERE))

from branding import MOREL_COLORS, apply_morel_template  # noqa: E402
from drift_data import load  # noqa: E402

AUDIT = date(2026, 7, 20)
LAST_ACTIVE = date(2026, 6, 30)


def _d(s):
    y, m, dd = (int(x) for x in s.split("-"))
    return date(y, m, dd)


def build():
    rows = sorted(load(), key=lambda r: (_d(r["frontmatter_updated"]), r["short"]))

    fig = go.Figure()
    seen = set()
    for i, r in enumerate(rows):
        start = _d(r["frontmatter_updated"])
        color = MOREL_COLORS["terracotta"] if r["mismatch"] else MOREL_COLORS["forest_green"]
        name = "status was wrong" if r["mismatch"] else "status was right"
        fig.add_trace(
            go.Scatter(
                x=[start, AUDIT],
                y=[i, i],
                mode="lines",
                line=dict(color=color, width=7),
                opacity=0.85 if r["mismatch"] else 0.4,
                name=name,
                legendgroup=name,
                showlegend=name not in seen,
                hovertemplate=(
                    f"{r['short']}<br>declared: {r['declared']}"
                    f"<br>actual: {r['reconciled']}"
                    f"<br>unrevised since {r['frontmatter_updated']}<extra></extra>"
                ),
            )
        )
        seen.add(name)

    fig.add_vline(
        x=LAST_ACTIVE.isoformat(),
        line=dict(color=MOREL_COLORS["muted_text"], width=1.5, dash="dot"),
    )
    fig.add_annotation(
        x=LAST_ACTIVE.isoformat(),
        y=len(rows) + 0.6,
        text="work pauses",
        showarrow=False,
        xanchor="right",
        font=dict(size=11, color=MOREL_COLORS["muted_text"]),
    )
    fig.add_vline(
        x=AUDIT.isoformat(),
        line=dict(color=MOREL_COLORS["dark_earth"], width=1.5),
    )
    fig.add_annotation(
        x=AUDIT.isoformat(),
        y=len(rows) + 0.6,
        text="audit",
        showarrow=False,
        xanchor="left",
        font=dict(size=11, color=MOREL_COLORS["dark_earth"]),
    )

    fig.update_yaxes(
        tickvals=list(range(len(rows))),
        ticktext=[r["short"] for r in rows],
        tickfont=dict(size=10, family="ui-monospace, SFMono-Regular, Menlo, monospace"),
        showgrid=False,
        range=[-1, len(rows) + 1.6],
    )
    fig.update_xaxes(showgrid=True, tickformat="%b %d")

    apply_morel_template(
        fig,
        title="Each bar is a status field nobody revised",
        subtitle="From the last time the document's frontmatter was touched to the audit. "
        "17 of these bars were asserting something false the whole way.",
        attribution="morel-research / studies/000-research-organization",
    )
    fig.update_layout(
        width=980,
        height=760,
        margin=dict(l=250, r=60, t=140, b=60),
        legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="left", x=0),
    )
    return fig


def stats():
    rows = load()
    wrong_days = sum((AUDIT - _d(r["frontmatter_updated"])).days for r in rows if r["mismatch"])
    all_days = sum((AUDIT - _d(r["frontmatter_updated"])).days for r in rows)
    return wrong_days, all_days


if __name__ == "__main__":
    fig = build()
    fig.write_image(str(HERE / "staleness_timeline.png"), scale=2)
    fig.write_html(str(HERE / "staleness_timeline.html"), include_plotlyjs="cdn")
    w, a = stats()
    print(f"document-days under a false status: {w} of {a} ({w / a:.0%})")
