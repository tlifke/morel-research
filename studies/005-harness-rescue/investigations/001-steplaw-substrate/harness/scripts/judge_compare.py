import glob
import html
import json
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
JUDG = HARNESS / "runs" / "judgments"
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
    return html.escape(str(s or ""))


def chip(v):
    c = VCOLOR.get(v, "#64748b")
    return f'<span class="chip" style="background:{c}">{esc(v)}</span>'


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


def load_verdicts(run_name):
    out = {}
    for f in glob.glob(str(JUDG / "*.json")):
        vs = json.load(open(f))
        for v in (vs if isinstance(vs, list) else [vs]):
            rn = v.get("_run") or Path(f).stem.split("__")[0]
            if rn == run_name:
                out[v.get("_judge") or Path(f).stem.split("__")[-1]] = v
    return out


def main():
    run_dir, out = sys.argv[1], sys.argv[2]
    run_name = Path(run_dir).name
    steps, summ = trajectory(run_dir)
    verdicts = load_verdicts(run_name)
    judges = [j for j in JORDER if j in verdicts] + [j for j in verdicts if j not in JORDER]

    rub = "".join(f'<div class="rp"><b>{esc(t)}</b> — {esc(d)}</div>' for t, d in RUBRIC)
    traj = ""
    for i, s in enumerate(steps, 1):
        traj += (f'<div class="exp"><div class="eh">EXP {i}: lr={s["a"].get("lr")} bs={s["a"].get("bs")} '
                 f'&rarr; <b>{s["loss"]}</b></div><div class="er">{esc(s["reason"])}</div></div>')
    bc = summ.get("best_config") or {}

    # comparison grid
    head = "".join(f"<th>{esc(j)}</th>" for j in judges)
    def row(label, getter):
        cells = "".join(f"<td>{chip(getter(verdicts[j]))}</td>" for j in judges)
        return f"<tr><th class='rl'>{esc(label)}</th>{cells}</tr>"
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
                    f'<div class="dd"><b>bifurcation:</b> {esc(v.get("bifurcation_point"))} '
                    f'[{chip(v.get("bifurcation_classification"))}] <span class="ev">{esc(v.get("bifurcation_reasoning"))}</span></div>'
                    f'<div class="dd"><b>justification:</b> <span class="ev">{esc(v.get("justification"))}</span></div></div>')

    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>Judge comparison — {esc(run_name)}</title>
<style>
*{{box-sizing:border-box}} body{{font:13px/1.5 -apple-system,Segoe UI,sans-serif;margin:0;background:#f9fafb;color:#111827}}
header{{background:#111827;color:#f9fafb;padding:16px 24px}} header h1{{margin:0;font-size:16px;font-family:ui-monospace,monospace}} header .o{{color:#9ca3af;font-size:12.5px;margin-top:4px}}
.wrap{{padding:16px 22px;display:grid;grid-template-columns:300px 1fr;gap:16px;align-items:start}}
.card{{background:#fff;border:1px solid #e5e7eb;border-radius:10px;padding:13px 15px}}
.card h3{{margin:0 0 9px;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#6b7280}}
.rp{{font-size:12px;margin-bottom:8px;color:#374151}} .rp b{{color:#111827}}
.exp{{border-left:3px solid #cbd5e1;padding:3px 0 3px 9px;margin-bottom:6px}} .eh{{font:11.5px ui-monospace,monospace;color:#0f172a}} .er{{color:#64748b;font-size:11.5px}}
table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #eef2f7;padding:6px 8px;text-align:center}}
th.rl{{text-align:left;font-weight:600;color:#374151;font-size:12px;background:#f8fafc}} thead th{{background:#111827;color:#fff;font-family:ui-monospace,monospace;font-size:12px}}
.chip{{color:#fff;font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:5px;text-transform:uppercase;white-space:nowrap}}
.jd{{border-top:1px solid #f1f5f9;padding-top:9px;margin-top:9px}} .jd h4{{margin:0 0 6px;font-family:ui-monospace,monospace;font-size:13px}}
.dd{{font-size:12px;margin-bottom:5px;color:#334155}} .ev{{color:#64748b}}
.full{{grid-column:1 / -1}}
</style></head><body>
<header><h1>{esc(run_name)}</h1>
<div class="o">outcome: {esc(summ['outcome'])} · {summ['experiments']} experiments · best lr={bc.get('lr')} bs={bc.get('bs')} · regret <b>{max(0.0,summ['final_regret']):.4f}</b> (0=optimum, random≈0.029) · judges: {esc(', '.join(judges))}</div></header>
<div class="wrap">
  <div class="card"><h3>The rubric (judges/process_judge.md)</h3>{rub}
    <div style="margin-top:10px;font-size:11.5px;color:#6b7280">Verdicts are coarse: {chip('strong')} {chip('adequate')} {chip('weak')}. Judges see the full trajectory + outcome + ground-truth optimum (privileged, retrospective).</div></div>
  <div class="card"><h3>What the agent did</h3>{traj}</div>
  <div class="card full"><h3>Judge comparison</h3><table><thead><tr><th class="rl">dimension</th>{head}</tr></thead><tbody>{grid}</tbody></table>{details}</div>
</div></body></html>"""
    Path(out).write_text(doc)
    print("wrote", out)


if __name__ == "__main__":
    main()
