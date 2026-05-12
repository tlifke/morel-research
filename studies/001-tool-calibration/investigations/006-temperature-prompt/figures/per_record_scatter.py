"""F2 — Per-record 4B vs 12B scatter at temp=1.0.

x = 4B success rate (Cell C neutral / Cell D directive)
y = 12B success rate (Cell C neutral / Cell D directive)

Two traces: neutral (light) and directive (dark). One point per
record per condition. Diagonal y=x reference shows scaling neutrality.
Points up and to the left of the diagonal: 12B scaled better than
4B. Color-set separation: prompt-engineering effect at that record.

Hover shows record_id and per-cell success rates.

Output: figures/per_record_scatter.{html,png}.
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
sys.path.insert(0, str(HERE))
from harness.parser import classify_trial  # noqa: E402
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402
from corpus_config import select_corpus, out_dir  # noqa: E402
CORPUS = select_corpus()

DATE = "2026-05-12"
MODELS = ["gemma3:4b-it-qat", "gemma3:12b-it-qat"]


def _safe(m: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9._-]", "_", m)


def _load(model: str, tag: str) -> list[dict]:
    path = RESULTS_ROOT / _safe(model) / f"{tag}_{DATE}.jsonl"
    if not path.exists():
        return []
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
    """Compact record label for hover. Drop trailing shortuuid."""
    parts = rid.rsplit("-", 1)
    return parts[0] if len(parts) == 2 and len(parts[1]) == 8 else rid


def main() -> None:
    # Load Cell C and Cell D for each model.
    data = {
        ("4B", "neutral"): _per_record(_load("gemma3:4b-it-qat", "006_C_neutral_temp1")),
        ("4B", "directive"): _per_record(_load("gemma3:4b-it-qat", "006_D_directive_temp1")),
        ("12B", "neutral"): _per_record(_load("gemma3:12b-it-qat", "006_C_neutral_temp1")),
        ("12B", "directive"): _per_record(_load("gemma3:12b-it-qat", "006_D_directive_temp1")),
    }

    all_rids = sorted(set().union(*(d.keys() for d in data.values())))

    fig = go.Figure()

    # Reference diagonal
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode="lines",
        line=dict(color=MOREL_COLORS["cream_dark"], dash="dash", width=1),
        showlegend=False,
        hoverinfo="skip",
    ))

    # Add a small jitter so dots that exactly overlap (e.g. both at
    # 1.0 or both at 0.0) are visible. Use deterministic jitter so
    # the same record sits at the same coordinate across re-renders.
    import hashlib
    def _jitter(rid: str, axis: str) -> float:
        h = int(hashlib.sha256(f"{rid}|{axis}".encode()).hexdigest()[:8], 16)
        return (h % 100) / 100 * 0.04 - 0.02   # ± 0.02

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
            marker=dict(size=10, color=color, opacity=0.85,
                        line=dict(color="white", width=1)),
            text=texts,
            hovertemplate="%{text}<extra></extra>",
        ))

    fig.update_layout(
        xaxis_title="4B IT success rate (n=10)",
        yaxis_title="12B IT success rate (n=10)",
        xaxis=dict(range=[-0.05, 1.08], tickformat=".0%"),
        yaxis=dict(range=[-0.05, 1.08], tickformat=".0%"),
        width=720,
        height=760,
        legend=dict(title="prompt set", orientation="v",
                    yanchor="bottom", y=0.02, xanchor="right", x=0.98),
    )
    apply_morel_template(
        fig,
        title="Per-record success: 4B IT vs 12B IT (temp=1.0)",
        subtitle="each dot = one of 36 records; up/left of dashed line = scaling improvement",
        attribution="studies/001-tool-calibration / inv 006",
    )

    out_html = out_dir(HERE) / "per_record_scatter.html"
    out_png = out_dir(HERE) / "per_record_scatter.png"
    fig.write_html(out_html)
    fig.write_image(out_png, engine="kaleido", scale=2)
    print(f"wrote {out_html.relative_to(STUDY_ROOT.parent.parent)}")
    print(f"wrote {out_png.relative_to(STUDY_ROOT.parent.parent)}")


if __name__ == "__main__":
    main()
