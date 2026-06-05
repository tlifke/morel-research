import argparse
from pathlib import Path

ZONES = {
    "researcher": ("#4f46e5", "Researcher host — Mac (Pi CLI)"),
    "wire": ("#d97706", "The wire — Tailscale"),
    "desktop": ("#0f766e", "Desktop — RTX 3080 / WSL"),
    "orchestrator": ("#9333ea", "Orchestrator — Flask :8000 (desktop)"),
}

ARTIFACTS = [
    {
        "zone": "researcher", "status": "live", "name": "trace.jsonl",
        "content": "Every researcher step: input, thinking, tool_use (+args), tool_result, assistant_text. One line per event.",
        "path": "studies/004-…/harness/runs/<ts>/trace.jsonl",
        "writer": "slice.ts via agent.subscribe()", "reader": "render_trace.py · you", "wire": False,
    },
    {
        "zone": "researcher", "status": "live", "name": "report.html",
        "content": "Rendered single-iteration view: sequence diagram + per-step I/O cards.",
        "path": "runs/<ts>/report.html",
        "writer": "scripts/render_trace.py", "reader": "you (browser)", "wire": False,
    },
    {
        "zone": "researcher", "status": "planned", "name": "OTel spans (Phoenix)",
        "content": "Move-tagged spans (ORIENT/EXECUTE/MEASURE/…) with timings, token usage, tool args/results as span attributes.",
        "path": "local Phoenix store (SQLite) · UI at localhost:6006",
        "writer": "OTel exporter in the harness", "reader": "Phoenix UI", "wire": False,
    },
    {
        "zone": "researcher", "status": "planned", "name": "handoff/iteration_NNN.yaml",
        "content": "Iteration state for the next session: idea, attempted command, metrics, learnings, next-action hints, failure log.",
        "path": "runs/<ts>/handoff/  (may be obviated by nemotron's 256K context — open question)",
        "writer": "harness (post-iteration extractor)", "reader": "next iteration's bootstrap", "wire": False,
    },
    {
        "zone": "wire", "status": "live", "name": "tool call (down)",
        "content": "bash command (+timeout, cwd) or evaluate_predictions args. The full request the model emits.",
        "path": "in-memory · logged into trace.jsonl",
        "writer": "researcher model", "reader": "substrate backend", "wire": "down",
    },
    {
        "zone": "wire", "status": "live", "name": "tool result — SUMMARY only (up)",
        "content": "exit_code, elapsed, stdout/stderr byte counts + log path refs, detected markers, eval_output path · and the PGR ack JSON.",
        "path": "in-memory · logged into trace.jsonl",
        "writer": "substrate backend", "reader": "researcher model", "wire": "up",
    },
    {
        "zone": "desktop", "status": "desktop", "name": "bash_subprocess_logs/bash_NNNN.log",
        "content": "RAW stdout+stderr of each training+eval run (tens of KB). Does NOT cross the wire — referenced by path in the summary.",
        "path": "<launch>/bash_subprocess_logs/bash_NNNN.log",
        "writer": "Pi bash tool (desktop side)", "reader": "stays desktop-side; summarized to researcher", "wire": False,
    },
    {
        "zone": "desktop", "status": "desktop", "name": "eval_output.json",
        "content": "Strong-model predictions + test_indices for the run. The thing evaluate_predictions scores.",
        "path": "results/math_vanilla_w2s/<cfg>/seed_42/.eval_inputs/eval_output.json",
        "writer": "vanilla_w2s.run (SFT + vLLM eval)", "reader": "evaluate_predictions tool", "wire": False,
    },
    {
        "zone": "desktop", "status": "desktop", "name": "LoRA adapters / checkpoints",
        "content": "SFT weights produced per config. Large; gitignored. Never crosses the wire.",
        "path": "results/math_vanilla_w2s/<cfg>/",
        "writer": "Unsloth SFT", "reader": "vLLM eval", "wire": False,
    },
    {
        "zone": "desktop", "status": "desktop", "name": "vram_samples.csv",
        "content": "1 Hz GPU memory samples across the run (debug substrate contention / OOM).",
        "path": "<launch>/vram_samples.csv",
        "writer": "launcher sampler (desktop)", "reader": "report / post-hoc analysis", "wire": False,
    },
    {
        "zone": "orchestrator", "status": "desktop", "name": "w2s_server.log",
        "content": "Every evaluate_predictions request + how PGR was computed. Lives with the Flask orchestrator.",
        "path": "/tmp/w2s_server.log",
        "writer": "Flask orchestrator", "reader": "debugging only", "wire": False,
    },
    {
        "zone": "orchestrator", "status": "live", "name": "server_ack (returned to researcher)",
        "content": "success, pgr, transfer_acc, correct/total, fixed_weak_acc, fixed_strong_acc, num_predictions.",
        "path": "in-memory · logged into trace.jsonl",
        "writer": "Flask orchestrator", "reader": "researcher model", "wire": "up",
    },
]

STATUS_LABEL = {
    "live": ("live now (Mac harness)", "#16a34a"),
    "planned": ("planned", "#7c3aed"),
    "desktop": ("desktop substrate (live in study 003; wired in 004 next)", "#0f766e"),
}


def esc(s):
    import html
    return html.escape(str(s))


def topology_svg():
    w, h = 820, 320
    cols = {"researcher": 150, "desktop": 520, "orchestrator": 700}
    s = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:820px" xmlns="http://www.w3.org/2000/svg" font-family="ui-sans-serif,system-ui,sans-serif">',
         '<defs><marker id="d" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#334155"/></marker>'
         '<marker id="u" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L7,3 L0,6 Z" fill="#d97706"/></marker></defs>']
    s.append('<rect x="20" y="20" width="270" height="280" rx="12" fill="#eef2ff" stroke="#c7d2fe"/>')
    s.append('<rect x="330" y="20" width="200" height="280" rx="12" fill="#fff7ed" stroke="#fed7aa"/>')
    s.append('<rect x="560" y="20" width="240" height="130" rx="12" fill="#f0fdfa" stroke="#99f6e4"/>')
    s.append('<rect x="560" y="170" width="240" height="130" rx="12" fill="#faf5ff" stroke="#e9d5ff"/>')
    s.append('<text x="155" y="42" fill="#3730a3" font-size="12.5" font-weight="700" text-anchor="middle">Researcher host · Mac</text>')
    s.append('<text x="430" y="42" fill="#9a3412" font-size="12.5" font-weight="700" text-anchor="middle">wire · Tailscale</text>')
    s.append('<text x="680" y="42" fill="#0f766e" font-size="12.5" font-weight="700" text-anchor="middle">Desktop · 3080/WSL</text>')
    s.append('<text x="680" y="192" fill="#7e22ce" font-size="12.5" font-weight="700" text-anchor="middle">Orchestrator :8000</text>')
    for i, t in enumerate(["nemotron (model)", "Pi loop (agent-core)", "trace.jsonl", "Phoenix spans", "handoff yaml"]):
        s.append(f'<text x="40" y="{72+i*30}" fill="#312e81" font-size="12">• {esc(t)}</text>')
    for i, t in enumerate(["bash subprocess", "bash_NNNN.log", "eval_output.json", "LoRA ckpts", "vram_samples.csv"]):
        s.append(f'<text x="572" y="{72+i*24}" fill="#115e59" font-size="11.5">• {esc(t)}</text>')
    for i, t in enumerate(["w2s_server.log", "PGR computation"]):
        s.append(f'<text x="572" y="{220+i*24}" fill="#7e22ce" font-size="11.5">• {esc(t)}</text>')
    s.append('<line x1="290" y1="120" x2="558" y2="120" stroke="#334155" stroke-width="2" marker-end="url(#d)"/>')
    s.append('<text x="424" y="112" fill="#334155" font-size="11" text-anchor="middle">tool call (full)</text>')
    s.append('<line x1="558" y1="210" x2="292" y2="210" stroke="#d97706" stroke-width="2" stroke-dasharray="6 3" marker-end="url(#u)"/>')
    s.append('<text x="424" y="202" fill="#b45309" font-size="11" text-anchor="middle">summary + metrics only</text>')
    s.append('<text x="424" y="250" fill="#9a3412" font-size="10.5" text-anchor="middle" font-style="italic">full logs stay desktop-side,</text>')
    s.append('<text x="424" y="264" fill="#9a3412" font-size="10.5" text-anchor="middle" font-style="italic">referenced by path</text>')
    s.append('<rect x="40" y="232" width="240" height="50" rx="8" fill="#fff" stroke="#c7d2fe"/>')
    s.append('<text x="50" y="252" fill="#3730a3" font-size="10.5">SUBSTRATE=mock short-circuits the wire:</text>')
    s.append('<text x="50" y="268" fill="#3730a3" font-size="10.5">fixtures returned locally, identical shape.</text>')
    s.append("</svg>")
    return "\n".join(s)


def card(a):
    zc = ZONES[a["zone"]][0]
    sl, sc = STATUS_LABEL[a["status"]]
    wire = ""
    if a["wire"] == "down":
        wire = '<span class="wire down">crosses wire ↓</span>'
    elif a["wire"] == "up":
        wire = '<span class="wire up">crosses wire ↑</span>'
    return (
        f'<div class="art" style="border-left-color:{zc}">'
        f'<div class="arthead"><span class="aname">{esc(a["name"])}</span>'
        f'<span class="status" style="background:{sc}">{esc(sl)}</span>{wire}</div>'
        f'<div class="acontent">{esc(a["content"])}</div>'
        f'<div class="arow"><span class="k">path</span><code>{esc(a["path"])}</code></div>'
        f'<div class="arow"><span class="k">writes</span>{esc(a["writer"])}</div>'
        f'<div class="arow"><span class="k">reads</span>{esc(a["reader"])}</div>'
        f"</div>"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="runs/data_map.html")
    args = ap.parse_args()

    zone_sections = ""
    for zk, (zc, ztitle) in ZONES.items():
        arts = "".join(card(a) for a in ARTIFACTS if a["zone"] == zk)
        zone_sections += f'<h2 style="color:{zc}">{esc(ztitle)}</h2>{arts}'

    legend = "".join(
        f'<span class="legpill"><span class="dot" style="background:{c}"></span>{esc(t)}</span>'
        for k, (c, t) in ZONES.items()
    )

    doc = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Researcher harness — data & log map</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f8fafc}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif}}
.wrap{{max-width:980px;margin:0 auto;padding:32px 22px 80px}}
h1{{font-size:23px;margin:0 0 4px}}
.sub{{color:var(--mut);margin:0 0 22px;font-size:13.5px}}
h2{{font-size:14px;text-transform:uppercase;letter-spacing:.05em;margin:30px 0 12px;border-bottom:2px solid var(--line);padding-bottom:6px}}
.diagram{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:14px;text-align:center}}
.legend{{display:flex;flex-wrap:wrap;gap:8px 14px;margin:12px 0 4px}}
.legpill{{font-size:12px;color:#334155;display:flex;align-items:center;gap:6px}}
.dot{{width:10px;height:10px;border-radius:3px;display:inline-block}}
.art{{background:#fff;border:1px solid var(--line);border-left:5px solid;border-radius:10px;padding:12px 15px;margin-bottom:10px}}
.arthead{{display:flex;align-items:center;gap:9px;flex-wrap:wrap;margin-bottom:5px}}
.aname{{font-weight:700;font-family:ui-monospace,Menlo,monospace;font-size:13.5px;color:#1e293b}}
.status{{color:#fff;font-size:10.5px;font-weight:600;padding:2px 8px;border-radius:5px}}
.wire{{font-size:10.5px;font-weight:700;padding:2px 8px;border-radius:5px}}
.wire.down{{background:#1e293b;color:#fff}}
.wire.up{{background:#fef3c7;color:#92400e;border:1px solid #fcd34d}}
.acontent{{font-size:13.5px;color:#334155;margin-bottom:7px}}
.arow{{display:flex;gap:8px;font-size:12.5px;margin:2px 0;align-items:baseline}}
.arow .k{{color:var(--mut);text-transform:uppercase;font-size:10.5px;letter-spacing:.04em;min-width:46px}}
.arow code{{background:#f1f5f9;padding:1px 6px;border-radius:4px;font-size:12px;word-break:break-all}}
.note{{background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:14px 18px;margin-top:18px;color:#78350f;font-size:13.5px}}
.foot{{color:var(--mut);font-size:12px;margin-top:28px;border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class="wrap">
<h1>Researcher harness — data &amp; log map</h1>
<p class="sub">study 004 · inv 001 · where every piece of data is produced, what it holds, and what actually crosses the wire</p>

<div class="diagram">{topology_svg()}</div>
<div class="legend">{legend}</div>

<div class="note"><b>The one rule that explains the layout:</b> the researcher only ever sees a <b>summary</b>. Heavy artifacts — raw training logs, predictions, checkpoints — are written and kept <b>desktop-side</b>; only a compact summary (exit code, markers, byte counts, a path reference) and the final <b>metrics</b> cross the wire into <code>trace.jsonl</code>. In <code>SUBSTRATE=mock</code> the wire is short-circuited and those same shapes come from study-003 fixtures.</div>

{zone_sections}

<div class="foot">Regenerate: <code>uv run --no-project python scripts/render_data_map.py</code>. Status badges: <b>live now</b> = produced by the Mac harness today · <b>desktop substrate</b> = exists in study 003, wired into 004 next · <b>planned</b> = designed, not yet built.</div>
</div></body></html>"""

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
