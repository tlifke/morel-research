import os, json, html

# Load ground truth
truth = {}
with open('contract_ground_truth', 'r', encoding='utf-8') as f:
    for line in f:
        line=line.strip()
        if not line:
            continue
        d=json.loads(line)
        cid = d['contract_id']
        truth[cid] = d['gold']

# Load texts
texts = {}
for fn in os.listdir('contract_text'):
    if not fn.endswith('.txt'):
        continue
    cid = fn[:-4]
    with open(os.path.join('contract_text', fn), 'r', encoding='utf-8') as f:
        texts[cid] = f.read()

# Verify all contracts present
missing = [cid for cid in texts if cid not in truth]
if missing:
    print('Missing truth for', len(missing))
missing2 = [cid for cid in truth if cid not in texts]
if missing2:
    print('Missing text for', len(missing2))
print('Contracts loaded:', len(texts))

# Write HTML
out = open('index.html', 'w', encoding='utf-8')

# Header
out.write('''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Contract Visualization</title>
<style>
  body { font-family: system-ui, -apple-system, sans-serif; margin: 20px; background: #f8f9fa; color: #212529; }
  h1 { font-size: 1.5rem; margin-bottom: 0.5rem; }
  .toolbar { background: #fff; padding: 12px 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 16px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
  select { font-size: 1rem; padding: 6px 10px; border-radius: 6px; border: 1px solid #ced4da; min-width: 420px; }
  .badge { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 9999px; font-size: 0.85rem; font-weight: 500; color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); }
  .info { background: #fff; padding: 12px 16px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); margin-bottom: 12px; }
  .info h2 { margin: 0 0 6px; font-size: 1.1rem; word-break: break-all; }
  .contract { background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 0.95rem; line-height: 1.45; white-space: pre-wrap; word-break: break-word; overflow-x: auto; }
  .contract span { border-radius: 2px; padding: 0 1px; box-decoration-break: clone; -webkit-box-decoration-break: clone; }
  .label { margin-top: 12px; font-weight: 600; color: #495057; }
</style>
</head>
<body>
<h1>Contract Highlight Viewer</h1>
<div class="toolbar">
  <label for="contractSelect"><strong>Select contract:</strong></label>
  <select id="contractSelect"></select>
  <span id="countInfo" style="font-size:0.95rem;color:#495057;"></span>
</div>
<div class="info" id="infoPanel" style="display:none;">
  <h2 id="contractTitle"></h2>
  <div id="badges"></div>
</div>
<div class="label">Contract text (highlights match ground-truth spans):</div>
<div class="contract" id="contractText"></div>

<script>
const DATA_TEXTS = ''')

# Write texts as JSON
out.write(json.dumps(texts, ensure_ascii=False))

out.write(''';
const DATA_TRUTH = ''')
out.write(json.dumps(truth, ensure_ascii=False))
out.write(''';

function escapeHtml(s) {
  return s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function hslToHex(h,s,l) {
  s /= 100; l /= 100;
  const k = n => (n + h/30) % 12;
  const a = s * Math.min(l, 1-l);
  const f = n => l - a * Math.max(-1, Math.min(k(n)-3, Math.min(9-k(n), 1)));
  const r = Math.round(f(0)*255), g = Math.round(f(8)*255), b = Math.round(f(4)*255);
  return "#" + ((1<<24)+(r<<16)+(g<<8)+b).toString(16).slice(1);
}

// Generate palette for 41 categories
const CATS = [
  "Affiliate License-Licensee","Affiliate License-Licensor","Agreement Date","Anti-Assignment","Audit Rights",
  "Cap On Liability","Change Of Control","Document Name","Effective Date","Expiration Date",
  "Governing Law","Joint Ip Ownership","License Grant","Non-Compete","Non-Transferable License",
  "Notice Period To Terminate Renewal","Parties","Post-Termination Services","Renewal Term",
  "Revenue/Profit Sharing","Uncapped Liability","Termination","Warranty","Indemnification",
  "Confidentiality","Non-Disparagement","Non-Solicit","Assignment","Choice Of Law",
  "Jurisdiction","Dispute Resolution","Limitation Of Liability","No Liability","Force Majeure",
  "Insurance","Representations","Warranties","Post-Termination Obligations","Termination For Cause",
  "Termination For Convenience","Renewal Options","Most Favored Customer","Exclusivity","No Assignment"
];
// Actually categories exact names from data; let's build from truth dynamically
const ALL_CATS = new Set();
for (const c in DATA_TRUTH) {
  const gold = DATA_TRUTH[c];
  for (const cat in gold) ALL_CATS.add(cat);
}
const CAT_LIST = Array.from(ALL_CATS).sort();
const CAT_COLOR = {};
CAT_LIST.forEach((cat, i) => {
  const h = Math.round((i / Math.max(CAT_LIST.length - 1, 1)) * 340);
  CAT_COLOR[cat] = hslToHex(h, 75, 82);
});

function getContracts() {
  return Object.keys(DATA_TEXTS).sort();
}

function buildHighlights(text, gold) {
  const events = [];
  for (const cat in gold) {
    const info = gold[cat];
    if (info.is_impossible) continue;
    for (const span of info.spans) {
      if (!Array.isArray(span) || span.length < 2) continue;
      const s = span[0], e = span[1];
      if (typeof s === 'number' && typeof e === 'number') {
        events.push({p: s, delta: 1, cat: cat});
        events.push({p: e, delta: -1, cat: cat});
      }
    }
  }
  events.sort((a,b) => {
    if (a.p !== b.p) return a.p - b.p;
    return a.delta - b.delta; // ends (-1) before starts (+1)
  });
  const active = new Set();
  const segments = [];
  let pos = 0;
  let i = 0;
  while (i < events.length) {
    const p = events[i].p;
    if (p > pos) {
      if (active.size > 0) {
        segments.push({start: pos, end: p, cats: Array.from(active).sort()});
      }
    }
    // process all events at p
    while (i < events.length && events[i].p === p) {
      if (events[i].delta === 1) active.add(events[i].cat);
      else active.delete(events[i].cat);
      i++;
    }
    pos = p;
  }
  if (pos < text.length && active.size > 0) {
    segments.push({start: pos, end: text.length, cats: Array.from(active).sort()});
  }
  return segments;
}

function renderContract(id) {
  const text = DATA_TEXTS[id];
  const gold = DATA_TRUTH[id];
  const infoPanel = document.getElementById('infoPanel');
  const title = document.getElementById('contractTitle');
  const badges = document.getElementById('badges');
  const container = document.getElementById('contractText');
  if (!text) {
    container.textContent = 'Contract not found.';
    infoPanel.style.display = 'none';
    return;
  }
  infoPanel.style.display = 'block';
  title.textContent = id;

  const present = [];
  for (const cat in gold) {
    if (!gold[cat].is_impossible) present.push(cat);
  }
  present.sort();
  document.getElementById('countInfo').textContent = 'Present categories: ' + present.length + ' / ' + CAT_LIST.length;

  badges.innerHTML = '';
  for (const cat of present) {
    const b = document.createElement('span');
    b.className = 'badge';
    b.style.backgroundColor = CAT_COLOR[cat] || '#888';
    b.textContent = cat + ' (' + gold[cat].spans.length + ')';
    b.title = 'Spans: ' + gold[cat].spans.length;
    badges.appendChild(b);
  }

  const segments = buildHighlights(text, gold);
  // Build HTML
  let html = '';
  let last = 0;
  for (const seg of segments) {
    if (seg.start > last) {
      html += escapeHtml(text.slice(last, seg.start));
    }
    const cats = seg.cats;
    const colors = cats.map(c => CAT_COLOR[c] || '#888');
    // Use first color for background, blend could be complex; just use first with opacity and border for others
    const bg = colors[0];
    const titleText = cats.join(', ');
    html += '<span style="background-color:' + bg + ';' + (cats.length > 1 ? 'outline:2px dashed #333;' : '') + '" title="' + escapeHtml(titleText) + '">' + escapeHtml(text.slice(seg.start, seg.end)) + '</span>';
    last = seg.end;
  }
  if (last < text.length) {
    html += escapeHtml(text.slice(last));
  }
  container.innerHTML = html;
}

function init() {
  const sel = document.getElementById('contractSelect');
  const ids = getContracts();
  for (const id of ids) {
    const opt = document.createElement('option');
    opt.value = id;
    opt.textContent = id;
    sel.appendChild(opt);
  }
  if (ids.length > 0) {
    sel.value = ids[0];
    renderContract(ids[0]);
  }
  sel.addEventListener('change', () => renderContract(sel.value));
}

init();
</script>
</body>
</html>
''')

out.close()
print('index.html written', os.path.getsize('index.html'))
