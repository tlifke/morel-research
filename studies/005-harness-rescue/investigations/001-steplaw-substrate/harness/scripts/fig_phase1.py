import csv
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

DATA = Path(__file__).resolve().parents[2] / "data" / "phase1_runs.csv"
ASSETS = Path(__file__).resolve().parents[2] / "assets"

ARMS = [("off", "False"), ("off", "True"), ("self", "False"), ("self", "True"), ("fresh", "False"), ("fresh", "True")]
LBL = {("off", "False"): "A0<br>minimal", ("off", "True"): "A1<br>+C4", ("self", "False"): "A2<br>+C1self",
       ("self", "True"): "A3<br>+C1self+C4", ("fresh", "False"): "A4<br>+C1fresh", ("fresh", "True"): "A5<br>+C1fresh+C4"}
FK_COLOR = {"clean": "#16a34a", "nudged": "#2563eb", "forced": "#7c3aed"}
C1_COLOR = {"off": "#9ca3af", "self": "#ea580c", "fresh": "#0d9488"}


def jitter(n, seed=0):
    out, v = [], seed + 1
    for _ in range(n):
        v = (v * 1103515245 + 12345) % 2147483648
        out.append((v / 2147483648 - 0.5) * 0.34)
    return out


def main():
    rows = list(csv.DictReader(open(DATA)))
    for r in rows:
        r["final_regret"] = max(0.0, float(r["final_regret"]))
    by = defaultdict(list)
    for r in rows:
        by[(r["reflect"], r["actuate"])].append(r)

    fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5],
                        subplot_titles=("<b>Outcome by arm</b>  (C4 eliminates the stall)",
                                        "<b>Regret by arm</b>  (C1-fresh tightens the tail)"),
                        horizontal_spacing=0.1)

    xs = list(range(1, 7))
    # panel 1: stacked outcome composition
    for kind in ["clean", "nudged", "forced"]:
        ys = [sum(1 for r in by[a] if r["outcome"] == "finished" and r["finish_kind"] == kind) for a in ARMS]
        fig.add_trace(go.Bar(x=xs, y=ys, name=f"finished: {kind}", marker_color=FK_COLOR[kind]), row=1, col=1)
    ys = [sum(1 for r in by[a] if r["outcome"] == "stalled") for a in ARMS]
    fig.add_trace(go.Bar(x=xs, y=ys, name="stalled", marker_color="#dc2626"), row=1, col=1)
    fig.update_xaxes(tickvals=xs, ticktext=[LBL[a] for a in ARMS], row=1, col=1)
    fig.update_yaxes(title_text="runs (of 20)", range=[0, 21], row=1, col=1)

    # panel 2: regret strip (log y to show the saturated-median + tail)
    for i, a in enumerate(ARMS):
        grp = by[a]
        jx = jitter(len(grp), seed=i)
        yv = [max(r["final_regret"], 0.00005) for r in grp]  # floor for log
        fig.add_trace(go.Scatter(x=[i + 1 + j for j in jx], y=yv, mode="markers",
                                 marker=dict(size=8, color=C1_COLOR[a[0]], line=dict(width=1, color="white"), opacity=0.8),
                                 showlegend=False, hovertemplate=f"{a}<br>regret=%{{y:.4f}}<extra></extra>"), row=1, col=2)
        mx = max(r["final_regret"] for r in grp)
        fig.add_trace(go.Scatter(x=[i + 0.72, i + 1.28], y=[mx, mx], mode="lines",
                                 line=dict(color="#111827", width=1.5, dash="dot"), showlegend=False,
                                 hovertemplate=f"max={mx:.4f}<extra></extra>"), row=1, col=2)
    fig.update_xaxes(tickvals=xs, ticktext=[LBL[a] for a in ARMS], row=1, col=2)
    fig.update_yaxes(title_text="simple regret (log)", type="log", row=1, col=2)

    fig.update_layout(
        barmode="stack", template="plotly_white", width=1340, height=560,
        title=dict(text="<b>Phase 1 — C1×C4 factorial: actuation fixes finishing, fresh reflection fixes the tail</b><br>"
                        "<sub>study 005 inv 002 · nemotron-4b · Env A · reasoning=low · 20 seeds/arm · dotted line = worst-case (max) regret per arm</sub>",
                   x=0.5, font=dict(size=15.5)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.25, title=""),
        margin=dict(t=95, b=85, l=70, r=30), font=dict(family="-apple-system, Segoe UI, sans-serif", size=12.5),
    )
    ASSETS.mkdir(exist_ok=True)
    fig.write_html(ASSETS / "fig_phase1.html", include_plotlyjs="cdn")
    fig.write_image(ASSETS / "fig_phase1.png", scale=2)
    print("wrote", ASSETS / "fig_phase1.png")


if __name__ == "__main__":
    main()
