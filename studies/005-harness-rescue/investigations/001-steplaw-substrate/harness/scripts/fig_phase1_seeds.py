import glob
import json
import math
from pathlib import Path

import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1] / "runs" / "phase1"
ASSETS = Path(__file__).resolve().parents[2] / "assets"
OPT = (0.007812, 1024)
ARMS = ["A0", "A1", "A2", "A3", "A4", "A5"]
ARMLBL = {"A0": "A0<br>minimal", "A1": "A1<br>+C4", "A2": "A2<br>+C1self",
          "A3": "A3<br>+C1self<br>+C4", "A4": "A4<br>+C1fresh", "A5": "A5<br>+C1fresh<br>+C4"}


def reached_opt(tr):
    return any(abs(math.log(t["lr"]) - math.log(OPT[0])) < 1e-6 and t["bs"] == OPT[1] for t in tr)


def main():
    data = {}
    for a in ARMS:
        for f in glob.glob(str(ROOT / f"ollama_{a}_*" / "loop_summary.json")):
            r = json.load(open(f))
            s = int(Path(f).parent.name.split("_s")[-1])
            data[(a, s)] = (max(0.0, r["final_regret"]), reached_opt(r["trajectory"]))

    seeds = list(range(1, 21))
    z, text = [], []
    for s in seeds:
        row, trow = [], []
        for a in ARMS:
            rg, op = data.get((a, s), (None, False))
            row.append(math.log10(max(rg, 5e-5)) if rg is not None else None)
            trow.append((("★ " if op else "") + (f"{rg:.4f}" if rg is not None else "")) if rg is not None else "")
        z.append(row); text.append(trow)

    fig = go.Figure(go.Heatmap(
        z=z, x=[ARMLBL[a] for a in ARMS], y=[f"seed {s}" for s in seeds],
        text=text, texttemplate="%{text}", textfont=dict(size=9.5),
        colorscale="RdYlGn_r", reversescale=False,
        colorbar=dict(title="regret<br>(log)", tickvals=[math.log10(v) for v in [0.0001, 0.001, 0.01, 0.1]],
                      ticktext=["0.0001", "0.001", "0.01", "0.1"]),
        zmin=math.log10(5e-5), zmax=math.log10(0.05),
        hovertemplate="%{x}<br>%{y}<br>regret=%{text}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_white", width=900, height=820,
        title=dict(text="<b>Phase 1 — regret per seed × arm</b>  (★ = reached the exact optimum)<br>"
                        "<sub>green = near-optimal · red = real miss · if rows were uniformly colored, seed would be the confound — they are not</sub>",
                   x=0.5, font=dict(size=15)),
        margin=dict(t=80, b=40, l=70, r=30), font=dict(family="-apple-system, Segoe UI, sans-serif"),
        yaxis=dict(autorange="reversed"),
    )
    ASSETS.mkdir(exist_ok=True)
    fig.write_html(ASSETS / "fig_phase1_seeds.html", include_plotlyjs="cdn")
    fig.write_image(ASSETS / "fig_phase1_seeds.png", scale=2)
    print("wrote", ASSETS / "fig_phase1_seeds.png")


if __name__ == "__main__":
    main()
