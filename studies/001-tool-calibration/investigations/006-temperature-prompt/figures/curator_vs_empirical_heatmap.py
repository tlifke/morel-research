"""F4 — Curator vs empirical difficulty confusion matrix (heatmap).

For each model, a 5×5 grid where:
  - rows = curator-assigned `difficulty_label.value` (trivial..extreme)
  - cols = empirical bucket derived from Cell C success_rate via the
    methodology thresholds (sr < 0.05 → extreme; 0.05-0.30 → hard;
    0.30-0.70 → medium; 0.70-0.95 → easy; ≥ 0.95 → trivial)
  - cells = number of records at that (curator, empirical) intersection

If the axes were predictive, dots would sit on the diagonal. F4 shows
how badly they deviate.

Output: figures/curator_vs_empirical_heatmap.{html,png}.
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
SEEDS_PATH = STUDY_ROOT / "seeds.jsonl"
RESULTS_ROOT = STUDY_ROOT / "results"
REPO_ROOT = Path(__file__).resolve().parents[5]

sys.path.insert(0, str(STUDY_ROOT))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "skills" / "morel-branding"))
from harness.parser import classify_trial  # noqa: E402
from branding import apply_morel_template, MOREL_COLORS, MOREL_SEQUENTIAL_SCALE  # noqa: E402

DATE = "2026-05-12"
BUCKETS = ["trivial", "easy", "medium", "hard", "extreme"]


def _bucket_of(sr: float) -> str:
    if sr < 0.05:
        return "extreme"
    if sr < 0.30:
        return "hard"
    if sr < 0.70:
        return "medium"
    if sr < 0.95:
        return "easy"
    return "trivial"


def _safe(m: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", m)


def _load_cellC_per_record(model: str) -> dict[str, float]:
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


def main() -> None:
    seeds = [json.loads(l) for l in SEEDS_PATH.read_text().splitlines() if l]
    curator_of = {s["id"]: s["difficulty_label"]["value"] for s in seeds}

    sr_4b = _load_cellC_per_record("gemma3:4b-it-qat")
    sr_12b = _load_cellC_per_record("gemma3:12b-it-qat")

    def matrix(sr_map: dict[str, float]) -> tuple[list[list[int]], list[list[str]]]:
        """Returns (counts, hover_text) as 5×5 grids (rows=curator, cols=empirical)."""
        counts = [[0] * 5 for _ in range(5)]
        records: dict[tuple[str, str], list[str]] = defaultdict(list)
        for rid, sr in sr_map.items():
            cur = curator_of.get(rid)
            if cur not in BUCKETS:
                continue
            emp = _bucket_of(sr)
            i = BUCKETS.index(cur)
            j = BUCKETS.index(emp)
            counts[i][j] += 1
            records[(cur, emp)].append(f"  {rid.rsplit('-', 1)[0]} (sr={sr:.0%})")
        hover = [[None] * 5 for _ in range(5)]
        for i, cur in enumerate(BUCKETS):
            for j, emp in enumerate(BUCKETS):
                items = records.get((cur, emp), [])
                hover[i][j] = (
                    f"<b>curator={cur} · empirical={emp}</b><br>"
                    f"n records = {counts[i][j]}<br>"
                    + ("<br>".join(items) if items else "(none)")
                )
        return counts, hover

    c4, h4 = matrix(sr_4b)
    c12, h12 = matrix(sr_12b)

    fig = make_subplots(rows=1, cols=2,
                        subplot_titles=("Gemma 3 4B IT", "Gemma 3 12B IT"),
                        horizontal_spacing=0.15)

    for idx, (counts, hover, cmap) in enumerate(
        [(c4, h4, MOREL_SEQUENTIAL_SCALE), (c12, h12, MOREL_SEQUENTIAL_SCALE)], start=1
    ):
        # text for cell labels
        text = [[str(v) if v > 0 else "" for v in row] for row in counts]
        fig.add_trace(go.Heatmap(
            z=counts,
            x=BUCKETS,
            y=BUCKETS,
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=14, color=MOREL_COLORS["dark_earth"]),
            colorscale=cmap,
            zmin=0,
            showscale=(idx == 2),
            hovertext=hover,
            hovertemplate="%{hovertext}<extra></extra>",
            xgap=2, ygap=2,
        ), row=1, col=idx)

    fig.update_layout(
        width=1080,
        height=520,
    )
    for ax in ("xaxis", "xaxis2"):
        fig.update_layout(**{ax: dict(title="empirical bucket")})
    for ax in ("yaxis", "yaxis2"):
        fig.update_layout(**{ax: dict(title="curator bucket", autorange="reversed")})
    apply_morel_template(
        fig,
        title="Curator-assigned vs. empirical difficulty (Cell C, n=10)",
        subtitle=(
            "Rows = curator bucket. Cols = empirical bucket from Cell C success_rate. "
            "Empirical bucketing is model-relative — sr→bucket thresholds are absolute but the "
            "underlying success rate depends on the model."
        ),
        attribution="studies/001-tool-calibration / inv 006",
    )

    out_html = HERE / "curator_vs_empirical_heatmap.html"
    out_png = HERE / "curator_vs_empirical_heatmap.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
