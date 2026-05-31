import sys
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import apply_morel_template, MOREL_COLORS

OUT_DIR = Path(__file__).resolve().parent

GPU_CAP_GIB = 12.0

PATCH_CELLS = [
    {
        "label": "patch 1<br>QwenCode-density",
        "Bash": 5, "bash_low": 0, "Read_Write": 2, "other": 2,
        "note": "hallucinates Python tool",
    },
    {
        "label": "patch 2<br>+ negative list",
        "Bash": 0, "bash_low": 0, "Read_Write": 0, "other": 0,
        "note": "ctx overflow",
    },
    {
        "label": "patch 3<br>minimal extension",
        "Bash": 15, "bash_low": 14, "Read_Write": 19, "other": 11,
        "note": "bails to text",
    },
    {
        "label": "patch 4<br>directive + persistence",
        "Bash": 10, "bash_low": 29, "Read_Write": 4, "other": 6,
        "note": "right first action, 49 retries",
    },
]

PATCH_SERIES = [
    ("Bash (canonical)", "Bash", MOREL_COLORS["forest_green"]),
    ("bash / BASH (rejected)", "bash_low", MOREL_COLORS["error_red"]),
    ("Read / Write", "Read_Write", MOREL_COLORS["terracotta"]),
    ("other invented", "other", MOREL_COLORS["mushroom"]),
]

VRAM_CONFIGS = [
    {
        "label": "qwen3.5:4b researcher<br>+ vLLM eval",
        "stacks": [
            ("Ollama researcher (resident)", 5.7, MOREL_COLORS["slate_blue"]),
            ("vLLM Qwen3-4B-Base weights", 7.6, MOREL_COLORS["terracotta"]),
            ("vLLM KV cache (required)", 1.2, MOREL_COLORS["terracotta_light"]),
        ],
        "verdict": "−2.5 GiB",
        "fits": False,
    },
    {
        "label": "nemotron-3-nano:4b researcher<br>+ vLLM eval",
        "stacks": [
            ("Ollama researcher (resident)", 4.86, MOREL_COLORS["slate_blue"]),
            ("vLLM Qwen3-4B-Base weights", 7.6, MOREL_COLORS["terracotta"]),
            ("vLLM KV cache (required)", 1.2, MOREL_COLORS["terracotta_light"]),
        ],
        "verdict": "−1.7 GiB",
        "fits": False,
    },
    {
        "label": "direct Bash<br>(LLM out of loop)",
        "stacks": [
            ("vLLM Qwen3-4B-Base weights", 7.6, MOREL_COLORS["terracotta"]),
            ("vLLM KV cache", 1.2, MOREL_COLORS["terracotta_light"]),
        ],
        "verdict": "+3.2 GiB ✓",
        "fits": True,
    },
]

fig = make_subplots(
    rows=1, cols=2,
    column_widths=[0.55, 0.45],
    subplot_titles=(
        "<b>Prompt floor</b> — tool-call shape converges on the right behavior",
        "<b>Substrate floor</b> — peak VRAM vs. 12 GiB cap on a 3080",
    ),
    horizontal_spacing=0.14,
)

patch_labels = [c["label"] for c in PATCH_CELLS]
for series_label, key, color in PATCH_SERIES:
    fig.add_trace(
        go.Bar(
            name=series_label,
            y=patch_labels,
            x=[c[key] for c in PATCH_CELLS],
            orientation="h",
            marker=dict(color=color),
            legendgroup="prompt",
            hovertemplate=f"{series_label}: %{{x}}<extra>%{{y}}</extra>",
        ),
        row=1, col=1,
    )

vram_labels = [c["label"] for c in VRAM_CONFIGS]
seen_legend = set()
for cfg in VRAM_CONFIGS:
    for component_name, gib, color in cfg["stacks"]:
        show_legend = component_name not in seen_legend
        seen_legend.add(component_name)
        fig.add_trace(
            go.Bar(
                name=component_name,
                y=[cfg["label"]],
                x=[gib],
                orientation="h",
                marker=dict(color=color),
                showlegend=show_legend,
                legendgroup="vram",
                hovertemplate=f"{component_name}: %{{x:.2f}} GiB<extra>%{{y}}</extra>",
            ),
            row=1, col=2,
        )

fig.update_layout(barmode="stack")

annotations = list(fig.layout.annotations)

for cell in PATCH_CELLS:
    total = cell["Bash"] + cell["bash_low"] + cell["Read_Write"] + cell["other"]
    annotations.append(
        dict(
            x=max(total + 3, 6),
            y=cell["label"],
            text=f"<i>{cell['note']}</i>",
            xref="x1", yref="y1",
            showarrow=False,
            font=dict(color=MOREL_COLORS["muted_text"], size=10),
            xanchor="left",
        )
    )

for cfg in VRAM_CONFIGS:
    total_gib = sum(s[1] for s in cfg["stacks"])
    color = MOREL_COLORS["forest_green"] if cfg["fits"] else MOREL_COLORS["error_red"]
    annotations.append(
        dict(
            x=max(total_gib + 0.3, GPU_CAP_GIB + 0.3),
            y=cfg["label"],
            text=f"<b>{cfg['verdict']}</b>",
            xref="x2", yref="y2",
            showarrow=False,
            font=dict(color=color, size=12),
            xanchor="left",
        )
    )

fig.add_shape(
    type="line",
    x0=GPU_CAP_GIB, x1=GPU_CAP_GIB,
    y0=-0.5, y1=len(VRAM_CONFIGS) - 0.5,
    xref="x2", yref="y2",
    line=dict(color=MOREL_COLORS["dark_earth"], width=2, dash="dash"),
)
annotations.append(
    dict(
        x=GPU_CAP_GIB, y=-0.45,
        xref="x2", yref="y2",
        text=f"<b>3080 cap · {GPU_CAP_GIB:.0f} GiB</b>",
        showarrow=False,
        font=dict(color=MOREL_COLORS["dark_earth"], size=11),
        xanchor="center", yanchor="bottom",
    )
)

fig.update_xaxes(title_text="tool calls per smoke", row=1, col=1, range=[0, 80])
fig.update_xaxes(title_text="peak VRAM (GiB)", row=1, col=2, range=[0, 17])
fig.update_yaxes(autorange="reversed", row=1, col=1, tickfont=dict(size=11))
fig.update_yaxes(autorange="reversed", row=1, col=2, tickfont=dict(size=11))

fig.update_layout(
    annotations=annotations,
    height=540,
    legend=dict(
        orientation="h",
        yanchor="bottom", y=-0.28,
        xanchor="center", x=0.5,
        groupclick="toggleitem",
    ),
    margin=dict(l=200, r=60, t=130, b=180),
)

apply_morel_template(
    fig,
    title="Prompt induction is solved; substrate is the residual wall",
    subtitle="left: 4 prompt patches on qwen3.5:4b. right: peak VRAM for SFT→eval handoff against the 3080's 12 GiB cap",
    attribution="studies/003-automated-w2s-replication / inv 004",
)

fig.write_image(str(OUT_DIR / "onepager_v2_two_panel.png"),
                width=1700, height=540, scale=2, engine="kaleido")
fig.write_html(str(OUT_DIR / "onepager_v2_two_panel.html"), include_plotlyjs="cdn")
