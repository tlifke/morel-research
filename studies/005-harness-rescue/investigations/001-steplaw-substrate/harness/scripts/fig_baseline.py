import csv
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

DATA = Path(__file__).resolve().parents[2] / "data" / "baseline_runs.csv"
ASSETS = Path(__file__).resolve().parents[2] / "assets"

NEMO = "nemotron-3-nano:4b"
GEM = "gemini-3.1-flash-lite"
C_NEMO, C_GEM = "#d1495b", "#1d4ed8"
C_FIN, C_STALL = "#16a34a", "#dc2626"


def load():
    rows = list(csv.DictReader(open(DATA)))
    for r in rows:
        r["final_regret"] = max(0.0, float(r["final_regret"]))
        r["experiments"] = int(r["experiments"])
    return rows


def jitter(n, seed=0):
    # deterministic pseudo-jitter in [-0.18, 0.18]
    out = []
    v = seed + 1
    for _ in range(n):
        v = (v * 1103515245 + 12345) % 2147483648
        out.append((v / 2147483648 - 0.5) * 0.36)
    return out


def main():
    rows = load()
    envA = [r for r in rows if r["env"] == "A"]
    nemoA = [r for r in envA if r["model"] == NEMO]
    gemA = [r for r in envA if r["model"] == GEM]

    fig = make_subplots(
        rows=1, cols=3, column_widths=[0.42, 0.28, 0.30],
        subplot_titles=(
            "<b>Regret on Env A</b>  (each dot = one run; lower is better)",
            "<b>Outcome on Env A</b>",
            "<b>Gemini regret across envs</b>",
        ),
        horizontal_spacing=0.09,
    )

    # ---- Panel 1: regret strip, Env A, nemotron vs gemini, colored by outcome ----
    for xi, (label, grp, base) in enumerate([("nemotron-4b", nemoA, 1.0), ("gemini-flash-lite", gemA, 2.0)]):
        jx = jitter(len(grp), seed=xi)
        for kind, color in [("finished", C_FIN), ("stalled", C_STALL)]:
            pts = [(base + j, r["final_regret"]) for r, j in zip(grp, jx) if r["outcome"].startswith(kind)]
            if not pts:
                continue
            fig.add_trace(go.Scatter(
                x=[p[0] for p in pts], y=[p[1] for p in pts], mode="markers",
                marker=dict(size=10, color=color, line=dict(width=1, color="white"), opacity=0.85),
                name=kind, legendgroup=kind, showlegend=(xi == 0),
                hovertemplate=f"{label}<br>regret=%{{y:.4f}}<br>{kind}<extra></extra>",
            ), row=1, col=1)
        # median line
        med = sorted(r["final_regret"] for r in grp)[len(grp) // 2]
        fig.add_trace(go.Scatter(x=[base - 0.28, base + 0.28], y=[med, med], mode="lines",
                                 line=dict(color="#111827", width=2, dash="solid"), showlegend=False,
                                 hovertemplate=f"{label} median regret=%{{y:.4f}}<extra></extra>"), row=1, col=1)
    fig.update_xaxes(tickvals=[1, 2], ticktext=[f"nemotron-4b<br>(n={len(nemoA)})", f"gemini<br>(n={len(gemA)})"],
                     range=[0.4, 2.6], row=1, col=1)
    fig.update_yaxes(title_text="simple regret (loss − optimum)", row=1, col=1, rangemode="tozero")

    # ---- Panel 2: outcome composition, Env A ----
    def comp(grp):
        c = defaultdict(int)
        for r in grp:
            c["stalled" if r["outcome"] == "stalled" else "finished"] += 1
        n = len(grp)
        return 100 * c["finished"] / n, 100 * c["stalled"] / n
    labels = ["nemotron-4b", "gemini"]
    fin = [comp(nemoA)[0], comp(gemA)[0]]
    stall = [comp(nemoA)[1], comp(gemA)[1]]
    fig.add_trace(go.Bar(x=labels, y=fin, name="finished", legendgroup="finished",
                         marker_color=C_FIN, showlegend=False,
                         text=[f"{v:.0f}%" for v in fin], textposition="inside"), row=1, col=2)
    fig.add_trace(go.Bar(x=labels, y=stall, name="stalled", legendgroup="stalled",
                         marker_color=C_STALL, showlegend=False,
                         text=[f"{v:.0f}%" for v in stall], textposition="inside"), row=1, col=2)
    fig.update_yaxes(title_text="% of runs", range=[0, 100], row=1, col=2)

    # ---- Panel 3: gemini regret across envs ----
    for xi, env in enumerate(["A", "B", "C"]):
        grp = [r for r in rows if r["model"] == GEM and r["env"] == env]
        jx = jitter(len(grp), seed=xi + 5)
        fig.add_trace(go.Scatter(
            x=[xi + 1 + j for j in jx], y=[r["final_regret"] for r in grp], mode="markers",
            marker=dict(size=10, color=C_GEM, line=dict(width=1, color="white"), opacity=0.85),
            showlegend=False, hovertemplate=f"Env {env}<br>regret=%{{y:.4f}}<extra></extra>",
        ), row=1, col=3)
    fig.update_xaxes(tickvals=[1, 2, 3], ticktext=["A<br>215M·over", "B<br>537M", "C<br>1.07B·sparse"], row=1, col=3)
    fig.update_yaxes(title_text="simple regret", row=1, col=3, rangemode="tozero")

    fig.update_layout(
        barmode="stack", template="plotly_white",
        title=dict(text="<b>Minimal-harness baseline on StepLaw</b>  ·  study 005 inv 001  ·  35 runs  ·  same prompt, same env",
                   x=0.5, font=dict(size=17)),
        legend=dict(orientation="h", yanchor="bottom", y=-0.16, xanchor="center", x=0.21, title=""),
        width=1280, height=540, margin=dict(t=90, b=80, l=70, r=30),
        font=dict(family="-apple-system, Segoe UI, sans-serif", size=13),
    )
    ASSETS.mkdir(exist_ok=True)
    fig.write_html(ASSETS / "fig_baseline.html", include_plotlyjs="cdn")
    fig.write_image(ASSETS / "fig_baseline.png", scale=2)
    print("wrote", ASSETS / "fig_baseline.png", "and .html")


if __name__ == "__main__":
    main()
