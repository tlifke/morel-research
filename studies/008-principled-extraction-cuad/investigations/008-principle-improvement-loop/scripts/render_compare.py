from __future__ import annotations

import json
import sys
from pathlib import Path

INV = Path(__file__).resolve().parents[1]
STUDY = INV.parents[1]
sys.path[:0] = [str(STUDY), str(INV), str(INV / "scripts")]

from render_highlights import CID, build_payload, parse_args

OUT = INV / "reviews" / "gainsco-compare.html"


def main():
    runs, cid, out = parse_args(OUT)
    b = build_payload(cid, runs)
    contract, text, cats, payload = b["contract"], b["text"], b["cats"], b["payload"]
    ci, gold_text = b["ci"], b["gold_text"]

    counts = {k: v["counts"] for k, v in payload.items()}
    agree = {}
    for a in payload:
        for c in payload:
            if a >= c:
                continue
            diff = [
                i for i in range(len(cats))
                if bool(counts[a].get(str(i), 0)) != bool(counts[c].get(str(i), 0))
            ]
            agree[f"{a}|{c}"] = diff

    out.write_text(
        TEMPLATE.format(
            title=contract["title"].replace("&", "&amp;").replace("<", "&lt;"),
            chars=f"{len(text):,}",
            tokens=f"{contract['n_tokens']:,}",
            text=json.dumps(text).replace("</", "<\\/"),
            cats=json.dumps(cats),
            data=json.dumps(payload),
            stats=json.dumps(b["stats"]),
            diffs=json.dumps(agree),
            runline=b["runline"],
        )
    )
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


TEMPLATE = """<title>GAINSCO Side by Side</title>
<style>
:root{{--bg:#faf9f7;--fg:#1a1a1a;--mut:#6b6b6b;--line:#e0ddd8;--card:#fff;--acc:#2c4f7c;--accbg:#e9eff7;
--warn:#8a5a00;--warnbg:#fdf2e0}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}}
.wrap{{max-width:1800px;margin:0 auto;padding:22px 16px 50px}}
h1{{font-size:21px;margin:0 0 3px}} .sub{{color:var(--mut);font-size:13px;margin-bottom:14px}}
.layout{{display:grid;grid-template-columns:262px 1fr 1fr;gap:14px;align-items:start}}
.panel{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px 13px;
position:sticky;top:12px;max-height:90vh;overflow:auto}}
.panel h3{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:0 0 7px}}
.btns{{display:flex;gap:4px;margin-bottom:8px;flex-wrap:wrap}}
.btns button{{flex:1;min-width:56px;font-size:11.5px;padding:4px 5px;border:1px solid var(--line);
background:#f6f5f2;border-radius:5px;cursor:pointer}}
.btns button.hot{{background:var(--warnbg);border-color:#e3c98f;color:var(--warn);font-weight:600}}
label.cat{{display:flex;align-items:center;gap:6px;font-size:12.5px;padding:2px 0;cursor:pointer}}
label.cat.zero{{opacity:.35}}
label.cat.diff span.nm{{font-weight:650;color:var(--warn)}}
.dot{{width:10px;height:10px;border-radius:3px;flex:none}}
.n{{margin-left:auto;font-size:11px;color:var(--mut);font-variant-numeric:tabular-nums;white-space:nowrap}}
.col h2{{font-size:13px;margin:0 0 7px;display:flex;align-items:center;gap:7px;flex-wrap:wrap}}
.srcs{{display:flex;gap:4px}}
.src{{padding:3px 10px;border:1px solid var(--line);border-radius:6px;cursor:pointer;font-size:12.5px;background:#f0eeea}}
.src.on{{background:var(--acc);color:#fff;border-color:var(--acc);font-weight:600}}
.doc{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:16px 18px;
font:12px/1.7 ui-monospace,SFMono-Regular,Menlo,monospace;white-space:pre-wrap;word-break:break-word;
height:80vh;overflow:auto}}
mark{{background:none;color:inherit;border-radius:2px;padding:1px 0}}
mark.miss{{text-decoration:underline wavy rgba(163,43,43,.65);text-underline-offset:3px}}
.bar{{font-size:11.5px;color:var(--mut);font-variant-numeric:tabular-nums;margin-left:auto}}
.note{{background:var(--accbg);border-left:3px solid var(--acc);padding:9px 12px;border-radius:0 6px 6px 0;
font-size:12.5px;margin:0 0 12px}}
.sync{{font-size:11.5px;color:var(--mut);display:flex;align-items:center;gap:5px;cursor:pointer}}
</style>
<div class="wrap">
<h1>Side by side</h1>
<div class="sub">{title} &middot; {chars} chars &middot; {tokens} tokens &middot; {runline}</div>
<div class="note">Each pane picks its own source. <strong>differing</strong> selects only the categories where the
two panes disagree about whether the clause is present at all &mdash; that is the fastest way to see what changed.
Wavy red underline marks a model span that does not match gold at Jaccard&nbsp;&ge;&nbsp;0.5.</div>
<div class="layout">
  <div class="panel">
    <h3>Categories</h3>
    <div class="btns">
      <button onclick="setAll(1)">all</button>
      <button onclick="setAll(0)">none</button>
      <button onclick="onlyPresent()">present</button>
      <button class="hot" onclick="onlyDiff()">differing</button>
    </div>
    <label class="sync"><input type=checkbox id="syncbox" checked> sync scrolling</label>
    <div id="cats" style="margin-top:8px"></div>
  </div>
  <div class="col">
    <h2><span>left</span><span class="srcs" id="srcsL"></span><span class="bar" id="barL"></span></h2>
    <div class="doc" id="docL"></div>
  </div>
  <div class="col">
    <h2><span>right</span><span class="srcs" id="srcsR"></span><span class="bar" id="barR"></span></h2>
    <div class="doc" id="docR"></div>
  </div>
</div>
</div>
<script>
const RAW = {text};
const CATS = {cats};
const DATA = {data};
const STATS = {stats};
const DIFFS = {diffs};
const KEYS = Object.keys(DATA);
let side = {{L: KEYS[0], R: KEYS[Math.min(1, KEYS.length-1)]}};
let on = new Set(CATS.map((_,i)=>i));

function colour(i){{ return 'hsl(' + ((i*137.508)%360).toFixed(1) + ' 72% 78%)'; }}
function diffSet(){{
  const a=side.L, b=side.R;
  if(a===b) return [];
  const k = a<b ? a+'|'+b : b+'|'+a;
  return DIFFS[k] || [];
}}

function buildSrcs(which){{
  const box = document.getElementById('srcs'+which);
  box.innerHTML = '';
  KEYS.forEach(function(k){{
    const d = document.createElement('div');
    d.className = 'src' + (side[which]===k?' on':'');
    d.textContent = k;
    d.onclick = function(){{
      if(side[which]===k) return;
      side[which]=k; buildSrcs(which); buildCats(); renderAll();
    }};
    box.appendChild(d);
  }});
}}

function buildCats(){{
  const box = document.getElementById('cats');
  box.innerHTML = '';
  const dif = new Set(diffSet());
  CATS.forEach(function(c,i){{
    const nl = DATA[side.L].counts[String(i)] || 0;
    const nr = DATA[side.R].counts[String(i)] || 0;
    const l = document.createElement('label');
    l.className = 'cat' + ((nl||nr) ? '' : ' zero') + (dif.has(i) ? ' diff' : '');
    l.innerHTML = '<input type=checkbox ' + (on.has(i)?'checked':'') + ' data-i=' + i + '>' +
      '<span class=dot style="background:' + colour(i) + '"></span>' +
      '<span class=nm>' + c + '</span><span class=n>' + nl + ' / ' + nr + '</span>';
    l.querySelector('input').onchange = function(e){{
      e.target.checked ? on.add(i) : on.delete(i); renderAll();
    }};
    box.appendChild(l);
  }});
}}

function render(which){{
  const src = side[which];
  const segs = DATA[src].segments;
  let out = '', shown = 0;
  for(const [a,b,cats,miss] of segs){{
    const piece = RAW.slice(a,b).replace(/&/g,'&amp;').replace(/</g,'&lt;');
    const hit = cats.filter(c=>on.has(c));
    if(hit.length){{
      shown++;
      out += '<mark class="' + (miss?'miss':'') + '" style="background:' + colour(hit[0]) +
             '" title="' + hit.map(c=>CATS[c]).join(', ') + '">' + piece + '</mark>';
    }} else out += piece;
  }}
  const doc = document.getElementById('doc'+which);
  const keep = doc.scrollTop;
  doc.innerHTML = out;
  doc.scrollTop = keep;
  const total = Object.values(DATA[src].counts).reduce((x,y)=>x+y,0);
  const st = STATS[src];
  document.getElementById('bar'+which).innerHTML =
    total + ' spans &middot; ' + shown + ' runs' +
    (st ? ' &middot; ' + st.exact + ' exact / ' + st.normalized + ' norm / ' + st.not_found + ' missing' : '');
}}

function renderAll(){{ render('L'); render('R'); }}
function setAll(v){{ on = v ? new Set(CATS.map((_,i)=>i)) : new Set(); buildCats(); renderAll(); }}
function onlyPresent(){{
  on = new Set(CATS.map((_,i)=>i).filter(i =>
    (DATA[side.L].counts[String(i)]||0) || (DATA[side.R].counts[String(i)]||0)));
  buildCats(); renderAll();
}}
function onlyDiff(){{ on = new Set(diffSet()); buildCats(); renderAll(); }}

let lock = false;
function link(a,b){{
  a.addEventListener('scroll', function(){{
    if(lock || !document.getElementById('syncbox').checked) return;
    lock = true; b.scrollTop = a.scrollTop;
    requestAnimationFrame(function(){{ lock = false; }});
  }});
}}
const dL = document.getElementById('docL'), dR = document.getElementById('docR');
link(dL,dR); link(dR,dL);

buildSrcs('L'); buildSrcs('R'); buildCats(); renderAll();
</script>
"""

if __name__ == "__main__":
    main()
