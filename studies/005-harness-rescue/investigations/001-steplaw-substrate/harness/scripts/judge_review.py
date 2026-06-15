import html
import json
import sys
from pathlib import Path

HARNESS = Path(__file__).resolve().parents[1]
VCOLOR = {"strong": "#16a34a", "adequate": "#b45309", "weak": "#dc2626",
          "sound_decision": "#16a34a", "information_gap": "#b45309", "decision_error": "#dc2626"}


def esc(s):
    return html.escape(str(s))


def trajectory(run_dir):
    rows = [json.loads(l) for l in open(Path(run_dir) / "trace.jsonl")]
    summ = json.load(open(Path(run_dir) / "loop_summary.json"))
    steps, pending = [], ""
    for r in rows:
        if r["kind"] == "thinking":
            pending = " ".join(r["text"].split())[:220]
        elif r["kind"] == "tool_use" and r.get("name") == "run_config":
            steps.append({"args": r["arguments"], "reason": pending, "loss": None})
            pending = ""
        elif r["kind"] == "tool_result" and steps and steps[-1]["loss"] is None:
            try:
                steps[-1]["loss"] = json.loads(r["text"].split("}")[0] + "}").get("val_loss")
            except Exception:
                pass
    return steps, summ


def agent_col(run_dir, label):
    steps, summ = trajectory(run_dir)
    rows = ""
    for i, s in enumerate(steps, 1):
        a = s["args"]
        rows += (f'<div class="exp"><div class="ehead">EXP {i}: lr={a.get("lr")} bs={a.get("bs")} '
                 f'&rarr; loss <b>{s["loss"]}</b></div><div class="reason">{esc(s["reason"])}</div></div>')
    bc = summ.get("best_config") or {}
    out = (f'<div class="outcome">OUTCOME — {summ["experiments"]} experiments · {summ["outcome"]} · '
           f'best lr={bc.get("lr")} bs={bc.get("bs")} · <b>regret {max(0.0,summ["final_regret"]):.4f}</b> '
           f'(0 = optimum; random ≈ 0.029)</div>')
    return f'<div class="col agent"><h3>{esc(label)} — what the agent actually did</h3>{rows}{out}</div>'


def dim(v, title):
    c = VCOLOR.get(v.get("verdict"), "#6b7280")
    return (f'<div class="dim"><span class="vb" style="background:{c}">{esc(v.get("verdict"))}</span>'
            f'<b>{esc(title)}</b><div class="ev">{esc(v.get("evidence"))}</div></div>')


def judge_col(verdict):
    pv = verdict.get("process_verdict")
    pc = VCOLOR.get(pv, "#6b7280")
    bc = VCOLOR.get(verdict.get("bifurcation_classification"), "#6b7280")
    return (f'<div class="col judge"><h3>What the Gemini judge concluded</h3>'
            f'<div class="pv" style="background:{pc}">process verdict: {esc(pv)}</div>'
            + dim(verdict["reasoned_about_structure"], "reasoned about structure (lr×bs interaction)")
            + dim(verdict["formed_tested_hypotheses"], "formed & tested hypotheses")
            + dim(verdict["exploration_quality"], "exploration quality")
            + f'<div class="bif"><b>bifurcation point</b><div>{esc(verdict.get("bifurcation_point"))}</div>'
            f'<span class="vb" style="background:{bc}">{esc(verdict.get("bifurcation_classification"))}</span> '
            f'<span class="ev">{esc(verdict.get("bifurcation_reasoning"))}</span></div>'
            f'<div class="just"><b>justification</b><div>{esc(verdict.get("justification"))}</div></div></div>')


def section(run_dir, gem_json, label):
    v = json.load(open(gem_json))
    return f'<div class="section"><div class="cols">{agent_col(run_dir, label)}{judge_col(v)}</div></div>'


def main():
    out = sys.argv[1]
    base = HARNESS / "runs"
    s11 = base / "phase1" / "ollama_A3_relow_N214663680_D100000000000_s11"
    s20 = base / "phase1" / "ollama_A3_relow_N214663680_D100000000000_s20"
    j11 = base / "judgments" / "ollama_A3_relow_N214663680_D100000000000_s11__gemini.json"
    j20 = base / "judgments" / "ollama_A3_relow_N214663680_D100000000000_s20__gemini.json"
    body = (section(s11, j11, "A3 seed 11 — FAILURE (regret 0.016)")
            + section(s20, j20, "A3 seed 20 — SUCCESS (regret 0)"))
    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>How the process-judge works</title>
<style>
*{{box-sizing:border-box}} body{{font:13px/1.55 -apple-system,Segoe UI,sans-serif;margin:0;background:#f9fafb;color:#111827}}
header{{background:#111827;color:#f9fafb;padding:18px 26px}} header h1{{margin:0;font-size:18px}} header .s{{color:#9ca3af;font-size:12.5px;margin-top:4px}}
.section{{margin:18px 22px;border:1px solid #e5e7eb;border-radius:10px;background:#fff;overflow:hidden}}
.cols{{display:grid;grid-template-columns:1fr 1fr}}
.col{{padding:14px 16px}} .col.agent{{border-right:2px solid #e5e7eb;background:#fcfcfd}}
.col h3{{margin:0 0 10px;font-size:13px;text-transform:uppercase;letter-spacing:.03em;color:#374151}}
.exp{{border-left:3px solid #cbd5e1;padding:5px 0 5px 10px;margin-bottom:7px}}
.ehead{{font:12px ui-monospace,monospace;color:#0f172a}} .reason{{color:#64748b;font-size:12px;margin-top:2px}}
.outcome{{margin-top:10px;background:#f1f5f9;border-radius:7px;padding:9px 11px;font-size:12.5px}}
.pv{{color:#fff;font-weight:700;padding:5px 11px;border-radius:7px;display:inline-block;margin-bottom:12px;text-transform:uppercase;font-size:12px}}
.dim{{margin-bottom:11px}} .vb{{color:#fff;font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:5px;margin-right:7px;text-transform:uppercase}}
.ev{{color:#475569;font-size:12px;margin-top:3px}} .bif,.just{{margin-top:12px;background:#f8fafc;border:1px solid #eef2f7;border-radius:7px;padding:9px 11px;font-size:12.5px}}
.bif b,.just b{{font-size:11px;text-transform:uppercase;letter-spacing:.03em;color:#6b7280}}
</style></head><body>
<header><h1>How the process-judge works — failure vs success (same A3 baseline)</h1>
<div class="s">LEFT = the agent's real run (the privileged case file the judge receives also includes the ground-truth optimum). RIGHT = the Gemini judge's verdict. Regret is objective; the judge's per-dimension verdicts are its qualitative best-estimate of the reasoning.</div></header>
{body}</body></html>"""
    Path(out).write_text(doc)
    print("wrote", out)


if __name__ == "__main__":
    main()
