import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import apply_morel_template, MOREL_COLORS

OUT_DIR = Path(__file__).resolve().parent

CELLS = [
    {
        "label": "qwen3:4b",
        "Bash": 0, "bash_low": 0, "Read_Write": 0,
        "share_finding": 0, "other_invented": 0,
        "verdict": "narrates — zero native tool calls",
    },
    {
        "label": "qwen3.5:4b",
        "Bash": 58, "bash_low": 27, "Read_Write": 15,
        "share_finding": 0, "other_invented": 0,
        "verdict": "loop closes mechanically; no evaluate_predictions",
    },
    {
        "label": "qwen3:8b",
        "Bash": 0, "bash_low": 0, "Read_Write": 0,
        "share_finding": 0, "other_invented": 0,
        "verdict": "narrates — zero native tool calls",
    },
    {
        "label": "qwen3.5:9b",
        "Bash": 0, "bash_low": 25, "Read_Write": 3,
        "share_finding": 8, "other_invented": 2,
        "verdict": "lowercase bash + share_finding hallucinations",
    },
]

SERIES = [
    ("Bash (canonical)", "Bash", MOREL_COLORS["forest_green"]),
    ("bash / BASH (rejected by shim)", "bash_low", MOREL_COLORS["error_red"]),
    ("Read / Write", "Read_Write", MOREL_COLORS["terracotta"]),
    ("share_finding (hallucinated)", "share_finding", MOREL_COLORS["mustard"]),
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
    total = (cell["Bash"] + cell["bash_low"] + cell["Read_Write"]
             + cell["share_finding"] + cell["other_invented"])
    annotations.append(
        dict(
            x=max(total + 4, 8),
            y=cell["label"],
            text=f"<i>{cell['verdict']}</i>",
            showarrow=False,
            font=dict(color=MOREL_COLORS["muted_text"], size=11),
            xanchor="left",
        )
    )

fig.update_layout(
    barmode="stack",
    annotations=annotations,
    xaxis=dict(title="tool calls observed per smoke", range=[0, 140]),
    yaxis=dict(autorange="reversed", title=None, tickfont=dict(size=12)),
    height=440,
    legend=dict(orientation="h", yanchor="bottom", y=-0.20, xanchor="center", x=0.5),
    margin=dict(l=140, r=80, t=110, b=120),
)

apply_morel_template(
    fig,
    title="Only qwen3.5:4b crossed the prompt-shape floor under the gate-5 hint",
    subtitle="four Ollama-served researchers under the same prompt condition (inv 003 gate-5 tool_invocation_hint)",
    attribution="studies/003-automated-w2s-replication / inv 003",
)

fig.write_image(str(OUT_DIR / "onepager_v4_model_sweep.png"),
                width=1500, height=440, scale=2, engine="kaleido")
fig.write_html(str(OUT_DIR / "onepager_v4_model_sweep.html"), include_plotlyjs="cdn")
