import sys
from pathlib import Path

import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))

from branding import apply_morel_template, MOREL_COLORS

OUT_DIR = Path(__file__).resolve().parent

FAILURE_MODES = {
    "prompt": {
        "label": "prompt / tool-name failure",
        "color": MOREL_COLORS["error_red"],
    },
    "structural_pass": {
        "label": "loop closes; no useful work",
        "color": MOREL_COLORS["cream_dark"],
    },
    "substrate": {
        "label": "substrate contention (VRAM)",
        "color": MOREL_COLORS["terracotta"],
    },
    "async_bash": {
        "label": "async-Bash agent-loop",
        "color": MOREL_COLORS["forest_green"],
    },
}

CELLS = [
    # Inv 003 gate-5 matrix
    {
        "group": "inv 3 (gate-5 prompt-shape)",
        "label": "qwen3:4b · patch on",
        "Bash": 0, "bash_low": 0, "Read_Write": 0,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 0,
        "verdict_label": "narrates",
        "failure_mode": "prompt",
    },
    {
        "group": "inv 3 (gate-5 prompt-shape)",
        "label": "qwen3.5:4b · patch off",
        "Bash": 0, "bash_low": 0, "Read_Write": 0,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 21,
        "verdict_label": "invents names",
        "failure_mode": "prompt",
    },
    {
        "group": "inv 3 (gate-5 prompt-shape)",
        "label": "qwen3.5:4b · patch on",
        "Bash": 58, "bash_low": 27, "Read_Write": 15,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 0,
        "verdict_label": "loop closes, no eval",
        "failure_mode": "structural_pass",
    },
    {
        "group": "inv 3 (gate-5 prompt-shape)",
        "label": "qwen3:8b · patch on",
        "Bash": 0, "bash_low": 0, "Read_Write": 0,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 0,
        "verdict_label": "narrates (8B)",
        "failure_mode": "prompt",
    },
    {
        "group": "inv 3 (gate-5 prompt-shape)",
        "label": "qwen3.5:9b · patch on",
        "Bash": 0, "bash_low": 25, "Read_Write": 3,
        "evaluate_predictions": 0, "share_finding": 8, "other_invented": 2,
        "verdict_label": "lowercase + invented",
        "failure_mode": "prompt",
    },
    # Inv 004 4b patch trajectory
    {
        "group": "inv 4b (qwen3.5:4b prompt induction)",
        "label": "patch 1 · QwenCode-density",
        "Bash": 5, "bash_low": 0, "Read_Write": 2,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 2,
        "verdict_label": "Python hallucinated, gave up",
        "failure_mode": "prompt",
    },
    {
        "group": "inv 4b (qwen3.5:4b prompt induction)",
        "label": "patch 2 · + negative-list + recovery",
        "Bash": 0, "bash_low": 0, "Read_Write": 0,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 0,
        "verdict_label": "ctx overflow, 0 tool calls / 26 sessions",
        "failure_mode": "prompt",
    },
    {
        "group": "inv 4b (qwen3.5:4b prompt induction)",
        "label": "patch 3 · minimal extension",
        "Bash": 15, "bash_low": 14, "Read_Write": 19,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 11,
        "verdict_label": "bails on first error",
        "failure_mode": "prompt",
    },
    {
        "group": "inv 4b (qwen3.5:4b prompt induction)",
        "label": "patch 4 · directive + persistence",
        "Bash": 49, "bash_low": 0, "Read_Write": 0,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 0,
        "verdict_label": "contention: ~5s Bash on a 84s task",
        "failure_mode": "substrate",
    },
    # Substrate diagnostics
    {
        "group": "inv 4 substrate diagnostics",
        "label": "nemotron-3-nano:4b · patch 4",
        "Bash": 25, "bash_low": 0, "Read_Write": 0,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 0,
        "verdict_label": "vLLM init OOM (-0.75 GiB)",
        "failure_mode": "substrate",
    },
    {
        "group": "inv 4 substrate diagnostics",
        "label": "qwen3.5:4b · patch 4 + time-multiplex",
        "Bash": 208, "bash_low": 111, "Read_Write": 0,
        "evaluate_predictions": 0, "share_finding": 0, "other_invented": 13,
        "verdict_label": "208 retries on 84s task → async-Bash",
        "failure_mode": "async_bash",
    },
]

SERIES = [
    ("Bash (canonical)", "Bash", MOREL_COLORS["forest_green"]),
    ("bash / BASH (rejected by shim)", "bash_low", MOREL_COLORS["error_red"]),
    ("Read / Write", "Read_Write", MOREL_COLORS["terracotta"]),
    ("evaluate_predictions", "evaluate_predictions", MOREL_COLORS["cream_dark"]),
    ("share_finding (hallucinated)", "share_finding", MOREL_COLORS["muted_text"]),
    ("other invented names", "other_invented", MOREL_COLORS["axis_gridline"]),
]

labels = [f"{c['group']} · {c['label']}" for c in CELLS]
short_labels = [c["label"] for c in CELLS]

fig = go.Figure()

for series_label, key, color in SERIES:
    fig.add_trace(
        go.Bar(
            name=series_label,
            y=short_labels,
            x=[c[key] for c in CELLS],
            orientation="h",
            marker=dict(color=color),
            hovertemplate=f"{series_label}: %{{x}}<extra>%{{y}}</extra>",
        )
    )

annotations = []
group_seen = set()
for i, cell in enumerate(CELLS):
    total = sum(cell[k] for k in ["Bash", "bash_low", "Read_Write", "evaluate_predictions", "share_finding", "other_invented"])
    mode = FAILURE_MODES[cell["failure_mode"]]
    annotations.append(
        dict(
            x=max(total + 6, 12),
            y=cell["label"],
            text=f"<b>{cell['verdict_label']}</b>",
            showarrow=False,
            font=dict(color=mode["color"], size=11),
            xanchor="left",
        )
    )

group_boundaries = [
    (4.5, "inv 3 · gate-5 prompt-shape matrix"),
    (8.5, "inv 4b · qwen3.5:4b prompt-induction patches"),
    (10.5, "inv 4 · substrate diagnostics"),
]

fig.update_layout(
    barmode="stack",
    annotations=annotations,
    xaxis=dict(title="tool calls observed per smoke", range=[0, 360]),
    yaxis=dict(autorange="reversed", title=None, tickfont=dict(size=11)),
    height=620,
    legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
    margin=dict(l=260, r=380, t=110, b=130),
)

for i, (boundary_y, group_title) in enumerate(group_boundaries):
    if i == 0:
        start = -0.5
    else:
        start = group_boundaries[i - 1][0]
    fig.add_shape(
        type="line",
        x0=0, x1=1, xref="paper",
        y0=boundary_y, y1=boundary_y,
        line=dict(color=MOREL_COLORS["axis_gridline"], width=1, dash="dot"),
    )

footer_lines = [
    "<b>Failure-mode legend</b>",
    f"<span style='color:{FAILURE_MODES['prompt']['color']}'>● prompt / tool-name failure</span>",
    f"<span style='color:{FAILURE_MODES['structural_pass']['color']}'>● loop closes; no useful work</span>",
    f"<span style='color:{FAILURE_MODES['substrate']['color']}'>● substrate contention (VRAM)</span>",
    f"<span style='color:{FAILURE_MODES['async_bash']['color']}'>● async-Bash agent-loop</span>",
    "",
    "<b>Direct-Bash control (no LLM in loop)</b>",
    "Option 2: paired vLLM eval (unquantized vs bnb int4)",
    "→ ΔPGR = 0.042 on identical checkpoint = <b>CONFOUND</b>",
    "(quantization is not viable for the inv-5 measurement plan)",
]

fig.add_annotation(
    text="<br>".join(footer_lines),
    xref="paper", yref="paper",
    x=1.02, y=1.0,
    xanchor="left", yanchor="top",
    align="left",
    showarrow=False,
    font=dict(size=11, color=MOREL_COLORS["muted_text"]),
    bgcolor="rgba(0,0,0,0)",
)

apply_morel_template(
    fig,
    title="Researcher floor — what configuration walls we hit, and why",
    subtitle="13 cells across inv 003 + inv 004; four distinct failure modes; no config closes the loop end-to-end",
    attribution="studies/003-automated-w2s-replication / inv 003 + inv 004",
)

png_path = OUT_DIR / "researcher_floor_matrix.png"
html_path = OUT_DIR / "researcher_floor_matrix.html"
fig.write_image(str(png_path), width=1500, height=620, scale=2, engine="kaleido")
fig.write_html(str(html_path), include_plotlyjs="cdn")
