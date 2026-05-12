"""Histogram of curator-prediction miscalibration deltas.

x = (empirical bucket index) − (Opus's predicted bucket index)
y = count of records

Buckets: trivial(0), easy(1), medium(2), hard(3), extreme(4).
Δ = 0 → curator calibrated. Δ > 0 → empirical *harder* than
predicted (curator underestimated). Δ < 0 → empirical *easier*
(curator overestimated).

Grouped bars per model. The skew direction is the headline.

Output: figures/prediction_miscalibration_histogram.{html,png}.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent.parent.parent
SEEDS_PATH = STUDY_ROOT / "seeds.jsonl"
RESULTS_ROOT = STUDY_ROOT / "results"

sys.path.insert(0, str(STUDY_ROOT))
from harness.parser import classify_trial  # noqa: E402

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
    rows = [json.loads(l) for l in (RESULTS_ROOT / _safe(model) / f"006_C_neutral_temp1_{DATE}.jsonl").read_text().splitlines() if l]
    by = defaultdict(list)
    for r in rows:
        ok, _ = classify_trial({"tool_target": r["tool_target"], "expected_tool_call": r["expected_tool_call"]}, r.get("output") or r.get("output_preview", ""))
        by[r["record_id"]].append(ok)
    return {k: sum(v)/len(v) for k, v in by.items()}


def _deltas(curator: dict[str, str], sr_map: dict[str, float]) -> dict[int, int]:
    counts = defaultdict(int)
    for rid, sr in sr_map.items():
        cur = curator.get(rid)
        if cur not in BUCKET_IDX:
            continue
        delta = BUCKET_IDX[_bucket_of(sr)] - BUCKET_IDX[cur]
        counts[delta] += 1
    return counts


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    curator = {s["id"]: s["difficulty_label"]["value"] for s in seeds}

    sr_4b = _per_record("gemma3:4b-it-qat")
    sr_12b = _per_record("gemma3:12b-it-qat")

    d_4b = _deltas(curator, sr_4b)
    d_12b = _deltas(curator, sr_12b)

    range_min = min(min(d_4b), min(d_12b))
    range_max = max(max(d_4b), max(d_12b))
    x_vals = list(range(range_min, range_max + 1))

    fig = go.Figure()
    palette = {"Gemma 3 4B IT": "#5B9BD5", "Gemma 3 12B IT": "#2E5984"}
    for label, deltas in [("Gemma 3 4B IT", d_4b), ("Gemma 3 12B IT", d_12b)]:
        ys = [deltas.get(d, 0) for d in x_vals]
        fig.add_trace(go.Bar(
            name=label, x=x_vals, y=ys,
            marker_color=palette[label],
            text=[str(y) if y else "" for y in ys],
            textposition="outside",
        ))

    # Zero-line annotation
    fig.add_shape(type="line",
                  x0=-0.5, x1=-0.5, y0=0, y1=max(max(d_4b.values()), max(d_12b.values())) + 2,
                  line=dict(color="rgba(0,0,0,0)", width=0))

    fig.update_layout(
        title=dict(
            text=(
                "Curator miscalibration: how far off were Opus 4.7's predictions?<br>"
                "<sub>Δ = empirical bucket − curator-predicted bucket. "
                "Δ&lt;0: Opus overestimated difficulty; Δ&gt;0: Opus underestimated; Δ=0: calibrated.</sub>"
            ),
            y=0.97, x=0.02, xanchor="left", yanchor="top",
        ),
        xaxis=dict(
            title="Δ (empirical − predicted), in bucket-band units",
            tickmode="array",
            tickvals=x_vals,
            ticktext=[f"{v:+d}" if v != 0 else "0 (calibrated)" for v in x_vals],
        ),
        yaxis=dict(title="record count"),
        barmode="group",
        template="plotly_white",
        width=880,
        height=480,
        margin=dict(l=70, r=30, t=110, b=70),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )

    # Highlight the zero column with a subtle vertical band
    fig.add_shape(type="rect",
                  x0=-0.5, x1=0.5, y0=0, y1=max(d_4b.get(0, 0), d_12b.get(0, 0)) + 2,
                  line=dict(width=0),
                  fillcolor="rgba(80,160,80,0.06)",
                  layer="below")

    out_html = HERE / "prediction_miscalibration_histogram.html"
    out_png = HERE / "prediction_miscalibration_histogram.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
