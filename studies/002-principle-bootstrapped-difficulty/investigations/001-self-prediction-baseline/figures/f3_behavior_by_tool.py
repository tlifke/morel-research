"""F3 (Q3 behavior-prediction) per-tool figure.

Two-panel:
  Left  — Q3 accuracy per tool against A4 modal empirical behavior, with
          95% bootstrap CIs. Reference line at 0.5 (chance for binary).
  Right — Stacked counts of (correct, under-predicted tool use,
          over-predicted tool use) per tool. Shows the directional
          structure of errors.

Loads analyze.py's output JSON. Run from repo root:
  uv run studies/002-principle-bootstrapped-difficulty/investigations/001-self-prediction-baseline/figures/f3_behavior_by_tool.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = Path(__file__).resolve().parent
INV_ROOT = HERE.parent
REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402

MODEL = "gemma3:4b-it-qat"
MODEL_DISPLAY = "Gemma 3 4B IT"
DATA_PATHS = sorted((INV_ROOT / "results-analysis").glob("self_prediction_*.json"))
DATA_PATH = DATA_PATHS[-1]
OUT_DIR = HERE / "out"
OUT_DIR.mkdir(exist_ok=True)

TOOL_LABEL = {
    "python_execute": "python_execute",
    "general_knowledge_lookup": "gen_knowledge_lookup",
    "user_knowledge_lookup": "user_knowledge_lookup",
    "calculator": "calculator",
    "unit_convert": "unit_convert",
    "datetime_now": "datetime_now",
}


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    f3 = data["facets"]["F3_behavior"]
    per_tool = f3["per_tool"]
    direction = f3.get("direction_per_tool", {})

    sort_key = sorted(per_tool, key=lambda t: per_tool[t]["accuracy"], reverse=True)
    y_labels = [TOOL_LABEL[t] for t in sort_key]

    fig = make_subplots(
        rows=1, cols=2,
        shared_yaxes=True,
        column_widths=[0.55, 0.45],
        subplot_titles=("Q3 behavior-prediction accuracy", "Error direction (counts)"),
        horizontal_spacing=0.08,
    )

    # Panel 1: accuracy with CIs
    accs = [per_tool[t]["accuracy"] for t in sort_key]
    errs_plus = [per_tool[t]["ci"]["hi"] - per_tool[t]["accuracy"] for t in sort_key]
    errs_minus = [per_tool[t]["accuracy"] - per_tool[t]["ci"]["lo"] for t in sort_key]
    hovers = [
        f"{TOOL_LABEL[t]}<br>"
        f"n = {per_tool[t]['n']}<br>"
        f"accuracy = {per_tool[t]['accuracy']:.3f} "
        f"[{per_tool[t]['ci']['lo']:.3f}, {per_tool[t]['ci']['hi']:.3f}]"
        for t in sort_key
    ]
    fig.add_trace(go.Bar(
        x=accs, y=y_labels, orientation="h",
        marker_color=MOREL_COLORS["terracotta"],
        error_x=dict(
            type="data",
            array=errs_plus, arrayminus=errs_minus,
            color=MOREL_COLORS["muted_text"], thickness=1.2, width=4,
        ),
        hovertext=hovers, hoverinfo="text",
        name="accuracy", showlegend=False,
    ), row=1, col=1)
    fig.add_shape(
        type="line", x0=0.5, x1=0.5, y0=-0.5, y1=len(sort_key) - 0.5,
        line=dict(color=MOREL_COLORS["muted_text"], width=1, dash="dash"),
        row=1, col=1,
    )
    fig.add_annotation(
        x=0.5, y=-0.5, yshift=-30,
        text="<i>chance (0.5)</i>", showarrow=False,
        font=dict(size=10, color=MOREL_COLORS["muted_text"]),
        xanchor="center", row=1, col=1,
    )

    # Panel 2: stacked error direction
    corrects = [direction.get(t, {}).get("correct", 0) for t in sort_key]
    unders = [direction.get(t, {}).get("under_predicted_tool_use", 0) for t in sort_key]
    overs = [direction.get(t, {}).get("over_predicted_tool_use", 0) for t in sort_key]
    fig.add_trace(go.Bar(
        x=corrects, y=y_labels, orientation="h",
        marker_color=MOREL_COLORS["forest_green"],
        name="correct",
        hovertext=[f"correct: {c}" for c in corrects], hoverinfo="text",
    ), row=1, col=2)
    fig.add_trace(go.Bar(
        x=unders, y=y_labels, orientation="h",
        marker_color=MOREL_COLORS["terracotta"],
        name="under-predicted tool use",
        hovertext=[f"under-predicted: {u}" for u in unders], hoverinfo="text",
    ), row=1, col=2)
    fig.add_trace(go.Bar(
        x=overs, y=y_labels, orientation="h",
        marker_color=MOREL_COLORS["error_red"],
        name="over-predicted tool use",
        hovertext=[f"over-predicted: {o}" for o in overs], hoverinfo="text",
    ), row=1, col=2)

    fig.update_xaxes(range=[0, 1.05], title_text="Accuracy", row=1, col=1)
    fig.update_xaxes(title_text="Record count", row=1, col=2)
    fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        barmode="stack",
        height=460,
        width=1080,
        margin=dict(l=170, r=40, t=130, b=110),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="center", x=0.5),
    )

    overall_dir = f3.get("direction_overall", {})
    pct_under = 100 * overall_dir.get("under_predicted_tool_use", 0) / max(1, overall_dir.get("under_predicted_tool_use", 0) + overall_dir.get("over_predicted_tool_use", 0))

    apply_morel_template(
        fig,
        title=f"Self-prediction of tool-call behavior — {MODEL_DISPLAY}",
        subtitle=f"Overall accuracy {f3['overall']['accuracy']:.3f} "
                 f"[{f3['overall']['ci']['lo']:.3f}, {f3['overall']['ci']['hi']:.3f}], "
                 f"n={f3['overall']['n']}. {pct_under:.0f}% of errors are under-predictions of own tool use.",
        attribution=f"studies/002 / inv 001 · model={MODEL} · n=3 self-predictions/record · A4 empirical n=10",
    )

    for ext in ("png", "html", "pdf"):
        out = OUT_DIR / f"f3_behavior_by_tool.{ext}"
        if ext == "html":
            fig.write_html(out)
        else:
            fig.write_image(out, scale=2)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
