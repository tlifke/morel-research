from __future__ import annotations

import json
import random
import sys
from collections import defaultdict
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "studies/001-tool-calibration"))
sys.path.insert(0, str(ROOT / ".claude/skills/morel-branding"))
from harness.parser import classify_trial, classify_no_tool_behavior  # noqa: E402
from branding import apply_morel_template, MOREL_COLORS  # noqa: E402

SEEDS = {json.loads(l)["id"]: json.loads(l) for l in (ROOT / "studies/001-tool-calibration/bulk_seeds.jsonl").read_text().splitlines() if l}

MODELS = [
    ("Gemma 3 4B IT", ROOT / "studies/001-tool-calibration/results/gemma3_4b-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl", "gemma3_4b-it-qat"),
    ("Gemma 3 12B IT", ROOT / "studies/001-tool-calibration/results/gemma3_12b-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl", "gemma3_12b-it-qat"),
]
GRADED_ROOT = ROOT / "studies/001-tool-calibration/results-correctness"

TOOL_ORDER = ["calculator", "unit_convert", "general_knowledge_lookup", "datetime_now", "user_knowledge_lookup", "python_execute"]
TOOL_LABEL = {
    "calculator": "calculator",
    "python_execute": "python_execute",
    "datetime_now": "datetime_now",
    "unit_convert": "unit_convert",
    "general_knowledge_lookup": "gen_knowledge_lookup",
    "user_knowledge_lookup": "user_knowledge_lookup",
}


def _ci(xs, iters=4000):
    if not xs:
        return (0.0, 0.0, 0.0)
    n = len(xs)
    rng = random.Random(0)
    means = []
    for _ in range(iters):
        s = sum(rng.choice(xs) for _ in range(n)) / n
        means.append(s)
    means.sort()
    return (sum(xs) / n, means[int(0.025 * iters)], means[int(0.975 * iters)])


def _load_trials(path):
    out = []
    for line in path.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        seed = SEEDS.get(r["record_id"])
        if seed is None:
            continue
        out.append((seed, r.get("output") or r.get("output_preview", "")))
    return out


def _calibration_by_tool(trials):
    per = defaultdict(list)
    for seed, output in trials:
        tool = seed["tool_target"]
        if tool is None:
            continue
        ok, _ = classify_trial(seed, output)
        per[tool].append(int(ok))
    return per


def _failure_breakdown(trials):
    per = defaultdict(lambda: defaultdict(int))
    n_per = defaultdict(int)
    for seed, output in trials:
        tool = seed["tool_target"]
        if tool is None:
            continue
        ok, err = classify_trial(seed, output)
        n_per[tool] += 1
        if ok:
            per[tool]["success"] += 1
            continue
        if err == "over_call":
            per[tool]["over_call"] += 1
        elif err == "wrong_tool":
            per[tool]["wrong_tool"] += 1
        else:
            sub = classify_no_tool_behavior(output)
            if sub == "clarifying_question":
                per[tool]["under_call_clarify"] += 1
            elif sub == "refusal":
                per[tool]["under_call_refusal"] += 1
            else:
                per[tool]["under_call_direct"] += 1
    return per, n_per


def _success_decomposition(trials):
    per = defaultdict(lambda: defaultdict(int))
    for seed, output in trials:
        tool = seed["tool_target"]
        if tool is None:
            continue
        ok, _ = classify_trial(seed, output)
        if not ok:
            continue
        if seed["expected_tool_call"]:
            per[tool]["success_tool_called"] += 1
        else:
            sub = classify_no_tool_behavior(output)
            if sub == "clarifying_question":
                per[tool]["success_clarify"] += 1
            elif sub == "refusal":
                per[tool]["success_refusal"] += 1
            else:
                per[tool]["success_direct"] += 1
    return per


def _load_graded(safe, tool):
    path = GRADED_ROOT / safe / f"007_a4_{tool}_graded.jsonl"
    if not path.exists():
        return None
    cells = defaultdict(int)
    excluded = 0
    for line in path.read_text().splitlines():
        if not line:
            continue
        r = json.loads(line)
        if r["grade"]["grade_status"] != "graded":
            excluded += 1
            continue
        cells[(bool(r["grade"]["correct"]), bool(r["calibration_success"]))] += 1
    total = sum(cells.values())
    return cells, total, excluded


def fig_calibration_compare():
    fig = make_subplots(
        rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
        subplot_titles=[m[0] for m in MODELS],
    )
    all_rows = []
    for col, (label, path, safe) in enumerate(MODELS, start=1):
        per = _calibration_by_tool(_load_trials(path))
        rows = []
        for tool in TOOL_ORDER:
            xs = per.get(tool, [])
            if not xs:
                continue
            mean, lo, hi = _ci(xs)
            rows.append((tool, mean, lo, hi, len(xs)))
        all_rows.append(rows)

    union = list(dict.fromkeys(t for rows in all_rows for t, *_ in rows))
    union.sort(key=lambda t: max(
        next((r[1] for r in all_rows[0] if r[0] == t), 0),
        next((r[1] for r in all_rows[1] if r[0] == t), 0),
    ), reverse=True)
    y_labels = [TOOL_LABEL[t] for t in union]

    for col, ((label, path, safe), rows) in enumerate(zip(MODELS, all_rows), start=1):
        by_tool = {r[0]: r for r in rows}
        means = [by_tool[t][1] if t in by_tool else 0 for t in union]
        ep = [by_tool[t][3] - by_tool[t][1] if t in by_tool else 0 for t in union]
        em = [by_tool[t][1] - by_tool[t][2] if t in by_tool else 0 for t in union]
        hovers = [
            f"{TOOL_LABEL[t]}<br>n={by_tool[t][4]} trials<br>success={by_tool[t][1]:.3f} [{by_tool[t][2]:.3f}, {by_tool[t][3]:.3f}]"
            if t in by_tool else "n/a" for t in union
        ]
        fig.add_trace(go.Bar(
            x=means, y=y_labels, orientation="h",
            marker_color=MOREL_COLORS["terracotta"],
            error_x=dict(type="data", array=ep, arrayminus=em,
                         color=MOREL_COLORS["muted_text"], thickness=1.2, width=4),
            hovertext=hovers, hoverinfo="text", showlegend=False,
        ), row=1, col=col)
        fig.update_xaxes(range=[0, 1.05], title_text="Calibration success rate", row=1, col=col)
    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=480, width=1280, margin=dict(l=180, r=40, t=160, b=110))
    apply_morel_template(
        fig,
        title="Calibration success per tool — 4B vs 12B",
        subtitle="Bootstrap 95% CIs. Success = called the warranted tool (or correctly didn't). Not answer correctness.",
        attribution="studies/001 inv 007 · A4 bulk neutral baseline, temp=1.0, n=10/record",
    )
    _write(fig, "compare_calibration_by_tool")


def fig_failure_compare():
    cats = [
        ("success", "success", MOREL_COLORS["forest_green"]),
        ("wrong_tool", "wrong tool", MOREL_COLORS["mustard"]),
        ("under_call_clarify", "under-call · clarifying", MOREL_COLORS["slate_blue"]),
        ("under_call_refusal", "under-call · refusal", MOREL_COLORS["muted_text"]),
        ("under_call_direct", "under-call · direct", MOREL_COLORS["error_red"]),
        ("over_call", "over-call", MOREL_COLORS["terracotta"]),
    ]
    fig = make_subplots(
        rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
        subplot_titles=[m[0] for m in MODELS],
    )
    results = []
    for label, path, safe in MODELS:
        per, n_per = _failure_breakdown(_load_trials(path))
        results.append((per, n_per))

    union = list(dict.fromkeys(t for per, _ in results for t in per))
    union = [t for t in TOOL_ORDER if t in union]
    y_labels = [TOOL_LABEL[t] for t in union]

    for col, (per, n_per) in enumerate(results, start=1):
        for key, label, color in cats:
            xs = [per[t][key] / n_per[t] if n_per[t] else 0 for t in union]
            counts = [per[t][key] for t in union]
            hovers = [
                f"{TOOL_LABEL[t]}<br>{label}<br>{counts[i]}/{n_per[t]} = {xs[i]:.1%}"
                for i, t in enumerate(union)
            ]
            fig.add_trace(go.Bar(
                x=xs, y=y_labels, orientation="h",
                name=label, marker_color=color, legendgroup=key,
                showlegend=(col == 1),
                hovertext=hovers, hoverinfo="text",
            ), row=1, col=col)
        fig.update_xaxes(range=[0, 1.02], title_text="Share of trials", tickformat=".0%", row=1, col=col)

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        barmode="stack",
        height=540, width=1280,
        margin=dict(l=180, r=40, t=200, b=110),
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, font=dict(size=11)),
    )
    apply_morel_template(
        fig,
        title="Failure breakdown by tool — 4B vs 12B",
        subtitle="Under-call split into clarifying / refusal / direct. Same colors across panels for direct comparison.",
        attribution="studies/001 inv 007 · A4 bulk neutral baseline, temp=1.0, n=10/record",
    )
    _write(fig, "compare_failure_breakdown")


def fig_success_compare():
    cats = [
        ("success_tool_called", "tool warranted → called right tool", MOREL_COLORS["forest_green"]),
        ("success_direct", "tool not warranted → direct answer", MOREL_COLORS["green_light"]),
        ("success_clarify", "tool not warranted → clarifying", MOREL_COLORS["slate_blue"]),
        ("success_refusal", "tool not warranted → refusal", MOREL_COLORS["muted_text"]),
    ]
    fig = make_subplots(
        rows=1, cols=2, shared_yaxes=True, horizontal_spacing=0.04,
        subplot_titles=[m[0] for m in MODELS],
    )
    results = []
    for label, path, safe in MODELS:
        results.append(_success_decomposition(_load_trials(path)))

    union = [t for t in TOOL_ORDER if any(t in r for r in results)]
    y_labels = [TOOL_LABEL[t] for t in union]
    max_x = 0
    for col, per in enumerate(results, start=1):
        for key, label, color in cats:
            counts = [per[t][key] for t in union]
            max_x = max(max_x, max(counts) if counts else 0)
            hovers = [f"{TOOL_LABEL[t]}<br>{label}<br>n={counts[i]}" for i, t in enumerate(union)]
            fig.add_trace(go.Bar(
                x=counts, y=y_labels, orientation="h",
                name=label, marker_color=color, legendgroup=key,
                showlegend=(col == 1),
                hovertext=hovers, hoverinfo="text",
            ), row=1, col=col)
        fig.update_xaxes(title_text="Success trials (counts)", row=1, col=col)

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        barmode="stack",
        height=540, width=1280,
        margin=dict(l=180, r=40, t=200, b=110),
        legend=dict(orientation="h", yanchor="bottom", y=1.06, xanchor="left", x=0, font=dict(size=11)),
    )
    apply_morel_template(
        fig,
        title="Success decomposition by tool — 4B vs 12B",
        subtitle='"Success" hides four behaviors. Same x-axis would obscure detail at the low end; left/right scale independently.',
        attribution="studies/001 inv 007 · A4 bulk neutral baseline, temp=1.0, n=10/record",
    )
    _write(fig, "compare_success_decomposition")


def fig_correctness_compare():
    tools = ["calculator", "unit_convert", "datetime_now"]
    fig = make_subplots(
        rows=2, cols=3,
        column_titles=tools,
        row_titles=[m[0] for m in MODELS],
        horizontal_spacing=0.08, vertical_spacing=0.18,
    )
    for row, (label, _, safe) in enumerate(MODELS, start=1):
        for col, tool in enumerate(tools, start=1):
            loaded = _load_graded(safe, tool)
            if loaded is None:
                continue
            cells, total, excluded = loaded
            cc = cells[(True, True)]
            cf = cells[(True, False)]
            wc = cells[(False, True)]
            wf = cells[(False, False)]
            if total == 0:
                continue
            z = [[cc / total, cf / total], [wc / total, wf / total]]
            text = [
                [f"<b>{cc}</b><br>{100*cc/total:.0f}%", f"<b>{cf}</b><br>{100*cf/total:.0f}%"],
                [f"<b>{wc}</b><br>{100*wc/total:.0f}%", f"<b>{wf}</b><br>{100*wf/total:.0f}%"],
            ]
            hovers = [
                [
                    f"correct ✓ · calibration ✓<br>{cc} ({100*cc/total:.1f}%)",
                    f"correct ✓ · calibration ✗<br>{cf} ({100*cf/total:.1f}%)",
                ],
                [
                    f"correct ✗ · calibration ✓<br>{wc} ({100*wc/total:.1f}%)",
                    f"correct ✗ · calibration ✗<br>{wf} ({100*wf/total:.1f}%)",
                ],
            ]
            fig.add_trace(go.Heatmap(
                z=z,
                x=["cal ✓", "cal ✗"], y=["correct ✓", "correct ✗"],
                colorscale=[
                    [0.0, MOREL_COLORS["off_white"]],
                    [1.0, MOREL_COLORS["terracotta"]],
                ],
                zmin=0, zmax=1,
                text=text, texttemplate="%{text}",
                textfont=dict(size=12, color=MOREL_COLORS["dark_earth"]),
                hovertext=hovers, hoverinfo="text",
                showscale=False,
            ), row=row, col=col)
            correctness = (cc + cf) / total
            calibration = (cc + wc) / total
            anchor = "x domain" if (row == 1 and col == 1) else f"x{(row-1)*3 + col} domain"
            yanchor = "y domain" if (row == 1 and col == 1) else f"y{(row-1)*3 + col} domain"
            fig.add_annotation(
                text=f"n={total}  ·  correctness {correctness:.0%}  ·  calibration {calibration:.0%}",
                x=0.5, xref=anchor, y=-0.35, yref=yanchor,
                showarrow=False, font=dict(size=10, color=MOREL_COLORS["muted_text"]),
            )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(height=720, width=1280, margin=dict(l=120, r=40, t=170, b=80))
    apply_morel_template(
        fig,
        title="Answer correctness vs calibration — 4B vs 12B",
        subtitle="Top row 4B, bottom row 12B. Top-right cell = correct despite calibration failure; bottom-left = calibration ✓ but answer ✗.",
        attribution="studies/001 inv 007 · A4 bulk neutral baseline, temp=1.0, n=10/record",
    )
    _write(fig, "compare_correctness_heatmap")


def _write(fig, base):
    for ext in ("png", "html", "pdf"):
        path = OUT / f"{base}.{ext}"
        if ext == "html":
            fig.write_html(path)
        else:
            fig.write_image(path, scale=2)
        print(f"wrote {path}")


if __name__ == "__main__":
    fig_calibration_compare()
    fig_failure_compare()
    fig_success_compare()
    fig_correctness_compare()
