import glob
import json
import math
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CSV = Path(__file__).resolve().parents[2] / "data" / "dense_lr_bs_loss.csv"
RUNS = Path(__file__).resolve().parents[1] / "runs" / "sweep"
ASSETS = Path(__file__).resolve().parents[2] / "assets"
N, D = 214663680, 100000000000


def landscape():
    df = pd.read_csv(CSV)
    g = df[(df["N"] == N) & (df["D"] == D)].groupby(["lr", "bs"], as_index=False)["smooth loss"].min()
    lrs = sorted(g["lr"].unique())
    bss = sorted(g["bs"].unique())
    x = [math.log10(v) for v in lrs]
    y = [math.log10(v) for v in bss]
    z = [[float(g[(g["lr"] == lr) & (g["bs"] == bs)]["smooth loss"].iloc[0]) if not g[(g["lr"] == lr) & (g["bs"] == bs)].empty else None for lr in lrs] for bs in bss]
    opt = g.loc[g["smooth loss"].idxmin()]
    return x, y, z, math.log10(float(opt["lr"])), math.log10(int(opt["bs"])), float(opt["smooth loss"])


OPT = (0.007812, 1024)


def runs():
    out = []
    files = glob.glob(str(RUNS / "ollama_*" / "loop_summary.json"))
    for f in sorted(files, key=lambda p: int(Path(p).parent.name.split("_s")[-1])):
        r = json.load(open(f))
        rep = r.get("finished") or r.get("best_config") or {}
        opt_step = next((i + 1 for i, t in enumerate(r["trajectory"])
                         if abs(math.log(t["lr"]) - math.log(OPT[0])) < 1e-6 and t["bs"] == OPT[1]), None)
        out.append({"seed": Path(f).parent.name.split("_s")[-1], "outcome": r["outcome"],
                    "regret": max(0.0, r["final_regret"]), "traj": r["trajectory"],
                    "reported": {"lr": rep.get("best_lr", rep.get("lr")), "bs": rep.get("best_bs", rep.get("bs"))},
                    "opt_step": opt_step})
    return out


def main():
    x, y, z, ox, oy, oloss = landscape()
    rs = runs()
    ncol, nrow = 5, 4
    titles = [f"s{r['seed']} · {'FIN' if r['outcome']=='finished' else 'STALL'} · reg {r['regret']:.3f}"
              + (f" · opt@{r['opt_step']}" if r['opt_step'] else "") for r in rs]
    fig = make_subplots(rows=nrow, cols=ncol, subplot_titles=titles,
                        horizontal_spacing=0.025, vertical_spacing=0.07)
    for i, r in enumerate(rs):
        row, col = i // ncol + 1, i % ncol + 1
        fig.add_trace(go.Heatmap(x=x, y=y, z=z, colorscale="Viridis_r", showscale=False,
                                 zmin=oloss, zmax=oloss + 0.12, hoverinfo="skip"), row=row, col=col)
        tx = [math.log10(t["lr"]) for t in r["traj"]]
        ty = [math.log10(t["bs"]) for t in r["traj"]]
        # path
        fig.add_trace(go.Scatter(x=tx, y=ty, mode="lines", line=dict(color="rgba(255,255,255,0.55)", width=1.2),
                                 showlegend=False, hoverinfo="skip"), row=row, col=col)
        # ordered points (color by step order)
        fig.add_trace(go.Scatter(x=tx, y=ty, mode="markers",
                                 marker=dict(size=6, color=list(range(len(tx))), colorscale="Hot", line=dict(width=0.5, color="black")),
                                 showlegend=False, hovertemplate="step %{marker.color}<extra></extra>"), row=row, col=col)
        # start (green ring) and end (outcome-colored ring)
        endc = "#16a34a" if r["outcome"] == "finished" else "#dc2626"
        fig.add_trace(go.Scatter(x=[tx[0]], y=[ty[0]], mode="markers",
                                 marker=dict(size=11, color="rgba(0,0,0,0)", line=dict(width=2.5, color="#22d3ee")),
                                 showlegend=False, hoverinfo="skip"), row=row, col=col)
        fig.add_trace(go.Scatter(x=[tx[-1]], y=[ty[-1]], mode="markers",
                                 marker=dict(size=13, color="rgba(0,0,0,0)", line=dict(width=2.5, color=endc)),
                                 showlegend=False, hoverinfo="skip"), row=row, col=col)
        # reported-best config (what the agent committed to via finish / its actual best)
        rep = r["reported"]
        if rep.get("lr") and rep.get("bs"):
            fig.add_trace(go.Scatter(x=[math.log10(rep["lr"])], y=[math.log10(rep["bs"])], mode="markers",
                                     marker=dict(size=15, color="rgba(255,255,255,0.0)", symbol="diamond-open",
                                                 line=dict(width=2.5, color="#f0abfc")),
                                     showlegend=False, hovertemplate="reported best<extra></extra>"), row=row, col=col)
        # optimum star
        fig.add_trace(go.Scatter(x=[ox], y=[oy], mode="markers",
                                 marker=dict(size=13, color="gold", symbol="star", line=dict(width=0.8, color="black")),
                                 showlegend=False, hoverinfo="skip"), row=row, col=col)
        fig.update_xaxes(showticklabels=False, row=row, col=col)
        fig.update_yaxes(showticklabels=False, row=row, col=col)

    fig.update_annotations(font_size=10.5)
    fig.update_layout(
        template="plotly_white", width=1320, height=1020,
        title=dict(text="<b>What nemotron-4b does on Env A</b>  ·  20 runs over the real StepLaw loss surface  (x=log lr → , y=log bs ↑ · brighter=lower loss · ★=optimum)<br>"
                        "<sub>cyan ring = first experiment · path dark→bright by step order · outer ring = last experiment (green=finished, red=stalled) · pink ◇ = config the agent REPORTED · 'opt@N' = reached exact optimum at step N</sub>",
                   x=0.5, font=dict(size=16)),
        margin=dict(t=95, b=20, l=20, r=20),
        font=dict(family="-apple-system, Segoe UI, sans-serif"),
    )
    ASSETS.mkdir(exist_ok=True)
    fig.write_html(ASSETS / "fig_trajectories.html", include_plotlyjs="cdn")
    fig.write_image(ASSETS / "fig_trajectories.png", scale=2)
    print("wrote", ASSETS / "fig_trajectories.png")


if __name__ == "__main__":
    main()
