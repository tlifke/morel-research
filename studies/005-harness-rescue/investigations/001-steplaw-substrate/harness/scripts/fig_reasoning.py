import csv
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

DATA = Path(__file__).resolve().parents[2] / "data" / "reasoning_runs.csv"
ASSETS = Path(__file__).resolve().parents[2] / "assets"
NEMO, GEM = "nemotron-3-nano:4b", "gemini-3.1-flash-lite"
C_NEMO, C_GEM = "#d1495b", "#1d4ed8"
NEMO_LEVELS = ["off", "low", "medium", "high"]
GEM_LEVELS = ["off", "low", "medium"]


def load():
    rows = list(csv.DictReader(open(DATA)))
    for r in rows:
        r["final_regret"] = max(0.0, float(r["final_regret"]))
        r["experiments"] = int(r["experiments"])
    return rows


def jitter(n, seed=0):
    out, v = [], seed + 1
    for _ in range(n):
        v = (v * 1103515245 + 12345) % 2147483648
        out.append((v / 2147483648 - 0.5) * 0.34)
    return out


def cell(rows, model, lvl):
    return [r for r in rows if r["model"] == model and r["think"] == lvl]


def main():
    rows = load()
    cats = [(NEMO, l) for l in NEMO_LEVELS] + [(GEM, l) for l in GEM_LEVELS]
    xlab = [f"nemotron-4b<br>{l}" for l in NEMO_LEVELS] + [f"gemini<br>{l}" for l in GEM_LEVELS]
    color = [C_NEMO] * len(NEMO_LEVELS) + [C_GEM] * len(GEM_LEVELS)
    NC = len(cats)

    fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45],
                        subplot_titles=("<b>Regret by reasoning level</b>  (each dot = one run · Env A · 15 seeds/cell)",
                                        "<b>Experiments run & stall rate</b>"),
                        horizontal_spacing=0.1)

    for i, (model, lvl) in enumerate(cats):
        grp = cell(rows, model, lvl)
        jx = jitter(len(grp), seed=i)
        fig.add_trace(go.Scatter(
            x=[i + 1 + j for j in jx], y=[r["final_regret"] for r in grp], mode="markers",
            marker=dict(size=9, color=color[i], line=dict(width=1, color="white"), opacity=0.8),
            showlegend=False, hovertemplate=f"{model.split(':')[0]} {lvl}<br>regret=%{{y:.4f}}<extra></extra>",
        ), row=1, col=1)
        med = sorted(r["final_regret"] for r in grp)[len(grp) // 2]
        fig.add_trace(go.Scatter(x=[i + 0.7, i + 1.3], y=[med, med], mode="lines",
                                 line=dict(color="#111827", width=2), showlegend=False,
                                 hovertemplate=f"median={med:.4f}<extra></extra>"), row=1, col=1)
    fig.update_xaxes(tickvals=list(range(1, NC + 1)), ticktext=xlab, range=[0.4, NC + 0.6], row=1, col=1)
    fig.update_yaxes(title_text="simple regret (loss − optimum)", rangemode="tozero", row=1, col=1)

    # panel 2: mean experiments bar + stall% text
    means, stalls, txt = [], [], []
    for model, lvl in cats:
        grp = cell(rows, model, lvl)
        me = sum(r["experiments"] for r in grp) / len(grp)
        sr = 100 * sum(1 for r in grp if r["outcome"] == "stalled") / len(grp)
        means.append(me); stalls.append(sr); txt.append(f"{me:.0f} exp<br>{sr:.0f}% stall")
    fig.add_trace(go.Bar(x=list(range(1, NC + 1)), y=means, marker_color=color, showlegend=False,
                         text=txt, textposition="outside", textfont=dict(size=10),
                         hovertemplate="mean experiments=%{y:.1f}<extra></extra>"), row=1, col=2)
    fig.update_xaxes(tickvals=list(range(1, NC + 1)), ticktext=xlab, range=[0.4, NC + 0.6], row=1, col=2)
    fig.update_yaxes(title_text="mean experiments / run", range=[0, 42], row=1, col=2)

    fig.update_layout(
        template="plotly_white", width=1360, height=540,
        title=dict(text="<b>Reasoning level is load-bearing — and the weak model is far more sensitive</b><br>"
                        "<sub>study 005 inv 001 · Env A (215M/100B) · 105 runs · 15 seeds/cell · nemotron reasoning_effort none/low/medium/high, gemini thinkingLevel off/low/medium</sub>",
                   x=0.5, font=dict(size=16)),
        margin=dict(t=95, b=70, l=70, r=30),
        font=dict(family="-apple-system, Segoe UI, sans-serif", size=13),
    )
    ASSETS.mkdir(exist_ok=True)
    fig.write_html(ASSETS / "fig_reasoning.html", include_plotlyjs="cdn")
    fig.write_image(ASSETS / "fig_reasoning.png", scale=2)
    print("wrote", ASSETS / "fig_reasoning.png")


if __name__ == "__main__":
    main()
