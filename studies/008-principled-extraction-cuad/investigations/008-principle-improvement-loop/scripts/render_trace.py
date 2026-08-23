from __future__ import annotations

import html
import json
from pathlib import Path

INV = Path(__file__).resolve().parents[1]
STUDY = INV.parents[1]
RUN = INV / "runs" / "baseline-001"
OUT = INV / "reviews" / "gainsco-trace.html"
CID = "GAINSCOINC_01_21_2010-EX-10.41-SPONSORSHIP AGREEMENT"

CSS = """
:root{--bg:#faf9f7;--fg:#1a1a1a;--mut:#6b6b6b;--line:#e0ddd8;--card:#fff;
--acc:#2c4f7c;--accbg:#e9eff7;--warnbg:#fdf2e0;--warn:#8a5a00}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1400px;margin:0 auto;padding:26px 20px 70px}
h1{font-size:23px;margin:0 0 4px} h2{font-size:16px;margin:30px 0 10px}
.sub{color:var(--mut);font-size:13px;margin-bottom:20px}
.note{background:var(--accbg);border-left:3px solid var(--acc);padding:11px 14px;
border-radius:0 6px 6px 0;font-size:13px;margin:14px 0}
.warn{background:var(--warnbg);border-left:3px solid var(--warn);padding:11px 14px;
border-radius:0 6px 6px 0;font-size:13px;margin:14px 0}
.tabs{display:flex;gap:6px;margin:0 0 -1px;flex-wrap:wrap}
.tab{padding:7px 15px;border:1px solid var(--line);border-bottom:none;
border-radius:7px 7px 0 0;background:#f0eeea;cursor:pointer;font-size:13px}
.tab.on{background:var(--card);font-weight:600}
.pane{display:none;background:var(--card);border:1px solid var(--line);
border-radius:0 8px 8px 8px;padding:0}
.pane.on{display:block}
pre{margin:0;padding:16px 18px;overflow:auto;max-height:78vh;
font:12px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;
white-space:pre-wrap;word-break:break-word;tab-size:2}
pre.doc{white-space:pre-wrap;font-size:12.5px;line-height:1.65;max-height:70vh}
.bar{display:flex;gap:20px;flex-wrap:wrap;padding:11px 18px;border-bottom:1px solid var(--line);
font-size:12px;color:var(--mut);font-variant-numeric:tabular-nums}
.bar b{color:var(--fg);font-weight:600}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:4px}
th,td{text-align:left;padding:6px 9px;border-bottom:1px solid var(--line)}
th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
.num{text-align:right;font-variant-numeric:tabular-nums}
"""

JS = """
function pick(g,i){
 document.querySelectorAll('[data-g="'+g+'"]').forEach(function(e){
   e.classList.toggle('on', e.dataset.i===i);});
}
"""


def esc(s):
    return html.escape(s or "")


def main():
    import sys
    sys.path[:0] = [str(STUDY), str(INV)]
    from loop.run_slice import load_contracts

    contract = load_contracts([CID])[0]
    trials = [
        json.loads(l)
        for l in (RUN / "trials.jsonl").read_text().splitlines()
        if json.loads(l)["key"]["contract_id"] == CID
    ]
    trials.sort(key=lambda t: t["key"]["repeat_idx"])
    manifest = json.loads((RUN / "manifest.json").read_text())

    P = [f"<title>GAINSCO Trace</title><style>{CSS}</style><script>{JS}</script><div class='wrap'>"]
    P.append("<h1>Raw input and raw output</h1>")
    P.append(
        f"<div class='sub'>{esc(contract['title'])} &middot; {contract['n_tokens']:,} tokens &middot; "
        f"run <code>baseline-001</code> &middot; {esc(manifest['model'])} &middot; "
        f"temp {manifest['temperature']} / top_p {manifest['top_p']} &middot; no principles</div>"
    )

    P.append(
        "<div class='warn'><strong>The reasoning is not here, and cannot be recovered.</strong> "
        "These trials ran with <code>separate_reasoning=True</code>, so the model's chain of thought came "
        "back in <code>reasoning_content</code> and the ledger recorded only its length &mdash; "
        "40,926 / 26,021 / 39,745 characters for r0 / r1 / r2. The text itself was never written to disk, "
        "and Tinker does not honour seeds, so re-running produces different reasoning rather than the same "
        "reasoning. Fixed for future runs; lost for these three.</div>"
    )

    P.append("<h2>The document as the model receives it</h2>")
    P.append(
        "<div class='note'>Verbatim CUAD text, no highlighting, no truncation, no chunking (D-2). "
        "In the prompt this sits inside a fenced <code>Context:</code> block, followed by the 41 questions, "
        "the principles block, and the JSON schema.</div>"
    )
    P.append("<div class='pane on'><div class='bar'>"
             f"<span>chars <b>{len(contract['text']):,}</b></span>"
             f"<span>tokens <b>{contract['n_tokens']:,}</b></span>"
             f"<span>sha256 <b>{contract['text_sha256'][:16]}…</b></span></div>")
    P.append(f"<pre class='doc'>{esc(contract['text'])}</pre></div>")

    P.append("<h2>What the model returned</h2>")
    P.append(
        "<div class='note'>Byte-for-byte as received &mdash; not re-serialised. Same prompt, same contract, "
        "three independent samples.</div>"
    )

    P.append("<table><tr><th>trial</th><th>trial_id</th><th class='num'>prompt tok</th>"
             "<th class='num'>completion tok</th><th class='num'>reasoning chars</th>"
             "<th class='num'>latency</th><th>finish</th><th>outcome</th></tr>")
    for t in trials:
        P.append(
            f"<tr><td>r{t['key']['repeat_idx']}</td><td><code>{t['trial_id']}</code></td>"
            f"<td class='num'>{t['n_prompt_tokens']:,}</td>"
            f"<td class='num'>{t['n_completion_tokens']:,}</td>"
            f"<td class='num'>{t['notes']['n_reasoning_chars']:,}</td>"
            f"<td class='num'>{t['latency_ms']//1000}s</td>"
            f"<td>{esc(t['finish_reason'])}</td><td>{esc(t['outcome'])}</td></tr>"
        )
    P.append("</table>")

    P.append("<div class='tabs'>")
    for i, t in enumerate(trials):
        on = " on" if i == 0 else ""
        P.append(f"<div class='tab{on}' data-g='o' data-i='{i}' onclick=\"pick('o','{i}')\">"
                 f"r{t['key']['repeat_idx']}</div>")
    P.append("</div>")
    for i, t in enumerate(trials):
        on = " on" if i == 0 else ""
        raw = (RUN / f"{t['trial_id']}.txt").read_text()
        P.append(f"<div class='pane{on}' data-g='o' data-i='{i}'><div class='bar'>"
                 f"<span>raw chars <b>{len(raw):,}</b></span>"
                 f"<span>sha256 <b>{t['response_sha256'][:16]}…</b></span>"
                 f"<span>decisions <b>{(t['notes'].get('conformance') or {}).get('n_decisions','—')}</b></span></div>")
        P.append(f"<pre>{esc(raw)}</pre></div>")

    P.append("</div>")
    OUT.write_text("\n".join(P))
    print(f"wrote {OUT} ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
