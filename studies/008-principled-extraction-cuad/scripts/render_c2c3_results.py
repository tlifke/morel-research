import html
import json
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]
DATA = STUDY / "reviews" / "c2-c3-results-data.json"
OUT = STUDY / "reviews" / "c2-c3-results.html"

C = {
    "terracotta": "#C1694F",
    "terracotta_dark": "#A3523A",
    "forest": "#2D5016",
    "green_light": "#4A7A2E",
    "parchment": "#F5E6D3",
    "cream_dark": "#E8D5BF",
    "dark_earth": "#3B2F2F",
    "off_white": "#FAFAF8",
    "error_red": "#C14F4F",
    "slate": "#3D6478",
    "mustard": "#B8821C",
    "mushroom": "#9C7676",
    "muted": "#6B5E5E",
}

MODEL_COLORS = {
    "RoBERTa-base": C["mushroom"],
    "RoBERTa-large": C["slate"],
    "DeBERTa-v2-xlarge": C["forest"],
}
COND_COLORS = {"C2": C["mustard"], "C3": C["terracotta"]}

W, H = 560, 420
PAD = {"l": 66, "r": 18, "t": 26, "b": 52}
PW = W - PAD["l"] - PAD["r"]
PH = H - PAD["t"] - PAD["b"]


def e(s):
    return html.escape(str(s))


def fmt(x, n=3, pct=False, plus=False):
    if x is None:
        return "&mdash;"
    v = x * 100 if pct else x
    s = f"{v:+.{n}f}" if plus else f"{v:.{n}f}"
    return s


def px(r):
    return PAD["l"] + r * PW


def py(p):
    return PAD["t"] + (1 - p) * PH


def axes(title_x="Recall (span-level, micro-pooled)", title_y="Precision"):
    parts = [f'<rect x="{PAD["l"]}" y="{PAD["t"]}" width="{PW}" height="{PH}" fill="#FFFFFF" stroke="{C["cream_dark"]}"/>']
    for i in range(11):
        v = i / 10
        x, y = px(v), py(v)
        parts.append(f'<line x1="{x:.1f}" y1="{PAD["t"]}" x2="{x:.1f}" y2="{PAD["t"]+PH}" stroke="{C["cream_dark"]}" stroke-width="0.6"/>')
        parts.append(f'<line x1="{PAD["l"]}" y1="{y:.1f}" x2="{PAD["l"]+PW}" y2="{y:.1f}" stroke="{C["cream_dark"]}" stroke-width="0.6"/>')
        if i % 2 == 0:
            parts.append(f'<text x="{x:.1f}" y="{PAD["t"]+PH+18}" text-anchor="middle" class="tick">{v:.1f}</text>')
            parts.append(f'<text x="{PAD["l"]-10}" y="{y+4:.1f}" text-anchor="end" class="tick">{v:.1f}</text>')
    parts.append(f'<text x="{PAD["l"]+PW/2:.0f}" y="{H-14}" text-anchor="middle" class="axlab">{e(title_x)}</text>')
    parts.append(f'<text x="16" y="{PAD["t"]+PH/2:.0f}" text-anchor="middle" class="axlab" transform="rotate(-90 16 {PAD["t"]+PH/2:.0f})">{e(title_y)}</text>')
    return "".join(parts)


def curve_figure(data):
    parts = [axes()]
    legend = []
    for i, (name, rows) in enumerate(data["cuad_curves"].items()):
        pts = " ".join(f"{px(r['recall']):.2f},{py(r['interpolated_precision']):.2f}" for r in rows)
        col = MODEL_COLORS[name]
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.2"/>')
        ly = PAD["t"] + 14 + i * 18
        legend.append(f'<line x1="{PAD["l"]+PW-150}" y1="{ly-4}" x2="{PAD["l"]+PW-128}" y2="{ly-4}" stroke="{col}" stroke-width="2.6"/>'
                      f'<text x="{PAD["l"]+PW-122}" y="{ly}" class="leg">{e(name)}</text>')
    for row in data["cuad_table2"]:
        op = row["operating_point_80"]
        if op:
            x, y = px(op["recall"]), py(op["interpolated_precision"])
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.4" fill="#FFFFFF" stroke="{MODEL_COLORS[row["model"]]}" stroke-width="1.8"/>')
    parts.append(f'<line x1="{px(0.8):.1f}" y1="{PAD["t"]}" x2="{px(0.8):.1f}" y2="{PAD["t"]+PH}" stroke="{C["muted"]}" stroke-width="1" stroke-dasharray="4 3"/>')
    parts.append(f'<text x="{px(0.8)-6:.1f}" y="{PAD["t"]+12}" text-anchor="end" class="note">R = 0.80</text>')
    parts.extend(legend)
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="CUAD precision-recall curves on the official test split">{"".join(parts)}</svg>'


def points_figure(data):
    parts = [axes()]
    ours = data["our_cuad_points"]
    for i, cond in enumerate(("C2", "C3")):
        col = COND_COLORS[cond]
        for seed, pt in ours["per_seed"][cond].items():
            parts.append(f'<circle cx="{px(pt["recall"]):.1f}" cy="{py(pt["precision"]):.1f}" r="3" fill="{col}" opacity="0.32"/>')
        p = ours["conditions"][cond]
        x, y = px(p["recall"]), py(p["precision"])
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="7" fill="{col}" stroke="#FFFFFF" stroke-width="2"/>')
        dy = -14 if cond == "C3" else 22
        parts.append(f'<text x="{x:.1f}" y="{y+dy:.1f}" text-anchor="middle" class="pointlab" fill="{col}">'
                     f'{cond} &#183; R {p["recall"]:.3f} / P {p["precision"]:.3f}</text>')
    ly = PAD["t"] + 14
    for i, cond in enumerate(("C2", "C3")):
        parts.append(f'<circle cx="{PAD["l"]+PW-152}" cy="{ly+i*18-4}" r="5" fill="{COND_COLORS[cond]}"/>'
                     f'<text x="{PAD["l"]+PW-140}" y="{ly+i*18}" class="leg">{cond} (pooled, 38 contracts)</text>')
    parts.append(f'<circle cx="{PAD["l"]+PW-152}" cy="{ly+36-4}" r="3" fill="{C["muted"]}" opacity="0.4"/>'
                 f'<text x="{PAD["l"]+PW-140}" y="{ly+36}" class="leg">per-seed points</text>')
    return f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Our C2 and C3 committed-decision points on harness_val">{"".join(parts)}</svg>'


FW, FH_ROW = 620, 26


def forest_figure(data):
    rows = [r for r in data["contrast"] if r["key"] not in ("completion_tokens", "prompt_tokens", "false_present", "false_absent")]
    n = len(rows)
    height = 46 + n * FH_ROW + 34
    lo = min(r["ci_low"] for r in rows)
    hi = max(r["ci_high"] for r in rows)
    span = max(abs(lo), abs(hi)) * 1.15
    left, right = 250, FW - 24
    width = right - left

    def X(v):
        return left + (v + span) / (2 * span) * width

    parts = [f'<rect x="0" y="0" width="{FW}" height="{height}" fill="#FFFFFF"/>']
    parts.append(f'<line x1="{X(0):.1f}" y1="30" x2="{X(0):.1f}" y2="{30+n*FH_ROW}" stroke="{C["dark_earth"]}" stroke-width="1.2"/>')
    for i, r in enumerate(rows):
        y = 30 + i * FH_ROW + FH_ROW / 2
        col = C["terracotta"] if r["excludes_zero"] else C["slate"]
        parts.append(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" class="frow">{e(r["label"])}</text>')
        parts.append(f'<line x1="{X(r["ci_low"]):.1f}" y1="{y:.1f}" x2="{X(r["ci_high"]):.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="2"/>')
        for b in (r["ci_low"], r["ci_high"]):
            parts.append(f'<line x1="{X(b):.1f}" y1="{y-4:.1f}" x2="{X(b):.1f}" y2="{y+4:.1f}" stroke="{col}" stroke-width="2"/>')
        parts.append(f'<circle cx="{X(r["delta"]):.1f}" cy="{y:.1f}" r="4" fill="{col}"/>')
    for v in (-round(span, 2), 0, round(span, 2)):
        parts.append(f'<text x="{X(v):.1f}" y="{30+n*FH_ROW+18}" text-anchor="middle" class="tick">{v:+.2f}</text>')
    parts.append(f'<text x="{(left+right)/2:.0f}" y="{height-4}" text-anchor="middle" class="axlab">C3 &minus; C2 (paired over 38 contracts, 95% bootstrap CI)</text>')
    parts.append(f'<text x="{left-12}" y="20" text-anchor="end" class="leg">metric</text>')
    return f'<svg viewBox="0 0 {FW} {height}" role="img" aria-label="Forest plot of C3 minus C2 differences">{"".join(parts)}</svg>'


CUAD_FW = 620


def cuad_forest_figure(data):
    boot = data["cuad_bootstrap"]["bootstrap"]
    rows = [("precision", "precision (C3 &minus; C2)"),
            ("recall", "recall (C3 &minus; C2)"),
            ("micro_f1", "micro-F1 (C3 &minus; C2)")]
    n = len(rows)
    height = 40 + n * 30 + 34
    span = max(max(abs(boot[k]["ci_low"]), abs(boot[k]["ci_high"])) for k, _ in rows) * 1.2
    left, right = 200, CUAD_FW - 24
    width = right - left

    def X(v):
        return left + (v + span) / (2 * span) * width

    parts = [f'<rect x="0" y="0" width="{CUAD_FW}" height="{height}" fill="#FFFFFF"/>']
    parts.append(f'<line x1="{X(0):.1f}" y1="24" x2="{X(0):.1f}" y2="{24+n*30}" stroke="{C["dark_earth"]}" stroke-width="1.2"/>')
    for i, (k, label) in enumerate(rows):
        r = boot[k]
        y = 24 + i * 30 + 15
        col = C["terracotta"] if r["excludes_zero"] else C["slate"]
        parts.append(f'<text x="{left-12}" y="{y+4:.1f}" text-anchor="end" class="frow">{label}</text>')
        parts.append(f'<line x1="{X(r["ci_low"]):.1f}" y1="{y:.1f}" x2="{X(r["ci_high"]):.1f}" y2="{y:.1f}" stroke="{col}" stroke-width="2.2"/>')
        for b in (r["ci_low"], r["ci_high"]):
            parts.append(f'<line x1="{X(b):.1f}" y1="{y-5:.1f}" x2="{X(b):.1f}" y2="{y+5:.1f}" stroke="{col}" stroke-width="2.2"/>')
        parts.append(f'<circle cx="{X(r["delta"]):.1f}" cy="{y:.1f}" r="4.2" fill="{col}"/>')
    for v in (-round(span, 2), 0, round(span, 2)):
        parts.append(f'<text x="{X(v):.1f}" y="{24+n*30+18}" text-anchor="middle" class="tick">{v:+.2f}</text>')
    parts.append(f'<text x="{(left+right)/2:.0f}" y="{height-4}" text-anchor="middle" class="axlab">C3 &minus; C2 under CUAD\'s scorer (paired bootstrap over 38 contracts, 95% percentile CI)</text>')
    return f'<svg viewBox="0 0 {CUAD_FW} {height}" role="img" aria-label="Forest plot of C3 minus C2 under the CUAD scorer">{"".join(parts)}</svg>'


def table(headers, rows, cls=""):
    th = "".join(f"<th>{h}</th>" for h in headers)
    trs = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f'<div class="tablewrap"><table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{trs}</tbody></table></div>'


def build(data):
    run = data["run"]
    ours = data["our_cuad_points"]
    la = data["level_a"]
    lb = data["level_b"]
    oc = data["outcomes"]
    cost = data["cost"]

    t2_rows = []
    for r in data["cuad_table2"]:
        t2_rows.append([
            f'<strong>{e(r["model"])}</strong>',
            f'{r["aupr_published"]:.1f}', f'<strong>{r["aupr_recovered"]:.3f}</strong>',
            f'{r["aupr_recovered"]-r["aupr_published"]:+.2f}',
            f'{r["p80_published"]:.1f}', f'<strong>{r["p80_recovered"]:.3f}</strong>',
            f'{r["p80_recovered"]-r["p80_published"]:+.2f}',
            f'{r["p90_published"]:.1f}', f'<strong>{r["p90_recovered"]:.3f}</strong>',
            f'{r["p90_recovered"]-r["p90_published"]:+.2f}',
            f'{r["max_recall"]:.3f}',
        ])

    contrast_rows = []
    for r in data["contrast"]:
        strong = r["excludes_zero"]
        d = f'{r["delta"]:+.4f}' if abs(r["delta"]) < 10 else f'{r["delta"]:+.0f}'
        ci = (f'[{r["ci_low"]:+.4f}, {r["ci_high"]:+.4f}]' if abs(r["delta"]) < 10
              else f'[{r["ci_low"]:+.0f}, {r["ci_high"]:+.0f}]')
        cell = lambda s: f"<strong>{s}</strong>" if strong else s
        contrast_rows.append([
            cell(e(r["label"])), r["n_contracts"], cell(d), cell(ci),
            "&mdash;" if r["t"] is None else f'{r["t"]:.2f}',
            f'{r["up"]}/{r["down"]}',
        ])

    cat_rows = []
    for cat in run["categories"]:
        a, b = data["per_category"]["C2"][cat], data["per_category"]["C3"][cat]
        below = (a["presence_f1"] < a["always_present_presence_f1"] and
                 b["presence_f1"] < b["always_present_presence_f1"])
        name = f'<strong class="warn">{e(cat)}</strong>' if below else e(cat)
        cat_rows.append([
            name,
            f'{a["counts"]["TP"]}/{a["counts"]["FP"]}/{a["counts"]["FN"]}/{a["counts"]["TN"]}',
            f'{b["counts"]["TP"]}/{b["counts"]["FP"]}/{b["counts"]["FN"]}/{b["counts"]["TN"]}',
            f'{a["presence_f1"]:.3f}', f'{b["presence_f1"]:.3f}',
            f'<span class="base">{a["always_present_presence_f1"]:.3f}</span>',
            f'{a["absent_f1"]:.3f}', f'{b["absent_f1"]:.3f}',
            f'<span class="base">{a["always_absent_absent_f1"]:.3f}</span>',
        ])

    la_rows = [
        ["TP / FP / FN / TN"] + [f'{la[c]["counts"]["TP"]} / {la[c]["counts"]["FP"]} / {la[c]["counts"]["FN"]} / {la[c]["counts"]["TN"]}' for c in ("C2", "C3")]
        + [f'0 / 0 / {la["C2"]["n_gold_present"]} / {la["C2"]["n_gold_absent"]}',
           f'{la["C2"]["n_gold_present"]} / {la["C2"]["n_gold_absent"]} / 0 / 0'],
        ["presence precision"] + [f'{la[c]["presence_precision"]:.3f}' for c in ("C2", "C3")] + ["0.000", f'{la["C2"]["always_present_decision_accuracy"]:.3f}'],
        ["presence recall"] + [f'{la[c]["presence_recall"]:.3f}' for c in ("C2", "C3")] + ["0.000", "1.000"],
        ["<strong>presence F1</strong>"] + [f'<strong>{la[c]["presence_f1"]:.3f}</strong>' for c in ("C2", "C3")] + ["<span class=\"base\">0.000</span>", f'<span class="base">{la["C2"]["always_present_presence_f1"]:.3f}</span>'],
        ["absent precision"] + [f'{la[c]["absent_precision"]:.3f}' for c in ("C2", "C3")] + [f'{la["C2"]["always_absent_decision_accuracy"]:.3f}', "0.000"],
        ["absent recall"] + [f'{la[c]["absent_recall"]:.3f}' for c in ("C2", "C3")] + ["1.000", "0.000"],
        ["<strong>absent F1</strong>"] + [f'<strong>{la[c]["absent_f1"]:.3f}</strong>' for c in ("C2", "C3")] + [f'<span class="base">{la["C2"]["always_absent_absent_f1"]:.3f}</span>', "<span class=\"base\">0.000</span>"],
        ["decision-kind accuracy"] + [f'{la[c]["decision_kind_accuracy"]:.3f}' for c in ("C2", "C3")] + [f'{la["C2"]["always_absent_decision_accuracy"]:.3f}', f'{la["C2"]["always_present_decision_accuracy"]:.3f}'],
        ["macro presence F1 (over 12 categories)"] + [f'{la[c]["macro_presence_f1"]:.3f}' for c in ("C2", "C3")] + ["&mdash;", "&mdash;"],
        ["macro absent F1 (over 12 categories)"] + [f'{la[c]["macro_absent_f1"]:.3f}' for c in ("C2", "C3")] + ["&mdash;", "&mdash;"],
        ["decisions scored"] + [str(la[c]["counts"]["n"]) for c in ("C2", "C3")] + ["&mdash;", "&mdash;"],
    ]

    lb_rows = [
        ["<strong>TP denominator (decisions)</strong>"] + [f'<strong>{lb[c]["tp_denominator"]}</strong>' for c in ("C2", "C3")],
        ["spans classified"] + [str(lb[c]["spans"]) for c in ("C2", "C3")],
        ["soft span precision"] + [f'{lb[c]["soft_precision"]:.3f}' for c in ("C2", "C3")],
        ["soft span recall"] + [f'{lb[c]["soft_recall"]:.3f}' for c in ("C2", "C3")],
        ["<strong>soft span F1</strong>"] + [f'<strong>{lb[c]["soft_f1"]:.3f}</strong>' for c in ("C2", "C3")],
        ["exact-match rate"] + [f'{lb[c]["exact_match_rate"]:.3f}' for c in ("C2", "C3")],
        ["verbatim exact"] + [f'{lb[c]["verbatim_exact"]} ({lb[c]["verbatim_exact_rate"]*100:.1f}%)' for c in ("C2", "C3")],
        ["verbatim normalised-only"] + [f'{lb[c]["verbatim_normalized_only"]} ({lb[c]["verbatim_normalized_only_rate"]*100:.1f}%)' for c in ("C2", "C3")],
        ["verbatim not-found"] + [f'{lb[c]["verbatim_not_found"]} ({lb[c]["verbatim_not_found_rate"]*100:.1f}%)' for c in ("C2", "C3")],
        ["multi-span ratio (pred/gold, mean over TP)"] + [f'{lb[c]["multi_span_ratio"]:.3f}' for c in ("C2", "C3")],
        ["FP-cell decisions / spans"] + [f'{lb[c]["fp_cell"]["decisions"]} / {lb[c]["fp_cell"]["spans"]}' for c in ("C2", "C3")],
        ["FP-cell verbatim not-found"] + [f'{lb[c]["fp_cell"]["not_found"]} ({lb[c]["fp_cell"]["not_found_rate"]*100:.1f}%)' for c in ("C2", "C3")],
    ]

    out_rows = [
        ["trials"] + [str(oc[c]["trials"]) for c in ("C2", "C3")],
        ["ok"] + [str(oc[c]["ok"]) for c in ("C2", "C3")],
        ["parse_failure"] + [f'{oc[c]["parse_failure"]} ({oc[c]["parse_failure"]/oc[c]["trials"]*100:.1f}%)' for c in ("C2", "C3")],
        ["api_error (transport, excluded)"] + [str(oc[c]["api_error"]) for c in ("C2", "C3")],
        ["infeasible_at_length"] + [str(oc[c]["infeasible_at_length"]) for c in ("C2", "C3")],
        ["<strong>truncated completions</strong>"] + [f'<strong>{oc[c]["truncated"]}</strong>' for c in ("C2", "C3")],
        ["<strong>conformance</strong> (ok / reached model)"] + [f'<strong>{oc[c]["ok"]}/{oc[c]["reached_model"]} = {oc[c]["conformance"]*100:.1f}%</strong>' for c in ("C2", "C3")],
        ["parse failures by stage"] + ["; ".join(f'{k} {v}' for k, v in sorted(oc[c]["parse_stages"].items())) for c in ("C2", "C3")],
    ]

    cite = data["citation"]
    cite_rows = [
        ["decisions scored"] + [str(cite[c]["n_decisions"]) for c in ("C2", "C3")],
        ["decisions with non-empty <code>principles_cited</code>"] + [f'<strong>{cite[c]["n_cited"]} ({cite[c]["rate"]*100:.1f}%)</strong>' for c in ("C2", "C3")],
        ["principle references leaked into free text"] + [str(cite[c]["leakage"]) for c in ("C2", "C3")],
    ]
    cite_dist = " &middot; ".join(f'<code>{e(k)}</code> {v}' for k, v in cite["C3"]["by_principle"].items())

    cost_rows = [
        ["prompt tokens per scored trial (mean)"] + [f'{cost[c]["prompt_tokens_mean"]:,.0f}' for c in ("C2", "C3")],
        ["completion tokens per scored trial (mean)"] + [f'{cost[c]["completion_tokens_mean"]:,.0f}' for c in ("C2", "C3")],
        ["latency per scored trial (mean)"] + [f'{cost[c]["latency_s_mean"]:.1f} s' for c in ("C2", "C3")],
        ["scored trials"] + [str(cost[c]["n"]) for c in ("C2", "C3")],
    ]
    rt = cost["run_totals"]

    trunc_rows = [[e(r["condition"]), r["seed"], e(r["bucket"]), f'{r["n_contract_tokens"]:,}',
                   f'<code>{e(r["contract_id"][:46])}&hellip;</code>', f'{e(r["outcome"])} / <code>{e(r["stage"])}</code>']
                  for r in data["truncations"]]

    ourpts = {c: ours["conditions"][c] for c in ("C2", "C3")}
    seed_rows = []
    for c in ("C2", "C3"):
        for s, pt in ours["per_seed"][c].items():
            seed_rows.append([c, s, pt["n_trials"], pt["tp"], pt["fp"], pt["fn"],
                              f'{pt["recall"]:.4f}', f'{pt["precision"]:.4f}'])

    catcuad_rows = []
    for cat in run["categories"]:
        a = ours["per_category"]["C2"][cat]
        b = ours["per_category"]["C3"][cat]
        f = lambda v: "&mdash;" if v is None else f"{v:.3f}"
        catcuad_rows.append([e(cat), f'{a["tp"]}/{a["fp"]}/{a["fn"]}', f(a["recall"]), f(a["precision"]),
                             f'{b["tp"]}/{b["fp"]}/{b["fn"]}', f(b["recall"]), f(b["precision"])])

    gp = ours["gold_profile"]

    cb = data["cuad_bootstrap"]
    cbm, cbb = cb["method"], cb["bootstrap"]
    boot_rows = []
    for key, label in (("precision", "precision"), ("recall", "recall"), ("micro_f1", "micro-F1")):
        r = cbb[key]
        boot_rows.append([
            label,
            f'{cb["point_seed_averaged"]["C2"][key]:.4f}',
            f'{cb["point_seed_averaged"]["C3"][key]:.4f}',
            f'<strong>{r["delta"]:+.4f}</strong>',
            f'[{r["ci_low"]:+.4f}, {r["ci_high"]:+.4f}]',
            f'{r["frac_above_zero"]*100:.2f}%',
            "excludes 0" if r["excludes_zero"] else "<strong>contains 0</strong>",
        ])
    stab_rows = [[f'{s["n_boot"]:,}', s["rng_seed"], f'{s["ci_low"]:+.5f}', f'{s["ci_high"]:+.5f}',
                  f'{s["frac_above_zero"]*100:.2f}%',
                  "excludes 0" if s["excludes_zero"] else "<strong>contains 0</strong>"]
                 for s in cb["precision_ci_stability"]]
    fps = cb["fp_by_contract_summary"]
    fpcat_rows = [[e(r["category"]), f'{r["c2_fp_mean"]:.2f}', f'{r["c3_fp_mean"]:.2f}',
                   f'{r["diff_mean"]:+.2f}', f'{r["c2_fp_raw"]}', f'{r["c3_fp_raw"]}', f'{r["diff_raw"]:+d}']
                  for r in cb["fp_by_category"]]
    ri = cb["recall_identity"]

    css = f"""
:root {{
  --bg: {C['off_white']}; --panel: #FFFFFF; --ink: {C['dark_earth']};
  --muted: {C['muted']}; --rule: {C['cream_dark']}; --accent: {C['terracotta']};
  --warn: {C['error_red']}; --parchment: {C['parchment']};
}}
* {{ box-sizing: border-box; }}
html, body {{ max-width: 100%; overflow-x: hidden; }}
body {{
  margin: 0; padding: 0 20px 80px;
  background: var(--bg); color: var(--ink);
  font-family: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  font-size: 16px; line-height: 1.62;
}}
.wrap {{ max-width: 980px; margin: 0 auto; }}
h1 {{ font-size: 30px; line-height: 1.2; margin: 44px 0 6px; }}
h2 {{ font-size: 22px; margin: 46px 0 10px; padding-bottom: 6px; border-bottom: 2px solid var(--rule); }}
h3 {{ font-size: 17px; margin: 28px 0 8px; color: {C['terracotta_dark']}; }}
p {{ margin: 12px 0; }}
code {{ font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 0.88em;
  background: var(--parchment); padding: 1px 5px; border-radius: 3px; }}
.sub {{ color: var(--muted); font-size: 15px; margin-top: 0; }}
.card {{ background: var(--panel); border: 1px solid var(--rule); border-radius: 6px;
  padding: 18px 20px; margin: 18px 0; }}
.banner {{ border-left: 6px solid var(--warn); background: #FBEEEA;
  border-radius: 4px; padding: 14px 18px; margin: 20px 0; }}
.banner strong {{ color: {C['error_red']}; }}
.note-box {{ border-left: 6px solid {C['slate']}; background: #EEF3F6;
  border-radius: 4px; padding: 12px 18px; margin: 16px 0; font-size: 15px; }}
.divider {{ background: {C['error_red']}; color: #FFFFFF; text-align: center;
  padding: 9px 14px; border-radius: 4px; margin: 22px 0; font-weight: 700;
  letter-spacing: .01em; font-size: 15px; }}
.tablewrap {{ overflow-x: auto; margin: 14px 0; border: 1px solid var(--rule);
  border-radius: 5px; background: var(--panel); }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px;
  font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; }}
th, td {{ padding: 7px 11px; text-align: right; border-bottom: 1px solid var(--rule);
  white-space: nowrap; }}
th {{ background: var(--parchment); font-weight: 700; text-align: right; }}
th:first-child, td:first-child {{ text-align: left; }}
tbody tr:last-child td {{ border-bottom: none; }}
.base {{ color: {C['mushroom']}; }}
.warn {{ color: var(--warn); }}
.figrow {{ display: flex; flex-wrap: wrap; gap: 20px; }}
.figrow > figure {{ flex: 1 1 380px; margin: 0; min-width: 0; }}
figure svg {{ width: 100%; height: auto; display: block; }}
figcaption {{ font-size: 14px; color: var(--muted); margin-top: 8px; }}
.tick {{ font-size: 11px; fill: {C['muted']}; font-family: -apple-system, Arial, sans-serif; }}
.axlab {{ font-size: 12.5px; fill: {C['dark_earth']}; font-family: -apple-system, Arial, sans-serif; }}
.leg {{ font-size: 11.5px; fill: {C['dark_earth']}; font-family: -apple-system, Arial, sans-serif; }}
.note {{ font-size: 11px; fill: {C['muted']}; font-family: -apple-system, Arial, sans-serif; }}
.pointlab {{ font-size: 12px; font-weight: 700; font-family: -apple-system, Arial, sans-serif; }}
.frow {{ font-size: 12.5px; fill: {C['dark_earth']}; font-family: -apple-system, Arial, sans-serif; }}
.meta {{ display: flex; flex-wrap: wrap; gap: 8px 26px; font-size: 14.5px;
  font-family: -apple-system, Arial, sans-serif; color: var(--muted); }}
.meta b {{ color: var(--ink); font-weight: 600; }}
ul {{ margin: 10px 0; padding-left: 22px; }}
li {{ margin: 7px 0; }}
footer {{ margin-top: 56px; padding-top: 18px; border-top: 2px solid var(--rule);
  font-size: 13.5px; color: var(--muted); }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #1E1A18; --panel: #262120; --ink: #F0E7DE; --muted: #B3A69C;
    --rule: #453B37; --parchment: #322A27;
  }}
  :root:not([data-theme="light"]) .banner {{ background: #3A2320; }}
  :root:not([data-theme="light"]) .note-box {{ background: #22302F; }}
  :root:not([data-theme="light"]) figure svg rect[fill="#FFFFFF"] {{ fill: #F7F2EC; }}
  :root:not([data-theme="light"]) figure svg {{ background: #F7F2EC; border-radius: 4px; }}
}}
:root[data-theme="dark"] {{
  --bg: #1E1A18; --panel: #262120; --ink: #F0E7DE; --muted: #B3A69C;
  --rule: #453B37; --parchment: #322A27;
}}
"""

    seeds_note = ("seeds are repetition labels, not reproducibility handles"
                  if all(x is False for x in run["seed_honored"]) else "seeds honoured")

    body = f"""<div class="wrap">
<h1>Does requiring citation change what the model extracts?</h1>
<p class="sub">Study 008 &middot; first experiment &middot; C2 vs C3 on <code>harness_val</code>, presented in the CUAD paper's own table and figure formats. Run <code>{e(run['run_id'])}</code>.</p>

<div class="card">
<div class="meta">
<span><b>Model:</b> <code>{e(run['model'])}</code> via {e(run['backend'])}</span>
<span><b>Temperature:</b> {run['temperature']}</span>
<span><b>Seeds:</b> {', '.join(str(s) for s in run['seeds'])} &mdash; {run['n_trials']} trials, {len(run['seeds'])} per contract per condition</span>
<span><b>Repair:</b> disabled (<code>max_repair_attempts = {run['max_repair_attempts']}</code>)</span>
<span><b><code>max_output_tokens</code>:</b> {run['max_output_tokens']:,}</span>
<span><b>Schema variant:</b> <code>{e(run['schema_variant'])}</code></span>
<span><b>Principle set:</b> <code>{e(run['principle_set_version'])}</code> (w01&ndash;w10)</span>
<span><b>Prompt template:</b> <code>{e(run['prompt_template_version'])}</code></span>
<span><b>Harness:</b> <code>{e(run['harness_git_sha'])}</code></span>
<span><b>Split:</b> <code>{e(run['split'])}</code>, {run['n_contracts']} contracts &times; {run['n_categories']} categories</span>
</div>
<p style="margin-bottom:0"><strong>Tinker does not honour seeds</strong> (<code>seed_honored = false</code> on all {run['n_trials']} trials). Seeds 0/1/2 are repetition labels; {seeds_note}. Individual trials cannot be re-rolled &mdash; the trace store is the only record of what was sampled.</p>
</div>

<div class="banner">
<p style="margin-top:0"><strong>Read this before the figures.</strong> Our run is on <code>harness_val</code>, 40 contracts carved from CUAD's <strong>official TRAIN split</strong> &mdash; the exact data the CUAD paper's three models were fine-tuned on. Their published curve is over the <strong>official TEST split</strong>, 102 contracts they never trained on.</p>
<p style="margin-bottom:0"><strong>These are not the same contracts and not the same contract of evidence.</strong> A point from ours placed on a curve from theirs would be a memorisation-inflated baseline against an uncontaminated one, on disjoint documents and a different category count (12 vs 41). <strong>We therefore do not draw the overlay.</strong> The two are shown on identical axes, in separate panels, with the panels explicitly marked non-comparable. The honest overlay becomes available only at gate G4, when <code>test</code> opens and both sides can be computed on the same contracts.</p>
</div>

<h2>1. Their Table 2, reproduced</h2>
<p>Published figures against figures recovered by running CUAD's own <code>evaluate.py</code>, completely unmodified, over the authors' own shipped <code>nbest_predictions_.json</code> and their own <code>test.json</code> &mdash; {data['cuad_meta']['n_questions']:,} questions ({e(data['cuad_meta']['gold'])}). Values are percentages. This is the gate: if the released checkpoints did not reproduce Table 2, nothing downstream would mean anything.</p>
{table(["model", "AUPR pub.", "AUPR rec.", "&Delta;", "P@80%R pub.", "P@80%R rec.", "&Delta;", "P@90%R pub.", "P@90%R rec.", "&Delta;", "max recall"], t2_rows)}
<p><strong>Gate: PASS.</strong> Every delta is smaller than the rounding step of the published table. The <code>0.0</code> published at P@90%R for both RoBERTas means <em>90% recall is unreachable</em> (max recall 0.899 and 0.905), not that precision collapsed; DeBERTa reaches 0.917 and is the only model with a non-zero figure there.</p>

<h2>2. Their PR curve &mdash; and our points, kept apart</h2>
<p>Left: the CUAD paper's precision&ndash;recall curves, one line per model, plotted from the checked-in 102-point sweep using the <strong>interpolated-precision</strong> column their <code>get_aupr</code> integrates and their P@R reads off. Hollow markers are the exact operating points at 80% recall. Right: our two committed-decision points, on identical axes, on <em>different data</em>.</p>

<div class="figrow">
<figure>
{curve_figure(data)}
<figcaption><strong>Panel A.</strong> CUAD Table 2 models. Official <code>test</code> split, 102 contracts, all 41 categories, interpolated precision. Their models were fine-tuned on the official train split and never saw these contracts.</figcaption>
</figure>
<figure>
{points_figure(data)}
<figcaption><strong>Panel B.</strong> Our C2 and C3, scored by their <code>evaluate.py</code>. Split <code>harness_val</code>, {ours['n_intersection']} contracts, 12 categories &mdash; carved from the official <strong>train</strong> split. Faint dots are per-seed points.</figcaption>
</figure>
</div>

<div class="divider">Panel A and Panel B are computed on different contracts and a different category set. Do not read a gap between them.</div>

<h3>How our point was computed</h3>
<p>Not with our own metrics. Per D-26, CUAD's scorer consumes our output unmodified:</p>
<ul>
<li>Gold: <code>data/raw/CUADv1.json</code> read by upstream <code>evaluate.get_answers</code>, subset to our {ours['n_intersection']}-contract intersection &times; 12 categories &mdash; {gp['questions']} questions in the full 40-contract split, of which {gp['with_gold_spans']} carry gold spans and {gp['empty']} are empty; {gp['total_gold_spans']} gold spans total.</li>
<li>Predictions: each <code>Extraction(category, spans)</code> becomes their <code>preds_list</code>; each <code>AbsenceClaim</code> becomes <code>[]</code>. No threshold is chosen on our side because we do not have one &mdash; D-14 commits to one decision per (contract, category), which is exactly their question granularity.</li>
<li>Scoring: their <code>compute_precision_recall</code> with their <code>get_jaccard</code> bag-of-words matcher at <code>IOU_THRESH = 0.5</code>, span-level micro-pooled TP/FP/FN, no true-negative cell. Each (contract, category, trial) is a separate question, so three seeds pool exactly as three repetitions. The recomputation was verified to agree bit-for-bit with a direct call to upstream <code>compute_precision_recall</code>.</li>
</ul>
{table(["condition", "trials", "questions", "TP", "FP", "FN", "recall", "precision"],
       [[c, ourpts[c]["n_trials"], ourpts[c]["n_questions"], ourpts[c]["tp"], ourpts[c]["fp"], ourpts[c]["fn"],
         f'<strong>{ourpts[c]["recall"]:.4f}</strong>', f'<strong>{ourpts[c]["precision"]:.4f}</strong>'] for c in ("C2", "C3")])}
{table(["condition", "seed", "trials", "TP", "FP", "FN", "recall", "precision"], seed_rows)}
<div class="note-box">
<p style="margin-top:0"><strong>Two further reasons the numbers are not like-for-like, beyond the split.</strong> (a) <strong>12 categories, not 41.</strong> Their pooled figures are over all 41; ours are over our 12-category subset, which is a different quantity and must never be printed as the same one. (b) <strong>Their matcher cannot see hallucination.</strong> <code>get_jaccard</code> is bag-of-words over lowercased, punctuation-stripped tokens, so a paraphrase or a normalised quotation can clear 0.5. Their models extract spans by construction and cannot invent text; ours can, at a measured {lb['C2']['verbatim_not_found_rate']*100:.1f}% (C2) / {lb['C3']['verbatim_not_found_rate']*100:.1f}% (C3) not-found rate overall and {lb['C2']['fp_cell']['not_found_rate']*100:.1f}% inside C2's false-present cell. Their scorer systematically flatters us; &sect;6 is the correction.</p>
<p style="margin-bottom:0">Recall lands at {ourpts['C2']['recall']:.2f} for both conditions, comfortably above the 0.2 floor below which the pre-registered reading says the comparison is uninformative &mdash; so the machinery is ready for G4. It is the split, not the recall level, that blocks the comparison today.</p>
</div>

<h3>The C2&ndash;C3 gap under their scorer, with an interval</h3>
<p>The two points above differ &mdash; C3 buys {abs(fps['raw_fp_total']['C3']-fps['raw_fp_total']['C2'])} fewer false-positive spans ({fps['raw_fp_total']['C2']} &rarr; {fps['raw_fp_total']['C3']}) at what looks like unchanged recall. <strong>That gap now has a confidence interval, and the interval does not support reading anything into it.</strong></p>
<p>Method, stated because it is the whole result: a <strong>paired bootstrap resampling contracts with replacement</strong>, never decisions. Decisions cluster within contracts, so resampling decisions would treat correlated observations as independent and manufacture intervals far too narrow. Each of the {cbm['n_boot']:,} draws takes the <em>same</em> resampled contract set into both arms, so pairing is preserved and contract-level difficulty cancels. Seeds are repetitions, not questions: a contract's TP/FP/FN are <strong>averaged over its scored seeds before aggregation</strong>, which keeps the resampling unit the contract and, incidentally, removes the unequal-seed survivorship asymmetry &mdash; {sum(1 for r in cb['fp_by_contract'] if r['c2_seeds'] != r['c3_seeds'])} of {cbm['n_contracts']} contracts have different scored-seed counts in the two arms. Within a draw the estimator is CUAD's own micro-pooled one: <code>P = &Sigma;TP/(&Sigma;TP+&Sigma;FP)</code>, <code>R = &Sigma;TP/(&Sigma;TP+&Sigma;FN)</code>. RNG: <code>{e(cbm['rng'])}</code>.</p>
<figure>
{cuad_forest_figure(data)}
<figcaption>All three intervals contain zero. Blue is the honest reading.</figcaption>
</figure>
{table(["metric (seed-averaged)", "C2", "C3", "C3 &minus; C2", "95% CI", "draws &gt; 0", "verdict"], boot_rows)}
<div class="banner">
<p style="margin-top:0"><strong>The precision difference is not distinguishable from noise.</strong> +{cbb['precision']['delta']:.4f} with a 95% interval of [{cbb['precision']['ci_low']:+.4f}, {cbb['precision']['ci_high']:+.4f}] &mdash; the lower bound sits <em>on</em> zero, and {cbb['precision']['frac_above_zero']*100:.1f}% of draws being positive is not a result. It is close enough to the boundary that the bound's sign is itself unstable across RNG seeds:</p>
{table(["resamples", "RNG seed", "CI low", "CI high", "draws &gt; 0", "verdict"], stab_rows)}
<p style="margin-bottom:0">Six honest runs of the same procedure, three saying <em>excludes zero</em> and three saying <em>contains zero</em>, separated in the fourth decimal place. <strong>A conclusion that flips on the RNG seed is not a conclusion.</strong> The micro-F1 difference &mdash; the headline metric under D-30 &mdash; is {cbb['micro_f1']['delta']:+.4f} [{cbb['micro_f1']['ci_low']:+.4f}, {cbb['micro_f1']['ci_high']:+.4f}], comfortably straddling zero. <strong>Nothing here is claimed.</strong></p>
</div>
<div class="note-box">
<p style="margin-top:0"><strong>The identical recall is a coincidence, not an invariance.</strong> The pooled figures print as {ri['c2_recall_raw']:.4f} in both arms, but they are not equal: C2 is {ri['c2_counts'][0]}/{ri['c2_counts'][0]+ri['c2_counts'][1]} = {ri['c2_recall_raw']:.7f} and C3 is {ri['c3_counts'][0]}/{ri['c3_counts'][0]+ri['c3_counts'][1]} = {ri['c3_recall_raw']:.7f}. Different numerators, different denominators, agreeing to five decimal places by accident. Under the seed-averaged pairing that the bootstrap uses, the recalls separate to {cb['point_seed_averaged']['C2']['recall']:.4f} vs {cb['point_seed_averaged']['C3']['recall']:.4f} &mdash; a {cbb['recall']['delta']:+.4f} difference that is also indistinguishable from zero, [{cbb['recall']['ci_low']:+.4f}, {cbb['recall']['ci_high']:+.4f}]. <strong>Do not describe this run as "identical recall".</strong> The four-decimal coincidence in the pooled table is a fact about unequal trial counts, not about the model.</p>
<p style="margin-bottom:0"><strong>The false-positive reduction is diffuse, not one outlier.</strong> Across the {cbm['n_contracts']} paired contracts the seed-averaged FP difference goes <strong>down on {fps['n_down']}, up on {fps['n_up']}, and is flat on {fps['n_flat']}</strong>. The largest single contract contributes {fps['top1_share_of_reduction']*100:.0f}% of the gross reduction and the top five contribute {fps['top5_share_of_reduction']*100:.0f}%, so the {abs(fps['raw_fp_total']['C3']-fps['raw_fp_total']['C2'])}-span figure is not an artifact of one or two documents. That is the one thing this check can rule out; it does not make the difference real, because 16-down-14-up is also exactly what a coin flip over contracts looks like.</p>
</div>
<p>Which categories the false positives come out of, seed-averaged and raw. <strong>Exclusivity alone accounts for {abs(cb['fp_by_category'][0]['diff_mean'])/abs(fps['total_reduction_mean_units'])*100:.0f}% of the net reduction</strong>; with Governing Law the two take {(abs(cb['fp_by_category'][0]['diff_mean'])+abs(cb['fp_by_category'][1]['diff_mean']))/abs(fps['total_reduction_mean_units'])*100:.0f}%. It is not a single category, but it is not spread evenly either &mdash; and Revenue/Profit Sharing moves the other way.</p>
{table(["category", "C2 FP (seed-avg)", "C3 FP (seed-avg)", "&Delta;", "C2 FP raw", "C3 FP raw", "&Delta; raw"], fpcat_rows)}
<p><strong>If a future run does separate these arms, here is what such a result would and would not be.</strong> It would be a precision gain at unchanged recall, on an <em>unselected</em> principle set, on {cbm['n_contracts']} contracts drawn from CUAD's train split, under a bag-of-words matcher that cannot see hallucination. It would still say nothing whatsoever about whether the citations were <em>correct</em> &mdash; no applicability source was loaded, and citation correctness is unmeasured in this run. Today it is not even that: it is a difference the data cannot separate from zero.</p>

<h3>Per-category, under their scorer</h3>
<p>Span-level TP/FP/FN under their Jaccard matcher, on <code>harness_val</code>. Note how differently this reads from our own Level A presence metric in &sect;5 &mdash; Governing Law scores 0.98 presence F1 for us and {ours['per_category']['C2']['Governing Law']['precision']:.2f} precision under their span matcher, because getting the presence call right is not the same as putting the span boundary where Atticus put it.</p>
{table(["category", "C2 TP/FP/FN", "C2 R", "C2 P", "C3 TP/FP/FN", "C3 R", "C3 P"], catcuad_rows)}

<h2>3. The contrast: C3 &minus; C2</h2>
<p>Paired by contract over the {data['contrast'][0]['n_contracts']}-contract intersection where both conditions produced at least one scored trial. Per-contract value is the mean over that contract's scored seeds; intervals are 10,000-sample bootstraps over contracts. Span metrics have n = {data['contrast'][5]['n_contracts']} because two contracts produced no true-positive cell in one arm.</p>
<figure>
{forest_figure(data)}
<figcaption>Accuracy metrics only; token costs are tabled below. Terracotta marks the one interval that excludes zero.</figcaption>
</figure>
{table(["metric", "n", "C3 &minus; C2", "95% CI", "t", "contracts up/down"], contrast_rows)}
<p><strong>The answer-quality result is null.</strong> Every accuracy interval contains zero. Nothing in the presence/absence call, the span overlap, or the exact-match rate moves when the model is required to cite the principles it used. Two things do move, and neither is an accuracy gain: byte-exactness of spans drops {abs(data['contrast'][9]['delta'])*100:.1f} points with the mass shifting into <em>normalised-only</em> and <em>not-found</em>, and C3 reasons about {data['contrast'][12]['delta']:,.0f} tokens longer for a prompt that is only {data['contrast'][13]['delta']:.0f} tokens larger &mdash; roughly 13&times; the prompt cost, paid in generated reasoning.</p>
<p>The manipulation demonstrably took, so this is a null <em>effect</em>, not a null treatment:</p>
{table(["", "C2", "C3"], cite_rows)}
<p>Citation distribution across C3's {cite['C3']['n_cited']:,} cited decisions: {cite_dist}</p>

<h2>4. Outcomes, conformance, and truncation</h2>
{table(["", "C2", "C3"], out_rows)}
<p>With repair disabled this is the clean unassisted conformance measurement. The <code>api_error</code> trials are all <code>tinker unreachable: [Errno 54] Connection reset by peer</code> during an 8-way parallel burst &mdash; infrastructure, not model behaviour &mdash; and are excluded from both numerator and denominator. They were not retried, because retrying means deleting rows from a store whose uniqueness invariant is what makes the run resumable.</p>
{table(["condition", "seed", "bucket", "contract tokens", "contract", "outcome"], trunc_rows)}

<h2>5. Level A &mdash; presence and absence, against the trivial baselines</h2>
<p>Pooled over all scored trials in each condition. The denominators differ between conditions ({la['C2']['counts']['n']:,} vs {la['C3']['counts']['n']:,} decisions), which is the survivorship asymmetry the paired contrast in &sect;3 exists to avoid &mdash; read these as per-condition descriptions and take the contrast from &sect;3.</p>
{table(["", "C2", "C3", "always-absent", "always-present"], la_rows)}
<p>Both conditions beat both trivial baselines on both classes at the micro level. The base rate is {la['C2']['always_present_decision_accuracy']*100:.1f}% present / {la['C2']['always_absent_decision_accuracy']*100:.1f}% absent, so decision-kind accuracy near {la['C2']['decision_kind_accuracy']:.2f} against an always-absent floor of {la['C2']['always_absent_decision_accuracy']:.3f} is a real but unspectacular margin, and it is base-rate-dominated. <strong>The dominant error is false-absent by roughly 4:1</strong> ({la['C2']['counts']['FN']} vs {la['C2']['counts']['FP']} in C2, {la['C3']['counts']['FN']} vs {la['C3']['counts']['FP']} in C3): the model under-claims presence, in both arms equally.</p>

<h3>Per category, with each category's own trivial baselines</h3>
{table(["category", "C2 TP/FP/FN/TN", "C3 TP/FP/FN/TN", "C2 pres F1", "C3 pres F1", "always-present pres F1", "C2 abs F1", "C3 abs F1", "always-absent abs F1"], cat_rows)}
<p>Categories in red lose to the always-present baseline in <em>both</em> conditions.</p>

<h2>6. Level B &mdash; spans, on the true-positive cell</h2>
<p>Denominator stated explicitly: Level B is computed on TP decisions only.</p>
{table(["", "C2", "C3"], lb_rows)}
<p><strong>Invented language concentrates in the false-present cell.</strong> C2's FP cell shows {lb['C2']['fp_cell']['not_found_rate']*100:.1f}% not-found against {lb['C2']['verbatim_not_found_rate']*100:.1f}% overall: when the model wrongly claims a category is present, it is markedly more likely to have made up the supporting text. Both conditions show it; C3's FP cell is smaller and cleaner, but on {lb['C3']['fp_cell']['decisions']} decisions that is a description, not a claim.</p>

<h2>7. Token and time cost</h2>
{table(["", "C2", "C3"], cost_rows)}
<p>The unpaired prompt means differ by ~{cost['C3']['prompt_tokens_mean']-cost['C2']['prompt_tokens_mean']:,.0f} tokens, but that is a composition artifact of which contracts scored. Paired, the citation requirement's prompt cost is exactly <strong>+{data['contrast'][13]['delta']:.0f} tokens on every one of the {data['contrast'][13]['n_contracts']} paired contracts</strong>, while its completion cost is <strong>+{data['contrast'][12]['delta']:,.0f}</strong> [{data['contrast'][12]['ci_low']:,.0f}, {data['contrast'][12]['ci_high']:,.0f}].</p>
<p>Totals for the {rt['n_trial_rows']} trial rows of this run: {rt['prompt_tokens']:,} prompt + {rt['completion_tokens']:,} completion = <strong>{rt['prompt_tokens']+rt['completion_tokens']:,} tokens</strong>, and <strong>{rt['model_hours']:.2f} model-hours</strong> of summed request latency.</p>

<h2>8. The three findings that outrank the null</h2>

<h3>a. Truncation is condition-dependent, and it strikes the shortest contracts</h3>
<p>{len(data['truncations'])} of {run['n_trials']} trials truncated. <strong>All four are C3. Three of four are in the 0&ndash;4k bucket</strong>, on contracts of {', '.join(f"{r['n_contract_tokens']:,}" for r in data['truncations'])} tokens against a {run['max_output_tokens']:,}-token output budget. C2 truncated zero times. Truncation rate is {oc['C3']['truncated']/oc['C3']['trials']*100:.1f}% in C3 and 0.0% in C2. The citation requirement is what tips reasoning past the budget, and it does so where the document gives least to reason about &mdash; which is also the mechanism behind C3's {(oc['C2']['conformance']-oc['C3']['conformance'])*100:.1f}-point conformance deficit, since truncation lands in <code>json_decode</code>. A pre-run 12-trial budget probe saw zero truncations and peaked at 58% of budget; it did not generalise.</p>

<h3>b. Citation frequency does not track principle quality</h3>
<p><code>w01</code> ({cite['C3']['by_principle']['w01']}) and <code>w06</code> ({cite['C3']['by_principle']['w06']}) take {(cite['C3']['by_principle']['w01']+cite['C3']['by_principle']['w06'])/sum(cite['C3']['by_principle'].values())*100:.0f}% of all citations between them. But <strong><code>w06</code>'s applicability checker fires on 1 of 480 <code>harness_val</code> decisions</strong> and its gate is <code>gold_absence</code>, and the model cited it {cite['C3']['by_principle']['w06']} times. <strong><code>w10</code> has no measured footprint at all</strong> &mdash; no applicability rate, no separability verdict, no phi, never built or footprinted &mdash; and drew {cite['C3']['by_principle']['w10']} citations. Models cite readily; a citation count is not evidence a principle did work. The smoke run showed the same pathology, where the two most-cited principles were fabricated calibration controls. Citation <em>correctness</em> remains unmeasured: no applicability source is loaded, the runner reports <code>citation: {{available: false}}</code> on all {oc['C3']['ok']} scored C3 trials, and nothing here is a citation-accuracy claim.</p>

<h3>c. Two categories lose to a trivial baseline, in both conditions</h3>
<ul>
<li><strong>Expiration Date</strong> scores {data['per_category']['C2']['Expiration Date']['presence_f1']:.3f} (C2) / {data['per_category']['C3']['Expiration Date']['presence_f1']:.3f} (C3) presence F1 against an always-present baseline of <strong>{data['per_category']['C2']['Expiration Date']['always_present_presence_f1']:.3f}</strong>. Gold marks it present on {data['per_category']['C2']['Expiration Date']['n_gold_present']} of {data['per_category']['C2']['Expiration Date']['counts']['n']} decisions; the model claims absent on {data['per_category']['C2']['Expiration Date']['counts']['FN']} of them. A constant "present" would nearly triple the score. This is the single worst cell in the study, and it is a task-definition problem, not a citation problem.</li>
<li><strong>Volume Restriction</strong> scores {data['per_category']['C2']['Volume Restriction']['presence_f1']:.3f} / {data['per_category']['C3']['Volume Restriction']['presence_f1']:.3f} against an always-present <strong>{data['per_category']['C2']['Volume Restriction']['always_present_presence_f1']:.3f}</strong>, with {data['per_category']['C2']['Volume Restriction']['counts']['FP']} false-presents and at most 1 true-present in either arm.</li>
<li><strong>Minimum Commitment</strong> sits at parity with its baseline ({data['per_category']['C2']['Minimum Commitment']['presence_f1']:.3f} vs {data['per_category']['C2']['Minimum Commitment']['always_present_presence_f1']:.3f}). Two thirds of the Savelka confusable trio are therefore at or below trivial. The third, Revenue/Profit Sharing, is the only per-category cell where C3 shows a visible gain ({data['per_category']['C2']['Revenue/Profit Sharing']['presence_f1']:.3f} &rarr; {data['per_category']['C3']['Revenue/Profit Sharing']['presence_f1']:.3f}) &mdash; on {data['per_category']['C2']['Revenue/Profit Sharing']['n_gold_present']} present decisions, uncorrected for twelve comparisons, so it is a hypothesis and not a result.</li>
</ul>

<h2>9. How I read this</h2>
<p>The headline is a null, and it is a good one. Requiring the model to name the principles it used changes nothing measurable about what it extracts: presence-class F1 moves {data['contrast'][0]['delta']:+.4f} [{data['contrast'][0]['ci_low']:+.4f}, {data['contrast'][0]['ci_high']:+.4f}], span F1 {data['contrast'][5]['delta']:+.4f} [{data['contrast'][5]['ci_low']:+.4f}, {data['contrast'][5]['ci_high']:+.4f}], exact-match {data['contrast'][8]['delta']:+.4f} [{data['contrast'][8]['ci_low']:+.4f}, {data['contrast'][8]['ci_high']:+.4f}] &mdash; fourteen paired comparisons and every accuracy interval straddling zero. <strong>The one place an effect might still have been hiding was CUAD's own scorer</strong>, where C3's point sits {cbb['precision']['delta']:.3f} higher in precision on {abs(fps['raw_fp_total']['C3']-fps['raw_fp_total']['C2'])} fewer false-positive spans. A paired contract-level bootstrap (&sect;2) puts that at [{cbb['precision']['ci_low']:+.4f}, {cbb['precision']['ci_high']:+.4f}], with a lower bound whose sign flips across RNG seeds, and the D-30 headline micro-F1 at {cbb['micro_f1']['delta']:+.4f} [{cbb['micro_f1']['ci_low']:+.4f}, {cbb['micro_f1']['ci_high']:+.4f}]. <strong>That closes it: the null holds on the primary metric too.</strong> What makes it worth having rather than merely uninformative is that the manipulation is demonstrated in the same data: C2 left <code>principles_cited</code> empty on all {cite['C2']['n_decisions']:,} of its decisions and leaked nothing, C3 filled it on {cite['C3']['rate']*100:.1f}% of {cite['C3']['n_decisions']:,}. A null with a treatment you can see landing is evidence; a null without one is a failed experiment. This is the first kind. Concretely it retires the risk the run was scheduled to retire &mdash; the citation half of the study can be built without hedging against the requirement degrading extraction &mdash; and that means the selection budget downstream buys principle quality rather than insurance.</p>
<p>Two boundaries on what has been shown. The first is the principle set. It is <code>working_set.yaml</code>, not a curated one, and its own records say so: nine of ten principles carry <code>needs_rebuild</code> or <code>not_yet_specified</code> checker status, <code>w10</code> was never footprinted at all, and several fail the D-21 separability rule outright by gating applicability on gold. C2 already contains all ten principles, so C3 &minus; C2 is the addition of the citation <em>instruction</em> alone, measured at exactly +{data['contrast'][13]['delta']:.0f} prompt tokens on all {data['contrast'][13]['n_contracts']} paired contracts. <strong>This run therefore tests the requirement, not the principles</strong>, and nothing here is evidence that principles do or do not help. The second boundary is the CUAD panel. Panel B exists to prove the wiring &mdash; their scorer ingests our committed decisions with no invented parameter on either side, and the numbers it returns are sane &mdash; but on <code>harness_val</code>, inside their fine-tuning data, at 12 categories rather than 41, it is not a comparison and I have not drawn it as one. When the overlay does become drawable at G4, it will still be a calibration point rather than a hypothesis test: it tells a reader whether our starting position is reasonable or a strawman, which is exactly what makes an unoptimised iteration 0 defensible. <strong>The result this study eventually reports is its own iteration-0-to-ladder delta</strong>, which shares contamination on both sides and cancels it, and which no comparison to a fine-tuned encoder can substitute for.</p>
<p>Three things in this data would change what I do next, and none of them is the null. The truncation asymmetry is the most actionable defect found: four trials, all C3, three of them on the shortest contracts in the split, is not noise shaped like noise &mdash; it says the citation obligation inflates reasoning hardest where there is least to reason about, and it converts directly into C3's {(oc['C2']['conformance']-oc['C3']['conformance'])*100:.1f}-point conformance deficit through <code>json_decode</code>. Fix it or record it as a known condition-asymmetric cost before the grid, because a manipulation that costs conformance is a manipulation that biases every downstream comparison through survivorship &mdash; the mechanism that manufactured a spuriously significant pooled presence-F1 result in this very run, and that a seed-balanced re-analysis reversed. The citation distribution is the second: <code>w06</code> drew {cite['C3']['by_principle']['w06']} citations while its checker fires on 1 of 480 decisions, and <code>w10</code> drew {cite['C3']['by_principle']['w10']} with no measured footprint whatsoever, which means citation counts must never stand in as evidence during principle selection. And the third is not about principles at all: Expiration Date at {data['per_category']['C2']['Expiration Date']['presence_f1']:.3f} against an always-present {data['per_category']['C2']['Expiration Date']['always_present_presence_f1']:.3f}, with two thirds of the Savelka trio at or below trivial, is a task-definition problem sitting in the middle of the category subset the study chose on purpose. It will contaminate any per-category reading of a principle effect until it is understood, and it is cheap to look at now.</p>

<footer>
<p>Generated by <code>scripts/render_c2c3_results.py</code> from <code>reviews/c2-c3-results-data.json</code>, built by <code>scripts/build_c2c3_page_data.py</code> and <code>scripts/score_c2c3_with_cuad_evaluator.py</code>. Sources: <code>data/traces/{e(run['run_id'])}/shard*/</code>, <code>data/cuad-baseline/table2/</code>, <code>data/raw/CUADv1.json</code>, <code>data/raw/evaluate.py</code>.</p>
<p>CUAD (the Contract Understanding Atticus Dataset), its gold annotations, its <code>evaluate.py</code>, and the Table 2 figures reproduced here are the work of <strong>The Atticus Project</strong> and are released under <strong>CC BY 4.0</strong>. Cite as <code>hendrycks2021cuad</code> &mdash; Hendrycks, Burns, Chen &amp; Ball, <em>CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review</em>, arXiv:2103.06268.</p>
<p>AI Assistant Used: Claude Code.</p>
</footer>
</div>"""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>C2 vs C3 on CUAD &mdash; study 008 results</title>
<style>{css}</style>
</head>
<body>
{body}
</body>
</html>
"""


def main():
    data = json.load(open(DATA))
    OUT.write_text(build(data))
    print(f"wrote {OUT} ({OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
