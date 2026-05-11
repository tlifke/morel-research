"""Render the capability map from tasks.yaml using Plotly.

Outputs two artifacts next to this script:
  - capability-map.html  (interactive view; open in a browser)
  - capability-map.png   (static export via kaleido, for embedding)

Treat the rendered figure as a living artifact: it regenerates from
tasks.yaml. The repo's stated preference is Plotly over matplotlib
(see CLAUDE.md "Figures" section).

Usage:
    pip install plotly kaleido pyyaml
    python3 capability-map/plot.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go
import yaml

HERE = Path(__file__).resolve().parent
TASKS_PATH = HERE / "tasks.yaml"
OUT_HTML = HERE / "capability-map.html"
OUT_PNG = HERE / "capability-map.png"

STATUS_STYLE = {
    "done":         {"color": "#2a9d8f", "symbol": "circle",        "label": "done"},
    "in-progress":  {"color": "#e9c46a", "symbol": "circle-open",   "label": "in progress"},
    "hypothesized": {"color": "#264653", "symbol": "triangle-up",   "label": "hypothesized"},
    "human-only":   {"color": "#e76f51", "symbol": "square",        "label": "human-only"},
    "blocked":      {"color": "#9b2226", "symbol": "x",             "label": "blocked"},
}


def load_tasks() -> list[dict]:
    with TASKS_PATH.open() as f:
        data = yaml.safe_load(f)
    return data.get("tasks", [])


def build_figure(tasks: list[dict]) -> go.Figure:
    fig = go.Figure()

    # Diagonal reference: where LLM and human capability are equal.
    fig.add_shape(
        type="line", x0=0, y0=0, x1=1, y1=1,
        line=dict(color="lightgray", width=1, dash="dot"),
        layer="below",
    )
    fig.add_annotation(
        x=0.985, y=1.0, text="LLM = human",
        showarrow=False, font=dict(size=10, color="gray"),
        xanchor="right", yanchor="top", textangle=-45,
    )

    # Quadrant guides at 0.5.
    fig.add_shape(type="line", x0=0, y0=0.5, x1=1, y1=0.5,
                  line=dict(color="lightgray", width=1), layer="below")
    fig.add_shape(type="line", x0=0.5, y0=0, x1=0.5, y1=1,
                  line=dict(color="lightgray", width=1), layer="below")

    # Group tasks by status so each status gets one legend entry.
    grouped: dict[str, list[dict]] = {}
    for task in tasks:
        status = task.get("status", "hypothesized")
        grouped.setdefault(status, []).append(task)

    # Preserve a stable legend order.
    legend_order = ["done", "in-progress", "hypothesized", "human-only", "blocked"]
    for status in legend_order:
        items = grouped.get(status)
        if not items:
            continue
        style = STATUS_STYLE.get(status, STATUS_STYLE["hypothesized"])
        xs = [float(t.get("llm_capability", 0.5)) for t in items]
        ys = [float(t.get("human_capability", 0.5)) for t in items]
        labels = [t.get("label", t.get("id", "?")) for t in items]
        hover = [
            "<b>{label}</b><br>"
            "id: {id}<br>"
            "study: {study}<br>"
            "investigation: {inv}<br>"
            "status: {status}<br>"
            "LLM: {x:.2f} &nbsp; human: {y:.2f}"
            "{notes_block}".format(
                label=t.get("label", "?"),
                id=t.get("id", "?"),
                study=t.get("study") or "—",
                inv=t.get("investigation") or "—",
                status=status,
                x=float(t.get("llm_capability", 0.5)),
                y=float(t.get("human_capability", 0.5)),
                notes_block=(
                    "<br>" + str(t["notes"]).replace("\n", "<br>")
                    if t.get("notes") else ""
                ),
            )
            for t in items
        ]
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers+text",
            name=style["label"],
            text=labels,
            textposition="top center",
            textfont=dict(size=10),
            hovertext=hover,
            hoverinfo="text",
            marker=dict(
                color=style["color"],
                symbol=style["symbol"],
                size=14,
                line=dict(color="black", width=0.8),
            ),
        ))

    fig.update_layout(
        title="Capability map — research tasks in this repo",
        xaxis=dict(
            title="LLM capability  (0 = infeasible, 1 = trivial)",
            range=[-0.05, 1.05],
            showgrid=False, zeroline=False,
        ),
        yaxis=dict(
            title="Human capability  (0 = infeasible, 1 = trivial)",
            range=[-0.05, 1.05],
            showgrid=False, zeroline=False,
            scaleanchor="x", scaleratio=1,
        ),
        template="plotly_white",
        width=1100, height=900,
        legend=dict(x=0.01, y=0.01, xanchor="left", yanchor="bottom",
                    bgcolor="rgba(255,255,255,0.9)"),
        margin=dict(l=70, r=30, t=60, b=60),
    )
    return fig


def main() -> None:
    tasks = load_tasks()
    if not tasks:
        print("no tasks found in tasks.yaml", file=sys.stderr)
        sys.exit(1)
    fig = build_figure(tasks)
    fig.write_html(OUT_HTML, include_plotlyjs="cdn", full_html=True)
    print(f"wrote {OUT_HTML.relative_to(HERE.parent)}", file=sys.stderr)
    fig.write_image(OUT_PNG, scale=2)
    print(f"wrote {OUT_PNG.relative_to(HERE.parent)}", file=sys.stderr)


if __name__ == "__main__":
    main()
