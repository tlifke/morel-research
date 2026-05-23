from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / ".claude/skills/morel-branding"))
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402

GRADED_DIR = ROOT / "studies/001-tool-calibration/results-correctness/gemma3_4b-it-qat"

TOOLS = [
    ("calculator", "calculator", "007_a4_calculator_graded.jsonl"),
    ("unit_convert", "unit_convert", "007_a4_unit_convert_graded.jsonl"),
    ("datetime_now", "datetime_now", "007_a4_datetime_now_graded.jsonl"),
]


def _load(path: Path):
    cells = defaultdict(int)
    excluded = 0
    for line in path.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        if r["grade"]["grade_status"] != "graded":
            excluded += 1
            continue
        correct = bool(r["grade"]["correct"])
        cal_ok = bool(r["calibration_success"])
        cells[(correct, cal_ok)] += 1
    total = sum(cells.values())
    return cells, total, excluded


def main() -> None:
    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=[label for _, label, _ in TOOLS],
        horizontal_spacing=0.08,
    )

    color_correct = MOREL_COLORS["forest_green"]
    color_wrong = MOREL_COLORS["error_red"]

    for i, (tool, _, fname) in enumerate(TOOLS, start=1):
        cells, total, excluded = _load(GRADED_DIR / fname)
        cc = cells[(True, True)]
        cf = cells[(True, False)]
        wc = cells[(False, True)]
        wf = cells[(False, False)]
        correctness = (cc + cf) / total if total else 0.0
        calibration = (cc + wc) / total if total else 0.0

        z = [
            [cc / total, cf / total],
            [wc / total, wf / total],
        ]
        labels = [
            [f"<b>{cc}</b><br>{100*cc/total:.0f}%", f"<b>{cf}</b><br>{100*cf/total:.0f}%"],
            [f"<b>{wc}</b><br>{100*wc/total:.0f}%", f"<b>{wf}</b><br>{100*wf/total:.0f}%"],
        ]
        hovers = [
            [
                f"correct ✓ · calibration ✓<br>{cc} ({100*cc/total:.1f}%)",
                f"correct ✓ · calibration ✗<br>{cf} ({100*cf/total:.1f}%)",
            ],
            [
                f"correct ✗ · calibration ✓<br>{wc} ({100*wc/total:.1f}%)",
                f"correct ✗ · calibration ✗<br>{wf} ({100*wf/total:.1f}%)",
            ],
        ]

        fig.add_trace(go.Heatmap(
            z=z,
            x=["calibration ✓", "calibration ✗"],
            y=["correct ✓", "correct ✗"],
            colorscale=[
                [0.0, MOREL_COLORS["off_white"]],
                [1.0, MOREL_COLORS["terracotta"]],
            ],
            zmin=0, zmax=1,
            text=labels, texttemplate="%{text}",
            textfont=dict(size=13, color=MOREL_COLORS["dark_earth"]),
            hovertext=hovers, hoverinfo="text",
            showscale=False,
        ), row=1, col=i)

        xref = "x domain" if i == 1 else f"x{i} domain"
        yref = "y domain" if i == 1 else f"y{i} domain"
        fig.add_annotation(
            text=f"n={total}  ·  correctness {correctness:.0%}  ·  calibration {calibration:.0%}"
                 + (f"  (excl. {excluded} ungradable)" if excluded else ""),
            x=0.5, xref=xref, y=-0.30, yref=yref,
            showarrow=False, font=dict(size=11, color=MOREL_COLORS["muted_text"]),
        )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=480, width=1180,
        margin=dict(l=80, r=40, t=170, b=140),
    )

    apply_morel_template(
        fig,
        title="Answer correctness vs calibration success — Gemma 3 4B IT",
        subtitle="Three deterministically-graded tools. "
                 "Top-right cell = correct answer despite calibration failure; "
                 "bottom-left = calibration ✓ but wrong answer (bad tool args, or tool call without prose answer).",
        attribution="studies/001 inv 007 · A4 bulk neutral baseline, temp=1.0, n=10/record · 2026-05-12",
    )

    for ext in ("png", "html", "pdf"):
        path = OUT / f"correctness_vs_calibration_heatmap.{ext}"
        if ext == "html":
            fig.write_html(path)
        else:
            fig.write_image(path, scale=2)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
