#!/usr/bin/env python3
import json, pathlib
base = pathlib.Path(__file__).parent

def load(p): return (base/p).read_text()
js = lambda p: json.dumps(json.load(open(base/p)), indent=2)

sections = [
 ("Pipeline Inputs","1. Manifest (final/manifest)","<pre>"+load("final/manifest.json")[:1200]+"</pre>"),
 ("Pipeline Inputs","2. Prompt snippet (intermediate/snippet)","<pre>"+load("intermediate/snippet.txt")+"</pre>"),
 ("Pipeline Inputs","3. Contract text (intermediate/contract_text)","<pre>"+load("intermediate/contract_text.txt")+"</pre>"),
 ("Compare","4. Compare — Input (step2 clauses / target cats)","<h4>Input: target_cats</h4><pre>"+js("intermediate/target_cats.json")+"</pre><h4>Input: step2 clauses</h4><pre>"+js("intermediate/step2_clauses.json")[:3000]+"</pre>"),
 ("Compare","5. Compare — LLM output (step1) + decision","<h4>LLM output</h4><pre>"+js("intermediate/step1.json")[:4000]+"</pre><h4>Decision / notes</h4><p>Script: step1_compare.py. Pre-principle extraction result.</p>"),
 ("Diagnose","6. Diagnose — Input (discrepancy)","<h4>Input</h4><pre>"+js("intermediate/step1_discrepancy.json")[:3000]+"</pre>"),
 ("Diagnose","7. Diagnose — Output / reasoning","<h4>LLM / derived</h4><pre>Script: step2_diagnose.py. Discrepancy analysis above.</pre>"),
 ("Derive","8. Derive — Input (principle proposal)","<h4>Input / proposed</h4><pre>"+js("intermediate/step3_principle.json")[:3000]+"</pre>"),
 ("Derive","9. Derive — Reasoning (final/)","<h4>LLM reasoning text</h4><pre>"+load("final/427fdf6d11488a9c.reasoning.txt")[:2500]+"</pre>"),
 ("Test","10. Test — Pre vs Post (final/)","<h4>Trials / scores</h4><pre>"+load("final/trials.jsonl")[:2500]+"</pre><h4>Reasoning / output</h4><pre>"+load("final/427fdf6d11488a9c.txt")[:2000]+"</pre>"),
]

toc = '\n'.join(f'<a href="#s{i}">{grp}: {title}</a>' for i,(grp,title,_) in enumerate(sections))
body = ''.join(f'<details id="s{i}" class="collapsible"><summary><strong>{grp} — {title}</strong></summary><div class="content">{body}</div></details>' for i,(grp,title,body) in enumerate(sections))

html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Pipeline view</title>
<style>
body{{font-family:system-ui,sans-serif;max-width:980px;margin:2rem auto;padding:0 1rem;color:#222}}
h1{{font-size:1.3rem;border-bottom:3px solid #4466aa;padding-bottom:.3rem}}
.toc{{background:#f4f6f8;padding:1rem;border-radius:6px;margin-bottom:1.5rem;border-left:4px solid #4466aa}}
.toc a{{display:block;padding:.15rem 0;color:#2255aa;text-decoration:none;font-size:.9rem}}
.toc a:hover{{text-decoration:underline}}
details.collapsible{{border:1px solid #ccc;border-radius:6px;margin:.6rem 0;overflow:hidden}}
details.collapsible summary{{cursor:pointer;padding:.6rem .8rem;background:#f0f3f7;font-weight:600;font-size:1rem;list-style:none}}
details.collapsible summary::before{{content:"▶ ";font-size:.8rem;color:#556}}
details.collapsible[open] summary::before{{content:"▼ "}}
.content{{padding:.8rem 1rem;background:#fff;border-top:1px solid #e2e4e8}}
.content h4{{margin:.6rem 0 .3rem;color:#445}}
pre{{background:#f8f9fa;padding:.7rem;overflow:auto;font-size:.82rem;border:1px solid #e6e8eb;border-radius:4px}}
.tag{{display:inline-block;padding:.15rem .35rem;border-radius:4px;font-size:.7rem;background:#e2e4e8;color:#333;margin-right:.3rem}}
</style></head>
<body>
<h1>Pipeline iteration view (file-driven)</h1>
<div class="toc"><strong>Contents</strong><br>{toc}</div>
{body}
<p style="margin-top:2rem;color:#666;font-size:.8rem">Built by build_view.py. Sections collapsed by default; open to inspect LLM outputs/decisions.</p>
</body></html>"""
(base/"view.html").write_text(html)
print("wrote view.html with", len(sections), "sections")
