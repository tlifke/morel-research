import argparse
import html
import json
from pathlib import Path

MOVE_META = {
    "INPUT": ("#475569", "Task handed to the agent"),
    "REASON": ("#7c3aed", "Private model reasoning (thinking)"),
    "ORIENT": ("#0891b2", "Reads prior state / history"),
    "HYPOTHESIZE": ("#7c3aed", "Proposes an idea"),
    "DESIGN": ("#6366f1", "Idea -> concrete command"),
    "EXECUTE": ("#2563eb", "Kicks off the experiment"),
    "OBSERVE": ("#0891b2", "Reads raw run output"),
    "MEASURE": ("#0d9488", "Gets the metric"),
    "INTERPRET": ("#0d9488", "Makes sense of the metric"),
    "DECIDE": ("#9333ea", "Refine / pivot / stop"),
    "RECORD": ("#ca8a04", "Writes state for its future self"),
    "DIAGNOSE": ("#dc2626", "Names error cause + correction"),
    "REPORT": ("#4f46e5", "States what was tried and the result"),
    "SUBSTRATE": ("#d97706", "Result returned by the substrate"),
    "TOOL": ("#475569", "Tool call"),
    "END": ("#64748b", "Run complete"),
}

INFER = {
    "bash": "EXECUTE", "evaluate_predictions": "MEASURE", "read": "OBSERVE",
    "glob": "ORIENT", "write": "RECORD", "share_finding": "REPORT", "edit": "RECORD",
}

DEFAULT_META = {
    "title": "Agent run — single trace",
    "subtitle": "",
    "model": "?",
    "substrate": "?",
    "scenario": "",
    "system_prompt": "",
    "first_user": "",
    "tools": [],
    "notes": [],
}


def esc(s):
    return html.escape(str(s))


def first_line(s, n=58):
    t = str(s).strip()
    line = t.splitlines()[0] if t else ""
    return (line[:n] + "…") if len(line) > n else line


def classify(rec):
    k = rec["kind"]
    if k == "input":
        return "INPUT", "cold-start prompt"
    if k == "thinking":
        return "REASON", rec.get("text", "")
    if k == "tool_use":
        move = rec.get("move") or INFER.get(rec.get("name", ""), "TOOL")
        return move, rec.get("name", "")
    if k == "tool_result":
        return "SUBSTRATE", rec.get("text", "")
    if k == "assistant_text":
        return "REPORT", rec.get("text", "")
    if k == "end":
        return "END", ""
    return k.upper(), ""


def build_sequence_svg(rows):
    rx, sx = 250, 600
    top, gap = 130, 66
    height = top + gap * len(rows) + 30
    out = [
        f'<svg viewBox="0 0 820 {height}" width="100%" style="max-width:820px" xmlns="http://www.w3.org/2000/svg" font-family="ui-sans-serif,system-ui,sans-serif">',
        '<defs>'
        '<marker id="ar" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#334155"/></marker>'
        '<marker id="arb" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#d97706"/></marker>'
        '</defs>',
    ]
    out.append(f'<line x1="{rx}" y1="86" x2="{rx}" y2="{height-30}" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="4 4"/>')
    out.append(f'<line x1="{sx}" y1="86" x2="{sx}" y2="{height-30}" stroke="#cbd5e1" stroke-width="2" stroke-dasharray="4 4"/>')
    y = top
    for move, payload in rows:
        color = MOVE_META.get(move, ("#475569", ""))[0]
        if move == "INPUT":
            out.append(f'<rect x="20" y="{y-16}" width="120" height="32" rx="6" fill="{color}"/>')
            out.append(f'<text x="80" y="{y+4}" fill="#fff" font-size="11" font-weight="600" text-anchor="middle">INPUT</text>')
            out.append(f'<line x1="140" y1="{y}" x2="{rx}" y2="{y}" stroke="#334155" stroke-width="1.5" marker-end="url(#ar)"/>')
        elif move in ("REASON", "DECIDE", "HYPOTHESIZE", "INTERPRET", "DESIGN", "ORIENT"):
            out.append(f'<circle cx="{rx}" cy="{y}" r="6" fill="{color}"/>')
            out.append(f'<text x="{rx-16}" y="{y+4}" fill="{color}" font-size="10.5" font-style="italic" text-anchor="end">{esc(move.lower())}: {esc(first_line(payload,28))}</text>')
        elif move in ("EXECUTE", "MEASURE", "OBSERVE", "RECORD", "TOOL"):
            out.append(f'<line x1="{rx}" y1="{y}" x2="{sx}" y2="{y}" stroke="#334155" stroke-width="1.8" marker-end="url(#ar)"/>')
            out.append(f'<rect x="{(rx+sx)//2-95}" y="{y-26}" width="190" height="20" rx="5" fill="{color}"/>')
            out.append(f'<text x="{(rx+sx)//2}" y="{y-12}" fill="#fff" font-size="10.5" font-weight="600" text-anchor="middle">{esc(move)} · {esc(payload)}</text>')
        elif move == "SUBSTRATE":
            out.append(f'<line x1="{sx}" y1="{y}" x2="{rx}" y2="{y}" stroke="#d97706" stroke-width="1.8" stroke-dasharray="5 3" marker-end="url(#arb)"/>')
            out.append(f'<text x="{(rx+sx)//2}" y="{y-8}" fill="#b45309" font-size="10.5" text-anchor="middle">result: {esc(first_line(payload,42))}</text>')
        elif move in ("REPORT", "DIAGNOSE"):
            out.append(f'<rect x="{rx-150}" y="{y-16}" width="300" height="32" rx="6" fill="{color}"/>')
            out.append(f'<text x="{rx}" y="{y+4}" fill="#fff" font-size="11" font-weight="600" text-anchor="middle">{esc(move)}</text>')
        elif move == "END":
            out.append(f'<line x1="{rx-26}" y1="{y}" x2="{rx+26}" y2="{y}" stroke="{color}" stroke-width="4"/>')
            out.append(f'<text x="{rx+38}" y="{y+4}" fill="{color}" font-size="11" font-weight="600">END</text>')
        y += gap
    out.append("</svg>")
    return "\n".join(out)


def actor_headers(meta):
    rx, sx = 250, 600
    return (
        f'<svg viewBox="0 0 820 96" width="100%" style="max-width:820px;margin-bottom:-8px" xmlns="http://www.w3.org/2000/svg" font-family="ui-sans-serif,system-ui,sans-serif">'
        f'<rect x="{rx-110}" y="20" width="220" height="46" rx="8" fill="#1e293b"/>'
        f'<text x="{rx}" y="40" fill="#fff" font-size="13" font-weight="700" text-anchor="middle">Agent</text>'
        f'<text x="{rx}" y="58" fill="#cbd5e1" font-size="11" text-anchor="middle">{esc(meta["model"])}</text>'
        f'<rect x="{sx-110}" y="20" width="220" height="46" rx="8" fill="#92400e"/>'
        f'<text x="{sx}" y="40" fill="#fff" font-size="13" font-weight="700" text-anchor="middle">Substrate</text>'
        f'<text x="{sx}" y="58" fill="#fde68a" font-size="11" text-anchor="middle">{esc(meta["substrate"])}</text>'
        f"</svg>"
    )


def render_step_card(idx, rec):
    move, _ = classify(rec)
    color = MOVE_META.get(move, ("#475569", ""))[0]
    k = rec["kind"]
    body = ""
    if k == "tool_use":
        args = json.dumps(rec.get("arguments", {}), indent=2)
        body = f'<div class="lbl">tool call · <b>{esc(rec.get("name",""))}</b></div><pre>{esc(args)}</pre>'
    elif k == "tool_result":
        body = f'<div class="lbl">substrate returned</div><pre>{esc(rec.get("text",""))}</pre>'
    elif k == "thinking":
        body = f'<div class="lbl">private reasoning</div><div class="think">{esc(rec.get("text",""))}</div>'
    elif k == "input":
        body = f'<div class="lbl">user message</div><div class="prose">{esc(rec.get("text",""))}</div>'
    elif k == "assistant_text":
        body = f'<div class="lbl">assistant final text</div><div class="prose">{esc(rec.get("text",""))}</div>'
    elif k == "end":
        body = '<div class="lbl">agent_end — loop settled</div>'
    return (
        f'<div class="card" style="border-left-color:{color}">'
        f'<div class="cardhead"><span class="num">{idx}</span>'
        f'<span class="badge" style="background:{color}">{esc(move)}</span>'
        f'<span class="kind">{esc(k)}</span></div>{body}</div>'
    )


def main():
    ap = argparse.ArgumentParser(description="Render an agent trace JSONL as a self-contained HTML report.")
    ap.add_argument("trace")
    ap.add_argument("--output")
    args = ap.parse_args()
    trace_path = Path(args.trace)
    records = [json.loads(l) for l in trace_path.read_text().splitlines() if l.strip()]

    meta = dict(DEFAULT_META)
    steps = []
    for r in records:
        if r.get("kind") == "meta":
            for key in DEFAULT_META:
                if key in r:
                    meta[key] = r[key]
        else:
            steps.append(r)
    seq_rows = [classify(r) for r in steps]

    setup_html = ""
    if meta["system_prompt"]:
        setup_html += f'<div class="panel"><div class="lbl">system prompt</div><div class="sys">{esc(meta["system_prompt"])}</div></div>'
    if meta["first_user"]:
        setup_html += f'<div class="panel"><div class="lbl">first user message</div><div class="sys">{esc(meta["first_user"])}</div></div>'
    if meta["tools"]:
        tools_html = "".join(
            f'<div class="tool"><div class="tname">{esc(t.get("name",""))}</div>'
            f'<div class="tdesc">{esc(t.get("desc",""))}</div>'
            + (f'<div class="tmeta">params: <code>{esc(t["params"])}</code></div>' if t.get("params") else "")
            + (f'<div class="tmeta">backend: {esc(t["backend"])}</div>' if t.get("backend") else "")
            + "</div>"
            for t in meta["tools"]
        )
        setup_html += f'<div class="panel"><div class="lbl">tools exposed to the model</div>{tools_html}</div>'
    setup_section = f'<h2>What the agent was given</h2>{setup_html}' if setup_html else ""

    legend_html = "".join(
        f'<span class="legpill"><span class="dot" style="background:{c}"></span>{esc(m)} — {esc(d)}</span>'
        for m, (c, d) in MOVE_META.items()
        if any(row[0] == m for row in seq_rows)
    )
    notes_html = ""
    if meta["notes"]:
        items = "".join(f"<li>{esc(n)}</li>" for n in meta["notes"])
        notes_html = f'<div class="note"><h3>What to notice</h3><ul>{items}</ul></div>'
    cards_html = "".join(render_step_card(i + 1, r) for i, r in enumerate(steps))
    chips = "".join(
        f'<span class="chip">{esc(label)}&nbsp;<b>{esc(val)}</b></span>'
        for label, val in [
            ("scenario", meta["scenario"]), ("model", meta["model"]),
            ("substrate", meta["substrate"]), ("steps", len(steps)),
        ] if val != ""
    )

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>{esc(meta["title"])}</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f8fafc;--card:#fff}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:980px;margin:0 auto;padding:32px 22px 80px}}
h1{{font-size:23px;margin:0 0 4px}}
.sub{{color:var(--mut);margin:0 0 22px;font-size:13.5px}}
.meta{{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 26px}}
.chip{{background:#fff;border:1px solid var(--line);border-radius:999px;padding:4px 12px;font-size:12.5px}}
h2{{font-size:15px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:34px 0 12px;border-bottom:1px solid var(--line);padding-bottom:6px}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:16px 18px;margin-bottom:12px}}
pre{{background:#0f172a;color:#e2e8f0;border-radius:8px;padding:12px 14px;overflow-x:auto;font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word;margin:6px 0 0}}
.sys{{white-space:pre-wrap;font:12.5px/1.55 ui-monospace,Menlo,monospace;background:#f1f5f9;border-radius:8px;padding:12px 14px;color:#334155}}
.tool{{border:1px solid var(--line);border-radius:10px;padding:11px 14px;margin-bottom:10px;background:#fff}}
.tname{{font-weight:700;font-family:ui-monospace,Menlo,monospace;color:#1d4ed8}}
.tdesc{{font-size:13px;color:#334155;margin:3px 0}}
.tmeta{{font-size:12px;color:var(--mut)}}
.tmeta code{{background:#f1f5f9;padding:1px 5px;border-radius:4px}}
.legend{{display:flex;flex-wrap:wrap;gap:8px 14px;margin:10px 0 6px}}
.legpill{{font-size:12px;color:#334155;display:flex;align-items:center;gap:6px}}
.dot{{width:10px;height:10px;border-radius:3px;display:inline-block}}
.diagram{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px;text-align:center}}
.card{{background:var(--card);border:1px solid var(--line);border-left:5px solid;border-radius:10px;padding:13px 16px;margin-bottom:11px}}
.cardhead{{display:flex;align-items:center;gap:10px;margin-bottom:4px}}
.num{{width:24px;height:24px;border-radius:50%;background:#f1f5f9;color:#475569;font-size:12.5px;font-weight:700;display:flex;align-items:center;justify-content:center}}
.badge{{color:#fff;font-size:11px;font-weight:700;padding:2px 9px;border-radius:5px;letter-spacing:.03em}}
.kind{{color:var(--mut);font-size:12px;font-family:ui-monospace,Menlo,monospace}}
.lbl{{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin-top:6px}}
.prose{{background:#eef2ff;border-radius:8px;padding:11px 13px;margin-top:5px;color:#312e81;font-size:14px}}
.think{{background:#faf5ff;border:1px dashed #d8b4fe;border-radius:8px;padding:11px 13px;margin-top:5px;color:#6b21a8;font-size:13px;white-space:pre-wrap}}
.note{{background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:14px 18px;margin-top:14px}}
.note h3{{margin:0 0 8px;font-size:14px;color:#92400e}}
.note li{{margin:4px 0;font-size:13.5px;color:#78350f}}
.foot{{color:var(--mut);font-size:12px;margin-top:30px;border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>{esc(meta["title"])}</h1>
<p class="sub">{esc(meta["subtitle"])}</p>
<div class="meta">{chips}</div>
{setup_section}
<h2>What happened — sequence</h2>
<div class="diagram">{actor_headers(meta)}{build_sequence_svg(seq_rows)}</div>
<div class="legend">{legend_html}</div>
<h2>What happened — ordered steps (full I/O)</h2>
{cards_html}
{notes_html}
<div class="foot">Generated from <code>{esc(str(trace_path))}</code> by the <code>agent-trace-report</code> skill.</div>
</div></body></html>"""

    out = Path(args.output) if args.output else trace_path.parent / "report.html"
    out.write_text(doc)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
