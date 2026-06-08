import html
import json
import sys
from pathlib import Path


def load(run_dir):
    lines = [json.loads(l) for l in open(Path(run_dir) / "trace.jsonl")]
    meta = lines[0] if lines and lines[0]["kind"] == "meta" else {}
    steps = [r for r in lines if r["kind"] in ("thinking", "assistant_text", "tool_use", "tool_result")]
    summary = json.load(open(Path(run_dir) / "loop_summary.json"))
    return meta, steps, summary


def esc(s):
    return html.escape(str(s))


STEP_CSS = {
    "thinking": ("REASON", "#6b7280", "#f3f4f6"),
    "tool_use": ("CALL", "#0f766e", "#ccfbf1"),
    "tool_result": ("SUBSTRATE", "#b45309", "#fef3c7"),
    "assistant_text": ("SAY", "#1d4ed8", "#dbeafe"),
}


def render_steps(steps):
    out = []
    expn = 0
    for s in steps:
        kind = s["kind"]
        label, fg, bg = STEP_CSS[kind]
        cls = "step"
        if kind == "tool_use":
            if s["name"] == "finish":
                label = "FINISH"
                fg, bg = "#5b21b6", "#ede9fe"
                body = "<code>finish(" + esc(json.dumps(s.get("arguments", {}))) + ")</code>"
            else:
                expn += 1
                label = f"EXP {expn}"
                body = "<code>run_config(" + esc(json.dumps(s.get("arguments", {}))) + ")</code>"
        elif kind == "tool_result":
            txt = s["text"]
            if '"error"' in txt or '"off_grid"' in txt:
                label, fg, bg, cls = "REJECT", "#991b1b", "#fee2e2", "step reject"
            body = "<code>" + esc(txt[:400]) + "</code>"
        elif kind == "thinking":
            body = "<em>" + esc(s["text"].strip()) + "</em>"
        else:
            body = esc(s["text"].strip())
        out.append(
            f'<div class="{cls}"><span class="badge" style="color:{fg};background:{bg}">{label}'
            f'</span><div class="body">{body}</div></div>'
        )
    return "".join(out)


OUTCOME_STYLE = {
    "finished": ("#166534", "#dcfce7", "&#10003; FINISHED &mdash; called the finish tool deliberately."),
    "stalled": ("#991b1b", "#fee2e2", "&#9888; STALLED &mdash; yielded without ever calling finish. Reached a conclusion in prose but never actuated the terminal tool."),
}


def outcome_banner(summary):
    oc = summary["outcome"]
    key = "finished" if oc == "finished" else ("stalled" if oc == "stalled" else "ceiling")
    if key == "ceiling":
        fg, bg, txt = "#92400e", "#fffbeb", f"&#9632; CEILING &mdash; hit a hard guard ({esc(oc)}) while still exploring."
    else:
        fg, bg, txt = OUTCOME_STYLE[key]
    return f'<div class="outcome" style="color:{fg};background:{bg}">{txt}</div>'


def summary_block(summary):
    rows = [
        ("outcome", summary["outcome"]),
        ("experiments run", summary["experiments"]),
        ("invalid (off-grid) requests", summary["invalid_requests"]),
        ("repeats", summary["repeats"]),
        ("best loss", f"{summary['best_loss']:.5f}"),
        ("best config", f"lr={summary['best_config']['lr']}, bs={summary['best_config']['bs']}" if summary.get("best_config") else "—"),
        ("final regret", f"{summary['final_regret']:+.5f}"),
        ("claim matches best", summary.get("claim_matches_best")),
    ]
    cells = "".join(f"<tr><td>{esc(k)}</td><td><b>{esc(v)}</b></td></tr>" for k, v in rows)
    return f"<table class='sum'>{cells}</table>"


def column(meta, steps, summary):
    return (
        f'<div class="col"><div class="colhead"><h2>{esc(meta.get("model","?"))}</h2>'
        f'{outcome_banner(summary)}{summary_block(summary)}</div>{render_steps(steps)}</div>'
    )


def main():
    nemo_dir, gem_dir, out = sys.argv[1], sys.argv[2], sys.argv[3]
    nmeta, nsteps, nsum = load(nemo_dir)
    gmeta, gsteps, gsum = load(gem_dir)
    sys_prompt = nmeta.get("system_prompt", "")
    first_user = nmeta.get("first_user", "")

    ncol = column(nmeta, nsteps, nsum)
    gcol = column(gmeta, gsteps, gsum)

    doc = f"""<!doctype html><html><head><meta charset="utf-8">
<title>StepLaw baseline (single-conversation) — two models</title>
<style>
*{{box-sizing:border-box}}
body{{font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;margin:0;color:#111827;background:#f9fafb}}
header{{background:#111827;color:#f9fafb;padding:22px 28px}}
header h1{{margin:0 0 4px;font-size:20px}}
header .sub{{color:#9ca3af;font-size:13px}}
.instr{{background:#fff;border-bottom:1px solid #e5e7eb;padding:18px 28px}}
.instr h3{{margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:.04em;color:#6b7280}}
.instr pre{{background:#0f172a;color:#e2e8f0;padding:14px 16px;border-radius:8px;white-space:pre-wrap;font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;margin:0 0 12px}}
.instr .tmpl{{background:#fef3c7;color:#78350f;padding:10px 14px;border-radius:8px;font:12.5px ui-monospace,monospace}}
.identical{{display:inline-block;background:#dcfce7;color:#166534;font-size:11px;font-weight:600;padding:2px 8px;border-radius:999px;margin-left:8px}}
.cols{{display:grid;grid-template-columns:1fr 1fr;gap:0}}
.col{{padding:0 0 40px}}
.col:first-child{{border-right:2px solid #e5e7eb}}
.colhead{{position:sticky;top:0;background:#f9fafb;padding:16px 20px;border-bottom:2px solid #e5e7eb;z-index:5}}
.colhead h2{{margin:0 0 8px;font-size:16px;font-family:ui-monospace,monospace}}
.outcome{{padding:8px 12px;border-radius:8px;font-size:12.5px;font-weight:600;margin-bottom:10px}}
table.sum{{border-collapse:collapse;font-size:12.5px;width:100%}}
table.sum td{{padding:2px 8px;border-bottom:1px solid #f3f4f6}}
table.sum td:first-child{{color:#6b7280}}
.step{{display:flex;gap:10px;padding:7px 14px;border-bottom:1px solid #f3f4f6;align-items:flex-start}}
.step.reject{{background:#fef2f2}}
.badge{{flex:0 0 auto;font-size:10px;font-weight:700;padding:2px 7px;border-radius:5px;letter-spacing:.03em;margin-top:1px;min-width:62px;text-align:center}}
.body{{flex:1;min-width:0;word-break:break-word}}
.body code{{font:11.5px ui-monospace,monospace;background:#f1f5f9;padding:1px 5px;border-radius:4px;white-space:pre-wrap}}
.body em{{color:#4b5563}}
</style></head><body>
<header>
<h1>StepLaw lr/bs tuning &mdash; single-conversation harness, two models</h1>
<div class="sub">study 005 &middot; inv 001 &middot; env N={esc(nsum['N'])} D={esc(nsum['D'])} &middot; optimum_loss={esc(round(nsum['optimum_loss'],5))} &middot; one agent.prompt() &middot; budget {esc(nsum['budget'])} &middot; finish-tool + off-grid rejection</div>
</header>
<div class="instr">
<h3>System prompt <span class="identical">IDENTICAL for both models</span></h3>
<pre>{esc(sys_prompt)}</pre>
<h3>Single opening message (no per-turn counting; the agent self-paces until it calls finish)</h3>
<div class="tmpl">{esc(first_user)}</div>
</div>
<div class="cols">{ncol}{gcol}</div>
</body></html>"""

    Path(out).write_text(doc)
    print("wrote", out)


if __name__ == "__main__":
    main()
