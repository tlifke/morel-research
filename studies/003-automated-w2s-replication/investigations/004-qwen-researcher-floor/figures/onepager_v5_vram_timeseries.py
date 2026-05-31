import csv
import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import apply_morel_template, MOREL_COLORS

OUT_DIR = Path(__file__).resolve().parent
GPU_CAP_GIB = 12.0

QWEN_RESIDENT_GIB = 5.67
NEMOTRON_RESIDENT_GIB = 4.86


def load_curve(path: Path) -> tuple[list[float], list[float], list[str]]:
    ts, used, phases = [], [], []
    with path.open() as f:
        rows = list(csv.DictReader(f))
    t0 = float(rows[0]["ts"])
    for r in rows:
        ts.append(float(r["ts"]) - t0)
        used.append(int(r["used_mib"].strip()) / 1024.0)
        phases.append(r["phase"].strip())
    return ts, used, phases


def trim_to_active(ts, used, phases):
    start = 0
    for i, p in enumerate(phases):
        if "TRAIN" in p:
            start = max(0, i - 4)
            break
    end = len(ts)
    for i in range(len(ts) - 1, -1, -1):
        if "POST_RUN" in phases[i] or "DONE" in phases[i]:
            if used[i] > 0.4:
                end = min(len(ts), i + 4)
                break
    if end == len(ts):
        for i in range(len(ts) - 1, start, -1):
            if used[i] > 0.4:
                end = min(len(ts), i + 4)
                break
    t0 = ts[start]
    return [t - t0 for t in ts[start:end]], used[start:end], phases[start:end]


direct_csv = OUT_DIR / "vram_direct_bash.csv"
coresident_csv = OUT_DIR / "vram_qwen35_coresident.csv"
nemotron_csv = OUT_DIR / "vram_nemotron_coresident.csv"

ts_direct, used_direct, ph_direct = trim_to_active(*load_curve(direct_csv))

fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=ts_direct, y=used_direct,
        mode="lines",
        name="direct Bash (LLM out of loop, succeeds)",
        line=dict(color=MOREL_COLORS["forest_green"], width=2.5),
        hovertemplate="t=%{x:.1f}s · %{y:.2f} GiB<extra>direct Bash</extra>",
    )
)

if coresident_csv.exists():
    ts_co, used_co, ph_co = trim_to_active(*load_curve(coresident_csv))
    fig.add_trace(
        go.Scatter(
            x=ts_co, y=used_co,
            mode="lines",
            name="qwen3.5:4b researcher co-resident",
            line=dict(color=MOREL_COLORS["error_red"], width=2.5),
            hovertemplate="t=%{x:.1f}s · %{y:.2f} GiB<extra>qwen3.5:4b co-resident</extra>",
        )
    )

if nemotron_csv.exists():
    ts_nm, used_nm, ph_nm = trim_to_active(*load_curve(nemotron_csv))
    fig.add_trace(
        go.Scatter(
            x=ts_nm, y=used_nm,
            mode="lines",
            name="nemotron-3-nano:4b researcher co-resident",
            line=dict(color=MOREL_COLORS["mustard"], width=2.5, dash="dashdot"),
            hovertemplate="t=%{x:.1f}s · %{y:.2f} GiB<extra>nemotron co-resident</extra>",
        )
    )

if coresident_csv.exists():
    co_peak = max(used_co)
    co_peak_idx = used_co.index(co_peak)
    fig.add_annotation(
        x=ts_co[co_peak_idx], y=co_peak,
        text=f"<b>both co-resident runs peg the cap</b><br>"
             f"<i>qwen3.5:4b peak 11.75 GiB (76 MiB headroom) · "
             f"nemotron peak 11.77 GiB (234 MiB headroom)</i>",
        showarrow=True, arrowhead=2,
        ax=140, ay=-44,
        font=dict(color=MOREL_COLORS["error_red"], size=13),
    )

fig.add_hline(
    y=GPU_CAP_GIB,
    line=dict(color=MOREL_COLORS["dark_earth"], width=2, dash="dash"),
    annotation_text=f"<b>RTX 3080 cap · {GPU_CAP_GIB:.0f} GiB</b>",
    annotation_position="top left",
    annotation_font=dict(color=MOREL_COLORS["dark_earth"], size=14),
)

fig.add_hline(
    y=QWEN_RESIDENT_GIB,
    line=dict(color=MOREL_COLORS["slate_blue"], width=1, dash="dot"),
    annotation_text=f"<span style='color:{MOREL_COLORS['slate_blue']};font-size:13px'>"
                    f"qwen3.5:4b researcher baseline ({QWEN_RESIDENT_GIB:.2f} GiB resident)</span>",
    annotation_position="bottom right",
)

max_t = max(ts_direct) if ts_direct else 100
phase_marks = [
    (25, "model load /<br>weak-label setup"),
    (45, "<b>SFT phase</b><br>(student LoRA fine-tune)"),
    (80, "<code>os.execv</code><br>SFT child exits"),
    (98, "<b>vLLM eval phase</b><br>(student inference)"),
]
for x, text in phase_marks:
    if x < max_t:
        fig.add_annotation(
            x=x, y=11.4,
            text=f"<span style='color:{MOREL_COLORS['muted_text']};font-size:13px'>{text}</span>",
            showarrow=False,
            xanchor="center", yanchor="top",
        )

fig.update_layout(
    font=dict(size=15),
    xaxis=dict(title=dict(text="seconds from process launch", font=dict(size=15)),
               tickfont=dict(size=13)),
    yaxis=dict(title=dict(text="GPU VRAM used (GiB)", font=dict(size=15)),
               tickfont=dict(size=13), range=[0, 13]),
    height=640,
    legend=dict(
        orientation="h",
        yanchor="bottom", y=-0.24,
        xanchor="center", x=0.5,
        font=dict(size=14),
        entrywidthmode="pixels", entrywidth=380,
    ),
    margin=dict(l=90, r=50, t=120, b=160),
)

apply_morel_template(
    fig,
    title="Per-idea VRAM trace: where 12 GiB stops being enough",
    subtitle="captured nvidia-smi during one vanilla_w2s iteration (train_size=64, test_size=64, --load-in-4bit). "
             "co-resident run fits at smoke scale but lives within ~76 MiB of OOM",
    attribution="studies/003-automated-w2s-replication / inv 004 — nvidia-smi sampling 2026-05-26",
)

fig.write_image(str(OUT_DIR / "onepager_v5_vram_timeseries.png"),
                width=1500, height=640, scale=2, engine="kaleido")
fig.write_html(str(OUT_DIR / "onepager_v5_vram_timeseries.html"), include_plotlyjs="cdn")
