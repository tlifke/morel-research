"""Slopegraph: Opus's predicted difficulty (left) vs empirical
difficulty (right), one line per record. Facet by target model.

The shape of the slopes carries the finding. If every line is
roughly horizontal, the curator's predictions match reality. If
they cross steeply, the predictions don't.

Output: figures/prediction_slopegraph.{html,png}.
"""

from __future__ import annotations

import json
import sys
import hashlib
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
    rows = [json.loads(l) for l in (RESULTS_ROOT / _safe(model) / CORPUS.results_filename_fmt.format(date=DATE)).read_text().splitlines() if l]
    by = defaultdict(list)
    for r in rows:
        ok, _ = classify_trial({"tool_target": r["tool_target"], "expected_tool_call": r["expected_tool_call"]}, r.get("output") or r.get("output_preview", ""))
        by[r["record_id"]].append(ok)
    return {k: sum(v)/len(v) for k, v in by.items()}


def _jitter(rid: str) -> float:
    """One deterministic vertical jitter value per record. Applied
    identically to both endpoints — calibrated records (same bucket
    both sides) get perfectly flat lines; non-calibrated lines still
    spread vertically within each band."""
    h = int(hashlib.sha256(rid.encode()).hexdigest()[:8], 16)
    return (h % 100) / 100 * 0.30 - 0.15


CATEGORY = {
    "overestimated": {"color": MOREL_COLORS["slate_blue"],
                      "label": "Opus overestimated (Δ < 0)"},
    "calibrated":    {"color": MOREL_COLORS["forest_green"],
                      "label": "Calibrated (Δ = 0)"},
    "underestimated":{"color": MOREL_COLORS["terracotta"],
                      "label": "Opus underestimated (Δ > 0)"},
}


def _categorize(delta: int) -> str:
    if delta == 0:
        return "calibrated"
    return "overestimated" if delta < 0 else "underestimated"


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    curator = {s["id"]: s["difficulty_label"]["value"] for s in seeds}

    sr_4b = _per_record("gemma3:4b-it-qat")
    sr_12b = _per_record("gemma3:12b-it-qat")

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Gemma 3 4B IT", "Gemma 3 12B IT"),
                        horizontal_spacing=0.15)

    for col, (model_label, sr_map) in enumerate(
        [("Gemma 3 4B IT", sr_4b), ("Gemma 3 12B IT", sr_12b)], start=1
    ):
        # Collect points by category — one combined Scatter trace per
        # category gives us a single legend entry per group, while
        # `None`-separated segments keep individual lines distinct.
        buckets: dict[str, dict[str, list]] = {
            k: {"x": [], "y": [], "marker_x": [], "marker_y": [], "hover": []}
            for k in CATEGORY
        }
        for rid, sr in sr_map.items():
            cur = curator.get(rid)
            if cur not in BUCKET_IDX:
                continue
            j = _jitter(rid)
            y_pred = BUCKET_IDX[cur] + j
            y_emp = BUCKET_IDX[_bucket_of(sr)] + j
            delta = BUCKET_IDX[_bucket_of(sr)] - BUCKET_IDX[cur]
            cat = _categorize(delta)
            buckets[cat]["x"].extend([0, 1, None])
            buckets[cat]["y"].extend([y_pred, y_emp, None])
            buckets[cat]["marker_x"].extend([0, 1])
            buckets[cat]["marker_y"].extend([y_pred, y_emp])
            hover = (
                f"<b>{rid.rsplit('-', 1)[0]}</b><br>"
                f"Opus predicted: {cur}<br>"
                f"Empirical: {_bucket_of(sr)} (sr={sr:.0%})<br>"
                f"Δ: {delta:+d} bands"
            )
            buckets[cat]["hover"].extend([hover, hover])

        for cat, data in buckets.items():
            if not data["x"]:
                continue
            color = CATEGORY[cat]["color"]
            label = CATEGORY[cat]["label"]
            # Combined line trace — one legend entry per category, only
            # shown on the first subplot to avoid duplicates.
            fig.add_trace(
                go.Scatter(
                    x=data["x"], y=data["y"],
                    mode="lines",
                    line=dict(color=color, width=1.5),
                    opacity=0.55,
                    name=label,
                    legendgroup=cat,
                    showlegend=(col == 1),
                    hoverinfo="skip",
                ),
                row=1, col=col,
            )
            # Markers carry the hover text. Hidden from legend; share
            # legendgroup so legend toggles hide both lines and markers.
            fig.add_trace(
                go.Scatter(
                    x=data["marker_x"], y=data["marker_y"],
                    mode="markers",
                    marker=dict(size=5, color=color, opacity=0.85,
                                line=dict(color="white", width=0.5)),
                    text=data["hover"],
                    hovertemplate="%{text}<extra></extra>",
                    name=label,
                    legendgroup=cat,
                    showlegend=False,
                ),
                row=1, col=col,
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
        title="Slopegraph: Opus 4.7's predicted difficulty vs Gemma's empirical (Cell C, n=10)",
        subtitle=(
            "Each line = one record. Flat = calibrated. "
            "Down-slope = Opus overestimated; up-slope = Opus underestimated."
        ),
        attribution="studies/001-tool-calibration / inv 006",
    )
    fig.update_layout(margin=dict(l=80, r=30, t=110, b=170))
    for ann in fig.layout.annotations:
        if ann.text and "001-tool-calibration" in ann.text:
            ann.y = -0.28

    out_html = out_dir(HERE) / "prediction_slopegraph.html"
    out_png = out_dir(HERE) / "prediction_slopegraph.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
