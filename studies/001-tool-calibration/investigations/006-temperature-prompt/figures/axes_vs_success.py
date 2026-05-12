"""F3 — Calibration curve: curator-assigned difficulty vs empirical success rate.

x = curator-assigned difficulty bucket (trivial / easy / medium /
hard / extreme), from `difficulty_label.value` in seeds.jsonl
y = empirical success rate (Cell C — neutral, temp=1.0, n=10)

One line per model, faceted into a single combined plot with
markers per (model, difficulty-bucket, tool). Bubble size = number
of records in that (tool, difficulty) cell.

Interpretation: a monotonically *decreasing* curve from trivial
to extreme means the axes predict difficulty (easier records →
higher success rate). Flat or non-monotonic suggests the axis
labels don't carry information about model behavior.

Output: figures/axes_vs_success.{html,png}.
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


def _safe(m: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", m)


def _load_cellC(model: str) -> dict[str, float]:
    path = RESULTS_ROOT / _safe(model) / f"006_C_neutral_temp1_{DATE}.jsonl"
    rows = [json.loads(l) for l in path.read_text().splitlines() if l]
    by: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        ok, _ = classify_trial(
            {"tool_target": r["tool_target"], "expected_tool_call": r["expected_tool_call"]},
            r.get("output") or r.get("output_preview", ""),
        )
        by[r["record_id"]].append(ok)
    return {k: sum(v) / len(v) for k, v in by.items()}


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    bucket_of = {s["id"]: s["difficulty_label"]["value"] for s in seeds}
    tool_of = {s["id"]: s["tool_target"] for s in seeds}

    sr_4b = _load_cellC("gemma3:4b-it-qat")
    sr_12b = _load_cellC("gemma3:12b-it-qat")

    # Aggregate by bucket per model
    def agg(sr_map: dict[str, float]) -> dict[str, list[float]]:
        out = {b: [] for b in BUCKETS}
        for rid, sr in sr_map.items():
            b = bucket_of.get(rid)
            if b in out:
                out[b].append(sr)
        return out

    by_bucket_4b = agg(sr_4b)
    by_bucket_12b = agg(sr_12b)

    fig = go.Figure()

    palette = {"Gemma 3 4B IT": "#5B9BD5", "Gemma 3 12B IT": "#2E5984"}
    for model_label, by_bucket in [
        ("Gemma 3 4B IT", by_bucket_4b),
        ("Gemma 3 12B IT", by_bucket_12b),
    ]:
        means = []
        sizes = []
        hover = []
        for b in BUCKETS:
            vals = by_bucket[b]
            if vals:
                means.append(sum(vals) / len(vals))
                sizes.append(max(8, 5 + 2 * len(vals)))
                hover.append(
                    f"<b>{model_label} · {b}</b><br>"
                    f"mean: {sum(vals)/len(vals):.1%}<br>"
                    f"n records: {len(vals)}<br>"
                    f"individual: " + ", ".join(f"{v:.0%}" for v in sorted(vals))
                )
            else:
                means.append(None)
                sizes.append(8)
                hover.append(f"<b>{model_label} · {b}</b><br>no records")
        fig.add_trace(go.Scatter(
            x=BUCKETS,
            y=means,
            mode="lines+markers",
            name=model_label,
            line=dict(color=palette[model_label], width=2),
            marker=dict(size=sizes, color=palette[model_label],
                        line=dict(color="white", width=1)),
            text=hover,
            hovertemplate="%{text}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(
            text=(
                "Curator-assigned difficulty vs. empirical success<br>"
                "<sub>Cell C — neutral prompts, temp=1.0, n=10. Marker size ∝ records in bucket. "
                "Monotonic decrease = axes predict difficulty.</sub>"
            ),
            y=0.96, x=0.02, xanchor="left", yanchor="top",
        ),
        xaxis_title="curator-assigned difficulty_label.value",
        yaxis_title="empirical success rate (Cell C)",
        yaxis_tickformat=".0%",
        yaxis_range=[0, 1.05],
        template="plotly_white",
        width=860,
        height=560,
        margin=dict(l=70, r=200, t=110, b=70),
        legend=dict(yanchor="middle", y=0.5, xanchor="left", x=1.02,
                    bgcolor="rgba(255,255,255,0.85)",
                    bordercolor="lightgray", borderwidth=1),
    )

    out_html = HERE / "axes_vs_success.html"
    out_png = HERE / "axes_vs_success.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
