"""Diverging dot plot of per-record miscalibration.

y-axis = each record (one row), sorted by 4B-IT Δ ascending.
x-axis = Δ (empirical − predicted bucket index), signed.

Two markers per row (circle = 4B, diamond = 12B). Records pulled
to the left of zero = Opus overestimated for that model.
Records to the right = Opus underestimated. Records exactly at
zero = calibrated.

Output: figures/prediction_miscalibration_diverging.{html,png}.
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
REPO_ROOT = Path(__file__).resolve().parents[5]

sys.path.insert(0, str(STUDY_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))
from harness.parser import classify_trial  # noqa: E402
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402

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


def _short(rid: str) -> str:
    parts = rid.rsplit("-", 1)
    return parts[0] if len(parts) == 2 and len(parts[1]) == 8 else rid


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    curator = {s["id"]: s["difficulty_label"]["value"] for s in seeds}

    sr_4b = _per_record("gemma3:4b-it-qat")
    sr_12b = _per_record("gemma3:12b-it-qat")

    rows: list[tuple[str, int, int]] = []  # (rid, delta_4b, delta_12b)
    for rid, sr in sr_4b.items():
        cur = curator.get(rid)
        if cur not in BUCKET_IDX:
            continue
        d4 = BUCKET_IDX[_bucket_of(sr)] - BUCKET_IDX[cur]
        sr12 = sr_12b.get(rid)
        d12 = BUCKET_IDX[_bucket_of(sr12)] - BUCKET_IDX[cur] if sr12 is not None else None
        rows.append((rid, d4, d12))

    # Sort by 4B delta ascending so the cleanest pattern (overestimate
    # → underestimate) reads top-to-bottom
    rows.sort(key=lambda r: (r[1], r[2] if r[2] is not None else 0))

    labels = [_short(r[0]) for r in rows]
    d4 = [r[1] for r in rows]
    d12 = [r[2] for r in rows]

    fig = go.Figure()

    # Zero line
    fig.add_shape(type="line",
                  x0=0, x1=0, y0=-1, y1=len(rows),
                  line=dict(color=MOREL_COLORS["forest_green"], width=1, dash="dash"))

    # Connecting line between 4B and 12B per record (faint)
    for i, (_, a, b) in enumerate(rows):
        if a is not None and b is not None and a != b:
            fig.add_shape(type="line",
                          x0=a, x1=b, y0=i, y1=i,
                          line=dict(color=MOREL_COLORS["cream_dark"], width=1))

    # 4B markers
    fig.add_trace(go.Scatter(
        x=d4, y=list(range(len(rows))),
        mode="markers",
        name="Gemma 3 4B IT",
        marker=dict(symbol="circle", size=11, color=MOREL_COLORS["terracotta_light"],
                    line=dict(color="white", width=1)),
        text=labels,
        hovertemplate="<b>%{text}</b><br>4B Δ: %{x:+d}<extra></extra>",
    ))

    # 12B markers
    fig.add_trace(go.Scatter(
        x=d12, y=list(range(len(rows))),
        mode="markers",
        name="Gemma 3 12B IT",
        marker=dict(symbol="diamond", size=12, color=MOREL_COLORS["terracotta_dark"],
                    line=dict(color="white", width=1)),
        text=labels,
        hovertemplate="<b>%{text}</b><br>12B Δ: %{x:+d}<extra></extra>",
    ))

    fig.update_layout(
        xaxis=dict(
            title="Δ (empirical − predicted)",
            zeroline=False,
            tickmode="array",
            tickvals=[-3, -2, -1, 0, 1, 2, 3],
            ticktext=["-3", "-2", "-1", "0", "+1", "+2", "+3"],
        ),
        yaxis=dict(
            tickmode="array",
            tickvals=list(range(len(rows))),
            ticktext=labels,
            tickfont=dict(size=9),
            autorange="reversed",
            range=[len(rows), -1],
        ),
        width=1050,
        height=max(560, 18 * len(rows) + 130),
        legend=dict(orientation="h", yanchor="bottom", y=1.01, xanchor="right", x=1),
    )
    apply_morel_template(
        fig,
        title="Per-record miscalibration: how far off was Opus 4.7's prediction?",
        subtitle=(
            "Δ = empirical − predicted, in bucket-band units. "
            "Left of zero: Opus overestimated. Right: underestimated. On the line: calibrated."
        ),
        attribution="studies/001-tool-calibration / inv 006",
    )
    fig.update_layout(margin=dict(l=380, r=30, t=100, b=70))

    out_html = HERE / "prediction_miscalibration_diverging.html"
    out_png = HERE / "prediction_miscalibration_diverging.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
