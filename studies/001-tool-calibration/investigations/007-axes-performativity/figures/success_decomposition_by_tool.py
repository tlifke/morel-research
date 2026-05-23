from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "studies/001-tool-calibration"))
sys.path.insert(0, str(ROOT / ".claude/skills/morel-branding"))
from harness.parser import classify_trial, classify_no_tool_behavior  # noqa: E402
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402

A4_4B = ROOT / "studies/001-tool-calibration/results/gemma3_4b-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl"
SEEDS = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "studies/001-tool-calibration/bulk_seeds.jsonl").read_text().splitlines() if l}

TOOL_LABEL = {
    "calculator": "calculator",
    "python_execute": "python_execute",
    "datetime_now": "datetime_now",
    "unit_convert": "unit_convert",
    "general_knowledge_lookup": "gen_knowledge_lookup",
    "user_knowledge_lookup": "user_knowledge_lookup",
}

CATEGORIES = [
    ("success_tool_called", "tool warranted → called the right tool", MOREL_COLORS["forest_green"]),
    ("success_direct", "tool not warranted → direct answer", MOREL_COLORS["green_light"]),
    ("success_clarify", "tool not warranted → clarifying question", MOREL_COLORS["slate_blue"]),
    ("success_refusal", "tool not warranted → refusal", MOREL_COLORS["muted_text"]),
]


def _bucket(seed: dict, output: str) -> str | None:
    ok, _ = classify_trial(seed, output)
    if not ok:
        return None
    if seed["expected_tool_call"]:
        return "success_tool_called"
    sub = classify_no_tool_behavior(output)
    if sub == "clarifying_question":
        return "success_clarify"
    if sub == "refusal":
        return "success_refusal"
    return "success_direct"


def main() -> None:
    per_tool: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    n_per_tool: dict[str, int] = defaultdict(int)
    for line in A4_4B.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        seed = SEEDS.get(r["record_id"])
        if seed is None:
            continue
        tool = seed["tool_target"]
        if tool is None:
            continue
        out = r.get("output") or r.get("output_preview", "")
        bucket = _bucket(seed, out)
        if bucket is None:
            continue
        per_tool[tool][bucket] += 1
        n_per_tool[tool] += 1

    order = sorted(per_tool, key=lambda t: n_per_tool[t], reverse=True)
    order = ["calculator", "python_execute", "general_knowledge_lookup",
             "unit_convert", "user_knowledge_lookup", "datetime_now"]
    y_labels = [TOOL_LABEL[t] for t in order]

    fig = go.Figure()
    for key, label, color in CATEGORIES:
        counts = [per_tool[t][key] for t in order]
        xs = counts
        hovers = [
            f"{TOOL_LABEL[t]}<br>{label}<br>n={counts[i]}"
            for i, t in enumerate(order)
        ]
        fig.add_trace(go.Bar(
            x=xs, y=y_labels, orientation="h",
            name=label, marker_color=color,
            hovertext=hovers, hoverinfo="text",
        ))

    fig.update_xaxes(title_text="Success trials (counts)")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        barmode="stack",
        height=520, width=1080,
        margin=dict(l=180, r=80, t=170, b=110),
        legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="left", x=0,
                    font=dict(size=11)),
    )

    apply_morel_template(
        fig,
        title="Success decomposition by tool — Gemma 3 4B IT (neutral baseline)",
        subtitle='"Success" hides four behaviors. For warranted records (left green) the right tool was called. '
                 'For unwarranted records, the model correctly didn\'t call a tool — but via direct answer, '
                 'clarifying question, or refusal. Direct-answer correctness still ungraded.',
        attribution="studies/001 inv 007 · A4 bulk neutral baseline, temp=1.0, n=10/record · 2026-05-12",
    )

    for ext in ("png", "html", "pdf"):
        path = OUT / f"success_decomposition_by_tool.{ext}"
        if ext == "html":
            fig.write_html(path)
        else:
            fig.write_image(path, scale=2)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
