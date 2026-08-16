import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cuad_dataset import CuadDataset

STUDY = Path(__file__).resolve().parent.parent
OUT = STUDY / "reviews" / "sample-contracts.html"

PICKS = [
    "GluMobileInc_20070319_S-1A_EX-10.09_436630_EX-10.09_Content License Agreement2",
    "DIVERSINETCORP_03_01_2012-EX-4-RESELLER AGREEMENT",
    "PlayboyEnterprisesInc_20090220_10-QA_EX-10.2_4091580_EX-10.2_Content License Agreement_ Marketing Agreement_ Sales-Purchase Agreement1",
]

TRIO = {"Minimum Commitment", "Volume Restriction", "Revenue/Profit Sharing"}

COLORS = {
    "Agreement Date": "#FFE9A3",
    "Governing Law": "#BFE8C6",
    "Expiration Date": "#FFCBA6",
    "Anti-Assignment": "#C7D6F7",
    "Cap On Liability": "#F6C4C4",
    "License Grant": "#BEE6F2",
    "Exclusivity": "#DED0F5",
    "Revenue/Profit Sharing": "#D9E8A0",
    "Minimum Commitment": "#E9C7E7",
    "Volume Restriction": "#A9DED4",
    "Most Favored Nation": "#F5B7D0",
    "Source Code Escrow": "#CBD2D9",
}

RATIONALE = [
    (
        "GluMobileInc_20070319_S-1A_EX-10.09_436630_EX-10.09_Content License Agreement2",
        "short",
        "2,796 tokens / 11,954 chars. The shortest contract that still carries the "
        "complete Savelka confusable trio (Minimum Commitment, Volume Restriction, "
        "Revenue/Profit Sharing) all at once, and it is absence-heavy: 6 of the 12 "
        "subset categories are present, 6 are is_impossible. It is also a "
        "fragment - CUAD split one SEC exhibit into four contract records "
        "(&hellip;Agreement1&ndash;4) - which is worth seeing early.",
    ),
    (
        "DIVERSINETCORP_03_01_2012-EX-4-RESELLER AGREEMENT",
        "mid",
        "15,914 tokens / 75,389 chars. Sits in the 8k-16k bucket and is the only "
        "reasonable-length contract in the pre-carve training pool carrying Source Code Escrow, the "
        "rarest category in the subset (13/510 overall). 10 of 12 present, 2 "
        "absent. Two of the three trio categories are present and the third "
        "(Revenue/Profit Sharing) is an explicit absence, which is exactly the "
        "confusion the trio is in the subset to probe.",
    ),
    (
        "PlayboyEnterprisesInc_20090220_10-QA_EX-10.2_4091580_EX-10.2_Content License Agreement_ Marketing Agreement_ Sales-Purchase Agreement1",
        "long",
        "25,919 tokens / 117,118 chars, in the &gt;16k bucket. The densest subset "
        "coverage available in the pre-carve training pool: 11 of 12 categories present including "
        "Most Favored Nation (28/510 overall) and the full trio. Only Source Code "
        "Escrow is absent - which the mid contract supplies, so the three "
        "contracts together cover all 12 subset categories at least once.",
    ),
]


def split_paragraphs(text):
    parts = []
    pos = 0
    for m in re.finditer(r"\n\s*\n", text):
        parts.append((pos, m.start()))
        pos = m.end()
    parts.append((pos, len(text)))

    out = []
    for start, end in parts:
        if end <= start:
            continue
        if end - start <= 1600:
            out.append((start, end))
            continue
        cursor = start
        for m in re.finditer(r"(?<=[.;:])\s{2,}", text[start:end]):
            abs_end = start + m.start()
            if abs_end - cursor >= 700:
                out.append((cursor, abs_end))
                cursor = start + m.end()
        if cursor < end:
            out.append((cursor, end))
    return out


def segment(text, para_start, para_end, spans):
    cuts = {para_start, para_end}
    for start, end, _ in spans:
        if start > para_start and start < para_end:
            cuts.add(start)
        if end > para_start and end < para_end:
            cuts.add(end)
    ordered = sorted(cuts)
    segs = []
    for a, b in zip(ordered, ordered[1:]):
        cats = [c for (s, e, c) in spans if s < b and a < e]
        segs.append((a, b, cats))
    return segs


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def swatch(category):
    trio = " trio" if category in TRIO else ""
    return (
        f'<span class="sw{trio}" style="background:{COLORS[category]}"></span>'
        f"{html.escape(category)}"
    )


def render_text(inst, idx, spans, first_anchor):
    paragraphs = split_paragraphs(inst.text)
    annotated = []
    for i, (ps, pe) in enumerate(paragraphs):
        hit = any(s < pe and ps < e for (s, e, _) in spans)
        annotated.append(hit)

    keep = [False] * len(paragraphs)
    for i, hit in enumerate(annotated):
        if hit:
            for j in (i - 1, i, i + 1):
                if 0 <= j < len(paragraphs):
                    keep[j] = True

    seen = set()
    chunks = []
    i = 0
    while i < len(paragraphs):
        if keep[i]:
            ps, pe = paragraphs[i]
            pieces = []
            for a, b, cats in segment(inst.text, ps, pe, spans):
                raw = html.escape(inst.text[a:b])
                pending = [
                    first_anchor[k]
                    for k in first_anchor
                    if k[1] < b and k not in seen
                ]
                for k in [k for k in first_anchor if k[1] < b and k not in seen]:
                    seen.add(k)
                if not cats:
                    pieces.append(
                        "".join(f'<i class="anc" id="{a_}"></i>' for a_ in pending)
                        + raw
                    )
                    continue
                anchor = ""
                if pending:
                    anchor = f' id="{pending[0]}"'
                    pieces.append(
                        "".join(f'<i class="anc" id="{a_}"></i>' for a_ in pending[1:])
                    )
                if len(cats) == 1:
                    style = f"background:{COLORS[cats[0]]}"
                    cls = "hl"
                else:
                    stops = []
                    width = 10
                    for n, c in enumerate(cats):
                        stops.append(f"{COLORS[c]} {n * width}px {(n + 1) * width}px")
                    style = (
                        "background:repeating-linear-gradient(135deg,"
                        + ",".join(stops)
                        + ")"
                    )
                    cls = "hl multi"
                tip = " + ".join(cats) + f"  [{a}:{b}]"
                pieces.append(
                    f'<span class="{cls}"{anchor} style="{style}" '
                    f'title="{html.escape(tip)}">{raw}</span>'
                )
            chunks.append('<p class="ct">' + "".join(pieces) + "</p>")
            i += 1
        else:
            j = i
            while j < len(paragraphs) and not keep[j]:
                j += 1
            body = html.escape(inst.text[paragraphs[i][0] : paragraphs[j - 1][1]])
            n_chars = paragraphs[j - 1][1] - paragraphs[i][0]
            chunks.append(
                f'<details class="fold"><summary>unannotated region &mdash; '
                f"{n_chars:,} chars, {j - i} block(s) &mdash; click to expand"
                f'</summary><p class="ct">{body}</p></details>'
            )
            i = j
    return "\n".join(chunks)


def task_output(inst, categories):
    extractions = []
    absent = []
    for c in categories:
        g = inst.gold[c]
        if g.is_impossible:
            absent.append({"category": c, "principles_cited": []})
        else:
            for s in g.spans:
                extractions.append(
                    {"category": c, "text": s.text, "principles_cited": []}
                )
    return {"extractions": extractions, "absent": absent}


def contract_section(d, cid, idx, record, rationale):
    inst = d.get_instance(cid)
    cats = d.categories
    present = [c for c in cats if not inst.gold[c].is_impossible]
    absent = [c for c in cats if inst.gold[c].is_impossible]

    spans = []
    first_anchor = {}
    for c in cats:
        for k, s in enumerate(inst.gold[c].spans):
            spans.append((s.start, s.end, c))
            first_anchor[(c, s.start)] = f"c{idx}-{slug(c)}-{k}"
    spans.sort()
    n_spans = len(spans)

    jump = []
    for c in cats:
        g = inst.gold[c]
        if g.is_impossible:
            jump.append(
                f'<li class="absent">{swatch(c)} <span class="tag">ABSENT</span></li>'
            )
        else:
            links = " ".join(
                f'<a href="#c{idx}-{slug(c)}-{k}">{k + 1}</a>'
                for k in range(len(g.spans))
            )
            jump.append(f"<li>{swatch(c)} <span class=\"jl\">{links}</span></li>")

    gt_rows = []
    for c in cats:
        g = inst.gold[c]
        if g.is_impossible:
            gt_rows.append(
                f'<div class="gt gt-absent"><div class="gt-h">{swatch(c)}</div>'
                f'<div class="gt-b"><span class="tag big">ABSENT '
                f"(is_impossible = true)</span> <span class=\"muted\">no gold span; "
                f"the correct output is an AbsenceClaim, not an empty slot</span>"
                f"</div></div>"
            )
            continue
        items = []
        for k, s in enumerate(g.spans):
            items.append(
                f'<div class="span"><div class="off">[{s.start}:{s.end}] '
                f"&middot; {s.end - s.start:,} chars &middot; span {k + 1}/"
                f'{len(g.spans)} <a href="#c{idx}-{slug(c)}-{k}">jump &rarr;</a></div>'
                f'<blockquote>{html.escape(s.text)}</blockquote></div>'
            )
        gt_rows.append(
            f'<div class="gt"><div class="gt-h">{swatch(c)} '
            f'<span class="cnt">{len(g.spans)} span(s)</span></div>'
            f'<div class="gt-b">{"".join(items)}</div></div>'
        )

    payload = json.dumps(task_output(inst, cats), indent=2, ensure_ascii=False)

    return f"""
<section class="contract" id="contract-{idx}">
  <h2>{idx}. <span class="mono">{html.escape(inst.title)}</span></h2>
  <div class="meta">
    <div><b>contract_id</b><span class="mono">{html.escape(cid)}</span></div>
    <div><b>split</b><span>{record["split"]}</span></div>
    <div><b>n_chars</b><span>{record["n_chars"]:,}</span></div>
    <div><b>n_tokens</b><span>{record["n_tokens"]:,}</span></div>
    <div><b>length_bucket</b><span>{record["length_bucket"]}</span></div>
    <div><b>subset coverage</b><span>{len(present)} present / {len(absent)} absent
      (of 12)</span></div>
    <div><b>gold spans (subset)</b><span>{n_spans}</span></div>
  </div>
  <p class="why"><b>Why this one ({rationale[1]}):</b> {rationale[2]}</p>

  <h3>Category index / jump list</h3>
  <ul class="jump">{"".join(jump)}</ul>

  <h3>Contract text with gold spans highlighted</h3>
  <p class="note-sm">Whitespace is preserved exactly as the model will receive it.
  Unannotated stretches are folded, not dropped &mdash; all body text is present;
  only the blank lines between blocks are consumed by the layout. Striped
  highlights are characters claimed by more than one category (hover for the
  category list and offsets).</p>
  <div class="doc">{render_text(inst, idx, spans, first_anchor)}</div>

  <h3>Ground truth &mdash; all 12 subset categories</h3>
  <div class="gtwrap">{"".join(gt_rows)}</div>

  <h3>What a correct <span class="mono">TaskOutput</span> would be</h3>
  <p class="note-sm"><b>principles_cited is empty on every decision by
  construction.</b> The principle set does not exist yet &mdash; investigation 002
  has not run &mdash; so there are no principle ids to cite and no gold citations.
  These are the answer-correct outputs only.</p>
  <div class="scroll"><pre class="json">{html.escape(payload)}</pre></div>
</section>
"""


def main():
    d = CuadDataset()
    cats = d.categories
    legend = "".join(
        f'<li>{swatch(c)}</li>' for c in cats
    )
    rmap = {r[0]: r for r in RATIONALE}
    sections = []
    for i, cid in enumerate(PICKS, start=1):
        sections.append(contract_section(d, cid, i, d._records[cid], rmap[cid]))

    body = PAGE.format(legend=legend, sections="".join(sections))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(body, encoding="utf-8")
    print(OUT)


PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CUAD sample contracts &mdash; ground-truth inspection (study 008)</title>
<style>
  :root {{
    --bg: #f7f6f3;
    --panel: #ffffff;
    --ink: #17181a;
    --muted: #5c6169;
    --rule: #d7d4cd;
    --accent: #7a3e12;
    --warn-bg: #fdf2d8;
    --warn-br: #c9992a;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ max-width: 100%; overflow-x: hidden; }}
  body {{
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font: 15px/1.55 "Iowan Old Style", "Charter", Georgia, "Times New Roman", serif;
  }}
  .wrap {{ max-width: 1180px; margin: 0 auto; padding: 28px 22px 80px; }}
  h1 {{ font-size: 27px; margin: 0 0 6px; line-height: 1.2; }}
  h2 {{
    font-size: 20px; margin: 46px 0 12px; padding-top: 18px;
    border-top: 2px solid var(--ink);
  }}
  h3 {{ font-size: 16px; margin: 28px 0 8px; color: var(--accent);
       text-transform: uppercase; letter-spacing: .06em; }}
  p {{ margin: 0 0 12px; }}
  a {{ color: #17458f; }}
  code, .mono, pre {{
    font-family: "SF Mono", "Menlo", "Consolas", monospace; font-size: 12.5px;
  }}
  .sub {{ color: var(--muted); font-size: 14px; margin-bottom: 20px; }}
  .banner {{
    background: var(--warn-bg); border: 1px solid var(--warn-br);
    border-left: 6px solid var(--warn-br); padding: 12px 14px; margin: 0 0 22px;
    font-size: 14px;
  }}
  .banner b {{ display: block; margin-bottom: 4px; }}
  .card {{
    background: var(--panel); border: 1px solid var(--rule);
    padding: 16px 18px; margin: 0 0 20px;
  }}
  .card h3 {{ margin-top: 0; }}
  ul.legend {{ list-style: none; margin: 0; padding: 0;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(215px, 1fr));
    gap: 4px 14px; font-size: 13.5px; }}
  .sw {{
    display: inline-block; width: 15px; height: 13px; margin-right: 7px;
    border: 1px solid #9a958c; vertical-align: -2px;
  }}
  .sw.trio {{ border: 2px solid #7a1f1f; }}
  .meta {{
    display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
    gap: 6px 16px; background: var(--panel); border: 1px solid var(--rule);
    padding: 12px 14px; font-size: 13px; margin-bottom: 12px;
  }}
  .meta > div {{ display: flex; flex-direction: column; min-width: 0; }}
  .meta b {{ color: var(--muted); font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: .05em; }}
  .meta span {{ overflow-wrap: anywhere; }}
  .why {{ font-size: 14px; background: #efeee9; border-left: 4px solid var(--accent);
    padding: 10px 12px; }}
  ul.jump {{ list-style: none; margin: 0; padding: 0;
    display: grid; grid-template-columns: repeat(auto-fill, minmax(255px, 1fr));
    gap: 3px 14px; font-size: 13px;
    background: var(--panel); border: 1px solid var(--rule); padding: 12px 14px; }}
  ul.jump li.absent {{ color: var(--muted); }}
  .jl a {{ display: inline-block; padding: 0 4px; margin-right: 2px;
    border: 1px solid var(--rule); background: #fff; font-size: 11px;
    text-decoration: none; }}
  .tag {{ font-family: "SF Mono", Menlo, monospace; font-size: 10.5px;
    background: #3a3d42; color: #fff; padding: 1px 5px; letter-spacing: .04em; }}
  .tag.big {{ font-size: 12px; padding: 2px 7px; background: #7a1f1f; }}
  .note-sm {{ font-size: 13px; color: var(--muted); }}
  .doc {{
    background: var(--panel); border: 1px solid var(--rule);
    padding: 4px 18px 14px; max-height: 640px; overflow-y: auto;
    overflow-x: auto;
  }}
  p.ct {{
    white-space: pre-wrap; overflow-wrap: anywhere;
    font-family: "SF Mono", Menlo, Consolas, monospace;
    font-size: 12.3px; line-height: 1.62; margin: 10px 0;
  }}
  .anc {{ display: inline; }}
  .anc, .hl {{ scroll-margin-top: 60px; }}
  .hl {{ padding: 1px 0; border-bottom: 1px solid rgba(0,0,0,.28); }}
  .hl.multi {{ border-bottom: 2px dotted #7a1f1f; }}
  details.fold {{ margin: 8px 0; border: 1px dashed var(--rule);
    background: #fbfaf7; }}
  details.fold > summary {{ cursor: pointer; padding: 5px 10px;
    font-size: 12px; color: var(--muted); }}
  details.fold p.ct {{ margin: 0; padding: 0 10px 10px; }}
  .gtwrap {{ display: flex; flex-direction: column; gap: 8px; }}
  .gt {{ background: var(--panel); border: 1px solid var(--rule); }}
  .gt-h {{ padding: 7px 12px; border-bottom: 1px solid var(--rule);
    font-size: 13.5px; font-weight: 600; background: #fbfaf7; }}
  .gt-b {{ padding: 8px 12px; }}
  .gt-absent .gt-b {{ background: #f4f0f0; }}
  .cnt {{ color: var(--muted); font-weight: 400; font-size: 12px; }}
  .muted {{ color: var(--muted); font-size: 12.5px; }}
  .span {{ margin-bottom: 10px; }}
  .span:last-child {{ margin-bottom: 0; }}
  .off {{ font-family: "SF Mono", Menlo, monospace; font-size: 11px;
    color: var(--muted); margin-bottom: 2px; }}
  blockquote {{ margin: 0; padding: 6px 10px; border-left: 3px solid #b9b4aa;
    background: #fbfaf7; white-space: pre-wrap; overflow-wrap: anywhere;
    font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 12px;
    line-height: 1.5; }}
  .scroll {{ overflow-x: auto; max-width: 100%; }}
  pre.json {{ background: #1f2126; color: #e7e4dd; padding: 14px;
    margin: 0; max-height: 460px; overflow: auto; line-height: 1.45; }}
  table {{ border-collapse: collapse; font-size: 13px; width: 100%; }}
  th, td {{ border: 1px solid var(--rule); padding: 5px 8px; text-align: left;
    vertical-align: top; }}
  th {{ background: #efeee9; }}
  ol.obs > li {{ margin-bottom: 10px; }}
  .ex {{ font-family: "SF Mono", Menlo, monospace; font-size: 11.5px;
    background: #efeee9; padding: 1px 4px; overflow-wrap: anywhere; }}
  footer {{ margin-top: 50px; padding-top: 14px; border-top: 1px solid var(--rule);
    font-size: 12.5px; color: var(--muted); }}
</style>
</head>
<body>
<div class="wrap">

<h1>CUAD sample contracts &mdash; what the data and the ground truth actually
look like</h1>
<p class="sub">Study 008 &middot; principled extraction on CUAD &middot;
inspection artifact, not a result. Generated by
<span class="mono">scripts/render_sample_contracts.py</span>.</p>

<div class="banner">
<b>Repository-policy note &mdash; this file embeds full contract text.</b>
The study's Repository policy says no full contract text goes in git. This page
deliberately embeds the complete text of <b>three training-pool contracts</b> as a
human-inspection artifact, so the reader can see exactly what the model is fed.
It is a considered exception, not an oversight; decide whether it is committed or
kept local. The underlying CUAD source (<span class="mono">data/raw/CUADv1.json</span>)
remains gitignored.
</div>

<div class="card">
<h3>Read this first</h3>
<p><b>Split.</b> All three contracts were drawn from the <b>pre-carve training
pool</b> (368 contracts, the split then called <span class="mono">ft_train</span>),
never from harness_val (40) or test (102). Under the post-INV1-D8 arrangement the
short contract is in <span class="mono">model_train</span> and the mid and long
contracts are in <span class="mono">principle_train</span>; the page was built
before that carve and its counts are over the 368-contract pool. harness_val and test have to stay unexamined:
harness_val is where P0 and the condition grid get measured and test is the final
report set, so any human or model exposure to them contaminates the numbers this
study exists to produce. model_train is reserved for Phase 2 fine-tuning, where
looking at examples is exactly the point. Nothing on this page should be read as
evidence about the model's test behaviour; it is evidence about the
<em>data</em>.</p>
<p><b>Gold is multi-span.</b> A CUAD category is not a slot with one answer. Most
present categories carry several disjoint spans scattered across the document
(here: up to 10, for Minimum Commitment in the long contract). The annotators
marked every passage that evidences the category, so a model that finds the one
"best" clause is partially right by construction, and span-level scoring has to
decide what to do with the other ten. Absence is the other half: a category with
<span class="mono">is_impossible = true</span> has zero spans and the correct
output is a positive claim that the contract does not contain it.</p>
<p><b>Subset.</b> The 12-category provisional subset from
<span class="mono">scripts/config/category_subset.yaml</span>. Categories with a
dark red swatch border are the Savelka confusable trio (Minimum Commitment /
Volume Restriction / Revenue/Profit Sharing).</p>
<ul class="legend">{legend}</ul>
</div>

<div class="card">
<h3>Selection rationale</h3>
<p>Three contracts spanning the length range, chosen from model_train only, to
maximise subset coverage and to put at least one full instance of the confusable
trio and a healthy number of <span class="mono">is_impossible</span> absences in
front of the reader. Between them they cover <b>all 12</b> subset categories at
least once, and contribute <b>9</b> explicit absences.</p>
<div class="scroll"><table>
<tr><th>#</th><th>contract</th><th>bucket</th><th>tokens</th><th>chars</th>
<th>present / absent</th><th>trio present</th></tr>
<tr><td>1</td><td class="mono">GluMobileInc&hellip;Content License Agreement2</td>
<td>&le;4k</td><td>2,796</td><td>11,954</td><td>6 / 6</td><td>3 of 3</td></tr>
<tr><td>2</td><td class="mono">DIVERSINETCORP&hellip;RESELLER AGREEMENT</td>
<td>8k&ndash;16k</td><td>15,914</td><td>75,389</td><td>10 / 2</td><td>2 of 3</td></tr>
<tr><td>3</td><td class="mono">PlayboyEnterprisesInc&hellip;Agreement1</td>
<td>&gt;16k</td><td>25,919</td><td>117,118</td><td>11 / 1</td><td>3 of 3</td></tr>
</table></div>
<p class="note-sm">Deliberate trade-off: the mid contract is the only
reasonable-length model_train contract carrying <b>Source Code Escrow</b> (13/510
overall), so it was picked for rarity coverage rather than for being the most
typical mid-length agreement. The long contract was capped at ~26k tokens; the
longest model_train contract is 82k tokens and would have made this page
unreadable without adding anything the reader cannot infer.</p>
</div>

<div class="card">
<h3>Quirks observed while reading these three contracts</h3>
<p class="note-sm">Everything below was seen directly in these three instances,
not assumed. Most of it will make span-level scoring awkward.</p>
<ol class="obs">
<li><b>Gold spans overlap across categories, sometimes byte-identically.</b>
In contract 1, <span class="ex">License Grant [4341:4672]</span> and
<span class="ex">Exclusivity [4341:4672]</span> are the same characters under two
labels; in contract 2 the same is true of
<span class="ex">License Grant / Exclusivity [1613:2052]</span>. A per-category
span-F1 handles this fine, but any "assign each character one label" evaluation
or any confusion-matrix built from character overlap will be wrong. It also means
a model that emits one span for both categories is fully correct twice.</li>

<li><b>Near-identical spans with off-by-one ends.</b> Contract 1 has
<span class="ex">License Grant [6689:6965]</span> and
<span class="ex">Exclusivity [6689:6964]</span> &mdash; the same passage,
one character apart. That is annotation jitter, not a distinction, and it sets a
floor on how precisely any span-boundary metric can be interpreted.</li>

<li><b>Spans nest.</b> Contract 1's <span class="ex">Minimum Commitment
[5349:6056]</span> strictly contains both <span class="ex">Revenue/Profit Sharing
[5349:5616]</span> and <span class="ex">[5883:6056]</span>. Token-level Jaccard
copes; "did the model find the span" as a set-membership question does not.</li>

<li><b>Redacted text is inside the contract.</b> Contracts 1 and 3 are
confidential-treatment filings: every commercial number is literally
<span class="ex">*****</span> (29 and 45 occurrences respectively). Several gold
spans are mostly asterisks &mdash;
<span class="ex">"an additional minimum recoupable guarantee of ***** dollars
(US$*****)"</span>. So the Minimum Commitment and Revenue/Profit Sharing
decisions have to be made on clause structure alone, with the amounts removed.
Good news for the study (it forces rule-following over number-spotting), bad news
for anyone assuming the text carries the facts.</li>

<li><b>SEC page furniture is embedded mid-sentence, and gold splits around it.</b>
Contract 3 contains <span class="ex">\\n\\n27\\n\\nSource: PLAYBOY ENTERPRISES INC,
10-Q/A, 2/20/2009\\n\\n\\n\\n\\n\\n</span> in the middle of a sentence. The
annotators stopped the Anti-Assignment span at
<span class="ex">[95903:96755]</span> ending "&hellip;the ability and intention,
to" and started a new one at <span class="ex">[96820:&hellip;]</span> beginning
lowercase "adequately invest&hellip;". One legal thought, two gold spans, split by
a page footer. A model that emits the whole passage as one span gets penalised
for the footer characters; one that emits two gets rewarded for reproducing a
scanning artifact.</li>

<li><b>At least one span looks plainly mislabeled.</b> Contract 3's
<span class="ex">License Grant [2764:2773]</span> is the nine characters
<span class="ex">"Business."</span> &mdash; the tail of "&hellip;marketing and
promotion of the Playboy Commerce Business." That is not a license grant; it is a
truncated selection. It will read as a false negative for any correct model.</li>

<li><b>Other spans look labeled by neighbourhood rather than content.</b>
Contract 2's <span class="ex">Minimum Commitment [5474:5516]</span> is
<span class="ex">"Either Party may terminate this Agreement:"</span> &mdash; a
termination heading, captured presumably because the sub-clause below it is about
failing to make an AMC payment. Expect a systematic class of gold spans that are
structurally adjacent to the concept rather than expressing it.</li>

<li><b>Boilerplate repeats verbatim, and gold marks each copy.</b> Contract 1 has
two Revenue/Profit Sharing spans at <span class="ex">[2121:2448]</span> and
<span class="ex">[3500:3824]</span> whose text is character-identical for the
first ~320 characters (the same royalty paragraph applied to a different
property). A model emitting the passage once cannot be distinguished from one
that missed the second occurrence unless scoring is offset-aware &mdash; and the
<span class="mono">TaskOutput</span> schema carries <em>text</em>, not offsets,
so it cannot be.</li>

<li><b>Whitespace is not paragraph structure.</b> These texts use runs of two or
more spaces where a line break belongs: contract 2 has 692 double-space runs
against only 208 newlines across 75k characters; contract 3 has 1,119. Words are
also broken by the original line-wrap and survive as
<span class="ex">"non- transferable"</span>,
<span class="ex">"non-assi&hellip;"</span>. Any whitespace normalisation before
scoring changes character offsets; any tokenizer will see these as split words.</li>

<li><b>OCR noise, low but present.</b> Contract 2 contains
<span class="ex">&yuml;</span> used as a bullet
(<span class="ex">"Terms and Conditions &yuml; Price proposals are valid&hellip;"</span>)
and <span class="ex">&frac14;</span> in a numeric context
(<span class="ex">"quarterly targets at &frac14; of annual amount"</span>), plus
&reg;/&trade; glyphs. Contract 3 uses <span class="ex">&middot;</span> and
<span class="ex">&bull;</span> as bullets. No CRs, no tabs in any of the three.</li>

<li><b>Date spans are tiny; clause spans are not.</b> Agreement Date is 16&ndash;17
characters in all three contracts; clause categories run 100&ndash;1,100. A macro
average over categories therefore mixes a near-exact-match task with a
fuzzy-boundary task, and one wrong character hurts the date far more than the
clause. Length stratification is already in the metrics plan; per-category
stratification by span length may be needed too.</li>

<li><b>One contract is a fragment of a filing.</b> Contract 1 is
<span class="mono">&hellip;Content License Agreement2</span>: CUAD split a single
SEC exhibit into four separate contract records (1&ndash;4), and record 4 has just
two present categories in 475 tokens. Absences in a fragment are not the same
event as absences in a whole agreement &mdash; the clause may exist, just in
sibling record 1. Worth knowing before absence accuracy is reported as if all
absences were equivalent.</li>

<li><b>Present categories are usually the same ones.</b> Across the three, the
head categories (Agreement Date, Governing Law, Expiration Date, License Grant)
are present nearly always and the rare ones nearly never. Absence accuracy will
be dominated by the tail, and a model that answers "absent" for
Source Code Escrow and Most Favored Nation unconditionally will score well on
absence without doing anything.</li>
</ol>
</div>

{sections}

<footer>
CUAD v1 is released by <b>The Atticus Project</b> under
<b>CC BY 4.0</b>. Contract text and annotations shown here are derived from that
release and remain under that licence. Cite as
<span class="mono">hendrycks2021cuad</span> &mdash; Hendrycks, Burns, Chen and
Ball, "CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review",
arXiv:2103.06268.
</footer>

</div>
</body>
</html>
"""


if __name__ == "__main__":
    main()
