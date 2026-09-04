#!/usr/bin/env python3
import os, json, html

CONTRACT_DIR = 'contract_text'
GT_PATH = 'contract_ground_truth'
OUT_DIR = 'app'

os.makedirs(OUT_DIR, exist_ok=True)

# Load ground truth
spans_data = {}
with open(GT_PATH, 'r', encoding='utf-8') as f:
    for line in f:
        line=line.strip()
        if not line:
            continue
        rec = json.loads(line)
        cid = rec['contract_id']
        gold = rec['gold']
        # keep only needed info
        spans_data[cid] = {}
        for cat, info in gold.items():
            spans_data[cid][cat] = {
                "is_impossible": info["is_impossible"],
                "spans": info["spans"]
            }

# Load texts into dict
texts = {}
ids = []
for fname in os.listdir(CONTRACT_DIR):
    if fname.endswith('.txt'):
        cid = fname[:-4]
        ids.append(cid)
        with open(os.path.join(CONTRACT_DIR, fname), 'r', encoding='utf-8') as f:
            texts[cid] = f.read()

ids.sort()

# Build colors for categories (max 41)
# Get all category names
categories = set()
for cid in spans_data:
    categories.update(spans_data[cid].keys())
categories = sorted(categories)
# Generate HSL palette
palette = {}
for i, cat in enumerate(categories):
    hue = (i * 360 / len(categories)) % 360
    palette[cat] = f"hsl({hue:.0f}, 70%, 80%)"
    # text color could be dark

# Write JS data file with texts and spans
# To avoid enormous single file parsing issues, split into two scripts? Still okay.
# We'll embed directly in HTML via script tags.

# Build JS objects
texts_json = json.dumps(texts, ensure_ascii=False)
spans_json = json.dumps(spans_data, ensure_ascii=False)
ids_json = json.dumps(ids, ensure_ascii=False)
palette_json = json.dumps(palette, ensure_ascii=False)

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Contract Visualization</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 0; padding: 20px; background: #f4f4f8; color: #222; }}
  h1 {{ font-size: 1.3rem; margin-bottom: 0.2rem; }}
  .subtitle {{ color: #555; font-size: 0.95rem; margin-bottom: 12px; }}
  .topbar {{ display: flex; gap: 12px; align-items: center; flex-wrap: wrap; background: #fff; padding: 12px 14px; border-radius: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); margin-bottom: 16px; }}
  select {{ font-size: 1rem; padding: 6px 10px; border-radius: 6px; border: 1px solid #ccc; min-width: 420px; max-width: 90vw; }}
  .stats {{ font-size: 0.9rem; color: #444; }}
  .layout {{ display: grid; grid-template-columns: 1fr 320px; gap: 16px; align-items: start; }}
  @media (max-width: 980px) {{ .layout {{ grid-template-columns: 1fr; }} }}
  .panel {{ background: #fff; border-radius: 10px; padding: 16px; box-shadow: 0 2px 6px rgba(0,0,0,0.05); }}
  .panel h2 {{ font-size: 1.05rem; margin: 0 0 10px; }}
  .contract-text {{ white-space: pre-wrap; word-break: break-word; line-height: 1.55; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, monospace; font-size: 0.92rem; color: #111; max-height: 78vh; overflow-y: auto; border: 1px solid #ddd; padding: 12px; border-radius: 6px; background: #fdfdfd; }}
  .highlight {{ border-radius: 3px; padding: 0 1px; cursor: default; }}
  .category-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .cat-chip {{ display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 999px; font-size: 0.82rem; font-weight: 500; background: #eee; border: 1px solid #ddd; cursor: pointer; user-select: none; }}
  .cat-chip .swatch {{ width: 12px; height: 12px; border-radius: 3px; border: 1px solid rgba(0,0,0,0.15); flex-shrink: 0; }}
  .cat-chip.active {{ background: #e0e8ff; border-color: #92a8e0; }}
</style>
</head>
<body>
<h1>Contract Visualization</h1>
<div class="subtitle">Select a contract to view highlighted spans from ground truth.</div>

<div class="topbar">
  <label for="contractSelect"><strong>Contract:</strong></label>
  <select id="contractSelect"></select>
  <div class="stats" id="stats"></div>
</div>

<div class="layout">
  <div class="panel">
    <h2>Contract Text</h2>
    <div id="textArea" class="contract-text">Select a contract above.</div>
  </div>
  <div class="panel">
    <h2>Present Categories <span id="countBadge" style="font-size:0.8rem;color:#777;margin-left:6px;">(0)</span></h2>
    <div id="catArea" class="category-list"></div>
  </div>
</div>

<script>
const CONTRACT_IDS = {ids_json};
const CONTRACT_TEXTS = {texts_json};
const CONTRACT_SPANS = {spans_json};
const PALETTE = {palette_json};

const select = document.getElementById('contractSelect');
const textArea = document.getElementById('textArea');
const catArea = document.getElementById('catArea');
const stats = document.getElementById('stats');
const countBadge = document.getElementById('countBadge');

function escapeHtml(str) {{
  return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function renderContract(cid) {{
  const text = CONTRACT_TEXTS[cid] || '';
  const spans = CONTRACT_SPANS[cid] || {{}};
  // Build present categories
  const present = [];
  const spansPerCat = {{}};
  for (const cat in spans) {{
    if (!spans[cat].is_impossible) {{
      present.push(cat);
      spansPerCat[cat] = spans[cat].spans || [];
    }}
  }}
  present.sort();

  // Stats
  const totalSpans = present.reduce((sum,cat)=>sum + (spansPerCat[cat].length||0), 0);
  stats.textContent = `Contracts: ${{CONTRACT_IDS.length}} | Spans in this contract: ${{totalSpans}} | Categories present: ${{present.length}}`;
  countBadge.textContent = `(${{present.length}})`;

  // Category chips
  catArea.innerHTML = '';
  if (present.length === 0) {{
    catArea.innerHTML = '<span style="color:#777;font-size:0.9rem;">None (all impossible)</span>';
  }} else {{
    for (const cat of present) {{
      const chip = document.createElement('button');
      chip.className = 'cat-chip';
      chip.innerHTML = `<span class="swatch" style="background:${{PALETTE[cat]||'#ccc'}}"></span><span>${{escapeHtml(cat)}}</span>`;
      // tooltip with count
      chip.title = `${{cat}} — ${{(spansPerCat[cat]||[]).length}} span(s)`;
      chip.addEventListener('click', () => {{
        chip.classList.toggle('active');
        // Re-render text with filter (optional)
        buildText(text, spans, chip.classList.contains('active') ? [cat] : null);
      }});
      catArea.appendChild(chip);
    }}
  }}

  // Initial full render
  buildText(text, spans, null);
}}

function buildText(text, spans, filterCats) {{
  // If filterCats is array, only show those categories; else show all present
  const points = new Set([0, text.length]);
  const segmentsCategories = []; // not needed if using interval method
  // Let's collect intervals using boundary points from all relevant spans
  for (const cat in spans) {{
    if (filterCats && !filterCats.includes(cat)) continue;
    if (spans[cat].is_impossible) continue;
    for (const [s,e] of spans[cat].spans) {{
      points.add(s);
      points.add(e);
    }}
  }}
  const sorted = Array.from(points).sort((a,b)=>a-b);
  let html = '';
  for (let i = 0; i < sorted.length - 1; i++) {{
    const s = sorted[i];
    const e = sorted[i+1];
    const segment = text.slice(s, e);
    const cats = [];
    for (const cat in spans) {{
      if (filterCats && !filterCats.includes(cat)) continue;
      if (spans[cat].is_impossible) continue;
      for (const [start, end] of spans[cat].spans) {{
        if (start <= s && end > s) {{
          cats.push(cat);
          break;
        }}
      }}
    }}
    const uniqueCats = [...new Set(cats)].sort();
    if (uniqueCats.length === 0) {{
      html += escapeHtml(segment);
    }} else {{
      // Build style
      const colors = uniqueCats.map(c => PALETTE[c] || '#ccc');
      let style;
      if (uniqueCats.length === 1) {{
        style = `background-color: ${{colors[0]}};`;
      }} else {{
        // striped gradient
        const stops = colors.map((c, idx) => `${{c}} ${{(idx/uniqueCats.length)*100}}%, ${{c}} ${{((idx+1)/uniqueCats.length)*100}}%`).join(', ');
        style = `background: linear-gradient(90deg, ${{stops}});`;
      }}
      const title = uniqueCats.join(', ');
      html += `<span class="highlight" style="${{style}}" title="${{escapeHtml(title)}}">${{escapeHtml(segment)}}</span>`;
    }}
  }}
  textArea.innerHTML = html;
}}

// Populate dropdown
for (const cid of CONTRACT_IDS) {{
  const opt = document.createElement('option');
  opt.value = cid;
  opt.textContent = cid;
  select.appendChild(opt);
}}

select.addEventListener('change', () => {{
  renderContract(select.value);
}});

// Load first
if (CONTRACT_IDS.length > 0) {{
  select.value = CONTRACT_IDS[0];
  renderContract(CONTRACT_IDS[0]);
}}
</script>
</body>
</html>
"""

with open(os.path.join(OUT_DIR, 'index.html'), 'w', encoding='utf-8') as f:
    f.write(html_content)

print("Built app/index.html")
print("Contracts:", len(ids))
print("Categories:", len(categories))
