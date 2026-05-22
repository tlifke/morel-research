"""Per-tool side-by-side bars: Opus's 'trivial' precision vs. baseline.

For each (tool, model), shows two adjacent horizontal bars:
  - Opus's precision when labeling records 'trivial' (terracotta).
  - The marginal trivial rate for that tool — what a random labeler
    would achieve in expectation (cream_dark, muted).

Where the filled bar extends beyond the baseline bar, Opus is adding
signal; where they match, Opus is at chance; where the filled bar is
shorter, Opus is anti-informative. Error bars on precision are 95%
percentile bootstrap CIs.

Bars whose lift CI does not clear zero are drawn with reduced opacity —
those (tool, model) cells are not distinguishable from baseline at
the data we have.

Run from repo root:
  uv run studies/001-tool-calibration/investigations/006-temperature-prompt/figures/per_tool_precision_vs_baseline_bars.py
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

MODELS = [
    ("gemma3:4b-it-qat", "ci_4b", "Gemma 3 4B IT"),
    ("gemma3:12b-it-qat", "ci_12b", "Gemma 3 12B IT"),
]


def lift_clears_zero(ci: dict) -> bool:
    lo, hi = ci["lo"], ci["hi"]
    if lo is None or hi is None:
        return False
    return (lo > 0) or (hi < 0)


def main() -> None:
    data = json.loads(DATA_PATH.read_text())
    per_tool = data["per_tool"]

    sort_key = sorted(
        per_tool,
        key=lambda t: max(
            per_tool[t]["point"]["gemma3:4b-it-qat"]["lift"],
            per_tool[t]["point"]["gemma3:12b-it-qat"]["lift"],
        ),
        reverse=True,
    )
    y_labels = [TOOL_LABEL[t] for t in sort_key]

    fig = make_subplots(
        rows=1, cols=2,
        shared_yaxes=True,
        subplot_titles=("Gemma 3 4B IT", "Gemma 3 12B IT"),
        horizontal_spacing=0.06,
    )

    base_color = MOREL_COLORS["cream_dark"]
    sig_color = MOREL_COLORS["terracotta"]
    nonsig_color = MOREL_COLORS["terracotta"]

    for col, (model, cikey, _label) in enumerate(MODELS, start=1):
        baselines = []
        precisions = []
        err_plus = []
        err_minus = []
        opacities = []
        hovers = []
        for tool in sort_key:
            d = per_tool[tool]
            p = d["point"][model]
            prec_ci = d[cikey]["precision"]
            lift_ci = d[cikey]["lift"]
            sig = lift_clears_zero(lift_ci)
            baselines.append(p["baseline"])
            precisions.append(p["precision"])
            err_plus.append(prec_ci["hi"] - p["precision"])
            err_minus.append(p["precision"] - prec_ci["lo"])
            opacities.append(1.0 if sig else 0.35)
            hovers.append(
                f"{tool}<br>"
                f"precision = {p['precision']:.3f} [{prec_ci['lo']:.3f}, {prec_ci['hi']:.3f}]<br>"
                f"baseline = {p['baseline']:.3f}<br>"
                f"lift = {(p['precision'] - p['baseline']) * 100:+.1f} pp "
                f"[{lift_ci['lo']*100:+.1f}, {lift_ci['hi']*100:+.1f}]<br>"
                f"n = {d['n']} (Opus called {p['pred_trivial_n']} trivial)<br>"
                f"<i>{'CI clears zero' if sig else 'CI overlaps zero — not distinguishable from baseline'}</i>"
            )

        fig.add_trace(
            go.Bar(
                x=baselines, y=y_labels, orientation="h",
                marker_color=base_color, name="Baseline (random-label rate)",
                hovertext=[f"baseline = {b:.3f}" for b in baselines],
                hoverinfo="text",
                showlegend=(col == 1),
                legendgroup="baseline",
            ),
            row=1, col=col,
        )
        fig.add_trace(
            go.Bar(
                x=precisions, y=y_labels, orientation="h",
                marker=dict(
                    color=[sig_color if o == 1.0 else nonsig_color for o in opacities],
                    opacity=opacities,
                ),
                name="Opus precision",
                error_x=dict(
                    type="data",
                    array=err_plus, arrayminus=err_minus,
                    color=MOREL_COLORS["muted_text"], thickness=1.2, width=4,
                ),
                hovertext=hovers, hoverinfo="text",
                showlegend=(col == 1),
                legendgroup="precision",
            ),
            row=1, col=col,
        )

    fig.update_xaxes(range=[0, 1.05], title_text="Rate (0 — 1)", row=1, col=1)
    fig.update_xaxes(range=[0, 1.05], title_text="Rate (0 — 1)", row=1, col=2)
    fig.update_yaxes(autorange="reversed")

    fig.update_layout(
        barmode="group",
        bargap=0.25,
        bargroupgap=0.12,
        height=520,
        width=1080,
        margin=dict(l=180, r=40, t=150, b=110),
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="center", x=0.5),
    )

    apply_morel_template(
        fig,
        title="Opus 'trivial' precision vs. baseline, by tool",
        subtitle="Filled bar = Opus's precision when labeling 'trivial'. Light bar = marginal trivial rate (random-label expectation). Faded fill = lift CI overlaps zero.",
        attribution=f"studies/001 / inv 006 · corpus={CORPUS} · n=10 trials/record · n_boot=10,000",
    )

    for ext in ("png", "html", "pdf"):
        out = OUT_DIR / f"per_tool_precision_vs_baseline_bars.{ext}"
        if ext == "html":
            fig.write_html(out)
        else:
            fig.write_image(out, scale=2)
        print(f"wrote {out}")


if __name__ == "__main__":
    main()
