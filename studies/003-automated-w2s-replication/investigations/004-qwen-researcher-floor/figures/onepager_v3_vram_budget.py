import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import apply_morel_template, MOREL_COLORS

OUT_DIR = Path(__file__).resolve().parent

GPU_CAP_GIB = 12.0

CONFIGS = [
    {
        "label": "qwen3.5:4b researcher<br>+ SFT → vLLM eval",
        "stacks": [
            ("Ollama researcher (resident, keep_alive)", 5.7, MOREL_COLORS["slate_blue"]),
            ("vLLM Qwen3-4B-Base weights", 7.6, MOREL_COLORS["terracotta"]),
            ("vLLM KV cache (minimum viable)", 1.2, MOREL_COLORS["terracotta_light"]),
        ],
        "verdict": "OVER by 2.5 GiB",
        "fits": False,
    },
    {
        "label": "nemotron-3-nano:4b researcher<br>+ SFT → vLLM eval",
        "stacks": [
            ("Ollama researcher (resident, keep_alive)", 4.86, MOREL_COLORS["slate_blue"]),
            ("vLLM Qwen3-4B-Base weights", 7.6, MOREL_COLORS["terracotta"]),
            ("vLLM KV cache (minimum viable)", 1.2, MOREL_COLORS["terracotta_light"]),
        ],
        "verdict": "OVER by 1.7 GiB",
        "fits": False,
    },
    {
        "label": "time-multiplex<br>(unload Ollama before Bash)",
        "stacks": [
            ("vLLM Qwen3-4B-Base weights", 7.6, MOREL_COLORS["terracotta"]),
            ("vLLM KV cache (minimum viable)", 1.2, MOREL_COLORS["terracotta_light"]),
        ],
        "verdict": "FITS in arithmetic — but async-Bash<br>re-pins researcher within 2-3s",
        "fits": "qualified",
    },
    {
        "label": "direct Bash<br>(LLM out of loop, inv 4a)",
        "stacks": [
            ("vLLM Qwen3-4B-Base weights", 7.6, MOREL_COLORS["terracotta"]),
            ("vLLM KV cache (minimum viable)", 1.2, MOREL_COLORS["terracotta_light"]),
        ],
        "verdict": "FITS · valid evaluate_predictions submission",
        "fits": True,
    },
]

VERDICT_COLOR = {
    True: MOREL_COLORS["forest_green"],
    False: MOREL_COLORS["error_red"],
    "qualified": MOREL_COLORS["mustard"],
}

fig = go.Figure()

labels = [c["label"] for c in CONFIGS]
seen_legend = set()
for cfg in CONFIGS:
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
                hovertemplate=f"{component_name}: %{{x:.2f}} GiB<extra>%{{y}}</extra>",
            )
        )

annotations = []
for cfg in CONFIGS:
    total = sum(s[1] for s in cfg["stacks"])
    color = VERDICT_COLOR[cfg["fits"]]
    annotations.append(
        dict(
            x=max(total + 0.4, GPU_CAP_GIB + 0.4),
            y=cfg["label"],
            text=f"<b>{cfg['verdict']}</b>",
            showarrow=False,
            font=dict(color=color, size=12),
            xanchor="left",
        )
    )
    annotations.append(
        dict(
            x=total / 2,
            y=cfg["label"],
            text=f"<span style='color:white;font-weight:600'>{total:.1f} GiB</span>",
            showarrow=False,
            font=dict(size=11),
            xanchor="center",
        )
    )

fig.add_shape(
    type="line",
    x0=GPU_CAP_GIB, x1=GPU_CAP_GIB,
    y0=-0.5, y1=len(CONFIGS) - 0.5,
    line=dict(color=MOREL_COLORS["dark_earth"], width=2.5, dash="dash"),
)
annotations.append(
    dict(
        x=GPU_CAP_GIB, y=-0.55,
        text=f"<b>RTX 3080 · {GPU_CAP_GIB:.0f} GiB cap</b>",
        showarrow=False,
        font=dict(color=MOREL_COLORS["dark_earth"], size=12),
        xanchor="center", yanchor="bottom",
    )
)

fig.update_layout(
    barmode="stack",
    annotations=annotations,
    xaxis=dict(title="peak VRAM during SFT → vLLM eval handoff (GiB)", range=[0, 18]),
    yaxis=dict(autorange="reversed", title=None, tickfont=dict(size=12)),
    height=480,
    legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
    margin=dict(l=260, r=80, t=110, b=130),
)

apply_morel_template(
    fig,
    title="A 12 GiB GPU can't co-host a 4B researcher and vLLM strong-model eval",
    subtitle="peak VRAM by configuration — only configs that evict the researcher fit; only direct-Bash actually closes the loop",
    attribution="studies/003-automated-w2s-replication / inv 004",
)

fig.write_image(str(OUT_DIR / "onepager_v3_vram_budget.png"),
                width=1500, height=480, scale=2, engine="kaleido")
fig.write_html(str(OUT_DIR / "onepager_v3_vram_budget.html"), include_plotlyjs="cdn")
