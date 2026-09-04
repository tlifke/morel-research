// Smoke test for the sweep-line highlight algorithm used in index.html.
// Verifies, for all 510 contracts:
//   1. highlight segments + plain segments tile the contract text exactly
//   2. every ground-truth span is fully covered by highlight segments
//      that include its category
import fs from 'fs';

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

// Sweep algorithm, copied verbatim from index.html's renderContract (minus DOM).
function render(text, present) {
  const events = [];
  present.forEach(({ cat, spans }) => {
    for (const [a, b] of spans) {
      const s = Math.max(0, Math.min(a, text.length));
      const e = Math.max(s, Math.min(b, text.length));
      if (e > s) { events.push([s, 1, cat]); events.push([e, -1, cat]); }
    }
  });
  events.sort((x, y) => x[0] - y[0] || (y[1] - x[1]));
  const parts = [];
  let pos = 0;
  let active = new Map();
  for (const [off, delta, cat] of events) {
    if (off > pos) {
      const chunk = text.slice(pos, off);
      if (active.size) {
        parts.push(['HL', [...active.keys()], chunk]);
      } else {
        parts.push(['TXT', null, chunk]);
      }
      pos = off;
    }
    if (delta === 1) active.set(cat, (active.get(cat) || 0) + 1);
    else { const n = (active.get(cat) || 0) - 1; if (n <= 0) active.delete(cat); else active.set(cat, n); }
  }
  if (pos < text.length) parts.push(['TXT', null, text.slice(pos)]);
  return parts;
}

eval(fs.readFileSync('data.js', 'utf8').replace('window.', 'globalThis.window=globalThis.window||{};window.'));
const { contracts, gold } = window.CONTRACT_DATA;

let totalHL = 0, totalSpans = 0, fails = 0, maxOverlap = 0;
for (const c of contracts) {
  const g = gold[c.id] || {};
  const present = [];
  for (const cat of Object.keys(g)) {
    const d = g[cat];
    if (!d.is_impossible && d.spans.length) present.push({ cat, spans: d.spans });
  }
  const parts = render(c.text, present);

  // 1) tiling
  const joined = parts.map(p => p[2]).join('');
  if (joined !== c.text) { fails++; console.log('TILE FAIL', c.id); }

  // 2) span coverage
  for (const { cat, spans } of present) {
    for (const [a, b] of spans) {
      totalSpans++;
      let covered = 0, ok = true, p = 0;
      for (const [kind, cats, chunk] of parts) {
        const s = p, e = p + chunk.length;
        const ov = Math.min(e, b) - Math.max(s, a);
        if (ov > 0) {
          if (!(kind === 'HL' && cats.includes(cat))) ok = false;
          covered += ov;
          if (kind === 'HL') maxOverlap = Math.max(maxOverlap, cats.length);
        }
        p = e;
      }
      if (!ok || covered !== (b - a)) {
        fails++;
        console.log('SPAN FAIL', c.id, cat, a, b, covered);
      }
    }
  }
  totalHL += parts.filter(p => p[0] === 'HL').length;
}
console.log(`contracts: ${contracts.length}, highlight segments: ${totalHL}, ` +
  `spans checked: ${totalSpans}, max overlapping categories on one segment: ${maxOverlap}, failures: ${fails}`);
if (fails) process.exit(1);
