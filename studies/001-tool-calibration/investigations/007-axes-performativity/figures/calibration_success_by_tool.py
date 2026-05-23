from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
HERE.mkdir(exist_ok=True)
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "studies/001-tool-calibration"))
sys.path.insert(0, str(ROOT / ".claude/skills/morel-branding"))
from harness.parser import classify_trial  # noqa: E402
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402

A4_4B = ROOT / "studies/001-tool-calibration/results/gemma3_4b-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl"
SEEDS = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "studies/001-tool-calibration/bulk_seeds.jsonl").read_text().splitlines() if l}

TOOL_ORDER = [
    "calculator", "python_execute", "datetime_now", "unit_convert",
    "general_knowledge_lookup", "user_knowledge_lookup", "none",
]
TOOL_LABEL = {
    "calculator": "calculator",
    "python_execute": "python_execute",
    "datetime_now": "datetime_now",
    "unit_convert": "unit_convert",
    "general_knowledge_lookup": "gen_knowledge_lookup",
    "user_knowledge_lookup": "user_knowledge_lookup",
    "none": "(no tool warranted)",
}


def _ci(xs: list[int], iters: int = 5000) -> tuple[float, float, float]:
    if not xs:
        return (0.0, 0.0, 0.0)
    n = len(xs)
    rng = random.Random(0)
    pop = list(xs)
    means = []
    for _ in range(iters):
        s = sum(rng.choice(pop) for _ in range(n)) / n
        means.append(s)
    means.sort()
    return (sum(xs) / n, means[int(0.025 * iters)], means[int(0.975 * iters)])


def main() -> None:
    per_tool: dict[str, list[int]] = defaultdict(list)
    for line in A4_4B.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        seed = SEEDS.get(r["record_id"])
        if seed is None:
            continue
        tool = seed["tool_target"] or "none"
        out = r.get("output") or r.get("output_preview", "")
        ok, _ = classify_trial(seed, out)
        per_tool[tool].append(int(ok))

    rows = []
    for tool in TOOL_ORDER:
        xs = per_tool.get(tool, [])
        if not xs:
            continue
        mean, lo, hi = _ci(xs)
        rows.append((tool, mean, lo, hi, len(xs)))

    rows.sort(key=lambda r: r[1], reverse=True)

    y_labels = [TOOL_LABEL[t] for t, *_ in rows]
    means = [r[1] for r in rows]
    err_plus = [r[3] - r[1] for r in rows]
    err_minus = [r[1] - r[2] for r in rows]
    hovers = [
        f"{TOOL_LABEL[t]}<br>n={n} trials<br>success={m:.3f} [{lo:.3f}, {hi:.3f}]"
        for t, m, lo, hi, n in rows
    ]
    counts_text = [f"   n={n}" for *_, n in rows]
    counts_x = [r[3] + 0.03 for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=means, y=y_labels, orientation="h",
        marker_color=MOREL_COLORS["terracotta"],
        error_x=dict(type="data", array=err_plus, arrayminus=err_minus,
                     color=MOREL_COLORS["muted_text"], thickness=1.2, width=4),
        hovertext=hovers, hoverinfo="text",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=counts_x, y=y_labels, text=counts_text, mode="text",
        textposition="middle right",
        textfont=dict(size=11, color=MOREL_COLORS["muted_text"]),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_xaxes(range=[0, 1.15], title_text="Calibration success rate (per trial)")
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=460, width=860, margin=dict(l=180, r=80, t=130, b=110))

    overall_xs = [v for xs in per_tool.values() for v in xs]
    overall_mean, overall_lo, overall_hi = _ci(overall_xs)
    apply_morel_template(
        fig,
        title="Calibration success per tool — Gemma 3 4B IT (neutral baseline)",
        subtitle=f"Overall {overall_mean:.3f} [{overall_lo:.3f}, {overall_hi:.3f}], "
                 f"n={len(overall_xs)} trials. Success = called the warranted tool "
                 f"(or correctly didn't call one). Not answer correctness.",
        attribution="studies/001 inv 007 · A4 bulk neutral baseline, temp=1.0, n=10/record · 2026-05-12",
    )

    for ext in ("png", "html", "pdf"):
        path = OUT / f"calibration_success_by_tool.{ext}"
        if ext == "html":
            fig.write_html(path)
        else:
            fig.write_image(path, scale=2)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
