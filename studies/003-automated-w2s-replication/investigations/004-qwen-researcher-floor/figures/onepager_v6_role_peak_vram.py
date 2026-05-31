import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import apply_morel_template, MOREL_COLORS

OUT_DIR = Path(__file__).resolve().parent
GPU_CAP_GIB = 12.0

ROLE_COLORS = {
    "researcher": MOREL_COLORS["slate_blue"],
    "student_sft": MOREL_COLORS["terracotta"],
    "student_vllm": MOREL_COLORS["terracotta_dark"],
    "weak_teacher": MOREL_COLORS["mustard"],
}

CONFIGS = [
    {
        "label": "<b>SFT phase</b> · direct Bash<br>(no researcher resident)",
        "stacks": [
            ("student SFT", 8.84, "student_sft"),
        ],
        "verdict": "measured peak 8.84 GiB · 3.16 GiB headroom",
        "verdict_color": MOREL_COLORS["forest_green"],
    },
    {
        "label": "<b>vLLM eval phase</b> · direct Bash<br>(no researcher resident)",
        "stacks": [
            ("student vLLM eval", 10.13, "student_vllm"),
        ],
        "verdict": "measured peak 10.13 GiB · 1.87 GiB headroom",
        "verdict_color": MOREL_COLORS["forest_green"],
    },
    {
        "label": "<b>SFT phase</b><br>+ qwen3.5:4b researcher resident",
        "stacks": [
            ("Ollama researcher (qwen3.5:4b)", 5.73, "researcher"),
            ("student SFT (unsloth chunks down to fit)", 6.02, "student_sft"),
        ],
        "verdict": "measured peak 11.75 GiB · 256 MiB headroom",
        "verdict_color": MOREL_COLORS["mustard"],
    },
    {
        "label": "<b>vLLM eval phase</b><br>+ qwen3.5:4b researcher resident",
        "stacks": [
            ("Ollama researcher (qwen3.5:4b)", 5.73, "researcher"),
            ("student vLLM eval (max_model_len capped at 3600)", 6.02, "student_vllm"),
        ],
        "verdict": "measured peak 11.75 GiB · 76 MiB headroom — fragile",
        "verdict_color": MOREL_COLORS["error_red"],
    },
    {
        "label": "<b>vLLM eval phase</b><br>+ nemotron-3-nano:4b researcher resident",
        "stacks": [
            ("Ollama researcher (nemotron-3-nano:4b)", 5.25, "researcher"),
            ("student vLLM eval (max_model_len capped at 3600)", 6.52, "student_vllm"),
        ],
        "verdict": "measured peak 11.77 GiB · 234 MiB headroom — fragile",
        "verdict_color": MOREL_COLORS["error_red"],
    },
    {
        "label": "<b>vLLM eval (projected, test_size=1315)</b><br>"
                 "+ qwen3.5:4b researcher resident",
        "stacks": [
            ("Ollama researcher (qwen3.5:4b)", 5.73, "researcher"),
            ("student vLLM eval (projected KV cache for 1315 prompts)", 9.5, "student_vllm"),
        ],
        "verdict": "projected ~15.2 GiB · OOM at vLLM init (per inv md)",
        "verdict_color": MOREL_COLORS["error_red"],
    },
]

fig = go.Figure()

labels = [c["label"] for c in CONFIGS]
seen_legend = set()
component_name_lookup = {
    "researcher": "Ollama researcher (resident)",
    "student_sft": "student SFT (Qwen3-4B-Base 4-bit + LoRA + activations)",
    "student_vllm": "student vLLM eval (Qwen3-4B-Base fp16 + KV cache)",
}

for cfg in CONFIGS:
    for component_name, gib, role in cfg["stacks"]:
        legend_name = component_name_lookup.get(role, component_name)
        show_legend = role not in seen_legend
        seen_legend.add(role)
        fig.add_trace(
            go.Bar(
                name=legend_name,
                y=[cfg["label"]],
                x=[gib],
                orientation="h",
                marker=dict(color=ROLE_COLORS[role]),
                showlegend=show_legend,
                hovertemplate=f"{component_name}: %{{x:.2f}} GiB<extra>%{{y}}</extra>",
            )
        )

annotations = []
for cfg in CONFIGS:
    total = sum(s[1] for s in cfg["stacks"])
    annotations.append(
        dict(
            x=max(total + 0.4, GPU_CAP_GIB + 0.4),
            y=cfg["label"],
            text=f"<b>{cfg['verdict']}</b>",
            showarrow=False,
            font=dict(color=cfg["verdict_color"], size=11),
            xanchor="left",
        )
    )
    annotations.append(
        dict(
            x=total / 2,
            y=cfg["label"],
            text=f"<span style='color:white;font-weight:600'>{total:.2f} GiB</span>",
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

annotations.append(
    dict(
        x=1.0, y=-0.32,
        xref="paper", yref="paper",
        text=(
            "<i>Note: vanilla_w2s loads <b>cached</b> weak-teacher labels and ceiling baselines — "
            "Qwen1.5-0.5B-Chat doesn't appear at per-idea runtime.<br>"
            "Per-idea hot path is student SFT + student vLLM eval. SFT footprint is adaptive "
            "(unsloth chunks down under constraint); vLLM eval footprint is essentially fixed.</i>"
        ),
        showarrow=False,
        align="right", xanchor="right", yanchor="top",
        font=dict(size=10, color=MOREL_COLORS["muted_text"]),
    )
)

fig.update_layout(
    barmode="stack",
    annotations=annotations,
    xaxis=dict(title="peak VRAM (GiB)", range=[0, 22]),
    yaxis=dict(autorange="reversed", title=None, tickfont=dict(size=11)),
    height=680,
    legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5),
    margin=dict(l=320, r=40, t=110, b=190),
)

apply_morel_template(
    fig,
    title="Peak VRAM per role · why one 12 GiB GPU can't co-host researcher + vLLM eval",
    subtitle="measured peaks from two direct-Bash runs (with and without qwen3.5:4b co-resident); production-scale row is projected from inv md observations",
    attribution="studies/003-automated-w2s-replication / inv 004",
)

fig.write_image(str(OUT_DIR / "onepager_v6_role_peak_vram.png"),
                width=1600, height=680, scale=2, engine="kaleido")
fig.write_html(str(OUT_DIR / "onepager_v6_role_peak_vram.html"), include_plotlyjs="cdn")
