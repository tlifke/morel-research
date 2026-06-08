import html
import json
import sys
from pathlib import Path

RUNS = Path(__file__).resolve().parents[1] / "runs" / "sweep"

STEP_CSS = {
    "thinking": ("REASON", "#6b7280", "#f3f4f6"),
    "tool_use": ("CALL", "#0f766e", "#ccfbf1"),
    "tool_result": ("RESULT", "#b45309", "#fef3c7"),
    "assistant_text": ("SAY", "#1d4ed8", "#dbeafe"),
}


def esc(s):
    return html.escape(str(s))


def load(seed):
    d = next(RUNS.glob(f"ollama_*_s{seed}"))
    lines = [json.loads(l) for l in open(d / "trace.jsonl")]
    meta = lines[0]
    steps = [r for r in lines if r["kind"] in ("thinking", "assistant_text", "tool_use", "tool_result")]
    summary = json.load(open(d / "loop_summary.json"))
    return meta, steps, summary


def render_steps(steps):
    out, expn = [], 0
    for s in steps:
        kind = s["kind"]
        label, fg, bg = STEP_CSS[kind]
        cls = "step"
        if kind == "tool_use":
            if s["name"] == "finish":
                label, fg, bg = "FINISH", "#5b21b6", "#ede9fe"
                body = "<code>finish(" + esc(json.dumps(s.get("arguments", {}))) + ")</code>"
            else:
                expn += 1
                label = f"EXP {expn}"
                body = "<code>run_config(" + esc(json.dumps(s.get("arguments", {}))) + ")</code>"
        elif kind == "tool_result":
            txt = s["text"]
            if '"error"' in txt:
                label, fg, bg, cls = "REJECT", "#991b1b", "#fee2e2", "step reject"
            body = "<code>" + esc(txt[:300]) + "</code>"
        elif kind == "thinking":
            body = "<em>" + esc(s["text"].strip()) + "</em>"
        else:
            body = esc(s["text"].strip())
        out.append(f'<div class="{cls}"><span class="badge" style="color:{fg};background:{bg}">{label}</span><div class="body">{body}</div></div>')
    return "".join(out)


def column(title, sub, subcolor, steps, summary):
    bc = summary.get("best_config") or {}
    stat = (f"{summary['outcome']} · {summary['experiments']} exp · regret {max(0.0,summary['final_regret']):.4f} · "
            f"best lr={bc.get('lr')} bs={bc.get('bs')}")
    return (f'<div class="col"><div class="colhead" style="border-top:4px solid {subcolor}">'
            f'<h2>{esc(title)}</h2><div class="sub" style="color:{subcolor}">{esc(sub)}</div>'
            f'<div class="stat">{esc(stat)}</div></div>{render_steps(steps)}</div>')


def main():
    out = sys.argv[1]
    cases = [
        ("1", "STALL", "concluded in prose, never called finish", "#dc2626"),
        ("3", "LUCKY WIN", "wandered into the true optimum, finished", "#16a34a"),
        ("4", "EARLY BAD FINISH", "settled in a weak basin, quit early", "#b45309"),
    ]
    cols = []
    sysp = None
    for seed, title, sub, color in cases:
        meta, steps, summary = load(seed)
        sysp = sysp or meta.get("system_prompt", "")
        cols.append(column(f"seed {seed} — {title}", sub, color, steps, summary))

    doc = f"""<!doctype html><html><head><meta charset="utf-8"><title>nemotron-4b on Env A — three faces of the same setup</title>
<style>
*{{box-sizing:border-box}} body{{font:13px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;color:#111827;background:#f9fafb}}
header{{background:#111827;color:#f9fafb;padding:20px 26px}} header h1{{margin:0 0 4px;font-size:19px}} header .sub{{color:#9ca3af;font-size:12.5px}}
.instr{{background:#fff;border-bottom:1px solid #e5e7eb;padding:14px 26px}} .instr h3{{margin:0 0 6px;font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#6b7280}}
.instr pre{{background:#0f172a;color:#e2e8f0;padding:12px 14px;border-radius:8px;white-space:pre-wrap;font:11.5px/1.5 ui-monospace,Menlo,monospace;margin:0}}
.cols{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:0}} .col{{border-right:1px solid #e5e7eb}} .col:last-child{{border-right:none}}
.colhead{{position:sticky;top:0;background:#f9fafb;padding:12px 16px;border-bottom:2px solid #e5e7eb;z-index:5}}
.colhead h2{{margin:0 0 2px;font-size:14px;font-family:ui-monospace,monospace}} .colhead .sub{{font-size:12px;font-weight:600}} .colhead .stat{{font-size:11px;color:#374151;margin-top:4px;font-family:ui-monospace,monospace}}
.step{{display:flex;gap:8px;padding:6px 12px;border-bottom:1px solid #f3f4f6;align-items:flex-start}} .step.reject{{background:#fef2f2}}
.badge{{flex:0 0 auto;font-size:9.5px;font-weight:700;padding:2px 6px;border-radius:5px;letter-spacing:.02em;margin-top:1px;min-width:52px;text-align:center}}
.body{{flex:1;min-width:0;word-break:break-word}} .body code{{font:11px ui-monospace,monospace;background:#f1f5f9;padding:1px 4px;border-radius:4px;white-space:pre-wrap}} .body em{{color:#4b5563}}
</style></head><body>
<header><h1>nemotron-3-nano:4b on Env A — three faces of the <em>identical</em> setup</h1>
<div class="sub">study 005 · inv 001 · same system prompt, same env (N=215M, D=100B), same budget · only the sampling seed differs · reasoning shown inline</div></header>
<div class="instr"><h3>System prompt (identical for all three)</h3><pre>{esc(sysp)}</pre></div>
<div class="cols">{''.join(cols)}</div>
</body></html>"""
    Path(out).write_text(doc)
    print("wrote", out)


if __name__ == "__main__":
    main()
