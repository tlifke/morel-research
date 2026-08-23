from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

INV = Path(__file__).resolve().parents[1]
STUDY = INV.parents[1]
sys.path[:0] = [str(STUDY), str(INV)]

from harness.comparison_metrics import is_match

from loop.models import LoopOutput
from loop.run_slice import load_contracts

RUN = INV / "runs" / "baseline-001"
OUT = INV / "reviews" / "gainsco-highlights.html"
CID = "GAINSCOINC_01_21_2010-EX-10.41-SPONSORSHIP AGREEMENT"


def normalize_map(t: str):
    norm, idx, prev_ws = [], [], False
    for i, ch in enumerate(t):
        if ch.isspace():
            if prev_ws:
                continue
            norm.append(" ")
            idx.append(i)
            prev_ws = True
        else:
            norm.append(ch)
            idx.append(i)
            prev_ws = False
    return "".join(norm), idx


def make_locator(text: str):
    N, IDX = normalize_map(text)

    def locate(s: str):
        i = text.find(s)
        if i >= 0:
            return "exact", i, i + len(s)
        q = re.sub(r"\s+", " ", s).strip()
        if q:
            j = N.find(q)
            if j >= 0:
                return "normalized", IDX[j], IDX[min(j + len(q) - 1, len(IDX) - 1)] + 1
        return "not_found", None, None

    return locate


def segments(text: str, anns: list[dict]):
    """Split text at every annotation boundary; each piece carries its active set."""
    bounds = {0, len(text)}
    for a in anns:
        bounds.add(a["start"])
        bounds.add(a["end"])
    pts = sorted(bounds)
    out = []
    for a, b in zip(pts, pts[1:]):
        active = [x for x in anns if x["start"] < b and x["end"] > a]
        out.append({"a": a, "b": b, "cats": sorted({x["ci"] for x in active}),
                    "miss": any(not x["match"] for x in active)})
    return out


def main():
    contract = load_contracts([CID])[0]
    text = contract["text"]
    locate = make_locator(text)

    cats = list(json.loads((INV / "task_definition" / "v1.json").read_text())["questions"])
    ci = {c: i for i, c in enumerate(cats)}

    row = [json.loads(l) for l in (STUDY / "data/processed/instances.jsonl").read_text().splitlines()
           if json.loads(l)["contract_id"] == CID][0]

    sources = {}
    gold_text = {}
    ganns = []
    for c in cats:
        g = row["gold"].get(c, {"is_impossible": True, "spans": []})
        if g.get("is_impossible", True):
            continue
        gold_text[c] = [text[s[0]:s[1]] for s in g["spans"]]
        for s in g["spans"]:
            ganns.append({"start": s[0], "end": s[1], "ci": ci[c], "match": True, "how": "gold"})
    sources["gold"] = ganns

    trials = [json.loads(l) for l in (RUN / "trials.jsonl").read_text().splitlines()
              if json.loads(l)["key"]["contract_id"] == CID]
    trials.sort(key=lambda t: t["key"]["repeat_idx"])

    stats = {}
    for t in trials:
        key = f"r{t['key']['repeat_idx']}"
        anns, how_counts = [], {"exact": 0, "normalized": 0, "not_found": 0}
        for d in LoopOutput(**t["output"]).decisions:
            for s in d.spans:
                how, a, b = locate(s)
                how_counts[how] += 1
                if a is None:
                    continue
                m = any(is_match(g, s, d.category) for g in gold_text.get(d.category, []))
                anns.append({"start": a, "end": b, "ci": ci[d.category], "match": m, "how": how})
        sources[key] = anns
        stats[key] = how_counts

    payload = {}
    for k, anns in sources.items():
        payload[k] = {
            "segments": [[s["a"], s["b"], s["cats"], 1 if s["miss"] else 0] for s in segments(text, anns)],
            "counts": {str(ci[c]): 0 for c in cats},
        }
        for a in anns:
            payload[k]["counts"][str(a["ci"])] = payload[k]["counts"].get(str(a["ci"]), 0) + 1

    html_out = TEMPLATE.format(
        title=html.escape(contract["title"]),
        tokens=f"{contract['n_tokens']:,}",
        chars=f"{len(text):,}",
        text=json.dumps(text).replace("</", "<\\/"),
        cats=json.dumps(cats),
        data=json.dumps(payload),
        stats=json.dumps(stats),
        goldcats=json.dumps(sorted(ci[c] for c in gold_text)),
    )
    OUT.write_text(html_out)
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")
    print("locator:", stats)


TEMPLATE = """<title>GAINSCO Highlights</title>
<style>
:root{{--bg:#faf9f7;--fg:#1a1a1a;--mut:#6b6b6b;--line:#e0ddd8;--card:#fff;--acc:#2c4f7c;--accbg:#e9eff7}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}}
.wrap{{max-width:1500px;margin:0 auto;padding:24px 18px 60px}}
h1{{font-size:22px;margin:0 0 3px}} .sub{{color:var(--mut);font-size:13px;margin-bottom:16px}}
.layout{{display:grid;grid-template-columns:300px 1fr;gap:18px;align-items:start}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:13px 14px;position:sticky;top:14px;max-height:88vh;overflow:auto}}
.panel h3{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:0 0 8px}}
.srcs{{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:14px}}
.src{{padding:5px 12px;border:1px solid var(--line);border-radius:6px;cursor:pointer;font-size:13px;background:#f0eeea}}
.src.on{{background:var(--acc);color:#fff;border-color:var(--acc);font-weight:600}}
.btns{{display:flex;gap:5px;margin-bottom:9px}}
.btns button{{flex:1;font-size:11.5px;padding:4px 6px;border:1px solid var(--line);background:#f6f5f2;border-radius:5px;cursor:pointer}}
label.cat{{display:flex;align-items:center;gap:7px;font-size:12.5px;padding:2px 0;cursor:pointer}}
label.cat.zero{{opacity:.38}}
.dot{{width:11px;height:11px;border-radius:3px;flex:none}}
.n{{margin-left:auto;font-size:11px;color:var(--mut);font-variant-numeric:tabular-nums}}
.doc{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:20px 22px;
font:12.5px/1.75 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word;
max-height:88vh;overflow:auto}}
mark{{background:none;color:inherit;border-radius:2px;padding:1px 0}}
mark.miss{{text-decoration:underline wavy rgba(163,43,43,.65);text-underline-offset:3px}}
.bar{{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--mut);margin-bottom:9px;font-variant-numeric:tabular-nums}}
.bar b{{color:var(--fg)}}
.note{{background:var(--accbg);border-left:3px solid var(--acc);padding:10px 13px;border-radius:0 6px 6px 0;font-size:12.5px;margin:0 0 14px}}
</style>
<div class="wrap">
<h1>Contract with toggleable highlights</h1>
<div class="sub">{title} &middot; {chars} chars &middot; {tokens} tokens &middot; run <code>baseline-001</code>, no principles</div>
<div class="note"><strong>Source</strong> switches between CUAD's gold annotation and each of the three
independent samples. <strong>Wavy red underline</strong> marks a model span that does not match gold at
Jaccard&nbsp;&ge;&nbsp;0.5. Overlapping categories take the colour of the first enabled one, so toggle down
to a few categories to read overlaps cleanly. Model spans are located by whitespace-normalised search &mdash;
most are not byte-exact against the source.</div>
<div class="layout">
  <div class="panel">
    <h3>Source</h3>
    <div class="srcs" id="srcs"></div>
    <h3>Categories</h3>
    <div class="btns"><button onclick="setAll(1)">all</button><button onclick="setAll(0)">none</button><button onclick="onlyPresent()">present</button></div>
    <div id="cats"></div>
  </div>
  <div>
    <div class="bar" id="bar"></div>
    <div class="doc" id="doc"></div>
  </div>
</div>
</div>
<script>
const RAW = {text};
const CATS = {cats};
const DATA = {data};
const STATS = {stats};
const GOLDCATS = {goldcats};
let src = 'gold';
let on = new Set(CATS.map((_,i)=>i));

function colour(i){{ return 'hsl(' + ((i*137.508)%360).toFixed(1) + ' 72% 78%)'; }}

function buildCats(){{
  const box = document.getElementById('cats');
  box.innerHTML = '';
  CATS.forEach(function(c,i){{
    const n = DATA[src].counts[String(i)] || 0;
    const l = document.createElement('label');
    l.className = 'cat' + (n ? '' : ' zero');
    l.innerHTML = '<input type=checkbox ' + (on.has(i)?'checked':'') + ' data-i=' + i + '>' +
      '<span class=dot style="background:' + colour(i) + '"></span>' +
      '<span>' + c + '</span><span class=n>' + n + '</span>';
    l.querySelector('input').onchange = function(e){{
      e.target.checked ? on.add(i) : on.delete(i); render();
    }};
    box.appendChild(l);
  }});
}}

function buildSrcs(){{
  const box = document.getElementById('srcs');
  box.innerHTML = '';
  ['gold','r0','r1','r2'].forEach(function(k){{
    if(!DATA[k]) return;
    const d = document.createElement('div');
    d.className = 'src' + (k===src?' on':'');
    d.textContent = k;
    d.onclick = function(){{
      if(src===k) return;
      src=k; buildSrcs(); buildCats(); render();
    }};
    box.appendChild(d);
  }});
}}

function render(){{
  const segs = DATA[src].segments;
  let out = '', shown = 0;
  for(const [a,b,cats,miss] of segs){{
    const piece = RAW.slice(a,b).replace(/&/g,'&amp;').replace(/</g,'&lt;');
    const hit = cats.filter(c=>on.has(c));
    if(hit.length){{
      shown++;
      const names = hit.map(c=>CATS[c]).join(', ');
      out += '<mark class="' + (miss?'miss':'') + '" style="background:' + colour(hit[0]) +
             '" title="' + names + '">' + piece + '</mark>';
    }} else out += piece;
  }}
  const doc = document.getElementById('doc');
  const keep = doc.scrollTop;
  doc.innerHTML = out;
  doc.scrollTop = keep;
  const st = STATS[src];
  const total = Object.values(DATA[src].counts).reduce((x,y)=>x+y,0);
  document.getElementById('bar').innerHTML =
    '<span>source <b>' + src + '</b></span>' +
    '<span>spans <b>' + total + '</b></span>' +
    '<span>categories shown <b>' + [...on].filter(i=>(DATA[src].counts[String(i)]||0)>0).length + '</b></span>' +
    '<span>highlighted runs <b>' + shown + '</b></span>' +
    (st ? '<span>located exact <b>' + st.exact + '</b> / normalised <b>' + st.normalized +
          '</b> / not found <b>' + st.not_found + '</b></span>' : '');
}}

function setAll(v){{ on = v ? new Set(CATS.map((_,i)=>i)) : new Set(); buildCats(); render(); }}
function onlyPresent(){{
  on = new Set(CATS.map((_,i)=>i).filter(i=>(DATA[src].counts[String(i)]||0)>0));
  buildCats(); render();
}}
buildSrcs(); buildCats(); render();
</script>
"""

if __name__ == "__main__":
    main()
