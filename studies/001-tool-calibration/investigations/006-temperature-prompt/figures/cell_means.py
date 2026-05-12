"""F1 — 2x2 cell means bar chart for the 006 4B vs 12B comparison.

Two grouped bar charts side by side (4B IT and 12B IT), each
showing the 4 cells (neutral × directive × temp=0 × temp=1.0)
mean success_rate.

Reads from results/<model>/006_*_{2026-05-12}.jsonl. Rescores from
raw output to handle parser-evolution rows.

Output: figures/cell_means.{html,png}.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
INVESTIGATION_ROOT = HERE.parent
STUDY_ROOT = INVESTIGATION_ROOT.parent.parent
RESULTS_ROOT = STUDY_ROOT / "results"
REPO_ROOT = Path(__file__).resolve().parents[5]

sys.path.insert(0, str(STUDY_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))
from harness.parser import classify_trial  # noqa: E402
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402


CELLS = {
    "A": ("006_A_neutral_temp0", "neutral", 0.0),
    "B": ("006_B_directive_temp0", "directive", 0.0),
    "C": ("006_C_neutral_temp1", "neutral", 1.0),
    "D": ("006_D_directive_temp1", "directive", 1.0),
}
DATE = "2026-05-12"
MODELS = [
    ("gemma3:4b-it-qat", "Gemma 3 4B IT"),
    ("gemma3:12b-it-qat", "Gemma 3 12B IT"),
]


def _safe(model: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", model)


def _load_cell(model: str, tag: str) -> list[dict]:
    path = RESULTS_ROOT / _safe(model) / f"{tag}_{DATE}.jsonl"
    rows = [json.loads(l) for l in path.read_text().splitlines() if l]
    out = []
    for r in rows:
        ok, err = classify_trial(
            {"tool_target": r["tool_target"],
             "expected_tool_call": r["expected_tool_call"]},
            r.get("output") or r.get("output_preview", ""),
        )
        out.append({**r, "success": ok, "error_type": err})
    return out


def _cell_mean(rows: list[dict]) -> float:
    by_rid: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by_rid[r["record_id"]].append(r["success"])
    per_record_sr = [sum(v) / len(v) for v in by_rid.values()]
    return sum(per_record_sr) / len(per_record_sr) if per_record_sr else 0.0


def main() -> None:
    cell_means: dict[tuple[str, str], float] = {}
    for model, _label in MODELS:
        for cell_key, (tag, _ps, _tmp) in CELLS.items():
            cell_means[(model, cell_key)] = _cell_mean(_load_cell(model, tag))

    # 4 condition labels along x
    condition_labels = [
        "neutral · temp=0",
        "directive · temp=0",
        "neutral · temp=1.0",
        "directive · temp=1.0",
    ]
    cell_order = ["A", "B", "C", "D"]

    fig = go.Figure()
    palette = {
        "Gemma 3 4B IT": MOREL_COLORS["terracotta_light"],
        "Gemma 3 12B IT": MOREL_COLORS["terracotta_dark"],
    }
    for model, label in MODELS:
        vals = [cell_means[(model, k)] for k in cell_order]
        fig.add_trace(
            go.Bar(
                name=label,
                x=condition_labels,
                y=vals,
                text=[f"{v:.1%}" for v in vals],
                textposition="outside",
                marker_color=palette[label],
            )
        )
    fig.update_layout(
        xaxis_title="condition (prompt-set × temperature)",
        yaxis_title="mean success rate across 36 records",
        yaxis_tickformat=".0%",
        yaxis_range=[0, 1.05],
        barmode="group",
        width=900,
        height=520,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    apply_morel_template(
        fig,
        title="2×2 cell means — success rate, 4B IT vs 12B IT",
        attribution="studies/001-tool-calibration / inv 006",
    )

    out_html = HERE / "cell_means.html"
    out_png = HERE / "cell_means.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
