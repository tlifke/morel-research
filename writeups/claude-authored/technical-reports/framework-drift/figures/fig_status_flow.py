import sys
from collections import Counter
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[4]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))
sys.path.insert(0, str(HERE))

from branding import MOREL_COLORS, apply_morel_template  # noqa: E402
from drift_data import load  # noqa: E402

STATES = ["planned", "in-progress", "complete"]
Y = {"planned": 3, "in-progress": 2, "complete": 1}


def build():
    rows = load()
    flows = Counter((r["declared"], r["reconciled"]) for r in rows)
    declared_totals = Counter(r["declared"] for r in rows)
    reconciled_totals = Counter(r["reconciled"] for r in rows)

    fig = go.Figure()

    for (src, dst), count in sorted(flows.items(), key=lambda kv: -kv[1]):
        changed = src != dst
        color = MOREL_COLORS["terracotta"] if changed else MOREL_COLORS["forest_green"]
        fig.add_trace(
            go.Scatter(
                x=[0, 1],
                y=[Y[src], Y[dst]],
                mode="lines",
                line=dict(color=color, width=2 + 2.4 * count),
                opacity=0.75 if changed else 0.35,
                hovertemplate=f"{src} → {dst}: {count} docs<extra></extra>",
                showlegend=False,
            )
        )
        label_x = 0.34
        label_y = Y[src] + (Y[dst] - Y[src]) * label_x
        fig.add_annotation(
            x=label_x,
            y=label_y,
            text=f"<b>{count}</b>",
            showarrow=False,
            font=dict(size=13, color=MOREL_COLORS["off_white"]),
            bgcolor=color,
            borderpad=3,
            opacity=0.95,
        )

    for state in STATES:
        fig.add_trace(
            go.Scatter(
                x=[0, 1],
                y=[Y[state], Y[state]],
                mode="markers",
                marker=dict(size=16, color=MOREL_COLORS["dark_earth"]),
                hoverinfo="skip",
                showlegend=False,
            )
        )
        fig.add_annotation(
            x=-0.04,
            y=Y[state],
            text=f"{state}<br><span style='font-size:11px'>{declared_totals[state]} docs</span>",
            showarrow=False,
            xanchor="right",
            font=dict(size=13, color=MOREL_COLORS["dark_earth"]),
        )
        fig.add_annotation(
            x=1.04,
            y=Y[state],
            text=f"{state}<br><span style='font-size:11px'>{reconciled_totals[state]} docs</span>",
            showarrow=False,
            xanchor="left",
            font=dict(size=13, color=MOREL_COLORS["dark_earth"]),
        )

    fig.add_annotation(
        x=0,
        y=3.55,
        text="<b>What the index said</b><br><span style='font-size:11px'>frontmatter, 2026-07-20</span>",
        showarrow=False,
        xanchor="center",
        font=dict(size=14, color=MOREL_COLORS["muted_text"]),
    )
    fig.add_annotation(
        x=1,
        y=3.55,
        text="<b>What the documents said</b><br><span style='font-size:11px'>after reconciliation</span>",
        showarrow=False,
        xanchor="center",
        font=dict(size=14, color=MOREL_COLORS["muted_text"]),
    )

    fig.update_xaxes(range=[-0.34, 1.34], showgrid=False, zeroline=False, showticklabels=False)
    fig.update_yaxes(range=[0.45, 3.95], showgrid=False, zeroline=False, showticklabels=False)

    apply_morel_template(
        fig,
        title="17 of 28 research documents disagreed with themselves",
        subtitle="Declared status vs. status implied by the document's own contents. "
        "Terracotta = the index was wrong.",
        attribution="morel-research / studies/000-research-organization",
    )
    fig.update_layout(width=980, height=560, margin=dict(l=150, r=150, t=130, b=60))
    return fig


if __name__ == "__main__":
    fig = build()
    fig.write_image(str(HERE / "status_flow.png"), scale=2)
    fig.write_html(str(HERE / "status_flow.html"), include_plotlyjs="cdn")
