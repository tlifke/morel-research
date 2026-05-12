"""F2b — annotated version of per_record_scatter with named regions.

Same data as per_record_scatter.py, but with shaded rectangles and
labels carving the plane into seven named regions per the
reviewer's framing:

  - Both fail        : x < 0.20, y < 0.20
  - Both succeed     : x ≥ 0.80, y ≥ 0.80
  - Similar          : |y - x| < 0.20, interior
  - Scale Solves     : x < 0.30, y > 0.70 (12B near-perfect on records 4B fails)
  - Scale Improves   : 0.30 ≤ x < 0.70, y ≥ x + 0.20 (moderate 4B → big 12B)
  - Scale Hurts      : 0.30 ≤ x < 0.80, y ≤ x − 0.20 (12B underperforms 4B)
  - Scale Breaks     : x ≥ 0.70, y < 0.30 (high 4B, near-zero 12B)

Boundaries are heuristics, not statistics. The point is to label
regions for reading, not to claim a partition.

Output: figures/per_record_scatter_banded.{html,png}.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent.parent.parent
RESULTS_ROOT = STUDY_ROOT / "results"
REPO_ROOT = Path(__file__).resolve().parents[5]

sys.path.insert(0, str(STUDY_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))
from harness.parser import classify_trial  # noqa: E402
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402

DATE = "2026-05-12"


def _safe(m: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", m)


def _load(model: str, tag: str) -> list[dict]:
    path = RESULTS_ROOT / _safe(model) / f"{tag}_{DATE}.jsonl"
    rows = [json.loads(l) for l in path.read_text().splitlines() if l]
    out = []
    for r in rows:
        ok, _ = classify_trial(
            {"tool_target": r["tool_target"], "expected_tool_call": r["expected_tool_call"]},
            r.get("output") or r.get("output_preview", ""),
        )
        out.append({**r, "success": ok})
    return out


def _per_record(rows: list[dict]) -> dict[str, float]:
    by: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        by[r["record_id"]].append(r["success"])
    return {k: sum(v) / len(v) for k, v in by.items()}


def _short_label(rid: str) -> str:
    parts = rid.rsplit("-", 1)
    return parts[0] if len(parts) == 2 and len(parts[1]) == 8 else rid


def main() -> None:
    data = {
        ("4B", "neutral"): _per_record(_load("gemma3:4b-it-qat", "006_C_neutral_temp1")),
        ("4B", "directive"): _per_record(_load("gemma3:4b-it-qat", "006_D_directive_temp1")),
        ("12B", "neutral"): _per_record(_load("gemma3:12b-it-qat", "006_C_neutral_temp1")),
        ("12B", "directive"): _per_record(_load("gemma3:12b-it-qat", "006_D_directive_temp1")),
    }

    all_rids = sorted(set().union(*(d.keys() for d in data.values())))
    fig = go.Figure()

    # ----- region labels only -----
    # The dotted ±0.20 diagonal lines (added below) already mark the
    # "similar" corridor boundaries, so the named regions (Scale
    # Improves / Scale Hurts) don't need explicit shaded shapes —
    # they live in the half-planes off the diagonal. Only the four
    # corner regions stay as shaded rectangles since they pick out
    # extreme sub-regions of those half-planes.

    rects = [
        ("Both fail",      -0.05, 0.20, -0.05, 0.20, "rgba(193,105,79,0.35)",  0.075, 0.075),
        ("Both succeed",    0.80, 1.05,  0.80, 1.05, "rgba(45,80,22,0.28)",    0.925, 0.925),
        ("Scale Solves",   -0.05, 0.25,  0.75, 1.05, "rgba(107,94,94,0.18)",   0.10,  0.90),
        ("Scale Breaks",    0.75, 1.05, -0.05, 0.25, "rgba(107,94,94,0.18)",   0.90,  0.10),
    ]
    for name, x0, x1, y0, y1, color, ax, ay in rects:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(width=0), fillcolor=color, layer="below")
        fig.add_annotation(x=ax, y=ay, text=name, showarrow=False,
                           font=dict(size=11, color=MOREL_COLORS["dark_earth"]),
                           bgcolor="rgba(255,255,255,0.82)", borderpad=2)

    # Labels only for the off-diagonal half-planes — placed in
    # representative spots so the reader knows the dotted lines
    # delimit named territory.
    fig.add_annotation(x=0.42, y=0.92, text="Scale Improves",
                       showarrow=False,
                       font=dict(size=11, color=MOREL_COLORS["forest_green"]),
                       bgcolor="rgba(255,255,255,0.0)", borderpad=2)
    fig.add_annotation(x=0.65, y=0.18, text="Scale Hurts",
                       showarrow=False,
                       font=dict(size=11, color=MOREL_COLORS["terracotta_dark"]),
                       bgcolor="rgba(255,255,255,0.0)", borderpad=2)
    fig.add_annotation(x=0.55, y=0.55, text="Similar",
                       showarrow=False,
                       font=dict(size=11, color=MOREL_COLORS["muted_text"]),
                       bgcolor="rgba(255,255,255,0.0)", borderpad=2,
                       textangle=-45)

    # Diagonal reference
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line=dict(color=MOREL_COLORS["muted_text"], dash="dash", width=1),
        showlegend=False,
        hoverinfo="skip",
    ))
    # ±0.2 bands around diagonal (similar performance corridor)
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0.20, 1.20],
        mode="lines", line=dict(color=MOREL_COLORS["cream_dark"], dash="dot", width=1),
        showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=[0.20, 1.20], y=[0, 1],
        mode="lines", line=dict(color=MOREL_COLORS["cream_dark"], dash="dot", width=1),
        showlegend=False, hoverinfo="skip"))

    # ----- points -----
    import hashlib
    def _jitter(rid: str, axis: str) -> float:
        h = int(hashlib.sha256(f"{rid}|{axis}".encode()).hexdigest()[:8], 16)
        return (h % 100) / 100 * 0.04 - 0.02

    for prompt_set, color in [
        ("neutral", MOREL_COLORS["forest_green"]),
        ("directive", MOREL_COLORS["terracotta"]),
    ]:
        xs, ys, texts = [], [], []
        for rid in all_rids:
            x = data[("4B", prompt_set)].get(rid)
            y = data[("12B", prompt_set)].get(rid)
            if x is None or y is None:
                continue
            xs.append(x + _jitter(rid, "x"))
            ys.append(y + _jitter(rid, "y"))
            texts.append(
                f"<b>{_short_label(rid)}</b><br>"
                f"4B {prompt_set}: {x:.0%}<br>"
                f"12B {prompt_set}: {y:.0%}"
            )
        fig.add_trace(go.Scatter(
            x=xs, y=ys,
            mode="markers",
            name=prompt_set,
            marker=dict(size=10, color=color, opacity=0.9,
                        line=dict(color="white", width=1)),
            text=texts,
            hovertemplate="%{text}<extra></extra>",
        ))

    fig.update_layout(
        xaxis_title="4B IT success rate (n=10)",
        yaxis_title="12B IT success rate (n=10)",
        xaxis=dict(range=[-0.05, 1.08], tickformat=".0%"),
        yaxis=dict(range=[-0.05, 1.08], tickformat=".0%"),
        width=920,
        height=900,
        legend=dict(title="prompt set", orientation="h",
                    yanchor="top", y=-0.10, xanchor="center", x=0.5),
    )
    apply_morel_template(
        fig,
        title="Per-record success — banded view: 4B IT vs 12B IT (temp=1.0)",
        subtitle=(
            "each dot = one record. Diagonal is scale-neutral; "
            "±0.20 dotted lines mark a 'similar performance' corridor."
        ),
        attribution="studies/001-tool-calibration / inv 006",
    )
    fig.update_layout(margin=dict(l=80, r=40, t=110, b=180))
    for ann in fig.layout.annotations:
        if ann.text and "001-tool-calibration" in ann.text:
            ann.y = -0.17

    out_html = HERE / "per_record_scatter_banded.html"
    out_png = HERE / "per_record_scatter_banded.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
