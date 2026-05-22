"""Per-tool precision-vs-baseline scatter.

Each (tool, model) is one dot. y=x is the no-information diagonal: dots
above the line = detector adds signal; dots on the line = at baseline;
below = anti-informative. Both 95% percentile bootstrap CIs shown as
error bars (precision in y, no baseline CI plotted — baseline is the
empirical fraction, treated as fixed for this view).

Loads the bootstrap output produced by
`scripts/prediction_agreement_per_tool.py`.

Run from repo root:
  uv run studies/001-tool-calibration/investigations/006-temperature-prompt/figures/per_tool_precision_vs_baseline.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
INVESTIGATION_ROOT = HERE.parent
REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402

DATE = "2026-05-12"
CORPUS = "a3_bulk"
DATA_PATH = INVESTIGATION_ROOT / "results-analysis" / f"prediction_agreement_per_tool_{CORPUS}_{DATE}.json"
OUT_DIR = HERE / "a3_bulk"
OUT_DIR.mkdir(exist_ok=True)

TOOL_SHORT = {
    "python_execute": "python",
    "general_knowledge_lookup": "gkl",
    "user_knowledge_lookup": "ukl",
    "calculator": "calc",
    "unit_convert": "unit",
    "datetime_now": "datetime",
}

MODEL_DISPLAY = {
    "gemma3:4b-it-qat": "Gemma 3 4B IT",
    "gemma3:12b-it-qat": "Gemma 3 12B IT",
}
MODEL_COLOR = {
    "gemma3:4b-it-qat": MOREL_COLORS["terracotta"],
    "gemma3:12b-it-qat": MOREL_COLORS["forest_green"],
}
MODEL_SYMBOL = {
    "gemma3:4b-it-qat": "circle",
    "gemma3:12b-it-qat": "square",
}


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    per_tool = data["per_tool"]

    fig = go.Figure()

    fig.add_shape(
        type="line", x0=0, y0=0, x1=1, y1=1,
        line=dict(color=MOREL_COLORS["muted_text"], width=1, dash="dash"),
        layer="below",
    )
    fig.add_annotation(
        x=0.95, y=0.95, xanchor="right", yanchor="bottom",
        text="<i>y = x  (no information)</i>", showarrow=False,
        font=dict(size=10, color=MOREL_COLORS["muted_text"]),
        textangle=-45,
    )

    for m, mkey in [("gemma3:4b-it-qat", "ci_4b"), ("gemma3:12b-it-qat", "ci_12b")]:
        xs, ys, errs_plus, errs_minus, labels, hover = [], [], [], [], [], []
        for tool, d in per_tool.items():
            p = d["point"][m]
            ci = d[mkey]["precision"]
            xs.append(p["baseline"])
            ys.append(p["precision"])
            errs_plus.append(ci["hi"] - p["precision"])
            errs_minus.append(p["precision"] - ci["lo"])
            labels.append(TOOL_SHORT[tool])
            hover.append(
                f"{tool} ({MODEL_DISPLAY[m]})<br>"
                f"baseline = {p['baseline']:.3f}<br>"
                f"precision = {p['precision']:.3f} [{ci['lo']:.3f}, {ci['hi']:.3f}]<br>"
                f"lift = {(p['precision'] - p['baseline']) * 100:+.1f} pp<br>"
                f"n = {d['n']} (Opus called {p['pred_trivial_n']} trivial)"
            )
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers+text",
            text=labels,
            textposition="top right",
            textfont=dict(size=10, color=MOREL_COLORS["muted_text"]),
            name=MODEL_DISPLAY[m],
            marker=dict(
                color=MODEL_COLOR[m],
                symbol=MODEL_SYMBOL[m],
                size=11,
                line=dict(color="white", width=1.2),
            ),
            error_y=dict(
                type="data",
                array=errs_plus,
                arrayminus=errs_minus,
                color=MOREL_COLORS["muted_text"],
                thickness=1.0,
                width=4,
            ),
            hovertext=hover,
            hoverinfo="text",
        ))

    fig.update_layout(
        xaxis=dict(title="Baseline (empirical trivial rate)", range=[0, 1], zeroline=False),
        yaxis=dict(title="Precision_trivial", range=[0, 1.05], zeroline=False, scaleanchor="x", scaleratio=1),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        height=620,
        width=720,
        margin=dict(l=80, r=40, t=110, b=80),
    )

    apply_morel_template(
        fig,
        title="Precision vs. baseline by tool",
        subtitle="Each point is one (tool, model). Above the diagonal = detector adds signal.",
        attribution=f"studies/001 / inv 006 · corpus={CORPUS} · n=10 trials/record",
    )

    for ext in ("png", "html", "pdf"):
        out = OUT_DIR / f"per_tool_precision_vs_baseline.{ext}"
        if ext == "html":
            fig.write_html(out)
        else:
            fig.write_image(out, scale=2)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
