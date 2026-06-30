import html
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

LRS = [2.441e-4, 3.453e-4, 4.883e-4, 6.905e-4, 9.766e-4, 1.381e-3, 1.953e-3, 2.762e-3, 3.906e-3, 5.524e-3, 7.812e-3, 1.105e-2]
BSS = [32, 64, 128, 192, 256, 352, 512, 736, 1024, 2048]
OPT_LR_I, OPT_BS_I = 10, 8

VCOLOR = {"strong": "#16a34a", "adequate": "#b45309", "weak": "#dc2626",
          "proceed": "#16a34a", "continue": "#2563eb", "revise": "#dc2626", "finish": "#475569"}
INK, MUT, LINE, BG = "#111827", "#64748b", "#e5e7eb", "#f8fafc"
ACCENT, TEAL, PURPLE = "#7c3aed", "#0d9488", "#b45309"
RCLR = {"orienter": PURPLE, "hypothesizer": TEAL, "designer": "#2563eb", "executor": "#2563eb", "analyst": "#0891b2", "terminator": "#475569"}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def nearest_i(vals, x):
    return min(range(len(vals)), key=lambda i: abs(math.log(vals[i]) - math.log(x)) if x and x > 0 else 1e9)


def chip(v, label=None, color=None):
    return f'<span class="chip" style="background:{color or VCOLOR.get(str(v).lower(), MUT)}">{esc(label or v)}</span>'


def collapsible(label, body):
    return f'<details class="think"><summary>{esc(label)}</summary><div class="thinkbody">{esc(body)}</div></details>' if body else ""


def regret_color(r, rmax):
    t = (min(max(r, 0), rmax) / rmax) ** 0.5 if rmax > 0 else 0
    stops = [(0.0, (22, 163, 74)), (0.5, (234, 179, 8)), (1.0, (220, 38, 38))]
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 0
            return "#%02x%02x%02x" % tuple(round(a + (b - a) * f) for a, b in zip(c0, c1))
    return "#dc2626"


def grid_svg(traj):
    W, H, ml, mt, mr, mb = 560, 430, 64, 40, 20, 48
    pw, ph = W - ml - mr, H - mt - mb
    X = lambda i: ml + (i / (len(LRS) - 1)) * pw
    Y = lambda j: mt + (1 - j / (len(BSS) - 1)) * ph
    rmax = max((t["regret"] for t in traj), default=0.05) or 0.05
    s = [f'<svg viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="ui-sans-serif,system-ui" font-size="10">',
         f'<rect width="{W}" height="{H}" fill="white"/>',
         f'<rect x="{X(8)-4:.1f}" y="{mt}" width="{X(11)-X(8)+8:.1f}" height="{ph}" fill="#fde68a" opacity="0.18"/>',
         f'<text x="{(X(8)+X(11))/2:.1f}" y="{mt-14}" fill="{PURPLE}" text-anchor="middle">high-lr region</text>']
    for i in range(len(LRS)):
        for j in range(len(BSS)):
            s.append(f'<circle cx="{X(i):.1f}" cy="{Y(j):.1f}" r="2" fill="{LINE}"/>')
    ox, oy = X(OPT_LR_I), Y(OPT_BS_I)
    s.append(f'<path d="M{ox:.1f},{oy-7:.1f} l2,5 5,0 -4,4 2,6 -5,-4 -5,4 2,-6 -4,-4 5,0 z" fill="{TEAL}"/>')
    s.append(f'<text x="{ox:.1f}" y="{oy-12:.1f}" fill="{TEAL}" text-anchor="middle" font-weight="700">optimum</text>')
    pts = [(nearest_i(LRS, t["lr"]), nearest_i(BSS, t["bs"])) for t in traj]
    for k in range(1, len(pts)):
        (i0, j0), (i1, j1) = pts[k - 1], pts[k]
        s.append(f'<line x1="{X(i0):.1f}" y1="{Y(j0):.1f}" x2="{X(i1):.1f}" y2="{Y(j1):.1f}" stroke="#94a3b8" stroke-width="1.3" opacity="0.6"/>')
    for k, (i, j) in enumerate(pts):
        col = regret_color(traj[k]["regret"], rmax)
        s.append(f'<circle cx="{X(i):.1f}" cy="{Y(j):.1f}" r="10" fill="{col}" stroke="white" stroke-width="1.5"/><text x="{X(i):.1f}" y="{Y(j)+3:.1f}" fill="white" stroke="#1f2937" stroke-width="0.4" paint-order="stroke" text-anchor="middle" font-weight="700">{k+1}</text>')
    # regret legend (top-left, above the plot)
    s.append(f'<text x="{ml}" y="14" fill="{MUT}">regret:</text>')
    for gx in range(0, 108, 12):
        s.append(f'<rect x="{ml+44+gx}" y="6" width="12" height="9" fill="{regret_color(rmax*(gx/108), rmax)}"/>')
    s.append(f'<text x="{ml+44}" y="26" fill="{MUT}">0</text><text x="{ml+44+108}" y="26" fill="{MUT}" text-anchor="end">{rmax:.3f}</text>')
    for i in range(len(LRS)):
        s.append(f'<text x="{X(i):.1f}" y="{H-mb+16}" fill="{MUT}" text-anchor="middle" transform="rotate(40 {X(i):.1f} {H-mb+16})">{LRS[i]:.1e}</text>')
    for j in range(len(BSS)):
        s.append(f'<text x="{ml-10}" y="{Y(j)+3:.1f}" fill="{MUT}" text-anchor="end">{BSS[j]}</text>')
    s.append(f'<text x="{ml+pw/2:.1f}" y="{H-4}" fill="{INK}" text-anchor="middle" font-weight="600">learning rate</text>')
    s.append(f'<text x="14" y="{mt+ph/2:.1f}" fill="{INK}" text-anchor="middle" font-weight="600" transform="rotate(-90 14 {mt+ph/2:.1f})">batch size</text></svg>')
    return "\n".join(s)


def regret_badge(r):
    c = "#16a34a" if r < 0.001 else "#b45309" if r < 0.005 else "#dc2626"
    return f'<span class="chip" style="background:{c}">regret {r:.4f}</span>'


def render_emit(role, v):
    if not v:
        return '<span class="note">(no output)</span>'
    if role == "orienter":
        h = "".join(f'<div class="kv"><div class="k">{k.replace("_"," ")}</div>{esc(v.get(k,""))}</div>' for k in ("knowledge", "expected_structure", "approach"))
        if v.get("uncertainties"):
            h += '<div class="kv"><div class="k">uncertainties</div><ul class="hyps">' + "".join(f"<li>{esc(u)}</li>" for u in v["uncertainties"]) + "</ul></div>"
        return h
    if role == "hypothesizer":
        return '<ul class="hyps">' + "".join(f'<li><b>[{esc(h.get("id"))}]</b> {esc(h.get("claim"))} <span style="color:{MUT}">— test: {esc(h.get("test"))}</span></li>' for h in v.get("hypotheses", [])) + "</ul>"
    if role in ("designer", "executor"):
        return f'<span class="mono">lr {float(v.get("lr",0)):.3e} · bs {v.get("bs")}</span> → runs <b>{esc(v.get("hypothesis_id"))}</b>' + (f', predicts {esc(v.get("predicted_loss"))}' if v.get("predicted_loss") is not None else "") + f'<div class="note">{esc(v.get("rationale"))}</div>'
    if role == "analyst":
        h = f'{esc(v.get("observation"))}'
        if v.get("updates"):
            h += '<div class="note">' + " · ".join(f'{esc(u.get("id"))}: <b>{esc(u.get("verdict"))}</b>' for u in v["updates"]) + "</div>"
        rb = v.get("running_best") or {}
        if rb:
            h += f'<div class="note">running best: <span class="mono">lr {rb.get("lr")} · bs {rb.get("bs")} · loss {rb.get("loss")}</span></div>'
        return h
    if role == "terminator":
        return chip(v.get("action"), color=VCOLOR.get(str(v.get("action")).lower(), MUT)) + (f' <span class="mono">best lr {v.get("best_lr")} · bs {v.get("best_bs")}</span>' if v.get("best_lr") is not None else "") + f'<div class="note">{esc(v.get("reason"))}</div>'
    return esc(json.dumps(v))


def main(run_dir):
    run = Path(run_dir)
    summ = json.load(open(run / "loop_summary.json"))
    judg = json.load(open(run / "judgments.json")) if (run / "judgments.json").exists() else {}
    steps = json.load(open(run / "steps.json")) if (run / "steps.json").exists() else {}
    rows = [json.loads(l) for l in open(run / "trace.jsonl")]

    tr = summ["trajectory"]
    max_lr = max(t["lr"] for t in tr) if tr else 0
    distinct = len({(t["lr"], t["bs"]) for t in tr})
    crit = [r for r in rows if r.get("kind") == "critique"]
    revs = [r for r in rows if r.get("kind") == "revision"]
    dec_by_role = Counter((r["role"], str(r.get("decision")).lower()) for r in crit)
    o = judg.get("orienter")
    has_critic = bool(crit)

    thinkq = defaultdict(list)
    for r in rows:
        if r.get("kind") == "thinking":
            thinkq[r.get("role")].append(r["text"])
    tptr = defaultdict(int)

    def pop_think(role):
        i = tptr[role]
        if i < len(thinkq[role]):
            tptr[role] += 1
            return thinkq[role][i]
        return ""

    H = [f'''<!doctype html><html><head><meta charset="utf-8"><title>Society + Critic — seed {esc(summ["seed"])}</title>
<style>
body{{margin:0;background:{BG};color:{INK};font-family:ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif;line-height:1.5}}
.wrap{{max-width:1000px;margin:0 auto;padding:28px 22px 90px}}
h1{{font-size:22px;margin:0 0 2px}} .sub{{color:{MUT};font-size:13px;margin-bottom:16px}}
.chip{{display:inline-block;color:white;border-radius:999px;padding:1px 9px;font-size:11px;font-weight:700;vertical-align:middle}}
.tiers{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;margin:14px 0 20px}}
.tier{{background:white;border:1px solid {LINE};border-radius:12px;padding:14px}}
.tier h3{{margin:0 0 8px;font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:{MUT}}}
.tier .row{{display:flex;justify-content:space-between;gap:8px;padding:2px 0;border-bottom:1px dashed {LINE}}}
.tier .k{{color:{MUT}}} .note{{font-size:12px;color:{MUT};margin-top:4px}}
.gridwrap{{background:white;border:1px solid {LINE};border-radius:12px;padding:8px;text-align:center;margin:14px 0}}
.turn{{background:white;border:1px solid {LINE};border-left-width:4px;border-radius:10px;padding:12px 14px;margin:10px 0}}
.role{{font-size:11px;letter-spacing:.06em;text-transform:uppercase;font-weight:800;padding:2px 8px;border-radius:6px;color:white}}
.kv{{margin:7px 0}} .kv .k{{color:{MUT};font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.03em}}
.think{{margin:8px 0 0;border-left:3px solid {LINE};padding-left:10px}} .think summary{{cursor:pointer;color:{MUT};font-size:12px}}
.thinkbody{{white-space:pre-wrap;font-size:12px;color:#374151;margin-top:6px;font-family:ui-monospace,monospace}}
.hyps{{font-size:13px;margin:4px 0;padding-left:18px}} .hyps li{{margin:3px 0}}
.crit{{background:#fff7ed;border:1px solid #fed7aa;border-radius:9px;padding:9px 12px;margin:8px 0 8px 26px;font-size:12.5px}}
.crit.revise{{background:#fef2f2;border-color:#fecaca}} .crit.proceed{{background:#f0fdf4;border-color:#bbf7d0}}
.crit .q{{font-style:italic;color:#374151;margin-top:4px}}
.expt{{display:flex;align-items:center;gap:10px;margin:18px 0 4px;font-weight:800;font-size:14px;color:{INK}}}
.expt .ln{{flex:1;height:1px;background:{LINE}}}
.judge{{background:#fef2f2;border:1px solid #fecaca;border-radius:10px;padding:10px 12px;margin-top:9px;font-size:12.5px}}
.judge.adequate{{background:#fffbeb;border-color:#fde68a}} .judge.strong{{background:#f0fdf4;border-color:#bbf7d0}}
.mono{{font-family:ui-monospace,monospace}}
</style></head><body><div class="wrap">''']

    title = "Society of agents + Critic" if has_critic else "Society of agents"
    H.append(f'<h1>{title} — single seed</h1>')
    H.append(f'<div class="sub">{esc(summ["model"])} · Env A · think={esc(summ["think"])} · seed {esc(summ["seed"])} · optimum {summ["optimum_loss"]:.4f} · {summ["model_calls"]} calls · {summ["elapsed_ms"]//60000}m</div>')
    H.append(f'<div class="sub" style="background:#eef2f7;border-radius:8px;padding:8px 12px"><b>Cadence:</b> Orienter → Hypothesizer → <b>[ Executor → ⚙ harness runs config → Analyst → Hypothesizer → Terminator ]</b> looped to budget. The <b>Hypothesizer</b> prioritizes hypotheses; the <b>Executor</b> just runs the top one.</div>')

    H.append('<div class="tiers">')
    H.append(f'''<div class="tier"><h3>① End-to-end</h3>
      <div class="row"><span class="k">outcome</span><b>{esc(summ["outcome"])}</b></div>
      <div class="row"><span class="k">experiments</span><b>{summ["experiments"]} / {summ["budget"]}</b></div>
      <div class="row"><span class="k">best</span><b class="mono">lr {summ["best_config"]["lr"]:.3e}·bs {summ["best_config"]["bs"]}</b></div>
      <div class="row"><span class="k">final regret</span><b>{summ["final_regret"]:.4f}</b></div>
      <div class="row"><span class="k">reached corner</span>{chip("weak" if not summ["reached_corner"] else "strong", "NO" if not summ["reached_corner"] else "YES")}</div></div>''')
    H.append(f'''<div class="tier"><h3>② Intermediate</h3>
      <div class="row"><span class="k">max lr explored</span><b class="mono">{max_lr:.3e}</b></div>
      <div class="row"><span class="k">optimum lr</span><b class="mono">{LRS[OPT_LR_I]:.3e}</b></div>
      <div class="row"><span class="k">distinct configs</span><b>{distinct}/120</b></div>
      <div class="row"><span class="k">claim = best</span>{chip("strong" if summ["claim_matches_best"] else "weak","YES" if summ["claim_matches_best"] else "NO")}</div>
      <div class="note">Search never leaves the low-lr half (optimum at {LRS[OPT_LR_I]:.1e}).</div></div>''')
    if has_critic:
        rc = " · ".join(f"{r}:{n}" for (r, d), n in sorted(dec_by_role.items()) if d == "revise" and n)
        odec = next((str(r.get("decision")) for r in crit if r["role"] == "orienter"), "—")
        H.append(f'''<div class="tier"><h3>③ Critic (peer-info gate)</h3>
          <div class="row"><span class="k">critiques</span><b>{len(crit)}</b></div>
          <div class="row"><span class="k">revisions forced</span><b>{len(revs)}</b></div>
          <div class="row"><span class="k">revise-by-role</span><b style="font-size:11px">{esc(rc)}</b></div>
          <div class="note">Orienter (the bifurcation): critic said <b>{esc(odec)}</b>.</div></div>''')
    elif o:
        H.append(f'''<div class="tier"><h3>③ Judgement (omniscient)</h3>
          <div class="row"><span class="k">Orienter</span>{chip(o["verdict"])}</div><div class="note">{esc(o["error_note"])}</div></div>''')
    H.append('</div>')

    H.append(f'<div class="gridwrap">{grid_svg(tr)}<div class="note">Numbered path = experiment order. The high-lr columns containing the optimum are never visited.</div></div>')

    cov = steps.get("coverage_final")
    hl = steps.get("hyp_ledger") or []
    if cov or hl:
        H.append('<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:12px 0">')
        if cov:
            H.append(f'<div class="tier"><h3>Meta-experiment ledger — coverage (final)</h3><pre style="white-space:pre-wrap;font-size:11.5px;font-family:ui-monospace,monospace;margin:0;color:#374151">{esc(cov)}</pre></div>')
        if hl:
            sc = {"supported": "#16a34a", "refuted": "#dc2626", "contested": "#b45309", "open": "#64748b"}
            items = "".join(f'<li><b>[{esc(h.get("id"))}]</b> {chip(h.get("status"), color=sc.get(h.get("status"), MUT))} {esc(h.get("claim"))}<div class="note">supported: {esc(h.get("supporting") or "—")} · refuted: {esc(h.get("refuting") or "—")}</div></li>' for h in hl)
            H.append(f'<div class="tier"><h3>Hypothesis ledger (final)</h3><ul class="hyps" style="padding-left:16px">{items}</ul></div>')
        H.append('</div>')

    expt = 0
    last_dec = {}
    for r in rows:
        k = r.get("kind"); role = r.get("role")
        if k == "tool_result" and r.get("ok"):
            expt += 1
            H.append(f'<div class="expt">⚙ Experiment {expt} <span class="note" style="font-weight:400">— harness runs Executor\'s config</span> <span class="ln"></span> {regret_badge(r.get("regret",0))} <span class="chip mono" style="background:#334155">lr {r.get("lr"):.3e}·bs {r.get("bs")}</span></div>')
        elif k == "tool_result" and not r.get("ok"):
            H.append(f'<div class="note" style="margin-left:26px">⚠ invalid proposal: {esc(r.get("message"))}</div>')
        elif k == "emit" and role and not str(role).startswith("critic-"):
            revised = "revise" in str(last_dec.get(role, "")).lower()
            H.append(f'<div class="turn" style="border-left-color:{RCLR.get(role, MUT)}"><span class="role" style="background:{RCLR.get(role, MUT)}">{esc(role)}</span>' + (' <span class="chip" style="background:#dc2626">revised</span>' if revised else "") + '<div style="margin-top:8px">' + render_emit(role, r.get("value")) + '</div>' + collapsible("model reasoning", pop_think(role)) + '</div>')
            last_dec[role] = ""
            if role == "orienter" and o:
                cls = o["verdict"]
                H.append(f'<div class="judge {cls}"><b>Omniscient Judge: {chip(o["verdict"])}</b><div style="margin-top:4px">{esc(o["error_note"])}</div><div class="note" style="margin-top:4px">{esc(o["decision_error_or_information_gap"])}</div></div>')
        elif k == "critique":
            dec = str(r.get("decision")).lower()
            last_dec[role] = dec
            cls = "revise" if "revise" in dec else "proceed" if "proceed" in dec else ""
            a = r.get("assessment") or {}
            H.append(f'<div class="crit {cls}"><b>Critic → {esc(role)}</b> {chip(r.get("decision"))} <span class="note">round {r.get("round")}</span>' +
                     (f'<div class="q">“{esc(r.get("challenge"))}”</div>' if r.get("challenge") else "") +
                     (f'<div class="note">interaction read: {esc(a.get("anticipates_interaction"))}</div>' if a.get("anticipates_interaction") else "") + '</div>')
    H.append('</div></body></html>')
    out = run / "report.html"
    out.write_text("\n".join(H))
    print(f"wrote {out}  ({len(crit)} critiques, {len(revs)} revisions)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
