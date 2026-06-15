import glob
import html
import json
import math
import sys
from collections import Counter
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
JUDG = HARNESS / "runs" / "judgments"
OPT_LR, OPT_BS = 0.007812, 1024
VCOLOR = {"strong": "#16a34a", "adequate": "#b45309", "weak": "#dc2626",
          "sound_decision": "#16a34a", "information_gap": "#b45309", "decision_error": "#dc2626",
          "originated_self": "#16a34a", "integrated_well": "#b45309", "none": "#64748b", "misused": "#dc2626"}
JORDER = ["opus", "haiku", "gemini", "nemotron"]
DIMS = [("reasoned_about_structure", "Reasoned about structure (lr×bs interaction)"),
        ("formed_tested_hypotheses", "Formed & tested hypotheses"),
        ("exploration_quality", "Exploration quality")]
RUBRIC = [
    ("Process, not luck", "A good number from bad reasoning is weak; sound reasoning that got unlucky is not."),
    ("Decision-error vs information-gap", "A weak-looking step may just lack evidence yet — judge relative to what was knowable then."),
    ("Bottleneck, not sum", "As good as the weakest pivotal decision; tidy filler doesn't rescue a missed key move."),
    ("Find the bifurcation point", "Identify the one decision that most determined the outcome and classify it."),
    ("Credit help where it happened", "Originating the insight = strong; integrating sound advice well = adequate; misusing help = weak."),
]


def esc(s):
    return html.escape(str(s if s is not None else ""))


def chip(v):
    return f'<span class="chip" style="background:{VCOLOR.get(v, "#64748b")}">{esc(v)}</span>'


def yn(b, good_is_true=True):
    ok = b if good_is_true else not b
    return f'<span class="chip" style="background:{"#16a34a" if ok else "#dc2626"}">{"YES" if b else "NO"}</span>'


def trajectory(run_dir):
    rows = [json.loads(l) for l in open(Path(run_dir) / "trace.jsonl")]
    summ = json.load(open(Path(run_dir) / "loop_summary.json"))
    steps, pend = [], ""
    for r in rows:
        if r["kind"] == "thinking":
            pend = " ".join(r["text"].split())[:180]
        elif r["kind"] == "tool_use" and r.get("name") == "run_config":
            steps.append({"a": r["arguments"], "reason": pend, "loss": None}); pend = ""
        elif r["kind"] == "tool_result" and steps and steps[-1]["loss"] is None:
            try:
                steps[-1]["loss"] = json.loads(r["text"].split("}")[0] + "}").get("val_loss")
            except Exception:
                pass
    return steps, summ


def intermediate(summ):
    tr = summ["trajectory"]
    n = len(tr)
    reached_opt = any(abs(math.log(t["lr"]) - math.log(OPT_LR)) < 1e-6 and t["bs"] == OPT_BS for t in tr)
    reached_corner = any(t["lr"] >= 0.0055 and t["bs"] >= 736 for t in tr)
    distinct = len({(t["lr"], t["bs"]) for t in tr})
    bs_share = max(Counter(t["bs"] for t in tr).values()) / n if n else 0
    lr_share = max(Counter(t["lr"] for t in tr).values()) / n if n else 0
    frozen = "bs" if bs_share > 0.6 else ("lr" if lr_share > 0.6 else None)
    return {"reached_corner": reached_corner, "reached_opt": reached_opt, "distinct": distinct,
            "coverage": distinct / 120, "repeats": summ.get("repeats", 0), "frozen": frozen,
            "experiments": summ["experiments"], "budget": summ.get("budget", 50),
            "claim_ok": summ.get("claim_matches_best")}


def load_verdicts(run_name):
    out = {}
    for f in glob.glob(str(JUDG / "*.json")):
        for v in (lambda x: x if isinstance(x, list) else [x])(json.load(open(f))):
            if (v.get("_run") or Path(f).stem.split("__")[0]) == run_name:
                out[v.get("_judge") or Path(f).stem.split("__")[-1]] = v
    return out


def main():
    run_dir, out = sys.argv[1], sys.argv[2]
    run_name = Path(run_dir).name
    steps, summ = trajectory(run_dir)
    verdicts = load_verdicts(run_name)
    judges = [j for j in JORDER if j in verdicts] + [j for j in verdicts if j not in JORDER]
    im = intermediate(summ)
    regret = max(0.0, summ["final_regret"])
    rc = "#16a34a" if regret < 0.002 else ("#b45309" if regret < 0.01 else "#dc2626")

    # ---- TIER 1: End-to-end (objective outcome) ----
    e2e = (f'<div class="big" style="color:{rc}">{regret:.4f}</div><div class="cap">simple regret '
           f'(0 = optimum · random ≈ 0.029 · worst 0.19)</div>'
           f'<div class="kv">reached exact optimum {yn(im["reached_opt"])}</div>'
           f'<div class="kv">outcome <b>{esc(summ["outcome"])}</b>{(" · "+esc(summ.get("finish_kind"))) if summ.get("finish_kind") else ""}</div>'
           f'<div class="kv">best loss <b>{summ["best_loss"]:.4f}</b></div>')

    # ---- TIER 2: Intermediate (problem-specific, computable) ----
    inter = (f'<div class="kv">reached high-lr / large-bs corner {yn(im["reached_corner"])}</div>'
             f'<div class="kv">froze an axis {chip("none") if not im["frozen"] else chip("misused")} '
             f'{("("+im["frozen"]+")") if im["frozen"] else ""}</div>'
             f'<div class="kv">coverage <b>{im["distinct"]}/120</b> ({im["coverage"]*100:.0f}%) · repeats <b>{im["repeats"]}</b></div>'
             f'<div class="kv">experiments used <b>{im["experiments"]}/{im["budget"]}</b></div>'
             f'<div class="kv">reported best matched actual {yn(im["claim_ok"]) if im["claim_ok"] is not None else chip("n/a")}</div>')

    # ---- TIER 3: Judgements (panel qualitative) ----
    pv = [verdicts[j].get("process_verdict") for j in judges]
    consensus = (chip(pv[0]) + " <b>unanimous</b>") if pv and len(set(pv)) == 1 else '<b>split</b>'
    jrows = "".join(f'<div class="kv"><span class="jn">{esc(j)}</span> {chip(verdicts[j].get("process_verdict"))} '
                    f'<span class="sub">help: {esc(verdicts[j].get("used_external_help") or "—")}</span></div>' for j in judges)
    judg = f'<div class="big" style="font-size:18px">{consensus}</div><div class="cap">panel process-verdict (qualitative — the <i>why</i>)</div>{jrows}'

    banner = (f'<div class="banner">'
              f'<div class="bcard t1"><div class="bh">① End-to-End Metrics</div><div class="bs">objective outcome</div>{e2e}</div>'
              f'<div class="bcard t2"><div class="bh">② Intermediate Metrics</div><div class="bs">problem-specific · computable (survive without regret)</div>{inter}</div>'
              f'<div class="bcard t3"><div class="bh">③ Judgements</div><div class="bs">{len(judges)}-judge panel · qualitative</div>{judg}</div>'
              f'</div>')

    # ---- details ----
    rub = "".join(f'<div class="rp"><b>{esc(t)}</b> — {esc(d)}</div>' for t, d in RUBRIC)
    traj = ""
    for i, s in enumerate(steps, 1):
        traj += (f'<div class="exp"><div class="eh">EXP {i}: lr={s["a"].get("lr")} bs={s["a"].get("bs")} '
                 f'&rarr; <b>{s["loss"]}</b></div><div class="er">{esc(s["reason"])}</div></div>')
    head = "".join(f"<th>{esc(j)}</th>" for j in judges)
    def row(label, getter):
        return f"<tr><th class='rl'>{esc(label)}</th>" + "".join(f"<td>{chip(getter(verdicts[j]))}</td>" for j in judges) + "</tr>"
    grid = row("PROCESS VERDICT", lambda v: v.get("process_verdict"))
    for key, lbl in DIMS:
        grid += row(lbl, lambda v, k=key: (v.get(k) or {}).get("verdict"))
    grid += row("bifurcation class", lambda v: v.get("bifurcation_classification"))
    grid += row("used external help", lambda v: v.get("used_external_help"))
    details = ""
    for j in judges:
        v = verdicts[j]
        dims = "".join(f'<div class="dd"><b>{esc(lbl)}:</b> {chip((v.get(k) or {}).get("verdict"))} '
                       f'<span class="ev">{esc((v.get(k) or {}).get("evidence"))}</span></div>' for k, lbl in DIMS)
        details += (f'<div class="jd"><h4>{esc(j)} — {chip(v.get("process_verdict"))}</h4>{dims}'
                    f'<div class="dd"><b>bifurcation:</b> {esc(v.get("bifurcation_point"))} [{chip(v.get("bifurcation_classification"))}] '
                    f'<span class="ev">{esc(v.get("bifurcation_reasoning"))}</span></div>'
                    f'<div class="dd"><b>justification:</b> <span class="ev">{esc(v.get("justification"))}</span></div></div>')

    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Evaluation — {esc(run_name)}</title>
<style>
*{{box-sizing:border-box}} body{{font:13px/1.5 -apple-system,Segoe UI,sans-serif;margin:0;background:#eef1f5;color:#111827}}
header{{background:#111827;color:#f9fafb;padding:14px 24px}} header h1{{margin:0;font-size:15px;font-family:ui-monospace,monospace}} header .o{{color:#9ca3af;font-size:12px;margin-top:3px}}
.banner{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;padding:18px 22px}}
.bcard{{background:#fff;border-radius:12px;padding:16px 18px;box-shadow:0 1px 3px rgba(0,0,0,.08);border-top:5px solid #999}}
.bcard.t1{{border-top-color:#1d4ed8}} .bcard.t2{{border-top-color:#0d9488}} .bcard.t3{{border-top-color:#7c3aed}}
.bh{{font-size:15px;font-weight:800;letter-spacing:.01em}} .bs{{font-size:11.5px;color:#6b7280;margin:2px 0 12px}}
.big{{font-size:30px;font-weight:800;line-height:1.1}} .cap{{font-size:11px;color:#6b7280;margin:2px 0 10px}}
.kv{{font-size:13px;margin-bottom:7px}} .jn{{display:inline-block;min-width:64px;font-family:ui-monospace,monospace;font-size:12px}} .sub{{color:#94a3b8;font-size:11px}}
.chip{{color:#fff;font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:5px;text-transform:uppercase;white-space:nowrap}}
.details{{padding:6px 22px 26px}} .details > h2{{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;border-top:1px solid #d8dee6;padding-top:14px;margin:6px 0 12px}}
.wrap{{display:grid;grid-template-columns:300px 1fr;gap:14px;align-items:start}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:13px 15px}} .card h3{{margin:0 0 9px;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:#6b7280}}
.rp{{font-size:12px;margin-bottom:8px;color:#374151}} .rp b{{color:#111827}}
.exp{{border-left:3px solid #cbd5e1;padding:3px 0 3px 9px;margin-bottom:6px}} .eh{{font:11.5px ui-monospace,monospace;color:#0f172a}} .er{{color:#64748b;font-size:11.5px}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #eef2f7;padding:6px 8px;text-align:center}}
th.rl{{text-align:left;font-weight:600;color:#374151;font-size:12px;background:#f8fafc}} thead th{{background:#111827;color:#fff;font-family:ui-monospace,monospace;font-size:12px}}
.jd{{border-top:1px solid #f1f5f9;padding-top:9px;margin-top:9px}} .jd h4{{margin:0 0 6px;font-family:ui-monospace,monospace;font-size:13px}} .dd{{font-size:12px;margin-bottom:5px;color:#334155}} .ev{{color:#64748b}}
.full{{grid-column:1 / -1}}
</style></head><body>
<header><h1>{esc(run_name)}</h1><div class="o">three-tier evaluation · judges: {esc(', '.join(judges))}</div></header>
{banner}
<div class="details">
  <h2>supporting detail</h2>
  <div class="wrap">
    <div class="card"><h3>The rubric (judges/process_judge.md)</h3>{rub}
      <div style="margin-top:10px;font-size:11.5px;color:#6b7280">Coarse verdicts: {chip('strong')} {chip('adequate')} {chip('weak')}. Judges see the full trajectory + outcome + ground-truth optimum (privileged, retrospective).</div></div>
    <div class="card"><h3>What the agent did</h3>{traj}</div>
    <div class="card full"><h3>Judge comparison grid</h3><table><thead><tr><th class="rl">dimension</th>{head}</tr></thead><tbody>{grid}</tbody></table>{details}</div>
  </div>
</div></body></html>"""
    Path(out).write_text(doc)
    print("wrote", out)


if __name__ == "__main__":
    main()
