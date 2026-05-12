"""F5 — Per-record dot plot: curator bucket × empirical bucket, color by tool.

x = curator-assigned `difficulty_label.value` (ordinal: trivial..extreme)
y = empirical success rate (continuous, Cell C — neutral, temp=1.0)
color = tool_target
shape = model (circle = 4B, diamond = 12B)

The empirical y-axis kept continuous (not bucketed) so the reader
sees the actual rate, not the band post-hoc. Bucket boundary lines
are drawn as horizontal references.

Companion to the heatmap (F4): the heatmap shows aggregate
agreement; this dot plot shows per-record disagreement and
attributes it by tool.

Output: figures/curator_vs_empirical_dots.{html,png}.
"""

from __future__ import annotations

import json
import sys
import hashlib
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

TOOL_PALETTE = {
    "calculator":               "#4C78A8",
    "python_execute":           "#F58518",
    "datetime_now":             "#54A24B",
    "unit_convert":             "#B279A2",
    "general_knowledge_lookup": "#E45756",
    "user_knowledge_lookup":    "#72B7B2",
}

# Methodology bucket boundaries on the success_rate axis.
BUCKET_LINES = [
    (0.05, "extreme | hard"),
    (0.30, "hard | medium"),
    (0.70, "medium | easy"),
    (0.95, "easy | trivial"),
]


def _safe(m: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", m)


def _load_cellC(model: str) -> dict[str, float]:
    path = RESULTS_ROOT / _safe(model) / f"006_C_neutral_temp1_{DATE}.jsonl"
    rows = [json.loads(l) for l in path.read_text().splitlines() if l]
    by: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        ok, _ = classify_trial(
            {"tool_target": r["tool_target"],
             "expected_tool_call": r["expected_tool_call"]},
            r.get("output") or r.get("output_preview", ""),
        )
        by[r["record_id"]].append(ok)
    return {k: sum(v) / len(v) for k, v in by.items()}


def _jitter(rid: str, model: str) -> float:
    """Small deterministic horizontal jitter so overlapping dots stay readable."""
    h = int(hashlib.sha256(f"{rid}|{model}".encode()).hexdigest()[:8], 16)
    return (h % 100) / 100 * 0.30 - 0.15  # ± 0.15


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    curator_of = {s["id"]: s["difficulty_label"]["value"] for s in seeds}
    tool_of = {s["id"]: s["tool_target"] for s in seeds}

    sr_4b = _load_cellC("gemma3:4b-it-qat")
    sr_12b = _load_cellC("gemma3:12b-it-qat")

    fig = go.Figure()

    # Bucket reference lines
    for y_val, label in BUCKET_LINES:
        fig.add_shape(type="line",
                      x0=-0.5, x1=4.5, y0=y_val, y1=y_val,
                      line=dict(color="lightgray", dash="dot", width=1))
        fig.add_annotation(x=4.4, y=y_val, text=label, showarrow=False,
                           xanchor="right", yanchor="bottom",
                           font=dict(size=9, color="#888"))

    for model_label, sr_map, marker_symbol in [
        ("Gemma 3 4B IT", sr_4b, "circle"),
        ("Gemma 3 12B IT", sr_12b, "diamond"),
    ]:
        # Group by tool so we can emit one trace per (tool, model)
        # with proper legendgrouping.
        for tool, color in TOOL_PALETTE.items():
            xs, ys, texts = [], [], []
            for rid, sr in sr_map.items():
                if tool_of.get(rid) != tool:
                    continue
                cur = curator_of.get(rid)
                if cur not in BUCKETS:
                    continue
                x_idx = BUCKETS.index(cur) + _jitter(rid, model_label)
                xs.append(x_idx)
                ys.append(sr)
                texts.append(
                    f"<b>{rid.rsplit('-', 1)[0]}</b><br>"
                    f"curator: {cur}<br>"
                    f"empirical sr: {sr:.0%}<br>"
                    f"tool: {tool}<br>"
                    f"model: {model_label}"
                )
            if xs:
                fig.add_trace(go.Scatter(
                    x=xs, y=ys,
                    mode="markers",
                    name=f"{tool} · {model_label}",
                    legendgroup=tool,
                    legendgrouptitle=dict(text=tool),
                    marker=dict(
                        color=color,
                        size=11 if marker_symbol == "circle" else 13,
                        symbol=marker_symbol,
                        opacity=0.85,
                        line=dict(color="white", width=1),
                    ),
                    text=texts,
                    hovertemplate="%{text}<extra></extra>",
                    showlegend=True,
                ))

    fig.update_layout(
        title=dict(
            text=(
                "Per-record curator-vs-empirical (Cell C, n=10) — color by tool, "
                "shape by model<br>"
                "<sub>x: curator-assigned bucket. y: empirical success_rate. "
                "Bucket reference lines mark methodology thresholds. "
                "Circles = 4B, diamonds = 12B.</sub>"
            ),
            y=0.97, x=0.02, xanchor="left", yanchor="top",
        ),
        xaxis=dict(
            title="curator-assigned difficulty_label.value",
            tickmode="array",
            tickvals=list(range(5)),
            ticktext=BUCKETS,
            range=[-0.5, 4.5],
        ),
        yaxis=dict(
            title="empirical success rate (Cell C)",
            range=[-0.05, 1.05],
            tickformat=".0%",
        ),
        template="plotly_white",
        width=1080,
        height=620,
        margin=dict(l=80, r=240, t=110, b=70),
        legend=dict(
            orientation="v",
            yanchor="top", y=1.0, xanchor="left", x=1.02,
            font=dict(size=10),
            grouptitlefont=dict(size=11, color="#333"),
        ),
    )

    out_html = HERE / "curator_vs_empirical_dots.html"
    out_png = HERE / "curator_vs_empirical_dots.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
