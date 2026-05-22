"""Per-tool lift bar chart — primary figure for the trivial-detector story.

Diverging horizontal bars of (precision - baseline) per (tool, model), with
95% percentile bootstrap CIs. Vertical zero line is the no-information
reference: bars right = detector adds signal; bars left = anti-informative;
straddling zero = at baseline.

Loads the bootstrap output produced by
`scripts/prediction_agreement_per_tool.py`.

Run from repo root:
  uv run studies/001-tool-calibration/investigations/006-temperature-prompt/figures/per_tool_lift_bars.py
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

TOOL_LABEL = {
    "python_execute": "python_execute",
    "general_knowledge_lookup": "gen_knowledge_lookup",
    "user_knowledge_lookup": "user_knowledge_lookup",
    "calculator": "calculator",
    "unit_convert": "unit_convert",
    "datetime_now": "datetime_now",
}

MODEL_DISPLAY = {
    "gemma3:4b-it-qat": "Gemma 3 4B IT",
    "gemma3:12b-it-qat": "Gemma 3 12B IT",
}
MODEL_COLOR = {
    "gemma3:4b-it-qat": MOREL_COLORS["terracotta"],
    "gemma3:12b-it-qat": MOREL_COLORS["forest_green"],
}


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    per_tool = data["per_tool"]

    rows = []
    for tool, d in per_tool.items():
        for m, mkey in [("gemma3:4b-it-qat", "ci_4b"), ("gemma3:12b-it-qat", "ci_12b")]:
            point = d["point"][m]
            ci = d[mkey]["lift"]
            rows.append({
                "tool": tool,
                "model": m,
                "lift_pp": point["lift"] * 100,
                "lift_lo_pp": ci["lo"] * 100,
                "lift_hi_pp": ci["hi"] * 100,
                "n": d["n"],
                "precision": point["precision"],
                "baseline": point["baseline"],
                "n_pred_T": point["pred_trivial_n"],
            })

    by_tool: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_tool.setdefault(r["tool"], {})[r["model"]] = r
    sort_key = sorted(
        by_tool,
        key=lambda t: max(by_tool[t]["gemma3:4b-it-qat"]["lift_pp"], by_tool[t]["gemma3:12b-it-qat"]["lift_pp"]),
    )
    y_labels = [TOOL_LABEL[t] for t in sort_key]

    fig = go.Figure()
    for m in ["gemma3:12b-it-qat", "gemma3:4b-it-qat"]:
        lifts = [by_tool[t][m]["lift_pp"] for t in sort_key]
        errs_plus = [by_tool[t][m]["lift_hi_pp"] - by_tool[t][m]["lift_pp"] for t in sort_key]
        errs_minus = [by_tool[t][m]["lift_pp"] - by_tool[t][m]["lift_lo_pp"] for t in sort_key]
        hover = [
            f"{TOOL_LABEL[t]} ({MODEL_DISPLAY[m]})<br>"
            f"lift = {by_tool[t][m]['lift_pp']:+.1f} pp "
            f"[{by_tool[t][m]['lift_lo_pp']:+.1f}, {by_tool[t][m]['lift_hi_pp']:+.1f}]<br>"
            f"precision = {by_tool[t][m]['precision']:.3f}, "
            f"baseline = {by_tool[t][m]['baseline']:.3f}<br>"
            f"n = {by_tool[t][m]['n']} (Opus called {by_tool[t][m]['n_pred_T']} trivial)"
            for t in sort_key
        ]
        fig.add_trace(go.Bar(
            x=lifts,
            y=y_labels,
            orientation="h",
            name=MODEL_DISPLAY[m],
            marker_color=MODEL_COLOR[m],
            error_x=dict(
                type="data",
                array=errs_plus,
                arrayminus=errs_minus,
                color=MOREL_COLORS["muted_text"],
                thickness=1.2,
                width=4,
            ),
            hovertext=hover,
            hoverinfo="text",
        ))

    fig.add_shape(
        type="line", x0=0, x1=0, y0=-0.5, y1=len(y_labels) - 0.5,
        line=dict(color=MOREL_COLORS["muted_text"], width=1, dash="solid"),
        layer="below",
    )

    fig.update_layout(
        barmode="group",
        bargap=0.30,
        bargroupgap=0.10,
        xaxis=dict(
            title="Lift over baseline (percentage points)",
            zeroline=False,
            ticksuffix=" pp",
        ),
        yaxis=dict(title="", autorange="reversed"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1.0),
        height=460,
        width=820,
        margin=dict(l=160, r=40, t=110, b=110),
    )

    apply_morel_template(
        fig,
        title="Opus trivial-detector lift by tool",
        subtitle="Precision − empirical trivial baseline; 95% bootstrap CIs. Right of zero = detector adds signal.",
        attribution=f"studies/001 / inv 006 · corpus={CORPUS} · n=10 trials/record",
    )

    for ext in ("png", "html", "pdf"):
        out = OUT_DIR / f"per_tool_lift_bars.{ext}"
        if ext == "html":
            fig.write_html(out)
        else:
            fig.write_image(out, scale=2)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
