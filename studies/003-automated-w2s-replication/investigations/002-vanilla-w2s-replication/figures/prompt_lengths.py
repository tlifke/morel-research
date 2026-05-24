"""Prompt-length distribution per (dataset, split), with truncation thresholds.

Renders a 1x3 small-multiples histogram showing how the train_unlabel and test
splits distribute prompt token lengths for math, chat, and code. Vertical
reference lines mark our max_ctx=2048 ceiling and the upstream default 8192.
Each panel reports the fraction of samples that exceed 2048.
"""
import json
import sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import (
    MOREL_COLORS,
    MOREL_CYCLE,
    apply_morel_template,
)


HERE = Path(__file__).parent
DATA = HERE / "data" / "prompt_lengths.json"
OUT = HERE / "out"

DATASETS = ["math", "chat", "code"]
SPLITS = ["train_unlabel", "test"]
OUR_MAX_CTX = 2048
PAPER_MAX_CTX = 8192


def frac_above(values: list[int], threshold: int) -> float:
    if not values:
        return 0.0
    return sum(1 for v in values if v > threshold) / len(values)


def main() -> None:
    data = json.loads(DATA.read_text())["splits"]
    OUT.mkdir(exist_ok=True)

    fig = make_subplots(
        rows=1,
        cols=3,
        subplot_titles=[d for d in DATASETS],
        shared_yaxes=False,
        horizontal_spacing=0.07,
    )

    split_colors = {
        "train_unlabel": MOREL_COLORS["terracotta"],
        "test": MOREL_COLORS["forest_green"],
    }

    for col_idx, ds in enumerate(DATASETS, start=1):
        all_vals = []
        for split in SPLITS:
            vals = data.get(ds, {}).get(split, [])
            all_vals.extend(vals)
            frac_trunc = frac_above(vals, OUR_MAX_CTX) * 100
            fig.add_trace(
                go.Histogram(
                    x=vals,
                    name=split,
                    nbinsx=60,
                    marker=dict(color=split_colors[split], line=dict(width=0)),
                    opacity=0.65,
                    legendgroup=split,
                    showlegend=col_idx == 1,
                    hovertemplate=f"{ds}/{split}<br>tokens: %{{x}}<br>count: %{{y}}<extra></extra>",
                ),
                row=1,
                col=col_idx,
            )

        max_val = max(all_vals) if all_vals else 1
        x_upper = min(max(max_val, OUR_MAX_CTX) * 1.05, 6500)
        fig.update_xaxes(range=[0, x_upper], row=1, col=col_idx)

        fig.add_vline(
            x=OUR_MAX_CTX,
            line=dict(color=MOREL_COLORS["error_red"], dash="dash", width=1.5),
            row=1,
            col=col_idx,
        )
        if PAPER_MAX_CTX <= x_upper:
            fig.add_vline(
                x=PAPER_MAX_CTX,
                line=dict(color=MOREL_COLORS["muted_text"], dash="dot", width=1.2),
                row=1,
                col=col_idx,
            )

        trunc_unlabel = frac_above(data[ds]["train_unlabel"], OUR_MAX_CTX) * 100
        trunc_test = frac_above(data[ds]["test"], OUR_MAX_CTX) * 100
        max_unlabel = max(data[ds]["train_unlabel"])
        max_test = max(data[ds]["test"])

        annotation_text = (
            f"<b>truncated at 2048</b><br>"
            f"train: {trunc_unlabel:.1f}% (max {max_unlabel})<br>"
            f"test: {trunc_test:.1f}% (max {max_test})"
        )
        fig.add_annotation(
            xref=f"x{col_idx} domain" if col_idx > 1 else "x domain",
            yref=f"y{col_idx} domain" if col_idx > 1 else "y domain",
            x=0.98,
            y=0.95,
            xanchor="right",
            yanchor="top",
            text=annotation_text,
            showarrow=False,
            font=dict(size=11, color=MOREL_COLORS["muted_text"]),
            bgcolor="rgba(255,255,255,0.7)",
            bordercolor=MOREL_COLORS["cream_dark"],
            borderwidth=1,
            borderpad=4,
            align="right",
        )

    fig.update_layout(
        barmode="overlay",
        height=400,
        width=1100,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.18,
            xanchor="center",
            x=0.5,
        ),
    )
    fig.update_xaxes(title_text="prompt tokens (Qwen3-4B-Base tokenizer)", row=1, col=2)
    fig.update_yaxes(title_text="count", row=1, col=1)

    apply_morel_template(
        fig,
        title="Prompt length distributions vs max_ctx",
        subtitle="dashed red = our max_ctx=2048 · dotted gray = paper max_ctx=8192",
        attribution="studies/003-automated-w2s-replication / inv 002",
    )

    fig.write_html(OUT / "prompt_lengths.html", include_plotlyjs="cdn")
    fig.write_image(OUT / "prompt_lengths.png", width=1100, height=400, scale=2, engine="kaleido")
    print(f"wrote {OUT/'prompt_lengths.html'} and {OUT/'prompt_lengths.png'}")


if __name__ == "__main__":
    main()
