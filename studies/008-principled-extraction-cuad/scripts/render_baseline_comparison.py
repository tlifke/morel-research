import html
import json
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
DATA = STUDY / "reviews" / "baseline-comparison-data.json"
OUT = STUDY / "reviews" / "baseline-comparison.html"

C = {
    "terracotta": "#C1694F",
    "forest": "#2D5016",
    "parchment": "#F5E6D3",
    "cream_dark": "#E8D5BF",
    "dark_earth": "#3B2F2F",
    "error_red": "#C14F4F",
    "slate": "#3D6478",
    "mustard": "#B8821C",
    "mushroom": "#9C7676",
    "muted": "#6B5E5E",
}

MODELS = ["RoBERTa-base", "RoBERTa-large", "DeBERTa-v2-xlarge"]
MODEL_COLORS = {
    "RoBERTa-base": C["mushroom"],
    "RoBERTa-large": C["slate"],
    "DeBERTa-v2-xlarge": C["forest"],
}
COND_COLORS = {"C2": C["mustard"], "C3": C["terracotta"]}


def e(s):
    return html.escape(str(s))


def f(x, n=3, pct=False, plus=False, dash="&mdash;"):
    if x is None:
        return dash
    v = x * 100 if pct else x
    return f"{v:+.{n}f}" if plus else f"{v:.{n}f}"


def pr(p, r, n=2):
    return f"{f(p, n)}&thinsp;/&thinsp;{f(r, n)}"


def table(headers, rows, cls=""):
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = []
    for row in rows:
        tds = "".join(f"<td{(' class=' + chr(34) + c + chr(34)) if c else ''}>{v}</td>" for v, c in row)
        body.append(f"<tr>{tds}</tr>")
    return (
        f'<div class="scroll"><table class="{cls}"><thead><tr>{head}</tr></thead>'
        f'<tbody>{"".join(body)}</tbody></table></div>'
    )


class Axes:
    def __init__(self, w, h, pad, xlab, ylab, xmax=1.0, ymax=1.0, xmin=0.0, ymin=0.0):
        self.w, self.h, self.pad = w, h, pad
        self.pw = w - pad["l"] - pad["r"]
        self.ph = h - pad["t"] - pad["b"]
        self.xlab, self.ylab = xlab, ylab
        self.xmax, self.ymax = xmax, ymax
        self.xmin, self.ymin = xmin, ymin

    def x(self, v):
        return self.pad["l"] + (v - self.xmin) / (self.xmax - self.xmin) * self.pw

    def y(self, v):
        return self.pad["t"] + (1 - (v - self.ymin) / (self.ymax - self.ymin)) * self.ph

    def frame(self, ticks=11):
        p = [
            f'<rect x="{self.pad["l"]}" y="{self.pad["t"]}" width="{self.pw}" '
            f'height="{self.ph}" fill="#FFFFFF" stroke="{C["cream_dark"]}"/>'
        ]
        for i in range(ticks):
            v = self.xmin + (self.xmax - self.xmin) * i / (ticks - 1)
            u = self.ymin + (self.ymax - self.ymin) * i / (ticks - 1)
            x, y = self.x(v), self.y(u)
            p.append(
                f'<line x1="{x:.1f}" y1="{self.pad["t"]}" x2="{x:.1f}" '
                f'y2="{self.pad["t"] + self.ph}" stroke="{C["cream_dark"]}" stroke-width="0.6"/>'
            )
            p.append(
                f'<line x1="{self.pad["l"]}" y1="{y:.1f}" x2="{self.pad["l"] + self.pw}" '
                f'y2="{y:.1f}" stroke="{C["cream_dark"]}" stroke-width="0.6"/>'
            )
            if i % 2 == 0:
                p.append(
                    f'<text x="{x:.1f}" y="{self.pad["t"] + self.ph + 18}" '
                    f'text-anchor="middle" class="tick">{v:.1f}</text>'
                )
                p.append(
                    f'<text x="{self.pad["l"] - 10}" y="{y + 4:.1f}" '
                    f'text-anchor="end" class="tick">{u:.1f}</text>'
                )
        p.append(
            f'<text x="{self.pad["l"] + self.pw / 2:.0f}" y="{self.h - 12}" '
            f'text-anchor="middle" class="axlab">{e(self.xlab)}</text>'
        )
        cy = self.pad["t"] + self.ph / 2
        p.append(
            f'<text x="16" y="{cy:.0f}" text-anchor="middle" class="axlab" '
            f'transform="rotate(-90 16 {cy:.0f})">{e(self.ylab)}</text>'
        )
        return "".join(p)

    def svg(self, inner):
        return (
            f'<svg viewBox="0 0 {self.w} {self.h}" role="img" '
            f'xmlns="http://www.w3.org/2000/svg">{inner}</svg>'
        )


def legend(ax, entries, x0, y0, dy=17):
    p = []
    for i, (label, col, shape) in enumerate(entries):
        y = y0 + i * dy
        if shape == "line":
            p.append(f'<line x1="{x0}" y1="{y - 4}" x2="{x0 + 20}" y2="{y - 4}" stroke="{col}" stroke-width="2.4"/>')
        elif shape == "hollow":
            p.append(f'<circle cx="{x0 + 10}" cy="{y - 4}" r="4.5" fill="#FFFFFF" stroke="{col}" stroke-width="2"/>')
        else:
            p.append(f'<circle cx="{x0 + 10}" cy="{y - 4}" r="5" fill="{col}"/>')
        p.append(f'<text x="{x0 + 27}" y="{y}" class="leg">{e(label)}</text>')
    return "".join(p)


def fig_test_curves(d):
    ax = Axes(900, 430, {"l": 62, "r": 20, "t": 24, "b": 50}, "Recall (span-level, micro-pooled, 41 categories)", "Interpolated precision")
    parts = [ax.frame()]
    for name in MODELS:
        rows = d["test_curves"][name]
        pts = " ".join(f"{ax.x(r['recall']):.2f},{ax.y(r['interpolated_precision']):.2f}" for r in rows)
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{MODEL_COLORS[name]}" stroke-width="2.3"/>')
    for row in d["table2"]:
        op = row["operating_point_80"]
        col = MODEL_COLORS[row["model"]]
        parts.append(
            f'<circle cx="{ax.x(op["recall"]):.2f}" cy="{ax.y(op["interpolated_precision"]):.2f}" '
            f'r="5" fill="#FFFFFF" stroke="{col}" stroke-width="2.4"/>'
        )
    parts.append(
        legend(
            ax,
            [(f"{m} — AUPR {f(r['aupr_recovered'], 2)}", MODEL_COLORS[m], "line") for m, r in zip(MODELS, d["table2"])]
            + [("P@80%R operating point", C["dark_earth"], "hollow")],
            ax.pad["l"] + 16,
            ax.pad["t"] + ax.ph - 60,
        )
    )
    return ax.svg("".join(parts))


def fig_headtohead(d):
    ax = Axes(
        900, 470, {"l": 62, "r": 20, "t": 24, "b": 50},
        "Recall (span-level, micro-pooled, 12 categories)", "Precision",
        xmin=0.3, xmax=0.9, ymin=0.4, ymax=1.0,
    )
    parts = [ax.frame(ticks=7)]
    hv = d["harness_val"]
    for name in MODELS:
        sweep = [s for s in hv["their"][name]["sweep"] if s["conf"] > 0]
        pts = " ".join(f"{ax.x(s['recall']):.2f},{ax.y(s['precision']):.2f}" for s in sorted(sweep, key=lambda s: s["recall"]))
        col = MODEL_COLORS[name]
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2" stroke-dasharray="5 3"/>')
        for s in sweep:
            r = 6 if abs(s["conf"] - d["headline_conf"]) < 1e-9 else 3
            parts.append(f'<circle cx="{ax.x(s["recall"]):.2f}" cy="{ax.y(s["precision"]):.2f}" r="{r}" fill="{col}"/>')
        if name == "RoBERTa-large":
            for s in sweep:
                parts.append(
                    f'<text x="{ax.x(s["recall"]):.1f}" y="{ax.y(s["precision"]) - 11:.1f}" '
                    f'text-anchor="middle" class="note" fill="{col}">{s["conf"]:g}</text>'
                )
    for cond, dx, dy in (("C2", -14, 20), ("C3", 14, -14)):
        o = hv["ours"][cond]
        col = COND_COLORS[cond]
        for s in o["per_seed"]:
            parts.append(
                f'<circle cx="{ax.x(s["recall"]):.2f}" cy="{ax.y(s["precision"]):.2f}" '
                f'r="3.5" fill="{col}" opacity="0.3"/>'
            )
        x, y = ax.x(o["recall"]), ax.y(o["precision"])
        parts.append(f'<path d="M {x:.1f} {y - 9:.1f} L {x + 9:.1f} {y:.1f} L {x:.1f} {y + 9:.1f} L {x - 9:.1f} {y:.1f} Z" fill="{col}" stroke="#FFFFFF" stroke-width="1.6"/>')
        parts.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x + dx:.1f}" y2="{y + dy:.1f}" stroke="{col}" stroke-width="1"/>')
        anchor = "end" if dx < 0 else "start"
        parts.append(f'<text x="{x + dx + (-3 if dx < 0 else 3):.1f}" y="{y + dy + 4:.1f}" text-anchor="{anchor}" class="pointlab" fill="{col}">{cond}</text>')
    parts.append(
        legend(
            ax,
            [(f"{m} — confidence sweep", MODEL_COLORS[m], "line") for m in MODELS]
            + [("our C2 (principles)", COND_COLORS["C2"], "dot"), ("our C3 (principles + citation)", COND_COLORS["C3"], "dot")],
            ax.pad["l"] + 16,
            ax.pad["t"] + ax.ph - 84,
        )
    )
    parts.append(
        f'<text x="{ax.pad["l"] + ax.pw - 8}" y="{ax.pad["t"] + 18}" text-anchor="end" class="note">'
        f'axes cropped to the occupied region; numbers on the blue curve are confidence thresholds</text>'
    )
    return ax.svg("".join(parts))


def fig_paper_figure4(d):
    rows = d["figure4a"]["rows"]
    w = 900
    labw, rowh, top = 250, 15.5, 44
    barw = w - labw - 70
    h = top + rowh * len(rows) + 40
    parts = [f'<text x="{labw}" y="24" class="axlab">AUPR &#8212; DeBERTa-v2-xlarge, official <tspan font-style="italic">test</tspan> split, per category</text>']
    for t in (0, 0.2, 0.4, 0.6, 0.8, 1.0):
        x = labw + t * barw
        parts.append(f'<line x1="{x:.1f}" y1="{top - 6}" x2="{x:.1f}" y2="{top + rowh * len(rows):.1f}" stroke="{C["cream_dark"]}" stroke-width="0.7"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + rowh * len(rows) + 16:.0f}" text-anchor="middle" class="tick">{t * 100:.0f}</text>')
    parts.append(f'<text x="{labw + barw / 2:.0f}" y="{top + rowh * len(rows) + 32:.0f}" text-anchor="middle" class="axlab">AUPR</text>')
    for i, r in enumerate(rows):
        y = top + i * rowh
        col = C["terracotta"] if r["in_our_subset"] else C["slate"]
        op = "1" if r["in_our_subset"] else "0.42"
        parts.append(f'<rect x="{labw}" y="{y + 1.5:.1f}" width="{max(r["aupr"] * barw, 0.6):.1f}" height="{rowh - 4:.1f}" fill="{col}" opacity="{op}"/>')
        weight = "700" if r["in_our_subset"] else "400"
        parts.append(f'<text x="{labw - 8}" y="{y + rowh - 4.5:.1f}" text-anchor="end" class="frow" font-weight="{weight}">{e(r["category"])}</text>')
        parts.append(f'<text x="{labw + r["aupr"] * barw + 6:.1f}" y="{y + rowh - 4.5:.1f}" class="note">{r["aupr"] * 100:.1f}</text>')
    parts.append(f'<rect x="{labw + barw - 210}" y="16" width="9" height="9" fill="{C["terracotta"]}"/>')
    parts.append(f'<text x="{labw + barw - 196}" y="24" class="leg">one of our 12 categories</text>')
    parts.append(f'<rect x="{labw + barw - 60}" y="16" width="9" height="9" fill="{C["slate"]}" opacity="0.42"/>')
    parts.append(f'<text x="{labw + barw - 46}" y="24" class="leg">other 29</text>')
    return f'<svg viewBox="0 0 {w} {h}" role="img" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'


def fig_f1_by_category(d):
    rows = d["figure4b"]["rows"]
    w = 900
    labw, top = 210, 52
    grouph, barh = 62, 9
    barw = w - labw - 80
    h = top + grouph * len(rows) + 34
    series = [
        ("RoBERTa-base", MODEL_COLORS["RoBERTa-base"], "their"),
        ("RoBERTa-large", MODEL_COLORS["RoBERTa-large"], "their"),
        ("DeBERTa-v2-xlarge", MODEL_COLORS["DeBERTa-v2-xlarge"], "their"),
        ("C2", COND_COLORS["C2"], "ours"),
        ("C3", COND_COLORS["C3"], "ours"),
    ]
    parts = [f'<text x="{labw}" y="22" class="axlab">Micro-F1 at the operating point &#8212; <tspan font-style="italic">harness_val</tspan>, 12 categories, same scorer both sides</text>']
    lx = labw
    for name, col, kind in series:
        parts.append(f'<rect x="{lx}" y="30" width="9" height="9" fill="{col}"/>')
        label = name if kind == "ours" else f"{name} @0.5"
        parts.append(f'<text x="{lx + 13}" y="38" class="leg">{e(label)}</text>')
        lx += 26 + 6.6 * len(label)
    parts.append(f'<line x1="{lx + 4}" y1="30" x2="{lx + 4}" y2="39" stroke="{C["dark_earth"]}" stroke-width="2"/>')
    parts.append(f'<text x="{lx + 11}" y="38" class="leg">their best @0.1</text>')
    for t in (0, 0.25, 0.5, 0.75, 1.0):
        x = labw + t * barw
        parts.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{top + grouph * len(rows) - 12:.1f}" stroke="{C["cream_dark"]}" stroke-width="0.7"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + grouph * len(rows) + 4:.0f}" text-anchor="middle" class="tick">{t:g}</text>')
    parts.append(f'<text x="{labw + barw / 2:.0f}" y="{top + grouph * len(rows) + 22:.0f}" text-anchor="middle" class="axlab">micro-F1</text>')
    for i, r in enumerate(rows):
        y0 = top + i * grouph
        parts.append(f'<text x="{labw - 10}" y="{y0 + 14:.1f}" text-anchor="end" class="frow">{e(r["category"])}</text>')
        parts.append(f'<text x="{labw - 10}" y="{y0 + 30:.1f}" text-anchor="end" class="note">their test AUPR {r["their_test_aupr"] * 100:.1f} (#{r["their_test_rank"]} of 41)</text>')
        best_open = max(r["their_open"].values())
        for j, (name, col, kind) in enumerate(series):
            v = r["their"][name] if kind == "their" else r["ours"][name]
            y = y0 + j * (barh + 1.5)
            parts.append(f'<rect x="{labw}" y="{y:.1f}" width="{max(v * barw, 0.6):.1f}" height="{barh}" fill="{col}"/>')
            parts.append(f'<text x="{labw + max(v * barw, 0.6) + 5:.1f}" y="{y + barh - 1:.1f}" class="note">{v:.2f}</text>')
        x = labw + best_open * barw
        parts.append(f'<line x1="{x:.1f}" y1="{y0 - 2:.1f}" x2="{x:.1f}" y2="{y0 + 3 * (barh + 1.5) - 2:.1f}" stroke="{C["dark_earth"]}" stroke-width="2"/>')
    return f'<svg viewBox="0 0 {w} {h}" role="img" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'


def fig_per_category(d):
    cats = list(reversed(d["per_category"]))
    rowh = 26
    top = 64
    h = top + rowh * len(cats) + 46
    w = 900
    labw = 190
    gap = 40
    panelw = (w - labw - gap - 24) / 2

    def panel_x(idx, v):
        base = labw + idx * (panelw + gap)
        return base + v * panelw

    parts = []
    for idx, title in enumerate(("Precision", "Recall")):
        x0, x1 = panel_x(idx, 0), panel_x(idx, 1)
        parts.append(f'<rect x="{x0}" y="{top - 8}" width="{panelw}" height="{rowh * len(cats) + 8}" fill="#FFFFFF" stroke="{C["cream_dark"]}"/>')
        parts.append(f'<text x="{(x0 + x1) / 2:.0f}" y="{top - 20}" text-anchor="middle" class="axlab">{title}</text>')
        for t in (0, 0.25, 0.5, 0.75, 1.0):
            x = panel_x(idx, t)
            parts.append(f'<line x1="{x:.1f}" y1="{top - 8}" x2="{x:.1f}" y2="{top + rowh * len(cats)}" stroke="{C["cream_dark"]}" stroke-width="0.6"/>')
            parts.append(f'<text x="{x:.1f}" y="{top + rowh * len(cats) + 16}" text-anchor="middle" class="tick">{t:g}</text>')

    for i, row in enumerate(cats):
        y = top + i * rowh + rowh / 2
        spq = row["gold_spans_per_question"]
        parts.append(f'<text x="{labw - 10}" y="{y + 4:.1f}" text-anchor="end" class="frow">{e(row["category"])}</text>')
        parts.append(f'<text x="{labw - 10}" y="{y + 4:.1f}" text-anchor="end" class="frow" opacity="0">.</text>')
        for idx, key in enumerate(("precision", "recall")):
            series = [
                (row["their"]["RoBERTa-large"][key], MODEL_COLORS["RoBERTa-large"], "sq"),
                (row["their"]["RoBERTa-large"]["open"][key], MODEL_COLORS["RoBERTa-large"], "ring"),
                (row["ours"]["C2"][key], COND_COLORS["C2"], "dot"),
                (row["ours"]["C3"][key], COND_COLORS["C3"], "dot"),
            ]
            vals = [v for v, _, _ in series if v is not None]
            if vals:
                parts.append(
                    f'<line x1="{panel_x(idx, min(vals)):.1f}" y1="{y:.1f}" '
                    f'x2="{panel_x(idx, max(vals)):.1f}" y2="{y:.1f}" stroke="{C["cream_dark"]}" stroke-width="2"/>'
                )
            for v, col, shape in series:
                if v is None:
                    continue
                x = panel_x(idx, v)
                if shape == "sq":
                    parts.append(f'<rect x="{x - 4:.1f}" y="{y - 4:.1f}" width="8" height="8" fill="{col}"/>')
                elif shape == "ring":
                    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="#FFFFFF" stroke="{col}" stroke-width="1.8"/>')
                else:
                    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.2" fill="{col}"/>')
        parts.append(f'<text x="{labw - 10}" y="{y + 4:.1f}" text-anchor="end" class="frow" visibility="hidden">{spq}</text>')

    parts.append(
        legend(
            None,
            [
                ("RoBERTa-large @ conf 0.5 (committed)", MODEL_COLORS["RoBERTa-large"], "dot"),
                ("RoBERTa-large @ conf 0.1 (open)", MODEL_COLORS["RoBERTa-large"], "hollow"),
                ("our C2", COND_COLORS["C2"], "dot"),
                ("our C3", COND_COLORS["C3"], "dot"),
            ],
            10,
            22,
            dy=0,
        )
        if False
        else ""
    )
    leg = [
        ("RoBERTa-large @ conf 0.5", MODEL_COLORS["RoBERTa-large"], "sq"),
        ("RoBERTa-large @ conf 0.1", MODEL_COLORS["RoBERTa-large"], "ring"),
        ("our C2", COND_COLORS["C2"], "dot"),
        ("our C3", COND_COLORS["C3"], "dot"),
    ]
    lx = labw
    for label, col, shape in leg:
        if shape == "sq":
            parts.append(f'<rect x="{lx}" y="12" width="8" height="8" fill="{col}"/>')
        elif shape == "ring":
            parts.append(f'<circle cx="{lx + 4}" cy="16" r="4.2" fill="#FFFFFF" stroke="{col}" stroke-width="1.8"/>')
        else:
            parts.append(f'<circle cx="{lx + 4}" cy="16" r="4.2" fill="{col}"/>')
        parts.append(f'<text x="{lx + 14}" y="20" class="leg">{e(label)}</text>')
        lx += 30 + 7.1 * len(label)
    return f'<svg viewBox="0 0 {w} {h}" role="img" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'


def fig_error_profile(d):
    rows = d["error_profile"]
    w = 900
    labw, top, rowh = 178, 58, 30
    h = top + len(rows) * rowh + 52
    barw = w - labw - 210
    parts = []
    parts.append(f'<text x="{labw}" y="26" class="axlab">False-positive composition (each bar = that system\'s total FP)</text>')
    parts.append(f'<text x="{labw + barw + 24}" y="26" class="axlab">declines / over-claims</text>')
    for i, r in enumerate(rows):
        y = top + i * rowh
        total = r["fp"]
        wa = barw * (r["fp_absent"] / total)
        wp = barw * (r["fp_present"] / total)
        col = C["slate"] if r["kind"] == "their" else C["terracotta"]
        parts.append(f'<text x="{labw - 10}" y="{y + 14:.0f}" text-anchor="end" class="frow">{e(r["system"])}</text>')
        parts.append(f'<rect x="{labw}" y="{y}" width="{wa:.1f}" height="19" fill="{col}"/>')
        parts.append(f'<rect x="{labw + wa:.1f}" y="{y}" width="{wp:.1f}" height="19" fill="{col}" opacity="0.28"/>')
        parts.append(f'<rect x="{labw}" y="{y}" width="{barw}" height="19" fill="none" stroke="{C["cream_dark"]}"/>')
        if wa > 52:
            parts.append(f'<text x="{labw + 8}" y="{y + 14:.0f}" class="barlab" fill="#FFFFFF">{r["fp_absent_share"] * 100:.0f}% on gold-absent</text>')
        if wp > 60:
            parts.append(f'<text x="{labw + wa + 8:.1f}" y="{y + 14:.0f}" class="barlab" fill="{C["dark_earth"]}">{r["fp_present_share"] * 100:.0f}% on gold-present</text>')
        parts.append(
            f'<text x="{labw + barw + 24}" y="{y + 14:.0f}" class="frow">'
            f'{r["decline_rate"] * 100:.0f}% / {r["overclaim_rate"] * 100:.0f}%</text>'
        )
    parts.append(f'<text x="{labw}" y="{top + len(rows) * rowh + 16:.0f}" class="note">Solid = FPs on questions whose gold is empty (over-claiming). Faded = FPs on questions that do have gold (wrong boundaries).</text>')
    parts.append(f'<text x="{labw}" y="{top + len(rows) * rowh + 32:.0f}" class="note">Their models at conf 0.5; ours pooled over 3 seeds. Bar lengths are normalised per system, so widths compare composition, not counts.</text>')
    return f'<svg viewBox="0 0 {w} {h}" role="img" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'


def fig_bootstrap(d):
    iv = d["bootstrap"]["intervals"]
    order = [("micro_f1", "micro-F1 (D-30 headline)"), ("precision", "precision"), ("recall", "recall")]
    w, h = 900, 250
    labw, top, rowh = 200, 60, 46
    lo, hi = -0.06, 0.10
    plotw = w - labw - 40

    def x(v):
        return labw + (v - lo) / (hi - lo) * plotw

    parts = [f'<rect x="{labw}" y="{top - 20}" width="{plotw}" height="{rowh * len(order) + 6}" fill="#FFFFFF" stroke="{C["cream_dark"]}"/>']
    for t in (-0.06, -0.04, -0.02, 0, 0.02, 0.04, 0.06, 0.08, 0.10):
        parts.append(f'<line x1="{x(t):.1f}" y1="{top - 20}" x2="{x(t):.1f}" y2="{top + rowh * len(order) - 14}" stroke="{C["cream_dark"] if t else C["error_red"]}" stroke-width="{2 if t == 0 else 0.6}"/>')
        parts.append(f'<text x="{x(t):.1f}" y="{top + rowh * len(order) + 6}" text-anchor="middle" class="tick">{t:+.2f}</text>')
    parts.append(f'<text x="{x(0):.1f}" y="{top - 28}" text-anchor="middle" class="note" fill="{C["error_red"]}">no difference</text>')
    for i, (key, label) in enumerate(order):
        v = iv[key]
        y = top + i * rowh
        parts.append(f'<text x="{labw - 12}" y="{y + 4:.0f}" text-anchor="end" class="frow">{e(label)}</text>')
        parts.append(f'<line x1="{x(v["ci_low"]):.1f}" y1="{y:.0f}" x2="{x(v["ci_high"]):.1f}" y2="{y:.0f}" stroke="{C["terracotta"]}" stroke-width="3"/>')
        for b in ("ci_low", "ci_high"):
            parts.append(f'<line x1="{x(v[b]):.1f}" y1="{y - 7:.0f}" x2="{x(v[b]):.1f}" y2="{y + 7:.0f}" stroke="{C["terracotta"]}" stroke-width="3"/>')
        parts.append(f'<circle cx="{x(v["delta"]):.1f}" cy="{y:.0f}" r="5" fill="{C["dark_earth"]}"/>')
        parts.append(
            f'<text x="{labw - 12}" y="{y + 20:.0f}" text-anchor="end" class="note">'
            f'{f(v["delta"], 4, plus=True)} [{f(v["ci_low"], 4, plus=True)}, {f(v["ci_high"], 4, plus=True)}]</text>'
        )
    parts.append(f'<text x="{labw}" y="{top + rowh * len(order) + 30}" class="note">C3 &#8722; C2, paired contract bootstrap, 10,000 resamples, 38 contracts. Every interval crosses zero.</text>')
    return f'<svg viewBox="0 0 {w} {h}" role="img" xmlns="http://www.w3.org/2000/svg">{"".join(parts)}</svg>'


def rng(vals, n=3, pct=False):
    lo, hi = min(vals), max(vals)
    if pct:
        return f"{lo * 100:.0f}&ndash;{hi * 100:.0f}%"
    return f"{f(lo, n)}&ndash;{f(hi, n)}"


def build(d):
    run = d["run"]
    hv = d["harness_val"]
    cmp_ = hv["comparability"]
    t2 = d["table2"]

    t2_rows = []
    for r in t2:
        t2_rows.append(
            [
                (e(r["model"]), ""),
                (f(r["aupr_published"], 1), ""),
                (f"<b>{f(r['aupr_recovered'], 3)}</b>", ""),
                (f(r["aupr_recovered"] - r["aupr_published"], 3, plus=True), "sub"),
                (f(r["p80_published"], 1), ""),
                (f"<b>{f(r['p80_recovered'], 3)}</b>", ""),
                (f(r["p80_recovered"] - r["p80_published"], 3, plus=True), "sub"),
                (f(r["p90_published"], 1), ""),
                (f"<b>{f(r['p90_recovered'], 3)}</b>", ""),
                (f(r["p90_recovered"] - r["p90_published"], 3, plus=True), "sub"),
                (f(r["max_recall"], 3), "sub"),
            ]
        )

    pooled_rows = []
    for m in MODELS:
        cur = hv["their"][m]["curve"]
        s = [x for x in hv["their"][m]["sweep"] if abs(x["conf"] - d["headline_conf"]) < 1e-9][0]
        pooled_rows.append(
            [
                (f"{e(m)} <span class=\"tag\">memorised</span>", ""),
                (f(cur["aupr"], 3), ""),
                (f(cur["prec_at_80_recall"], 3), ""),
                (f(cur["prec_at_90_recall"], 3), ""),
                (f(cur["max_recall"], 3), ""),
                (f(s["precision"], 3), ""),
                (f(s["recall"], 3), ""),
                (f"{s['tp']} / {s['fp']} / {s['fn']}", "sub"),
            ]
        )
    for cond in ("C2", "C3"):
        o = hv["ours"][cond]
        pooled_rows.append(
            [
                (f"our {cond} <span class=\"tag ours\">no threshold</span>", ""),
                ("&mdash;", "sub"),
                ("&mdash;", "sub"),
                ("&mdash;", "sub"),
                ("&mdash;", "sub"),
                (f"<b>{f(o['precision'], 3)}</b>", ""),
                (f"<b>{f(o['recall'], 3)}</b>", ""),
                (f"{o['tp']} / {o['fp']} / {o['fn']}", "sub"),
            ]
        )

    cat_rows = []
    for row in d["per_category"]:
        cells = [
            (e(row["category"]), ""),
            (f(row["gold_spans_per_question"], 2), "sub"),
            (f"{row['questions_gold_present']} / {row['questions_gold_absent']}", "sub"),
        ]
        for m in MODELS:
            t = row["their"][m]
            cells.append((pr(t["precision"], t["recall"]), ""))
        cells.append((pr(row["their"]["RoBERTa-large"]["open"]["precision"], row["their"]["RoBERTa-large"]["open"]["recall"]), "sub"))
        for cond in ("C2", "C3"):
            o = row["ours"][cond]
            hl = "hl" if row["category"] in ("Governing Law", "Expiration Date", "Volume Restriction") else ""
            cells.append((pr(o["precision"], o["recall"]), hl))
        cat_rows.append(cells)

    err_rows = []
    for r in d["error_profile"]:
        err_rows.append(
            [
                (e(r["system"]), ""),
                (f"{r['declines']} / {r['questions_gold_present']} ({r['decline_rate'] * 100:.0f}%)", ""),
                (f"{r['overclaims']} / {r['questions_gold_absent']} <b>({r['overclaim_rate'] * 100:.0f}%)</b>", ""),
                (f"{r['fp_absent']} <span class=\"sub\">({r['fp_absent_share'] * 100:.0f}%)</span>", ""),
                (f"{r['fp_present']} <span class=\"sub\">({r['fp_present_share'] * 100:.0f}%)</span>", ""),
                (str(r["fp"]), "sub"),
            ]
        )

    exp_rows = []
    label = {"calendar_date": "calendar date", "duration": "duration", "event": "event / perpetual", "other": "other (multi-limb)"}
    for row in d["expiration"]:
        cells = [(label[row["cls"]], ""), (str(row.get("n_gold_spans", "")), "sub")]
        for m in MODELS:
            t = row["their"].get(m)
            cells.append((pr(t["presence_recall"], t["span_iou_recall"]) if t else "&mdash;", ""))
        for cond in ("C2", "C3"):
            o = row["ours"].get(cond)
            hl = "hl" if row["cls"] == "duration" else ""
            cells.append((f'{pr(o["presence_recall"], o["span_iou_recall"])} <span class="sub">n={o["n_decisions"]}</span>' if o else "&mdash;", hl))
        exp_rows.append(cells)

    stab_rows = []
    for s in d["bootstrap"]["precision_ci_stability"]:
        stab_rows.append(
            [
                (f"{s['n_boot']:,}", ""),
                (str(s["rng_seed"]), ""),
                (f(s["ci_low"], 5, plus=True), ""),
                (f(s["ci_high"], 5, plus=True), ""),
                (f"{s['frac_above_zero'] * 100:.2f}%", ""),
                ("<b>excludes 0</b>" if s["excludes_zero"] else "contains 0", "warn" if s["excludes_zero"] else ""),
            ]
        )

    fp_cat_rows = []
    for s in d["bootstrap"]["fp_by_category"]:
        fp_cat_rows.append(
            [
                (e(s["category"]), ""),
                (f(s["c2_fp_mean"], 2), ""),
                (f(s["c3_fp_mean"], 2), ""),
                (f(s["diff_mean"], 2, plus=True), "warn" if s["diff_mean"] > 0 else ""),
                (f"{s['diff_raw']:+d}", "sub"),
            ]
        )

    css = f"""
:root {{
  --bg: #FBF7F2; --panel: #FFFFFF; --ink: #241C1A; --muted: {C['muted']};
  --rule: {C['cream_dark']}; --parchment: {C['parchment']}; --warn: {C['error_red']};
  --accent: {C['terracotta']};
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink);
  font-family: Georgia, 'Times New Roman', serif; font-size: 17px; line-height: 1.62;
  overflow-x: hidden; }}
.wrap {{ max-width: 1000px; margin: 0 auto; padding: 44px 24px 80px; }}
h1 {{ font-size: 33px; line-height: 1.24; margin: 0 0 8px; }}
h2 {{ font-size: 24px; margin: 52px 0 12px; padding-bottom: 7px; border-bottom: 2px solid var(--rule); }}
h3 {{ font-size: 19px; margin: 30px 0 8px; }}
p {{ margin: 12px 0; }}
.sub-title {{ color: var(--muted); font-size: 16.5px; margin: 0 0 22px; }}
code {{ font-family: 'SF Mono', Menlo, Consolas, monospace; font-size: 0.86em;
  background: var(--parchment); padding: 1px 5px; border-radius: 3px; }}
.card {{ background: var(--panel); border: 1px solid var(--rule); border-radius: 6px;
  padding: 16px 20px; margin: 20px 0; }}
.banner {{ background: #FBEDE8; border-left: 6px solid {C['error_red']};
  border-radius: 0 6px 6px 0; padding: 14px 20px; margin: 20px 0; }}
.banner.ok {{ background: #EDF3E9; border-left-color: {C['forest']}; }}
.banner.neutral {{ background: var(--parchment); border-left-color: {C['mustard']}; }}
.banner p:first-child {{ margin-top: 0; }}
.banner p:last-child {{ margin-bottom: 0; }}
.verdicts {{ display: grid; gap: 14px; margin: 22px 0; }}
.verdict {{ background: var(--panel); border: 1px solid var(--rule); border-left: 6px solid var(--rule);
  border-radius: 0 6px 6px 0; padding: 13px 18px; }}
.verdict.yes {{ border-left-color: {C['forest']}; }}
.verdict.no {{ border-left-color: {C['error_red']}; }}
.verdict.missing {{ border-left-color: {C['mustard']}; }}
.verdict h4 {{ margin: 0 0 5px; font-size: 17.5px; }}
.verdict p {{ margin: 4px 0 0; font-size: 16px; }}
.flag {{ display: inline-block; font-family: -apple-system, Arial, sans-serif; font-size: 11.5px;
  font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; padding: 2px 8px;
  border-radius: 3px; vertical-align: 2px; margin-right: 8px; color: #FFFFFF; }}
.flag.yes {{ background: {C['forest']}; }}
.flag.no {{ background: {C['error_red']}; }}
.flag.missing {{ background: {C['mustard']}; }}
.scroll {{ overflow-x: auto; margin: 16px 0; border: 1px solid var(--rule); border-radius: 6px;
  background: var(--panel); }}
table {{ border-collapse: collapse; width: 100%; min-width: 560px;
  font-family: -apple-system, Arial, sans-serif; font-size: 14px; }}
th, td {{ padding: 7px 11px; border-bottom: 1px solid var(--rule); text-align: right;
  white-space: nowrap; }}
th {{ background: var(--parchment); font-weight: 700; position: sticky; top: 0; }}
th:first-child, td:first-child {{ text-align: left; }}
tbody tr:last-child td {{ border-bottom: none; }}
td.sub, .sub {{ color: var(--muted); }}
td.warn, .warn {{ color: var(--warn); }}
td.hl {{ background: #FBEDE8; font-weight: 700; }}
.tag {{ font-family: -apple-system, Arial, sans-serif; font-size: 10.5px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em; background: {C['error_red']}; color: #FFF;
  padding: 1px 6px; border-radius: 3px; margin-left: 6px; }}
.tag.ours {{ background: {C['mustard']}; }}
figure {{ margin: 18px 0; }}
figure svg {{ width: 100%; height: auto; display: block; background: #FFFFFF;
  border: 1px solid var(--rule); border-radius: 6px; }}
figcaption {{ font-size: 14.5px; color: var(--muted); margin-top: 8px; }}
.tick {{ font-size: 11px; fill: {C['muted']}; font-family: -apple-system, Arial, sans-serif; }}
.axlab {{ font-size: 12.5px; fill: {C['dark_earth']}; font-family: -apple-system, Arial, sans-serif; }}
.leg {{ font-size: 11.5px; fill: {C['dark_earth']}; font-family: -apple-system, Arial, sans-serif; }}
.note {{ font-size: 11.5px; fill: {C['muted']}; font-family: -apple-system, Arial, sans-serif; }}
.barlab {{ font-size: 11.5px; font-family: -apple-system, Arial, sans-serif; font-weight: 700; }}
.frow {{ font-size: 12.5px; fill: {C['dark_earth']}; font-family: -apple-system, Arial, sans-serif; }}
.pointlab {{ font-size: 13px; font-weight: 700; font-family: -apple-system, Arial, sans-serif; }}
.meta {{ display: flex; flex-wrap: wrap; gap: 6px 26px; font-size: 14.5px;
  font-family: -apple-system, Arial, sans-serif; color: var(--muted); }}
.meta b {{ color: var(--ink); font-weight: 600; }}
ul {{ margin: 10px 0; padding-left: 22px; }}
li {{ margin: 7px 0; }}
footer {{ margin-top: 58px; padding-top: 18px; border-top: 2px solid var(--rule);
  font-size: 13.5px; color: var(--muted); }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #1E1A18; --panel: #262120; --ink: #F0E7DE; --muted: #B3A69C;
    --rule: #453B37; --parchment: #322A27;
  }}
  :root:not([data-theme="light"]) .banner {{ background: #3A2320; }}
  :root:not([data-theme="light"]) .banner.ok {{ background: #24301F; }}
  :root:not([data-theme="light"]) .banner.neutral {{ background: #322A27; }}
  :root:not([data-theme="light"]) td.hl {{ background: #3A2320; }}
  :root:not([data-theme="light"]) figure svg {{ background: #F7F2EC; }}
}}
:root[data-theme="dark"] {{
  --bg: #1E1A18; --panel: #262120; --ink: #F0E7DE; --muted: #B3A69C;
  --rule: #453B37; --parchment: #322A27;
}}
:root[data-theme="dark"] .banner {{ background: #3A2320; }}
:root[data-theme="dark"] .banner.ok {{ background: #24301F; }}
:root[data-theme="dark"] .banner.neutral {{ background: #322A27; }}
:root[data-theme="dark"] td.hl {{ background: #3A2320; }}
:root[data-theme="dark"] figure svg {{ background: #F7F2EC; }}
"""

    c2, c3 = hv["ours"]["C2"], hv["ours"]["C3"]
    their_hv_aupr = [hv["their"][m]["curve"]["aupr"] for m in MODELS]
    their_test_aupr = [r["aupr_recovered"] / 100 for r in t2]
    their_err = [r for r in d["error_profile"] if r["kind"] == "their"]
    our_err = [r for r in d["error_profile"] if r["kind"] == "ours"]
    gl = [r for r in d["per_category"] if r["category"] == "Governing Law"][0]
    gl_their_prec = [gl["their"][m]["precision"] for m in MODELS]
    iv = d["bootstrap"]["intervals"]
    body = f"""<div class="wrap">
<h1>Study 008 beside the CUAD paper: which comparisons are legitimate?</h1>
<p class="sub-title">Three sets of numbers now exist. Two of them can be put on the same axes; only one of those two means what a reader will assume it means; the comparison that would settle the question has not been run and cannot be run before gate&nbsp;G4.</p>

<div class="verdicts">
<div class="verdict yes">
<h4><span class="flag yes">legitimate</span>Their published performance, reproduced exactly</h4>
<p>CUAD's three released checkpoints score AUPR {f(t2[0]['aupr_recovered'], 3)} / {f(t2[1]['aupr_recovered'], 3)} / {f(t2[2]['aupr_recovered'], 3)} against published {f(t2[0]['aupr_published'], 1)} / {f(t2[1]['aupr_published'], 1)} / {f(t2[2]['aupr_published'], 1)} on the official <code>test</code> split ({cmp_['test_questions']:,} questions, {cmp_['test_categories']} categories). This is the honest reference for what a task-specific fine-tuned extractor achieves. It says nothing about us.</p>
</div>
<div class="verdict no">
<h4><span class="flag no">ceiling only</span>Same scorer, but a memorised opponent &mdash; their models vs ours on <code>harness_val</code></h4>
<p>Same scorer, same contracts, same {cmp_['hv_categories']} categories &mdash; and their models were <strong>fine-tuned on these contracts</strong>. Their AUPR here is {rng(their_hv_aupr)} against their honest {rng(their_test_aupr)}, with the published model ordering scrambled. Usable as a <strong>memorised ceiling</strong> and as a diagnostic on annotation convention. <strong>Not</strong> usable to say who is better.</p>
</div>
<div class="verdict missing">
<h4><span class="flag missing">does not exist</span>Their published numbers vs our numbers</h4>
<p>Different contracts, different category set ({cmp_['test_categories']} vs {cmp_['hv_categories']}), different gold pool. There is no arithmetic that makes AUPR {f(t2[1]['aupr_recovered'], 1)} on <code>test</code> comparable to precision {f(c3['precision'], 3)} on <code>harness_val</code>. The clean comparison needs our committed decision on <code>test</code>, which is sealed until gate G4.</p>
</div>
</div>

<div class="card">
<div class="meta">
<span><b>Our model:</b> <code>{e(run['model'])}</code> via {e(run['backend'])}</span>
<span><b>Temperature:</b> {run['temperature']}</span>
<span><b>Seeds:</b> {', '.join(str(s) for s in run['seeds'])} &mdash; 3 per contract per condition</span>
<span><b>Repair:</b> off (<code>max_repair_attempts = {run['max_repair_attempts']}</code>)</span>
<span><b><code>max_output_tokens</code>:</b> {run['max_output_tokens']:,}</span>
<span><b>Schema variant:</b> <code>{e(run['schema_variant'])}</code></span>
<span><b>Principle set:</b> <code>{e(run['principle_set_version'])}</code> (w01&ndash;w10)</span>
<span><b>Harness:</b> <code>{e(run['harness_git_sha'])}</code></span>
<span><b>Split:</b> <code>{e(run['split'])}</code></span>
<span><b>Scorer:</b> <code>data/raw/evaluate.py</code>, unmodified import</span>
</div>
<p style="margin-bottom:0"><strong>Tinker does not honour seeds.</strong> Seeds 0/1/2 are repetition labels, not reproducibility handles; individual trials cannot be re-rolled. C2 = task definition + principles; C3 = task definition + principles + a required citation of the principle relied on.</p>
</div>

<h2>1. Their Table 2, published against reproduced</h2>
<p>Recovered by running CUAD's own <code>evaluate.py</code> completely unmodified over the authors' own shipped <code>nbest_predictions_.json</code> and their own <code>test.json</code> &mdash; {cmp_['test_questions']:,} questions, 102 contracts &times; {cmp_['test_categories']} categories, no inference run and none of our splits loaded. Values are percentages.</p>
{table(["model", "AUPR pub.", "AUPR rec.", "&Delta;", "P@80%R pub.", "P@80%R rec.", "&Delta;", "P@90%R pub.", "P@90%R rec.", "&Delta;", "max recall"], t2_rows)}
<div class="banner ok">
<p><strong>Gate: PASS.</strong> Every delta is smaller than the rounding step of the published table &mdash; the largest is RoBERTa-large's AUPR at {f(t2[1]['aupr_recovered'] - t2[1]['aupr_published'], 4, plus=True)} pp. This is the same computation on the same bytes, so the scoring path is isolated and confirmed.</p>
<p style="margin-bottom:0">The published <code>0.0</code> at P@90%R for both RoBERTas means <em>90% recall is unreachable</em> (max recall {f(t2[0]['max_recall'], 3)} and {f(t2[1]['max_recall'], 3)}), not that precision collapsed. DeBERTa reaches {f(t2[2]['max_recall'], 3)} and is the only model with a non-zero figure there. What this does <em>not</em> establish is that our re-run of their weights reproduces their inference &mdash; that check is a <code>test</code>-split operation and stays sealed.</p>
</div>

<h2>2. Their honest reference &mdash; the curve, and their Figure 4</h2>
<p>The precision&ndash;recall curves on the official <code>test</code> split, plotted from the checked-in 102-point sweep using the <strong>interpolated-precision</strong> column their <code>get_aupr</code> integrates and their P@R figures read off. Hollow markers are the exact operating points at 80% recall.</p>
<figure>
{fig_test_curves(d)}
<figcaption><strong>Figure 1.</strong> CUAD Table 2 models on the official <code>test</code> split &mdash; 102 contracts they never trained on, all {cmp_['test_categories']} categories. This is the only figure on this page that carries the CUAD paper's honest published performance. <strong>No point of ours belongs on these axes</strong>: our numbers are on different contracts and {cmp_['hv_categories']} categories.</figcaption>
</figure>

<h3>Their Figure 4, recomputed &mdash; and why we cannot appear in it</h3>
<p>The CUAD paper's Figure&nbsp;4 is captioned &ldquo;<em>{e(d['figure4a']['paper_presentation']['caption'])}</em>&rdquo;: per-category AUPR, a <strong>single model</strong> (DeBERTa-xlarge), horizontal bars, sorted descending. Figure&nbsp;2 below matches that presentation, recomputed from the authors' shipped predictions with <strong>exact-match</strong> category subsetting rather than <code>evaluate.py</code>'s substring filter &mdash; the substring filter leaks on <code>Insurance</code> (102 exact questions against 142 substring matches), and exact match is the correct subsetting.</p>
<p><strong>No bar of ours belongs on this axis &mdash; not because an AUPR is impossible for us, but because this run has no ranking to sweep.</strong> AUPR summarises a threshold sweep over <em>scored</em> candidates; their extractive head emits a top-20 candidate list per question with probabilities, swept by one global threshold. Our output contract emits a single committed decision with no score attached, which is a <strong>design choice in the contract</strong> rather than a property of prompting &mdash; D-32 was corrected on this point on 2026-08-17, and <code>plans/comparability-plan.md</code> records what producing a ranking would take (sampling frequency, sequence logprob, or teacher-forced candidate likelihood via Tinker's <code>TopKPromptLogprobs</code>) and why the resulting AUPR would be a fair <em>system-level</em> comparison rather than a like-for-like measurement of the same construct. Until that exists, Figure&nbsp;5 below is the closest comparable per-category view we can honestly draw &mdash; micro-F1 at the operating point, on <code>harness_val</code> &mdash; and it is a different quantity on a different split, which is why it is a separate figure rather than extra bars here.</p>
<figure>
{fig_paper_figure4(d)}
<figcaption><strong>Figure 2.</strong> Their Figure&nbsp;4, recomputed: per-category AUPR for DeBERTa-v2-xlarge on the official <code>test</code> split, all {len(d['figure4a']['rows'])} categories, sorted descending as they sort. Terracotta bars are the {cmp_['hv_categories']} categories study 008 works on. Bar <em>values</em> could not be read from the published PDF &mdash; only their category ordering &mdash; so this is a recomputation matching their presentation, not a pixel-level match.</figcaption>
</figure>
<div class="banner neutral">
<p style="margin-top:0"><strong>Two things fall out of the overlay, and both belong in the interpretation.</strong></p>
<p><strong>Our 12 categories are the easy end of their 41.</strong> Mean AUPR {f(d['figure4a']['subset_mean_aupr'], 3)} across our subset against {f(d['figure4a']['rest_mean_aupr'], 3)} across the other {len(d['figure4a']['rows']) - cmp_['hv_categories']}; nine of our twelve sit in the top half of their ranking, including their three best-performing clause types. <strong>Any absolute number we report on this subset is flattered relative to a full-corpus result</strong>, and a future <code>test</code>-split comparison must either recompute their side on the same 12 or be read as category-mismatched.</p>
<p><strong>Our recomputed ordering is not their published ordering.</strong> Rank agreement is Spearman &rho;&nbsp;=&nbsp;{f(d['figure4a']['rank_agreement_spearman'], 3)} over the {d['figure4a']['n_ranked_together']} categories their figure labels &mdash; strong at the top (their top five and ours share four members) and loose in the middle: we place Source Code Escrow at #{[r['our_rank'] + 1 for r in d['figure4a']['rows'] if r['category'] == 'Source Code Escrow'][0]} against their #{[r['paper_rank'] + 1 for r in d['figure4a']['rows'] if r['category'] == 'Source Code Escrow'][0]}, and Volume Restriction at #{[r['our_rank'] + 1 for r in d['figure4a']['rows'] if r['category'] == 'Volume Restriction'][0]} against their #{[r['paper_rank'] + 1 for r in d['figure4a']['rows'] if r['category'] == 'Volume Restriction'][0]}. The pooled Table&nbsp;2 figures reproduce to four decimal places, so the scoring path is not in doubt; the per-category divergence is unexplained and is a caveat on Figure&nbsp;2, not on &sect;1.</p>
<p style="margin-bottom:0"><strong>Their figure plots 40 categories, not 41.</strong> The caption and body say all 41; the axis carries {len(d['figure4a']['paper_presentation']['order'])} labels. The one absent is <code>{e(d['figure4a']['not_in_paper_figure'][0])}</code>, which scores AUPR 0.000 for all three released checkpoints in our reproduction. We plot it, at zero.</p>
</div>

<h2>3. The <code>harness_val</code> head-to-head &mdash; and why the banner matters more than the figure</h2>

<div class="banner">
<p><strong>These are memorised scores. Read the figure as a ceiling, not as an opponent.</strong> The {cmp_['their_contracts']} <code>harness_val</code> contracts sit inside CUAD's official <em>train</em> split, i.e. inside these three checkpoints' fine-tuning data. Their AUPR here is {' / '.join(f(a, 3) for a in their_hv_aupr)} against the reproduced Table 2 values of {f(t2[0]['aupr_recovered'] / 100, 3)} / {f(t2[1]['aupr_recovered'] / 100, 3)} / {f(t2[2]['aupr_recovered'] / 100, 3)}, and the model ordering is scrambled relative to the published one. Nothing in this section is evidence that our system is better or worse than theirs.</p>
<p style="margin-bottom:0"><strong>Second caveat, equally load-bearing.</strong> At any single confidence threshold their models emit <strong>at most one span per question</strong>. On categories whose gold carries several spans per contract &mdash; License Grant averages {f([r for r in d['per_category'] if r['category'] == 'License Grant'][0]['gold_spans_per_question'], 2)} gold spans per gold-present question here, Source Code Escrow {f([r for r in d['per_category'] if r['category'] == 'Source Code Escrow'][0]['gold_spans_per_question'], 2)} &mdash; their recall is structurally capped near 1&thinsp;/&thinsp;spans-per-question. Their apparent weakness there is an artifact of the comparison. That is why every per-category number below is reported at two thresholds.</p>
</div>

<figure>
{fig_headtohead(d)}
<figcaption><strong>Figure 3.</strong> Identical axes, identical scorer (<code>evaluate.py</code>, IOU&nbsp;0.5), the same {cmp_['hv_categories']} categories, on <code>harness_val</code>. Dashed lines trace each of their models across the confidence sweep (0.1 &rarr; 0.9); the enlarged marker is conf&nbsp;{d['headline_conf']:g}, their committed decision. Diamonds are our C2 and C3, which have no threshold to sweep; faint dots are our per-seed points. <strong>Their curves are memorised; the vertical gap to our diamonds is not a quality gap.</strong></figcaption>
</figure>

{table(["system", "AUPR", "P@80%R", "P@90%R", "max recall", f"precision @{d['headline_conf']:g}", f"recall @{d['headline_conf']:g}", "TP / FP / FN"], pooled_rows)}

<p>Our C2 sits at precision {f(c2['precision'], 3)} / recall {f(c2['recall'], 3)} and C3 at {f(c3['precision'], 3)} / {f(c3['recall'], 3)} &mdash; between their conf&nbsp;0.5 and conf&nbsp;0.7 points. A 9B general model with a prompt lands at the same operating point as a fine-tuned extractor that has been shown the key for these documents. That is interesting; it is not a capability claim, because the two sides reach that point through completely different errors (&sect;5).</p>

<div class="banner neutral">
<p style="margin-top:0"><strong>The two sides' question pools are not quite identical, and the reviews do not say so.</strong> Their run covers all {cmp_['their_contracts']} <code>harness_val</code> contracts ({cmp_['their_questions']} questions, {cmp_['their_gold_present']} gold-present, {cmp_['their_gold_spans']} gold spans). Ours covers the {cmp_['our_contracts']}-contract C2&cap;C3 intersection over 3 seeds, and per-trial dropout (parse failures, API errors) removes further question sets: C2 scores {c2['n_trials']} trials / {c2['n_questions']:,} questions, C3 {c3['n_trials']} / {c3['n_questions']:,}. The resulting gold-present share differs &mdash; {cmp_['their_gold_present_share'] * 100:.1f}% for them against {cmp_['our_gold_present_share']['C2'] * 100:.1f}% (C2) and {cmp_['our_gold_present_share']['C3'] * 100:.1f}% (C3) for us. Small, but it means &sect;3&ndash;&sect;5 are same-scorer and same-category rather than strictly same-question.</p>
</div>

<h2>4. Per category, where the diagnostic value is</h2>
<p>Both operating points are shown because neither alone is honest. conf&nbsp;0.5 is their committed decision and the like-for-like point against our single-answer harness; conf&nbsp;0.1 lets them emit multiple spans and is the point at which multi-span categories become interpretable.</p>

<figure>
{fig_per_category(d)}
<figcaption><strong>Figure 4.</strong> Precision and recall by category on <code>harness_val</code>, RoBERTa-large at both thresholds against our C2 and C3. Categories are ordered by gold spans per question (Agreement Date {f(d['per_category'][0]['gold_spans_per_question'], 2)} at the top, Source Code Escrow {f(d['per_category'][-1]['gold_spans_per_question'], 2)} at the bottom). The three findings called out below are the rows where the horizontal spread is widest.</figcaption>
</figure>

{table(["category", "gold spans/Q", "gold present / absent Q", "RoBERTa-base @0.5", "RoBERTa-large @0.5", "DeBERTa @0.5", "RoBERTa-large @0.1", "our C2", "our C3"], cat_rows)}
<p class="sub" style="font-size:14.5px">Cells are precision&thinsp;/&thinsp;recall. Highlighted cells mark the three findings below. <code>&mdash;</code> where a model made no prediction at all in that category.</p>

<h3>The comparable per-category view &mdash; our stand-in for their Figure 4</h3>
<p>Figure&nbsp;2 is an AUPR axis and we cannot stand on it. This is the nearest thing we can draw honestly: per-category <strong>micro-F1 at the operating point</strong> &mdash; the pinned headline aggregate &mdash; for their three models at their committed threshold and for our C2 and C3, on <code>harness_val</code>, through the same scorer. It is a different quantity from their Figure&nbsp;4 (a point, not an area under a sweep) on a different split, which is why it is a second figure rather than extra bars on the first. Categories are ordered by their <code>test</code>-split AUPR, so the two figures can be read against each other by eye.</p>
<div class="banner">
<p style="margin:0"><strong>Their bars in Figure 5 are memorised.</strong> Every <code>harness_val</code> contract is inside these checkpoints' fine-tuning data. A taller bar of theirs is not evidence that their model is better than ours &mdash; it is the ceiling a model reaches when it has been shown the answers, which is exactly what makes it useful as a target and useless as an opponent.</p>
</div>
<figure>
{fig_f1_by_category(d)}
<figcaption><strong>Figure 5.</strong> Micro-F1 at the operating point, by category, on <code>harness_val</code>. Their three models at conf&nbsp;{d['headline_conf']:g}; the vertical rule marks their best F1 at conf&nbsp;{d['open_conf']:g}, the open threshold at which multi-span categories become interpretable. Pooled, the same quantity is {f(d['figure4b']['pooled_f1']['RoBERTa-base'], 3)} / {f(d['figure4b']['pooled_f1']['RoBERTa-large'], 3)} / {f(d['figure4b']['pooled_f1']['DeBERTa-v2-xlarge'], 3)} for them and {f(d['figure4b']['pooled_f1']['C2'], 3)} / {f(d['figure4b']['pooled_f1']['C3'], 3)} for our C2 / C3.</figcaption>
</figure>

<h3>Finding 1 &mdash; Expiration Date expressed as a duration: they get it, we do not</h3>
<p>Presence recall / span-IOU recall by gold-span class, at conf&nbsp;{d['headline_conf']:g}. Their models handle duration-expressed expiration terms at {f(d['expiration'][1]['their']['RoBERTa-base']['presence_recall'], 2)}&ndash;{f(d['expiration'][1]['their']['RoBERTa-large']['presence_recall'], 2)} presence recall; ours score {f(d['expiration'][1]['ours']['C2']['presence_recall'], 2)} and {f(d['expiration'][1]['ours']['C3']['presence_recall'], 2)}. Three architectures at three scales, trained on this corpus, all converge on &ldquo;the clause that fixes the term answers the Expiration Date question, however it fixes it&rdquo; &mdash; so the annotation convention is real and learnable, and our miss is a convention miss, not a reading-comprehension failure.</p>
{table(["gold span class", "n spans", "RoBERTa-base", "RoBERTa-large", "DeBERTa-v2-xlarge", "our C2", "our C3"], exp_rows)}
<p>Note the calendar-date row, which is the trap: our presence recall there is 1.00 and our span-IOU recall {f(d['expiration'][0]['ours']['C2']['span_iou_recall'], 2)} / {f(d['expiration'][0]['ours']['C3']['span_iou_recall'], 2)} against their 1.00. On the cases we do claim, the span fails the IOU bar because our prompt clips the answer to the bare date value while the gold span is a whole sentence. Fixing the duration false-absents without also widening the span would buy presence and lose it again at the IOU gate.</p>

<h3>Finding 2 &mdash; Governing Law precision: {rng(gl_their_prec, 2)} theirs, {f(d['per_category'][1]['ours']['C2']['precision'], 2)} ours</h3>
<p>Their precision is {f(d['per_category'][1]['their']['RoBERTa-base']['precision'], 2)}&ndash;{f(d['per_category'][1]['their']['RoBERTa-large']['precision'], 2)}; ours is {f(d['per_category'][1]['ours']['C2']['precision'], 2)} (C2) and {f(d['per_category'][1]['ours']['C3']['precision'], 2)} (C3), on {d['per_category'][1]['ours']['C2']['fp']} and {d['per_category'][1]['ours']['C3']['fp']} false positives. Every one of those false positives falls on a <em>gold-present</em> question ({d['per_category'][1]['ours']['C2']['fp_on_gold_absent_questions']} on gold-absent questions), so we are not failing to find the clause &mdash; we are adding venue, forum and arbitration clauses beside it. Their models were trained on annotations that exclude those, and they exclude them. This is independent corroboration of the same convention that principle <code>w03</code> exists to state, and <code>w03</code> is the one record in the working set with <code>checker_status: usable</code>. It is not yet fixing this: C2 and C3 carry essentially the same false positives.</p>

<h3>Finding 3 &mdash; Volume Restriction is poor for everyone</h3>
<p>They reach recall {f(d['per_category'][9]['their']['RoBERTa-base']['recall'], 2)}&ndash;{f(d['per_category'][9]['their']['RoBERTa-large']['recall'], 2)} only by holding precision at {f(d['per_category'][9]['their']['RoBERTa-base']['precision'], 2)}&ndash;{f(d['per_category'][9]['their']['DeBERTa-v2-xlarge']['precision'], 2)}; at conf&nbsp;0.1 RoBERTa-large is {pr(d['per_category'][9]['their']['RoBERTa-large']['open']['precision'], d['per_category'][9]['their']['RoBERTa-large']['open']['recall'])}. We score {pr(d['per_category'][9]['ours']['C2']['precision'], d['per_category'][9]['ours']['C2']['recall'])} and {pr(d['per_category'][9]['ours']['C3']['precision'], d['per_category'][9]['ours']['C3']['recall'])}. <strong>A model that memorised this corpus cannot make Volume Restriction precise either</strong>, which is the strongest available evidence that the category's boundary is genuinely disputed in the gold rather than merely hard for us. It is a reason not to write a principle for it off this split.</p>

<h2>5. The error profiles differ in kind, not degree</h2>
<p>This is the part of the comparison that survives the memorisation caveat, because it is about the <em>shape</em> of the mistakes rather than their count.</p>
<figure>
{fig_error_profile(d)}
<figcaption><strong>Figure 6.</strong> Where each system's false positives land, on <code>harness_val</code> at their conf&nbsp;{d['headline_conf']:g}. Right-hand column: decline rate (gold-present questions answered with nothing) and over-claim rate (gold-absent questions answered with something).</figcaption>
</figure>
{table(["system", "declines on gold-present Q", "over-claims on gold-absent Q", "FP on gold-absent Q", "FP on gold-present Q", "total FP"], err_rows)}
<p><strong>Their false positives are {rng([r['fp_absent_share'] for r in their_err], pct=True)} over-claims on gold-absent questions, with near-perfect span boundaries. Ours are {rng([r['fp_present_share'] for r in our_err], pct=True)} wrong boundaries on gold-present questions.</strong> The decline rates are nearly identical &mdash; {rng([r['decline_rate'] for r in their_err], pct=True)} theirs against {rng([r['decline_rate'] for r in our_err], pct=True)} ours &mdash; so both systems lose about the same recall to silence and then differ completely in what they do when they speak. We over-claim on {rng([r['overclaim_rate'] for r in our_err], pct=True)} of gold-absent questions against their {rng([r['overclaim_rate'] for r in their_err], pct=True)}.</p>
<p>Read as system character: <strong>conservative-and-sloppy-bounded</strong> against <strong>aggressive-and-precisely-bounded</strong>. That tracks the task framings exactly. Ours is prompted for a committed decision that has to be defensible, including a decision to say nothing; theirs is a recall-first shortlist for a human reviewer, swept over a threshold. It also means span fidelity and absence discipline are separable problems for us &mdash; any principle that improves boundaries is not in tension with the absence machinery, which is the half already working.</p>

<h2>6. Our own contrast, C2 vs C3, is a null</h2>
<figure>
{fig_bootstrap(d)}
<figcaption><strong>Figure 7.</strong> C3&nbsp;&minus;&nbsp;C2 under a paired contract-level bootstrap (10,000 resamples, {d['bootstrap']['method']['n_contracts']} contracts, per-contract counts seed-averaged before aggregation). Dot is the point estimate, bar is the 95% percentile interval.</figcaption>
</figure>
<p>On the registered headline metric &mdash; CUAD-scorer micro-F1 &mdash; the difference is <strong>{f(iv['micro_f1']['delta'], 4, plus=True)} [{f(iv['micro_f1']['ci_low'], 4, plus=True)}, {f(iv['micro_f1']['ci_high'], 4, plus=True)}]</strong>. Recall is {f(iv['recall']['delta'], 4, plus=True)} [{f(iv['recall']['ci_low'], 4, plus=True)}, {f(iv['recall']['ci_high'], 4, plus=True)}]. Precision is {f(iv['precision']['delta'], 4, plus=True)} with an interval whose lower bound sits on zero.</p>
<p><strong>The precision interval is not stable across RNG seeds, so it is not a conclusion.</strong> Re-running the identical bootstrap under other seeds and at 100,000 resamples flips the verdict in the fourth decimal place, and it does not converge with more resamples &mdash; the bound <em>is</em> at zero, and {d['bootstrap']['method']['n_contracts']} contracts is not enough data to place it.</p>
{table(["resamples", "RNG seed", "CI low", "CI high", "draws &gt; 0", "verdict"], stab_rows)}
<p>The underlying false-positive movement is a coin flip: down on 16 contracts, up on 14, flat on 8. By category, Exclusivity alone is 35% of the net reduction and Governing Law brings the pair to 57% &mdash; a description of where the noise sits, not an effect decomposition.</p>
{table(["category", "C2 FP (seed-avg)", "C3 FP (seed-avg)", "&Delta; seed-avg", "&Delta; raw"], fp_cat_rows)}
<p class="sub" style="font-size:14.5px">C3 cited a principle on {d['citation']['C3']['rate'] * 100:.1f}% of its {d['citation']['C3']['n_decisions']:,} decisions, with zero leakage of principle text into the extracted spans. Citation compliance is high; citation <em>correctness</em> is unestablishable in this run &mdash; no applicability source was loaded.</p>

<h2>7. The comparison that would settle it, and what it needs</h2>
<p>The clean comparison is: <strong>our committed decision and their released checkpoints, both on the official <code>test</code> split, both scored by <code>evaluate.py</code>, on the same category set.</strong> It does not exist yet. Concretely it requires:</p>
<ul>
<li><strong>Gate G4</strong> &mdash; a deliberate human go/no-go opening the {cmp_['test_questions'] // cmp_['test_categories']}-contract <code>test</code> split, which no part of this study has loaded. Everything on this page is pre-G4 development evidence.</li>
<li><strong>Our run on <code>test</code></strong> at whatever condition the ladder settles on. As the output contract stands that produces one committed-decision point rather than a curve; adding a candidate score would produce a curve, at the cost of the comparison becoming system-level rather than like-for-like.</li>
<li><strong>A decision on the category axis.</strong> Their published figures pool {cmp_['test_categories']} categories; we run {cmp_['hv_categories']}. A {cmp_['hv_categories']}-category recomputation of their side is a different quantity from Table&nbsp;2 and must never be printed beside it. Either we recompute theirs at {cmp_['hv_categories']} from their shipped predictions, or the comparison is category-mismatched and inadmissible &mdash; and Figure&nbsp;2 shows the mismatch is not neutral: our {cmp_['hv_categories']} average AUPR {f(d['figure4a']['subset_mean_aupr'], 3)} for their best model against {f(d['figure4a']['rest_mean_aupr'], 3)} for the categories we left out.</li>
<li><strong>An aggregate that both sides can occupy.</strong> Their headline is AUPR; we do not have one <em>yet</em> &mdash; it needs a scored ranking our output contract does not currently emit, and <code>plans/comparability-plan.md</code> costs out the three ways to get one. Micro-F1 at the operating point is the aggregate both sides can stand on, and it is what &sect;4's Figure&nbsp;5 uses &mdash; but a single committed point compared against a model free to pick a threshold favours whoever chose better, and the pre-registration should fix which of their operating points is the reference before the split opens.</li>
<li><strong>An honest treatment of the single-point-versus-curve mismatch.</strong> As long as we report a point and they report a curve, where our point lands relative to their <em>operating points</em> is the only defensible reading, and the pre-registration on that should stand before the split opens.</li>
</ul>
<p>Until then, the memorised-ceiling comparison is what we have, and it answers a different question: not &ldquo;are we good&rdquo; but &ldquo;what does competence on this annotation convention look like, and which of our gaps are convention gaps.&rdquo;</p>

<h2>8. Reading</h2>
<p>The honest summary of this page is that it contains one confirmed reproduction, one diagnostic, and one null &mdash; and no result about whether our approach works. The reproduction is solid and does exactly one job: it certifies the scoring path, so that when a real comparison becomes available the scorer will not be the thing in doubt. The diagnostic is genuinely informative but only in one direction. Where their memorised models are near-perfect and we are not &mdash; duration-expressed Expiration Dates at {f(d['expiration'][1]['their']['RoBERTa-large']['presence_recall'], 2)} against {f(d['expiration'][1]['ours']['C2']['presence_recall'], 2)}, Governing Law precision {f(d['per_category'][1]['their']['RoBERTa-large']['precision'], 2)} against {f(d['per_category'][1]['ours']['C2']['precision'], 2)} &mdash; we learn that the CUAD annotation convention is learnable and that we have not learned it, which is actionable. Where <em>nobody</em> does well, as in Volume Restriction, we learn something about the gold rather than about any model. But where we appear to beat them, at conf&nbsp;0.5 on the multi-span categories, the advantage mostly evaporates at conf&nbsp;0.1, and even the residue &mdash; License Grant, where they do not overtake us at any threshold &mdash; is a comparison against a model that was shown these answers in training. It cannot be cashed as a win.</p>
<p>Figure&nbsp;2 adds a caution that applies to every absolute number on this page, including ones that will survive to <code>test</code>. The twelve categories this study works on are the easy end of CUAD: their best model averages AUPR {f(d['figure4a']['subset_mean_aupr'], 3)} across our subset and {f(d['figure4a']['rest_mean_aupr'], 3)} across the {len(d['figure4a']['rows']) - cmp_['hv_categories']} we excluded, with nine of our twelve in the top half of their ranking. The subset was chosen for other reasons &mdash; annotation tractability and principle coverage &mdash; but the consequence is the same: a precision of {f(c3['precision'], 3)} here is not a precision of {f(c3['precision'], 3)} on CUAD, and any headline we eventually publish has to say which twelve.</p>
<p>The C2/C3 contrast is a null, and it should be reported as one. Micro-F1 moves {f(iv['micro_f1']['delta'], 4, plus=True)} with an interval from {f(iv['micro_f1']['ci_low'], 4, plus=True)} to {f(iv['micro_f1']['ci_high'], 4, plus=True)}; the precision effect that looked promising flips sign-of-verdict across RNG seeds. Two things bound how much that null can be made to mean. First, {d['bootstrap']['method']['n_contracts']} contracts is the binding constraint, not the effect size &mdash; a better-powered run could still separate the arms, and Exclusivity is where to look. Second, and more limiting: the principle set is <strong>unselected</strong>. Nine of its ten records carry <code>checker_status: needs_rebuild</code>, so what C3 actually tests is the <em>citation requirement</em> layered on an unvetted set, not the principles. A null here is evidence about requiring a citation. It is close to no evidence about whether good principles help.</p>
<p>Which points at what this study's result will actually be. It is not any comparison to the CUAD paper's models &mdash; those are a fixed reference, one honest and one memorised, and neither is the thing under test. The result is the <strong>iteration-0-to-ladder delta</strong>: whether principled iteration moves our own numbers on our own split, measured against our own starting point, with the CUAD scorer holding the measurement fixed. The three findings in &sect;4 are useful precisely because they are hypotheses for that ladder &mdash; the Expiration Date convention, the Governing Law exclusion, the span-width clipping &mdash; each with a memorised model's behaviour as an existence proof that the target is reachable. That is what this page licenses. Nothing on it licenses a claim that we beat CUAD's models, or that they beat us.</p>

<footer>
<p>Generated by <code>scripts/render_baseline_comparison.py</code> from <code>reviews/baseline-comparison-data.json</code>, built by <code>scripts/build_baseline_comparison_data.py</code> from <code>data/cuad-baseline/</code> and <code>reviews/c2-c3-bootstrap-data.json</code>. The published Figure&nbsp;4 category ordering is pinned in <code>data/cuad-baseline/paper_figure4_category_order.json</code>, read from the arXiv PDF's figure axis; no bar values were taken from the paper. Underlying reviews: <code>reviews/cuad-table2-reproduction.md</code>, <code>reviews/cuad-baseline-on-train-splits.md</code>, <code>reviews/c2-c3-bootstrap.md</code>. The official <code>test</code> split was never loaded; the reproduction reads only the authors' released predictions and their shipped <code>test.json</code>.</p>
<p>CUAD (the Contract Understanding Atticus Dataset), its released checkpoints, its <code>evaluate.py</code> and the gold annotations used throughout are the work of <strong>The Atticus Project</strong> and are licensed <strong>CC BY 4.0</strong>. Cite: Dan Hendrycks, Collin Burns, Anya Chen, Spencer Ball, &ldquo;CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review&rdquo;, NeurIPS 2021 Datasets and Benchmarks Track &mdash; <code>arXiv:2103.06268</code> (<code>hendrycks2021cuad</code>).</p>
<p>AI Assistant Used: Claude Code.</p>
</footer>
</div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Study 008 beside CUAD &mdash; which comparisons are legitimate</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def main():
    with open(DATA) as fh:
        d = json.load(fh)
    OUT.write_text(build(d))
    print(f"wrote {OUT.relative_to(STUDY)} ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
