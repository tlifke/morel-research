#!/usr/bin/env python3
"""Local contract visualization server. Run: python3 app.py"""
import json
import os
import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

PORT = 8765
BASE = os.path.dirname(os.path.abspath(__file__))
CONTRACT_DIR = os.path.join(BASE, "contract_text")
GT_PATH = os.path.join(BASE, "contract_ground_truth")

# Load ground truth once
with open(GT_PATH, "r", encoding="utf-8") as f:
    GROUND_TRUTH = {}
    for line in f:
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        cid = rec["contract_id"]
        GROUND_TRUTH[cid] = rec["gold"]

CONTRACT_IDS = sorted(GROUND_TRUTH.keys())

# Generate a palette of 41 distinct colors (pastel backgrounds / dark borders)
CATEGORY_NAMES = sorted({cat for gold in GROUND_TRUTH.values() for cat in gold})
# In case categories vary by record, take union; but ground truth has all 41 per record likely.
# Ensure we have exactly the categories present.
PALETTE = {}
for i, cat in enumerate(CATEGORY_NAMES):
    hue = int(i * (360 / max(len(CATEGORY_NAMES), 1)))
    # Pastel background
    bg = f"hsl({hue}, 75%, 85%)"
    # Darker border/text
    border = f"hsl({hue}, 80%, 45%)"
    PALETTE[cat] = {"bg": bg, "border": border, "hex": f"#{int(hue/360*255):02x}{int(0.75*255):02x}{int(0.85*255):02x}"}
    # Actually let's use simple HSL strings directly in CSS.
    PALETTE[cat] = {"bg": f"hsl({hue}, 70%, 88%)", "border": f"hsl({hue}, 85%, 40%)"}

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Contract Highlight Viewer</title>
<style>
  :root { --bg: #f7f8fa; --panel: #ffffff; --text: #1a1a2e; --border: #d1d5db; --accent: #2563eb; }
  * { box-sizing: border-box; }
  body { margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); }
  header { background: linear-gradient(90deg, #1e3a8a, #2563eb); color: white; padding: 1rem 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }
  header h1 { margin: 0; font-size: 1.4rem; letter-spacing: -0.02em; }
  header p { margin: 0.25rem 0 0; opacity: 0.9; font-size: 0.9rem; }
  .container { max-width: 1400px; margin: 0 auto; padding: 1rem; display: grid; grid-template-columns: 1fr 320px; gap: 1rem; }
  @media (max-width: 1000px) { .container { grid-template-columns: 1fr; } }
  .card { background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }
  .toolbar { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.75rem; }
  select { font-size: 0.95rem; padding: 0.35rem 0.6rem; border-radius: 8px; border: 1px solid var(--border); background: #fff; min-width: 420px; max-width: 100%; }
  .stats { font-size: 0.85rem; color: #4b5563; margin-left: auto; }
  .text-area { background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 1rem; overflow: auto; max-height: 78vh; line-height: 1.6; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; font-size: 0.85rem; white-space: pre-wrap; word-break: break-word; }
  .text-area .segment { padding: 0 1px; border-radius: 2px; }
  .text-area .segment:hover { outline: 1px dashed rgba(255,255,255,0.35); }
  .legend { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .legend-item { display: inline-flex; align-items: center; gap: 0.35rem; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 999px; padding: 0.2rem 0.6rem; font-size: 0.8rem; }
  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; border: 1px solid rgba(0,0,0,0.15); }
  .category-list { max-height: 70vh; overflow-y: auto; }
  .cat-row { display: flex; align-items: center; gap: 0.6rem; padding: 0.45rem 0.4rem; border-bottom: 1px solid #f3f4f6; }
  .cat-row:last-child { border-bottom: none; }
  .cat-row .swatch { width: 16px; height: 16px; border-radius: 4px; border: 1px solid rgba(0,0,0,0.15); flex-shrink: 0; }
  .cat-row .label { font-weight: 600; font-size: 0.88rem; }
  .cat-row .count { margin-left: auto; font-size: 0.8rem; color: #6b7280; }
  .empty-state { color: #6b7280; font-style: italic; padding: 0.5rem 0; }
</style>
</head>
<body>
<header>
  <h1>Contract Span Visualizer</h1>
  <p>Select a contract to see categories and highlighted spans inside the text.</p>
</header>
<div class="container">
  <main>
    <div class="card">
      <div class="toolbar">
        <label for="contractSelect" style="font-weight:600;font-size:0.95rem;">Contract:</label>
        <select id="contractSelect"><option value="">Choose a contract…</option></select>
        <span class="stats" id="stats"></span>
      </div>
      <div id="textArea" class="text-area">Select a contract to begin.</div>
    </div>
  </main>
  <aside>
    <div class="card">
      <h2 style="margin-top:0;font-size:1rem;">Categories Present</h2>
      <div id="categoryList" class="category-list"><div class="empty-state">No contract selected.</div></div>
    </div>
  </aside>
</div>
<script>
const COLORS = {};  // injected below
const CATEGORY_NAMES = []; // injected below
</script>
<script>
/* Injected data */
{"COLORS": "COLORS_PLACEHOLDER", "CATS": "CATS_PLACEHOLDER"}
</script>
<script>
// Replace placeholders with actual JSON
const raw = document.querySelector('script:nth-of-type(3)').textContent;
const parsed = JSON.parse(raw.replace('{"COLORS": "COLORS_PLACEHOLDER", "CATS": "CATS_PLACEHOLDER"}', '{}'));
// Actually let's do simpler: serve colors directly via script tag
</script>
</body>
</html>
"""

# Instead of complicated injection, build HTML in Python with format

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Contract Highlight Viewer</title>
<style>
  :root {{ --bg: #f7f8fa; --panel: #ffffff; --text: #1a1a2e; --border: #d1d5db; --accent: #2563eb; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; background: var(--bg); color: var(--text); }}
  header {{ background: linear-gradient(90deg, #1e3a8a, #2563eb); color: white; padding: 1rem 1.5rem; box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
  header h1 {{ margin: 0; font-size: 1.4rem; letter-spacing: -0.02em; }}
  header p {{ margin: 0.25rem 0 0; opacity: 0.9; font-size: 0.9rem; }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 1rem; display: grid; grid-template-columns: 1fr 340px; gap: 1rem; }}
  @media (max-width: 1000px) {{ .container {{ grid-template-columns: 1fr; }} }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .toolbar {{ display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 0.75rem; }}
  select {{ font-size: 0.95rem; padding: 0.35rem 0.6rem; border-radius: 8px; border: 1px solid var(--border); background: #fff; min-width: 480px; max-width: 100%; }}
  .stats {{ font-size: 0.85rem; color: #4b5563; margin-left: auto; }}
  .text-area {{ background: #0f172a; color: #e2e8f0; border-radius: 8px; padding: 1rem; overflow: auto; max-height: 78vh; line-height: 1.65; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; font-size: 0.85rem; white-space: pre-wrap; word-break: break-word; }}
  .text-area .segment {{ padding: 0 1px; border-radius: 2px; transition: outline 0.05s; }}
  .text-area .segment:hover {{ outline: 1px dashed rgba(255,255,255,0.35); }}
  .category-list {{ max-height: 70vh; overflow-y: auto; }}
  .cat-row {{ display: flex; align-items: center; gap: 0.6rem; padding: 0.45rem 0.4rem; border-bottom: 1px solid #f3f4f6; }}
  .cat-row:last-child {{ border-bottom: none; }}
  .cat-row .swatch {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid rgba(0,0,0,0.15); flex-shrink: 0; }}
  .cat-row .label {{ font-weight: 600; font-size: 0.88rem; }}
  .cat-row .count {{ margin-left: auto; font-size: 0.8rem; color: #6b7280; }}
  .empty-state {{ color: #6b7280; font-style: italic; padding: 0.5rem 0; }}
  .legend {{ display: flex; flex-wrap: wrap; gap: 0.4rem; margin-top: 0.5rem; }}
  .legend-item {{ display: inline-flex; align-items: center; gap: 0.35rem; background: #f3f4f6; border: 1px solid #e5e7eb; border-radius: 999px; padding: 0.2rem 0.6rem; font-size: 0.75rem; }}
  .dot {{ width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; border: 1px solid rgba(0,0,0,0.15); }}
</style>
</head>
<body>
<header>
  <h1>Contract Span Visualizer</h1>
  <p>Select a contract to see categories present and every highlighted span inside the text.</p>
</header>
<div class="container">
  <main>
    <div class="card">
      <div class="toolbar">
        <label for="contractSelect" style="font-weight:600;font-size:0.95rem;">Contract:</label>
        <select id="contractSelect"><option value="">Choose a contract…</option></select>
        <span class="stats" id="stats"></span>
      </div>
      <div id="textArea" class="text-area">Select a contract from the dropdown to begin.</div>
    </div>
  </main>
  <aside>
    <div class="card">
      <h2 style="margin-top:0;font-size:1rem;">Categories Present</h2>
      <div id="categoryList" class="category-list"><div class="empty-state">No contract selected.</div></div>
      <div id="legend" class="legend"></div>
    </div>
  </aside>
</div>
<script>
const COLORS = /*COLORS_JSON*/{};
</script>
<script>
const CONTRACT_IDS = /*IDS_JSON*/[];
const select = document.getElementById('contractSelect');
CONTRACT_IDS.forEach(id => {{
  const opt = document.createElement('option');
  opt.value = id; opt.textContent = id; select.appendChild(opt);
}});

select.addEventListener('change', async () => {{
  const cid = select.value;
  const textArea = document.getElementById('textArea');
  const catList = document.getElementById('categoryList');
  const stats = document.getElementById('stats');
  if (!cid) {{ textArea.textContent = 'Select a contract from the dropdown to begin.'; catList.innerHTML = '<div class="empty-state">No contract selected.</div>'; stats.textContent = ''; return; }}
  textArea.textContent = 'Loading…';
  try {{
    const resp = await fetch('/contract?cid=' + encodeURIComponent(cid));
    if (!resp.ok) throw new Error('Failed to load');
    const data = await resp.json();
    // Render text with highlights
    const text = data.text;
    const categories = data.categories; // {cat: {spans: [[s,e],...]}}
    // Build segments from all spans
    const intervals = [];
    for (const [cat, info] of Object.entries(categories)) {{
      for (const span of info.spans) {{
        intervals.push({{start: span[0], end: span[1], cat}});
      }}
    }}
    const boundaries = new Set();
    boundaries.add(0);
    boundaries.add(text.length);
    for (const iv of intervals) {{ boundaries.add(iv.start); boundaries.add(iv.end); }}
    const sortedBounds = Array.from(boundaries).sort((a,b)=>a-b);
    // Build HTML segments
    let html = '';
    let last = 0;
    for (let i = 0; i < sortedBounds.length - 1; i++) {{
      const s = sortedBounds[i];
      const e = sortedBounds[i+1];
      const slice = text.slice(s, e);
      const cats = [];
      for (const iv of intervals) {{
        if (iv.start <= s && iv.end >= e) cats.push(iv.cat);
      }}
      // Escape HTML
      const safe = slice.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      if (cats.length === 0) {{
        html += '<span class="segment">' + safe + '</span>';
      }} else {{
        // Nested spans for each category (outer to inner)
        let inner = safe;
        for (let j = cats.length - 1; j >= 0; j--) {{
          const cat = cats[j];
          const style = `background:${{COLORS[cat].bg}}; border-left:3px solid ${{COLORS[cat].border}}; padding:0 1px;`;
          const title = cat + (cats.length > 1 ? ' (plus others)' : '');
          inner = `<span class="segment" style="${{style}}" title="${{title.replace(/"/g,'&quot;')}}">${{inner}}</span>`;
        }}
        html += inner;
      }}
    }}
    textArea.innerHTML = html;
    // Category list
    const presentCats = Object.keys(categories).sort();
    if (presentCats.length === 0) {{
      catList.innerHTML = '<div class="empty-state">No categories present.</div>';
    }} else {{
      catList.innerHTML = presentCats.map(cat => {{
        const spans = categories[cat].spans;
        return `<div class="cat-row"><div class="swatch" style="background:${{COLORS[cat].bg}}; border-color:${{COLORS[cat].border}};"></div><div class="label">${{cat.replace(/</g,'&lt;').replace(/>/g,'&gt;')}}</div><div class="count">${{spans.length}} span${{spans.length===1?'':'s'}}</div></div>`;
      }}).join('');
    }}
    stats.textContent = `${{presentCats.length}} categories • ${{Object.values(categories).reduce((a,v)=>a+v.spans.length,0)}} spans • ${{text.length.toLocaleString()}} chars`;
    document.getElementById('legend').innerHTML = presentCats.map(cat => `<div class="legend-item"><div class="dot" style="background:${{COLORS[cat].bg}}; border-color:${{COLORS[cat].border}};"></div><span>${{cat}}</span></div>`).join('');
  }} catch (e) {{
    textArea.textContent = 'Error: ' + e.message;
    catList.innerHTML = '<div class="empty-state">Error loading data.</div>';
  }}
}});
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # suppress default logging to keep terminal clean
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/":
            colors_json = {}
            for cat in CATEGORY_NAMES:
                colors_json[cat] = PALETTE.get(cat, {"bg": "#e5e7eb", "border": "#9ca3af"})
            html = HTML_TEMPLATE.replace("/*COLORS_JSON*/{}", json.dumps(colors_json)).replace("/*IDS_JSON*/[]", json.dumps(CONTRACT_IDS))
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(html.encode("utf-8"))
            return

        if path == "/contracts":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(CONTRACT_IDS).encode("utf-8"))
            return

        if path == "/contract":
            cid = query.get("cid", [None])[0]
            if not cid or cid not in GROUND_TRUTH:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error":"not found"}).encode())
                return
            # Read text file
            fname = os.path.join(CONTRACT_DIR, cid + ".txt")
            try:
                with open(fname, "r", encoding="utf-8") as f:
                    text = f.read()
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error":str(e)}).encode())
                return
            gold = GROUND_TRUTH[cid]
            categories = {}
            for cat, info in gold.items():
                if not info.get("is_impossible", True):
                    categories[cat] = {"spans": info.get("spans", [])}
            payload = {"contract_id": cid, "text": text, "categories": categories}
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        # 404
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not found")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def run():
    server = HTTPServer(("", PORT), Handler)
    url = f"http://localhost:{PORT}/"
    print(f"Serving at {url}")
    print("Opening browser automatically...")
    try:
        webbrowser.open(url, new=2)
    except Exception:
        pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()

if __name__ == "__main__":
    run()
