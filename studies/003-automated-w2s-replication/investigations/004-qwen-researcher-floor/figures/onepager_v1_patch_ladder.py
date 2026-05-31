import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import apply_morel_template, MOREL_COLORS

OUT_DIR = Path(__file__).resolve().parent

FAILURE_MODES = {
    "prompt": {"label": "prompt / tool-name failure", "color": MOREL_COLORS["error_red"]},
    "substrate": {"label": "substrate contention (VRAM)", "color": MOREL_COLORS["terracotta"]},
    "async_bash": {"label": "async-Bash agent loop", "color": MOREL_COLORS["mustard"]},
}

CELLS = [
    {
        "label": "baseline · no hint",
        "Bash": 0, "bash_low": 0, "Read_Write": 0, "other_invented": 21,
        "verdict": "invents tool names (no canonical Bash fires)",
        "mode": "prompt",
    },
    {
        "label": "baseline · inv 003 gate-5 hint",
        "Bash": 58, "bash_low": 27, "Read_Write": 15, "other_invented": 0,
        "verdict": "loop closes mechanically; never reaches evaluate_predictions",
        "mode": "prompt",
    },
    {
        "label": "patch 1 · QwenCode-density",
        "Bash": 5, "bash_low": 0, "Read_Write": 2, "other_invented": 2,
        "verdict": "hallucinates Python tool, gives up on first 'unknown tool'",
        "mode": "prompt",
    },
    {
        "label": "patch 2 · + negative list + recovery",
        "Bash": 0, "bash_low": 0, "Read_Write": 0, "other_invented": 0,
        "verdict": "context overflow → 0 native tool calls across 26 sessions",
        "mode": "prompt",
    },
    {
        "label": "patch 3 · minimal extension",
        "Bash": 15, "bash_low": 14, "Read_Write": 19, "other_invented": 11,
        "verdict": "tools fire; agent bails to summary-text after 2 calls",
        "mode": "prompt",
    },
    {
        "label": "patch 4 · directive + persistence",
        "Bash": 10, "bash_low": 29, "Read_Write": 4, "other_invented": 6,
        "verdict": "right first action, 49 retries — Bash returns in ~5s on 84s task",
        "mode": "substrate",
    },
    {
        "label": "nemotron-3-nano:4b · patch 4",
        "Bash": 25, "bash_low": 0, "Read_Write": 2, "other_invented": 0,
        "verdict": "smaller researcher, same wall — vLLM init OOM by 0.75 GiB",
        "mode": "substrate",
    },
    {
        "label": "qwen3.5:4b · patch 4 + time-multiplex",
        "Bash": 208, "bash_low": 111, "Read_Write": 0, "other_invented": 13,
        "verdict": "208 Bash retries inside one 84s task — async-Bash is the residual blocker",
        "mode": "async_bash",
    },
]

SERIES = [
    ("Bash (canonical)", "Bash", MOREL_COLORS["forest_green"]),
    ("bash / BASH (rejected by shim)", "bash_low", MOREL_COLORS["error_red"]),
    ("Read / Write", "Read_Write", MOREL_COLORS["terracotta"]),
    ("other invented names", "other_invented", MOREL_COLORS["mushroom"]),
]

labels = [c["label"] for c in CELLS]

fig = go.Figure()
for series_label, key, color in SERIES:
    fig.add_trace(
        go.Bar(
            name=series_label,
            y=labels,
            x=[c[key] for c in CELLS],
            orientation="h",
            marker=dict(color=color),
            hovertemplate=f"{series_label}: %{{x}}<extra>%{{y}}</extra>",
        )
    )

annotations = []
for cell in CELLS:
    total = cell["Bash"] + cell["bash_low"] + cell["Read_Write"] + cell["other_invented"]
    color = FAILURE_MODES[cell["mode"]]["color"]
    annotations.append(
        dict(
            x=max(total + 8, 14),
            y=cell["label"],
            text=f"<b>{cell['verdict']}</b>",
            showarrow=False,
            font=dict(color=color, size=11),
            xanchor="left",
        )
    )

for boundary_y in (1.5, 5.5):
    fig.add_shape(
        type="line",
        x0=-0.5, x1=1.5, xref="paper",
        y0=boundary_y, y1=boundary_y,
        line=dict(color=MOREL_COLORS["axis_gridline"], width=1, dash="dot"),
    )

mode_legend = (
    f"<b>verdict color:</b> &nbsp;"
    f"<span style='color:{FAILURE_MODES['prompt']['color']}'>● prompt / tool-name failure</span>"
    f" &nbsp;&nbsp;&nbsp;"
    f"<span style='color:{FAILURE_MODES['substrate']['color']}'>● substrate contention (VRAM)</span>"
    f" &nbsp;&nbsp;&nbsp;"
    f"<span style='color:{FAILURE_MODES['async_bash']['color']}'>● async-Bash agent loop</span>"
)

fig.add_annotation(
    text=mode_legend,
    xref="paper", yref="paper",
    x=0.5, y=-0.20,
    xanchor="center", yanchor="top",
    showarrow=False,
    font=dict(size=12, color=MOREL_COLORS["muted_text"]),
)

fig.update_layout(
    barmode="stack",
    annotations=annotations + list(fig.layout.annotations),
    xaxis=dict(title="tool calls observed per smoke", range=[0, 460]),
    yaxis=dict(autorange="reversed", title=None, tickfont=dict(size=11)),
    height=680,
    legend=dict(orientation="h", yanchor="bottom", y=-0.14, xanchor="center", x=0.5),
    margin=dict(l=300, r=80, t=110, b=180),
)

apply_morel_template(
    fig,
    title="Prompt induction succeeds; substrate is the wall",
    subtitle="qwen3.5:4b researcher floor: two baselines, four prompt patches, two substrate diagnostics",
    attribution="studies/003-automated-w2s-replication / inv 004",
)

fig.write_image(str(OUT_DIR / "onepager_v1_patch_ladder.png"),
                width=1500, height=680, scale=2, engine="kaleido")
fig.write_html(str(OUT_DIR / "onepager_v1_patch_ladder.html"), include_plotlyjs="cdn")
