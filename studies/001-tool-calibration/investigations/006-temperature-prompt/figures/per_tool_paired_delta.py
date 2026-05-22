"""Per-tool paired-difference figure (12B − 4B) — supplemental.

For each tool, shows the paired bootstrap delta in precision_trivial
(left subplot) and in lift_pp (right subplot), with 95% CIs. Same Opus
predictions are scored against both models, so the bootstrap is paired
over records.

Interpretation:
- Δprecision = how much higher 12B's precision is than 4B's on the
  records Opus called trivial. Large positive Δ + small Δlift = the
  baseline caught up to Opus, not Opus adding new signal.
- Δlift = how much more *signal-over-baseline* 12B captures than 4B.
  Positive = scale closes the calibration gap; near zero = the detector
  is model-invariant on this tool.

Loads the bootstrap output from
`scripts/prediction_agreement_per_tool.py`.

Run from repo root:
  uv run studies/001-tool-calibration/investigations/006-temperature-prompt/figures/per_tool_paired_delta.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

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


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    per_tool = data["per_tool"]

    rows = []
    for tool, d in per_tool.items():
        diff = d["paired_diff_12b_minus_4b"]
        rows.append({
            "tool": tool,
            "n": d["n"],
            "d_prec": diff["precision"]["point"] or 0.0,
            "d_prec_lo": diff["precision"]["ci"]["lo"] or 0.0,
            "d_prec_hi": diff["precision"]["ci"]["hi"] or 0.0,
            "d_prec_p": diff["precision"]["p_two_sided"],
            "d_lift_pp": (diff["lift"]["point"] or 0.0) * 100,
            "d_lift_lo_pp": (diff["lift"]["ci"]["lo"] or 0.0) * 100,
            "d_lift_hi_pp": (diff["lift"]["ci"]["hi"] or 0.0) * 100,
            "d_lift_p": diff["lift"]["p_two_sided"],
        })

    rows.sort(key=lambda r: r["d_prec"])

    y_labels = [TOOL_LABEL[r["tool"]] for r in rows]
    color = MOREL_COLORS["terracotta"]

    fig = make_subplots(
        rows=1, cols=2,
        shared_yaxes=True,
        subplot_titles=("Δ precision_trivial (12B − 4B)", "Δ lift over baseline (12B − 4B, pp)"),
        horizontal_spacing=0.10,
    )

    d_prec = [r["d_prec"] for r in rows]
    d_prec_plus = [r["d_prec_hi"] - r["d_prec"] for r in rows]
    d_prec_minus = [r["d_prec"] - r["d_prec_lo"] for r in rows]
    hover_prec = [
        f"{TOOL_LABEL[r['tool']]} (n={r['n']})<br>"
        f"Δ precision = {r['d_prec']:+.3f} [{r['d_prec_lo']:+.3f}, {r['d_prec_hi']:+.3f}]<br>"
        f"p (two-sided) = {r['d_prec_p']:.3f}"
        for r in rows
    ]
    fig.add_trace(
        go.Bar(
            x=d_prec, y=y_labels, orientation="h",
            marker_color=color, name="Δ precision",
            error_x=dict(
                type="data",
                array=d_prec_plus, arrayminus=d_prec_minus,
                color=MOREL_COLORS["muted_text"], thickness=1.2, width=4,
            ),
            hovertext=hover_prec, hoverinfo="text",
            showlegend=False,
        ),
        row=1, col=1,
    )

    d_lift = [r["d_lift_pp"] for r in rows]
    d_lift_plus = [r["d_lift_hi_pp"] - r["d_lift_pp"] for r in rows]
    d_lift_minus = [r["d_lift_pp"] - r["d_lift_lo_pp"] for r in rows]
    hover_lift = [
        f"{TOOL_LABEL[r['tool']]} (n={r['n']})<br>"
        f"Δ lift = {r['d_lift_pp']:+.1f} pp [{r['d_lift_lo_pp']:+.1f}, {r['d_lift_hi_pp']:+.1f}]<br>"
        f"p (two-sided) = {r['d_lift_p']:.3f}"
        for r in rows
    ]
    fig.add_trace(
        go.Bar(
            x=d_lift, y=y_labels, orientation="h",
            marker_color=MOREL_COLORS["forest_green"], name="Δ lift",
            error_x=dict(
                type="data",
                array=d_lift_plus, arrayminus=d_lift_minus,
                color=MOREL_COLORS["muted_text"], thickness=1.2, width=4,
            ),
            hovertext=hover_lift, hoverinfo="text",
            showlegend=False,
        ),
        row=1, col=2,
    )

    for col in (1, 2):
        fig.add_shape(
            type="line", x0=0, x1=0, y0=-0.5, y1=len(y_labels) - 0.5,
            line=dict(color=MOREL_COLORS["muted_text"], width=1),
            row=1, col=col,
        )

    fig.update_xaxes(title_text="Δ precision (12B − 4B)", row=1, col=1)
    fig.update_xaxes(title_text="Δ lift (pp)", ticksuffix=" pp", row=1, col=2)
    fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        height=470,
        width=1000,
        margin=dict(l=170, r=40, t=110, b=110),
    )

    apply_morel_template(
        fig,
        title="Scale effect by tool (paired 12B − 4B)",
        subtitle="Tools with large Δ precision but small Δ lift gained baseline, not detector signal.",
        attribution=f"studies/001 / inv 006 · corpus={CORPUS} · n_boot=10,000 · paired over records",
    )

    for ext in ("png", "html", "pdf"):
        out = OUT_DIR / f"per_tool_paired_delta.{ext}"
        if ext == "html":
            fig.write_html(out)
        else:
            fig.write_image(out, scale=2)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
