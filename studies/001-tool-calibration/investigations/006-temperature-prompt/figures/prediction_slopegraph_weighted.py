"""Weighted slopegraph: one line per (predicted, empirical) bucket pair.

Companion to prediction_slopegraph.py. Instead of drawing one line per
record (cluttered at bulk n=366), each transition class (predicted bucket
→ empirical bucket) is collapsed to a single line whose stroke width is
proportional to the % of records that follow it.

Output: figures/{a1_seed_n36|a3_bulk}/prediction_slopegraph_weighted.{html,png}.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent.parent.parent
RESULTS_ROOT = STUDY_ROOT / "results"
REPO_ROOT = Path(__file__).resolve().parents[5]

sys.path.insert(0, str(STUDY_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))
sys.path.insert(0, str(HERE))
from harness.parser import classify_trial  # noqa: E402
from branding import apply_morel_template, MOREL_COLORS, horizontal_legend  # noqa: E402
from corpus_config import select_corpus, out_dir  # noqa: E402

CORPUS = select_corpus()
SEEDS_PATH = STUDY_ROOT / CORPUS.seeds_filename

DATE = "2026-05-12"
BUCKETS = ["trivial", "easy", "medium", "hard", "extreme"]
BUCKET_IDX = {b: i for i, b in enumerate(BUCKETS)}

# Stroke width range for the weighted lines (px at scale=1; scale=2 in
# fig.write_image doubles them). Min keeps very small fractions visible;
# max keeps the heaviest transitions from dominating the canvas.
MIN_W, MAX_W = 1.0, 14.0


def _bucket_of(sr: float) -> str:
    if sr < 0.05: return "extreme"
    if sr < 0.30: return "hard"
    if sr < 0.70: return "medium"
    if sr < 0.95: return "easy"
    return "trivial"


def _safe(m: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", m)


def _per_record(model: str) -> dict[str, float]:
    path = RESULTS_ROOT / _safe(model) / CORPUS.results_filename_fmt.format(date=DATE)
    rows = [json.loads(l) for l in path.read_text().splitlines() if l]
    by = defaultdict(list)
    for r in rows:
        ok, _ = classify_trial(
            {"tool_target": r["tool_target"], "expected_tool_call": r["expected_tool_call"]},
            r.get("output") or r.get("output_preview", ""),
        )
        by[r["record_id"]].append(ok)
    return {k: sum(v) / len(v) for k, v in by.items()}


CATEGORY = {
    "overestimated": MOREL_COLORS["slate_blue"],
    "calibrated":    MOREL_COLORS["forest_green"],
    "underestimated":MOREL_COLORS["terracotta"],
}


def _categorize(delta: int) -> str:
    if delta == 0:
        return "calibrated"
    return "overestimated" if delta < 0 else "underestimated"


def _transition_counts(curator: dict[str, str], sr_map: dict[str, float]
                       ) -> tuple[dict[tuple[str, str], int], int]:
    """Returns ({(predicted, empirical): count}, total_records)."""
    counts: dict[tuple[str, str], int] = defaultdict(int)
    total = 0
    for rid, sr in sr_map.items():
        cur = curator.get(rid)
        if cur not in BUCKET_IDX:
            continue
        emp = _bucket_of(sr)
        counts[(cur, emp)] += 1
        total += 1
    return counts, total


def _width_for(frac: float, max_frac: float) -> float:
    """Linear interpolation from MIN_W..MAX_W keyed on the heaviest line."""
    if max_frac <= 0:
        return MIN_W
    t = frac / max_frac
    return MIN_W + (MAX_W - MIN_W) * t


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    curator = {s["id"]: s["difficulty_label"]["value"] for s in seeds}

    sr_4b = _per_record("gemma3:4b-it-qat")
    sr_12b = _per_record("gemma3:12b-it-qat")

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Gemma 3 4B IT", "Gemma 3 12B IT"),
        horizontal_spacing=0.15,
    )

    # First pass: find the heaviest fraction across both models so widths
    # are comparable side-by-side.
    counts_4b, total_4b = _transition_counts(curator, sr_4b)
    counts_12b, total_12b = _transition_counts(curator, sr_12b)
    global_max_frac = max(
        max((c / total_4b for c in counts_4b.values()), default=0.0),
        max((c / total_12b for c in counts_12b.values()), default=0.0),
    )

    seen_cats: set[str] = set()  # for one legend entry per category

    for col, (counts, total) in enumerate(
        [(counts_4b, total_4b), (counts_12b, total_12b)], start=1
    ):
        # Sort so heaviest lines render on top.
        items = sorted(counts.items(), key=lambda kv: kv[1])
        for (pred, emp), n in items:
            frac = n / total
            delta = BUCKET_IDX[emp] - BUCKET_IDX[pred]
            cat = _categorize(delta)
            color = CATEGORY[cat]
            width = _width_for(frac, global_max_frac)
            show_in_legend = cat not in seen_cats and col == 1
            if show_in_legend:
                seen_cats.add(cat)
            label = {
                "overestimated": "Opus overestimated (Δ < 0)",
                "calibrated":    "Calibrated (Δ = 0)",
                "underestimated":"Opus underestimated (Δ > 0)",
            }[cat]
            # Line for the transition
            fig.add_trace(
                go.Scatter(
                    x=[0, 1],
                    y=[BUCKET_IDX[pred], BUCKET_IDX[emp]],
                    mode="lines",
                    line=dict(color=color, width=width),
                    opacity=0.75,
                    name=label,
                    legendgroup=cat,
                    showlegend=show_in_legend,
                    hovertemplate=(
                        f"<b>{pred} → {emp}</b><br>"
                        f"n records: {n}/{total} ({frac:.0%})<br>"
                        f"Δ: {delta:+d} bands<extra></extra>"
                    ),
                ),
                row=1, col=col,
            )
            # Endpoint dots so the lines have visual anchors
            fig.add_trace(
                go.Scatter(
                    x=[0, 1],
                    y=[BUCKET_IDX[pred], BUCKET_IDX[emp]],
                    mode="markers",
                    marker=dict(size=4, color=color, opacity=0.9,
                                line=dict(color="white", width=0.5)),
                    legendgroup=cat,
                    showlegend=False,
                    hoverinfo="skip",
                ),
                row=1, col=col,
            )
            # Inline % annotation on the heaviest few transitions per side.
            # Anchor near the predicted side (x=0.22) instead of midpoint so
            # labels don't pile up at the line-crossing point.
            if frac >= 0.05:
                x_anchor = 0.32
                y_anchor = BUCKET_IDX[pred] + (BUCKET_IDX[emp] - BUCKET_IDX[pred]) * x_anchor
                fig.add_annotation(
                    x=x_anchor, y=y_anchor,
                    text=f"{frac:.0%}",
                    showarrow=False,
                    font=dict(size=10, color=MOREL_COLORS["dark_earth"]),
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor=color,
                    borderwidth=0.5,
                    borderpad=2,
                    xref=f"x{col if col > 1 else ''}",
                    yref=f"y{col if col > 1 else ''}",
                )

    for col in (1, 2):
        fig.update_xaxes(
            row=1, col=col,
            tickmode="array",
            tickvals=[0, 1],
            ticktext=["Opus<br>predicted", "Gemma<br>empirical"],
            range=[-0.2, 1.2],
            showgrid=False,
        )
        fig.update_yaxes(
            row=1, col=col,
            tickmode="array",
            tickvals=list(range(5)),
            ticktext=BUCKETS,
            range=[-0.5, 4.5],
            autorange=False,
        )

    fig.update_layout(
        width=1080,
        height=640,
        legend=horizontal_legend(),
    )
    apply_morel_template(
        fig,
        title=f"Weighted slopegraph: prediction → empirical (n={CORPUS.n_records} records)",
        subtitle=(
            "One line per (predicted, empirical) bucket pair. "
            "Line width ∝ share of records on that path; labels mark paths ≥ 5%."
        ),
        attribution="studies/001-tool-calibration / inv 006",
    )
    fig.update_layout(margin=dict(l=80, r=30, t=110, b=170))
    for ann in fig.layout.annotations:
        if ann.text and "001-tool-calibration" in ann.text:
            ann.y = -0.28

    out_html = out_dir(HERE) / "prediction_slopegraph_weighted.html"
    out_png = out_dir(HERE) / "prediction_slopegraph_weighted.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
