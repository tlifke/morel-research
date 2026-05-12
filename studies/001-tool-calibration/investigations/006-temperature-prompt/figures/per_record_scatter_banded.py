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

sys.path.insert(0, str(STUDY_ROOT))
from harness.parser import classify_trial  # noqa: E402

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

    # ----- shaded region polygons -----
    # Regions are defined relative to the y=x diagonal so they don't
    # overlap the "similar" corridor. The two large diagonal-aligned
    # regions ("Scale Improves" / "Scale Hurts") are triangles cut by
    # y = x ± 0.20 lines. The four corner regions are rectangles for
    # the extreme cases (both succeed / both fail / Scale Solves /
    # Scale Breaks).
    # Layer order: shapes draw under traces in Plotly.

    # Rectangular regions: (name, x0,x1,y0,y1, color, ax,ay)
    rects = [
        ("Both fail",      -0.05, 0.20, -0.05, 0.20, "rgba(200,80,80,0.10)",   0.075, 0.075),
        ("Both succeed",    0.80, 1.05,  0.80, 1.05, "rgba(80,160,80,0.12)",   0.925, 0.925),
        ("Scale Solves",   -0.05, 0.25,  0.75, 1.05, "rgba(46,89,132,0.20)",   0.10,  0.90),
        ("Scale Breaks",    0.75, 1.05, -0.05, 0.25, "rgba(196,78,82,0.20)",   0.90,  0.10),
    ]
    for name, x0, x1, y0, y1, color, ax, ay in rects:
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1,
                      line=dict(width=0), fillcolor=color, layer="below")
        fig.add_annotation(x=ax, y=ay, text=name, showarrow=False,
                           font=dict(size=11, color="#333"),
                           bgcolor="rgba(255,255,255,0.78)", borderpad=2)

    # Triangular regions, aligned to the diagonal ±0.20 corridor.
    # Scale Improves: above y = x+0.20, between Solves corner (x≥0.25)
    # and Both-Succeed corner (x≤0.80). Triangle (0.25,0.45) →
    # (0.25,1.0) → (0.80,1.0) closed back to start; (the diagonal
    # +0.20 line passes through (0.25,0.45) and (0.80,1.00).
    fig.add_shape(type="path",
                  path="M 0.25,0.45 L 0.25,1.0 L 0.80,1.0 Z",
                  line=dict(width=0),
                  fillcolor="rgba(91,155,213,0.20)",
                  layer="below")
    fig.add_annotation(x=0.40, y=0.90, text="Scale Improves",
                       showarrow=False, font=dict(size=11, color="#333"),
                       bgcolor="rgba(255,255,255,0.78)", borderpad=2)

    # Scale Hurts: below y = x-0.20, mirror of Scale Improves.
    # Triangle (0.25,0.05) → (0.80,0.05) → (0.80,0.60) closed; the
    # diagonal -0.20 line passes through (0.25,0.05) and (0.80,0.60).
    fig.add_shape(type="path",
                  path="M 0.25,0.05 L 0.80,0.60 L 0.80,0.05 Z",
                  line=dict(width=0),
                  fillcolor="rgba(255,170,70,0.22)",
                  layer="below")
    fig.add_annotation(x=0.65, y=0.16, text="Scale Hurts",
                       showarrow=False, font=dict(size=11, color="#333"),
                       bgcolor="rgba(255,255,255,0.78)", borderpad=2)

    # Diagonal reference
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line=dict(color="gray", dash="dash", width=1),
        showlegend=False,
        hoverinfo="skip",
    ))
    # ±0.2 bands around diagonal (similar performance corridor)
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0.20, 1.20],
        mode="lines", line=dict(color="lightgray", dash="dot", width=1),
        showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=[0.20, 1.20], y=[0, 1],
        mode="lines", line=dict(color="lightgray", dash="dot", width=1),
        showlegend=False, hoverinfo="skip"))

    # ----- points -----
    import hashlib
    def _jitter(rid: str, axis: str) -> float:
        h = int(hashlib.sha256(f"{rid}|{axis}".encode()).hexdigest()[:8], 16)
        return (h % 100) / 100 * 0.04 - 0.02

    for prompt_set, color in [("neutral", "#A4C5E8"), ("directive", "#C44E52")]:
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
        title=dict(
            text=(
                "Per-record success — banded view: 4B IT vs 12B IT (temp=1.0)<br>"
                "<sub>each dot = one record. Bands carve the plane into named regions for reading."
                " The diagonal is scale-neutral; ±0.20 dotted lines mark a 'similar performance' corridor.</sub>"
            ),
            y=0.97, x=0.02, xanchor="left", yanchor="top",
        ),
        xaxis_title="4B IT success rate (n=10)",
        yaxis_title="12B IT success rate (n=10)",
        xaxis=dict(range=[-0.05, 1.08], tickformat=".0%"),
        yaxis=dict(range=[-0.05, 1.08], tickformat=".0%"),
        template="plotly_white",
        width=820,
        height=820,
        margin=dict(l=70, r=30, t=120, b=70),
        legend=dict(title="prompt set", orientation="v",
                    yanchor="bottom", y=0.02, xanchor="right", x=0.98,
                    bgcolor="rgba(255,255,255,0.9)",
                    bordercolor="lightgray", borderwidth=1),
    )

    out_html = HERE / "per_record_scatter_banded.html"
    out_png = HERE / "per_record_scatter_banded.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
