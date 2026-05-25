import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import apply_morel_template, MOREL_COLORS

OUT_DIR = Path(__file__).resolve().parent

CELLS = [
    {
        "label": "qwen3:4b · patch on",
        "family": "qwen3",
        "size": "4B",
        "pass": False,
        "tool_use_native": False,
        "Bash": 0,
        "bash_lower": 0,
        "Read_Write": 0,
        "evaluate_predictions": 4,
        "share_finding": 0,
        "other_invented": 0,
        "note": "narrates shell in markdown; no tool_use blocks emitted",
    },
    {
        "label": "qwen3.5:4b · patch off",
        "family": "qwen3.5",
        "size": "4B",
        "pass": False,
        "tool_use_native": True,
        "Bash": 0,
        "bash_lower": 0,
        "Read_Write": 0,
        "evaluate_predictions": 1,
        "share_finding": 0,
        "other_invented": 0,
        "note": "native tool_use but rare and not on canonical names",
    },
    {
        "label": "qwen3.5:4b · patch on",
        "family": "qwen3.5",
        "size": "4B",
        "pass": True,
        "tool_use_native": True,
        "Bash": 58,
        "bash_lower": 27,
        "Read_Write": 15,
        "evaluate_predictions": 0,
        "share_finding": 0,
        "other_invented": 0,
        "note": "loop closes; agent stuck on env discovery (ls/pwd/cat)",
    },
    {
        "label": "qwen3:8b · patch on",
        "family": "qwen3",
        "size": "8/9B",
        "pass": False,
        "tool_use_native": False,
        "Bash": 0,
        "bash_lower": 0,
        "Read_Write": 0,
        "evaluate_predictions": 0,
        "share_finding": 0,
        "other_invented": 0,
        "note": "same narration failure as 4B; scale does not fix",
    },
    {
        "label": "qwen3.5:9b · patch on",
        "family": "qwen3.5",
        "size": "8/9B",
        "pass": False,
        "tool_use_native": True,
        "Bash": 0,
        "bash_lower": 25,
        "Read_Write": 3,
        "evaluate_predictions": 0,
        "share_finding": 8,
        "other_invented": 2,
        "note": "ignores casing instruction; reverts to lowercase 'bash'",
    },
]

SERIES = [
    ("Bash (canonical)", "Bash", MOREL_COLORS["forest_green"]),
    ("bash (lowercase, rejected)", "bash_lower", MOREL_COLORS["error_red"]),
    ("Read / Write", "Read_Write", MOREL_COLORS["terracotta"]),
    ("evaluate_predictions", "evaluate_predictions", MOREL_COLORS["cream_dark"]),
    ("share_finding", "share_finding", MOREL_COLORS["muted_text"]),
    ("other invented names", "other_invented", MOREL_COLORS["axis_gridline"]),
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
for i, cell in enumerate(CELLS):
    total = cell["Bash"] + cell["bash_lower"] + cell["Read_Write"] + cell["evaluate_predictions"] + cell["share_finding"] + cell["other_invented"]
    verdict = "PASS" if cell["pass"] else "FAIL"
    verdict_color = MOREL_COLORS["forest_green"] if cell["pass"] else MOREL_COLORS["error_red"]
    annotations.append(
        dict(
            x=max(total + 4, 8),
            y=cell["label"],
            text=f"<b>{verdict}</b>",
            showarrow=False,
            font=dict(color=verdict_color, size=13),
            xanchor="left",
        )
    )

fig.update_layout(
    barmode="stack",
    annotations=annotations,
    xaxis=dict(title="tool calls observed in smoke run", range=[0, 115]),
    yaxis=dict(autorange="reversed", title=None),
    height=460,
    legend=dict(orientation="h", yanchor="bottom", y=-0.32, xanchor="center", x=0.5),
    margin=dict(l=170, r=80, t=90, b=110),
)

apply_morel_template(
    fig,
    title="Gate 5 matrix — tool-call composition by (model family × size × patch)",
    subtitle="failure modes are family-typed, not size-typed; the lone PASS does not reach evaluate_predictions",
    attribution="studies/003-automated-w2s-replication / inv 003 — claude-sdk-shim-and-researcher-swap",
)

png_path = OUT_DIR / "gate_5_matrix.png"
html_path = OUT_DIR / "gate_5_matrix.html"
fig.write_image(str(png_path), width=1100, height=460, scale=2, engine="kaleido")
fig.write_html(str(html_path), include_plotlyjs="cdn")
