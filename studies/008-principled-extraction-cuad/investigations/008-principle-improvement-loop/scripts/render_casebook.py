from __future__ import annotations

import html
import json
from pathlib import Path

INV = Path(__file__).resolve().parents[1]
DATA = INV / "reviews" / "gainsco_casebook_data.json"
OUT = INV / "reviews" / "gainsco-casebook.html"

CSS = """
:root{--bg:#faf9f7;--fg:#1a1a1a;--mut:#6b6b6b;--line:#e0ddd8;--card:#fff;
--gold:#7a5c00;--goldbg:#fdf6e0;--ok:#1a6b3c;--okbg:#e8f5ed;--bad:#a32b2b;--badbg:#fbeaea;
--warn:#8a5a00;--warnbg:#fdf2e0;--acc:#2c4f7c;--accbg:#e9eff7}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 20px 80px}
h1{font-size:24px;margin:0 0 4px} h2{font-size:17px;margin:34px 0 10px;
padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--mut);font-size:13px;margin-bottom:22px}
.legend{display:flex;gap:16px;flex-wrap:wrap;margin:14px 0 26px;font-size:12.5px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:12px;height:12px;border-radius:3px;display:inline-block}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-weight:600;font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
.num{text-align:right;font-variant-numeric:tabular-nums}
.card{background:var(--card);border:1px solid var(--line);border-radius:9px;
padding:14px 16px;margin:0 0 12px}
.cat{font-weight:650;font-size:15px}
.q{color:var(--mut);font-size:12px;margin:3px 0 11px}
.grid{display:grid;grid-template-columns:74px 1fr;gap:8px 12px;align-items:start}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);padding-top:3px}
.span{display:block;padding:6px 9px;border-radius:5px;margin-bottom:5px;
font:12.5px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word}
.g{background:var(--goldbg);border-left:3px solid var(--gold)}
.m{background:var(--okbg);border-left:3px solid var(--ok)}
.x{background:var(--badbg);border-left:3px solid var(--bad)}
.none{color:var(--mut);font-style:italic;font-size:12.5px;padding:4px 0}
.pill{display:inline-block;padding:1px 7px;border-radius:9px;font-size:10.5px;
font-weight:600;letter-spacing:.03em;text-transform:uppercase;margin-left:6px}
.p-ac{background:var(--okbg);color:var(--ok)} .p-aw{background:var(--badbg);color:var(--bad)}
.p-sp{background:var(--warnbg);color:var(--warn)}
.p-tp{background:var(--okbg);color:var(--ok)} .p-tn{background:#eee;color:#555}
.p-fp{background:var(--badbg);color:var(--bad)} .p-fn{background:var(--badbg);color:var(--bad)}
.meta{font-size:11px;color:var(--mut);margin-left:7px;font-variant-numeric:tabular-nums}
.stat{display:flex;gap:22px;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);
border-radius:9px;padding:14px 18px;margin-bottom:8px}
.stat div{min-width:96px} .stat .v{font-size:21px;font-weight:650}
.stat .k{font-size:11px;color:var(--mut);text-transform:uppercase;letter-spacing:.04em}
.note{background:var(--accbg);border-left:3px solid var(--acc);padding:11px 14px;
border-radius:0 6px 6px 0;font-size:13px;margin:14px 0}
details{margin-top:9px} summary{cursor:pointer;font-size:12px;color:var(--acc)}
.scroll{overflow-x:auto}
"""


def esc(s):
    return html.escape(s or "")


def clip(s, n=420):
    s = s or ""
    return esc(s[:n]) + ("…" if len(s) > n else "")


def main():
    d = json.loads(DATA.read_text())
    rows = d["rows"]
    nrep = d["n_repeats"]
    buckets = {"always_correct": [], "always_wrong": [], "split": []}
    for r in rows:
        buckets[r["bucket"]].append(r)

    P = []
    P.append(f"<title>GAINSCO Casebook</title><style>{CSS}</style><div class='wrap'>")
    P.append("<h1>One contract, three trials, forty-one categories</h1>")
    P.append(
        f"<div class='sub'>{esc(d['title'])} &middot; {d['n_tokens']:,} tokens &middot; "
        f"run <code>{esc(d['run_id'])}</code> &middot; no principles &middot; "
        f"task definition v1 &middot; temp 1.0 / top_p 0.95</div>"
    )

    P.append("<div class='stat'>")
    for k, lbl in [("always_correct", "always correct"), ("split", "split / flaky"), ("always_wrong", "always wrong")]:
        P.append(f"<div><div class='v'>{len(buckets[k])}</div><div class='k'>{lbl}</div></div>")
    P.append(f"<div><div class='v'>41</div><div class='k'>categories</div></div>")
    P.append(f"<div><div class='v'>{nrep}</div><div class='k'>repeats</div></div>")
    P.append("</div>")

    P.append(
        "<div class='note'><strong>How to read this.</strong> Each card is one category. "
        "<em>Gold</em> is CUAD's annotation. <em>r0/r1/r2</em> are the three independent samples at "
        "temperature 1.0 &mdash; same prompt, same contract, nothing changed between them. "
        "A span is green when it matches gold at Jaccard&nbsp;&ge;&nbsp;0.5, red when it does not. "
        "The detection cell (tp/tn/fp/fn) only asks <em>did the model say something here at all</em>; "
        "span quality lives inside the tp cell.</div>"
    )

    P.append("<div class='legend'>")
    for c, t in [("g", "gold"), ("m", "matches gold"), ("x", "no match")]:
        P.append(f"<span><i class='sw {c}' style='border-left:3px solid'></i>{t}</span>")
    P.append("</div>")

    P.append("<h2>Per-trial detection cells</h2><div class='scroll'><table><tr><th>trial</th>"
             "<th class='num'>tp</th><th class='num'>tn</th><th class='num'>fp</th><th class='num'>fn</th></tr>")
    for i in range(nrep):
        c = {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
        for r in rows:
            c[r["trials"][i]["cell"]] += 1
        P.append(f"<tr><td>r{i}</td><td class='num'>{c['tp']}</td><td class='num'>{c['tn']}</td>"
                 f"<td class='num'>{c['fp']}</td><td class='num'>{c['fn']}</td></tr>")
    P.append("</table></div>")

    order = [("always_wrong", "Always wrong &mdash; the principle targets"),
             ("split", "Split across repeats &mdash; same input, different answer"),
             ("always_correct", "Always correct")]

    for key, heading in order:
        P.append(f"<h2>{heading} <span class='meta'>{len(buckets[key])} categories</span></h2>")
        for r in buckets[key]:
            pill = {"always_correct": "p-ac", "always_wrong": "p-aw", "split": "p-sp"}[r["bucket"]]
            lab = r["bucket"].replace("_", " ")
            P.append("<div class='card'>")
            P.append(f"<div class='cat'>{esc(r['category'])}<span class='pill {pill}'>{lab}</span></div>")
            P.append(f"<div class='q'>{esc(r['question'])}</div>")
            P.append("<div class='grid'>")

            P.append("<div class='lbl'>gold</div><div>")
            if r["gold"]:
                for g in r["gold"]:
                    P.append(f"<span class='span g'>{clip(g['text'])}</span>")
            else:
                P.append("<div class='none'>no clause of this type in this contract</div>")
            P.append("</div>")

            for t in r["trials"]:
                cell = t["cell"]
                P.append(f"<div class='lbl'>r{t['repeat']}<span class='pill p-{cell}'>{cell}</span></div><div>")
                if t["spans"]:
                    for s in t["spans"]:
                        cls = "m" if s["match"] else "x"
                        j = f"J={s['jaccard']:.2f}" if s["jaccard"] is not None else "no gold"
                        vb = "" if s["verbatim"] else " &middot; NOT VERBATIM"
                        P.append(f"<span class='span {cls}'>{clip(s['text'])}</span>")
                        P.append(f"<div class='meta'>{j}{vb}</div>")
                else:
                    P.append("<div class='none'>declared absent</div>")
                P.append("</div>")
            P.append("</div></div>")

    P.append("</div>")
    OUT.write_text("\n".join(P))
    print(f"wrote {OUT} ({OUT.stat().st_size//1024} KB)")


if __name__ == "__main__":
    main()
