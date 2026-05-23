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
from harness.parser import classify_trial, parse_tool_calls, classify_no_tool_behavior  # noqa: E402
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
    ("success", "success", MOREL_COLORS["forest_green"]),
    ("wrong_tool", "wrong tool", MOREL_COLORS["mustard"]),
    ("under_call_clarify", "under-call · clarifying question", MOREL_COLORS["slate_blue"]),
    ("under_call_refusal", "under-call · refusal", MOREL_COLORS["muted_text"]),
    ("under_call_direct", "under-call · direct answer", MOREL_COLORS["error_red"]),
    ("over_call", "over-call (unwarranted tool)", MOREL_COLORS["terracotta"]),
]


def _bucket(seed: dict, output: str) -> str:
    ok, err = classify_trial(seed, output)
    if ok:
        return "success"
    if err == "over_call":
        return "over_call"
    if err == "wrong_tool":
        return "wrong_tool"
    sub = classify_no_tool_behavior(output)
    if sub == "clarifying_question":
        return "under_call_clarify"
    if sub == "refusal":
        return "under_call_refusal"
    return "under_call_direct"


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
        per_tool[tool][_bucket(seed, out)] += 1
        n_per_tool[tool] += 1

    order = sorted(per_tool, key=lambda t: per_tool[t]["success"] / n_per_tool[t], reverse=True)
    y_labels = [TOOL_LABEL[t] for t in order]

    fig = go.Figure()
    for key, label, color in CATEGORIES:
        xs = [per_tool[t][key] / n_per_tool[t] for t in order]
        counts = [per_tool[t][key] for t in order]
        hovers = [
            f"{TOOL_LABEL[t]}<br>{label}<br>{counts[i]}/{n_per_tool[t]} = {xs[i]:.1%}"
            for i, t in enumerate(order)
        ]
        fig.add_trace(go.Bar(
            x=xs, y=y_labels, orientation="h",
            name=label, marker_color=color,
            hovertext=hovers, hoverinfo="text",
        ))

    counts_text = [f"   n={n_per_tool[t]}" for t in order]
    fig.add_trace(go.Scatter(
        x=[1.005] * len(order), y=y_labels,
        text=counts_text, mode="text", textposition="middle right",
        textfont=dict(size=11, color=MOREL_COLORS["muted_text"]),
        showlegend=False, hoverinfo="skip",
    ))

    fig.update_xaxes(range=[0, 1.12], title_text="Share of trials", tickformat=".0%")
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
        title="Failure breakdown by tool — Gemma 3 4B IT (neutral baseline)",
        subtitle="Under-call split into clarifying-question / refusal / direct-answer using the refined parser. "
                 "Under-call·direct is the worst class — silent confabulation.",
        attribution="studies/001 inv 007 · A4 bulk neutral baseline, temp=1.0, n=10/record · 2026-05-12",
    )

    for ext in ("png", "html", "pdf"):
        path = OUT / f"failure_breakdown_by_tool.{ext}"
        if ext == "html":
            fig.write_html(path)
        else:
            fig.write_image(path, scale=2)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
