import glob
import json
import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

CSV = Path(__file__).resolve().parents[2] / "data" / "dense_lr_bs_loss.csv"
ROOT = Path(__file__).resolve().parents[1] / "runs" / "phase1"
ASSETS = Path(__file__).resolve().parents[2] / "assets"
N, D = 214663680, 100000000000
FLOOR = 5e-5


def arm_regrets(arm):
    out = []
    for f in glob.glob(str(ROOT / f"ollama_{arm}_*" / "loop_summary.json")):
        out.append(max(0.0, json.load(open(f))["final_regret"]))
    return out


def jitter(n, seed=0, amp=0.16):
    out, v = [], seed + 1
    for _ in range(n):
        v = (v * 1103515245 + 12345) % 2147483648
        out.append((v / 2147483648 - 0.5) * 2 * amp)
    return out


def main():
    df = pd.read_csv(CSV)
    g = df[(df.N == N) & (df.D == D)].groupby(["lr", "bs"], as_index=False)["smooth loss"].min()
    opt = g["smooth loss"].min()
    config_reg = sorted(float(l) - opt for l in g["smooth loss"])
    rand_med = sorted(config_reg)[len(config_reg) // 2]

    rows = [
        ("all 120 configs", config_reg, "#9ca3af", 0),
        ("A0 minimal (20 runs)", arm_regrets("A0"), "#6b7280", 1),
        ("A3 +C1self+C4 (20)", arm_regrets("A3"), "#ea580c", 2),
        ("A5 +C1fresh+C4 (20)", arm_regrets("A5"), "#0d9488", 3),
    ]

    fig = go.Figure()
    # basin shading
    for thr, lbl, col in [(0.002, "top-5 (≤0.002)", "rgba(16,185,129,0.10)"),
                          (0.005, "top-13 (≤0.005)", "rgba(16,185,129,0.06)"),
                          (0.01, "top-22 (≤0.01)", "rgba(16,185,129,0.03)")]:
        fig.add_vrect(x0=FLOOR, x1=thr, fillcolor=col, line_width=0, layer="below")
    for yi, (label, vals, color, _) in enumerate(rows):
        xv = [max(v, FLOOR) for v in vals]
        jy = jitter(len(xv), seed=yi)
        fig.add_trace(go.Scatter(x=xv, y=[yi + j for j in jy], mode="markers",
                                 marker=dict(size=7 if yi else 4, color=color, opacity=0.6 if yi == 0 else 0.85,
                                             line=dict(width=0.5, color="white")),
                                 name=label, showlegend=False,
                                 hovertemplate=f"{label}<br>regret=%{{x:.4f}}<extra></extra>"))
        med = sorted(vals)[len(vals) // 2]
        fig.add_trace(go.Scatter(x=[max(med, FLOOR)], y=[yi], mode="markers",
                                 marker=dict(size=14, color=color, symbol="line-ns", line=dict(width=3, color="#111827")),
                                 showlegend=False, hovertemplate=f"{label} median={med:.4f}<extra></extra>"))

    fig.add_vline(x=rand_med, line=dict(color="#b91c1c", width=1.5, dash="dot"),
                  annotation_text=f"random median {rand_med:.3f}", annotation_position="top")
    fig.add_vline(x=0.1912, line=dict(color="#7f1d1d", width=1, dash="dot"),
                  annotation_text="worst 0.19", annotation_position="top")

    fig.update_layout(
        template="plotly_white", width=1180, height=480,
        title=dict(text="<b>How good is the regret? Grounding it in the Env A landscape</b><br>"
                        "<sub>green bands = the optimum's shallow basin (5/13/22 of 120 configs within 0.002/0.005/0.01) · ticks = per-row median · log x</sub>",
                   x=0.5, font=dict(size=15)),
        xaxis=dict(title="simple regret (log)  ·  0 = exact optimum, left is better", type="log",
                   range=[math.log10(FLOOR), math.log10(0.25)]),
        yaxis=dict(tickvals=list(range(len(rows))), ticktext=[r[0] for r in rows], range=[-0.6, len(rows) - 0.4]),
        margin=dict(t=78, b=55, l=150, r=30), font=dict(family="-apple-system, Segoe UI, sans-serif", size=12.5),
    )
    ASSETS.mkdir(exist_ok=True)
    fig.write_html(ASSETS / "fig_regret_context.html", include_plotlyjs="cdn")
    fig.write_image(ASSETS / "fig_regret_context.png", scale=2)
    print("wrote", ASSETS / "fig_regret_context.png")


if __name__ == "__main__":
    main()
