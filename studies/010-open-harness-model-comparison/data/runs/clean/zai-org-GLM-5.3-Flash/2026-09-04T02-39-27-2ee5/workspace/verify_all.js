// Full sweep: verify EVERY contract renders byte-identical text and every
// ground-truth span is exactly covered by correctly-tagged highlights.
const path = require('path');
const fs = require('fs');
const { chromium } = require('playwright');

const HERE = __dirname;
const GT = fs.readFileSync(path.join(HERE, 'contract_ground_truth'), 'utf8')
  .split('\n').filter(l => l.trim()).map(JSON.parse);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('pageerror', e => { console.error('PAGE ERROR:', e.message); process.exit(1); });
  await page.goto('file://' + path.join(HERE, 'index.html'));
  await page.waitForSelector('.contract-item');

  let totalSpans = 0, contractsPresent = 0;
  for (let i = 0; i < GT.length; i++) {
    const rec = GT[i];
    const text = fs.readFileSync(path.join(HERE, 'contract_text', rec.contract_id + '.txt'), 'utf8');
    await page.evaluate(idx => document.querySelectorAll('.contract-item')[idx].click(), i);
    const r = await page.evaluate(() => {
      const container = document.getElementById('contract-text');
      const rendered = container.textContent;
      const hls = [];
      let off = 0;
      const walk = node => {
        for (const child of node.childNodes) {
          if (child.nodeType === 3) off += child.textContent.length;
          else if (child.classList && child.classList.contains('hl')) {
            hls.push({ start: off, end: off + child.textContent.length,
                       cats: child.getAttribute('data-cats').split('\u0001') });
            off += child.textContent.length;
          } else walk(child);
        }
      };
      walk(container);
      const rows = document.querySelectorAll('.cat-row').length;
      return { rendered, hls, rows };
    });
    if (r.rendered !== text) throw new Error(`[${i}] ${rec.contract_id}: rendered text mismatch`);
    let expected = 0;
    for (const [cat, v] of Object.entries(rec.gold)) {
      if (v.is_impossible) continue;
      // Ground truth may contain nested/overlapping spans within a category;
      // the renderer shows their union, so verify the union.
      const ivs = v.spans.slice().sort((a, b) => a[0] - b[0]);
      const union = [];
      for (const [s, e] of ivs) {
        if (union.length && s <= union[union.length - 1][1]) {
          union[union.length - 1][1] = Math.max(union[union.length - 1][1], e);
        } else union.push([s, e]);
      }
      expected += v.spans.length;
      for (const [s, e] of union) {
        const cov = r.hls.filter(h => h.cats.includes(cat) && h.start < e && h.end > s)
                         .sort((a, b) => a.start - b.start);
        if (!cov.length) throw new Error(`[${i}] ${rec.contract_id}: "${cat}" @${s}-${e} not highlighted`);
        let pos = s;
        for (const h of cov) {
          if (h.start < s || h.end > e) throw new Error(`[${i}] "${cat}" @${s}-${e}: highlight leaks @${h.start}-${h.end}`);
          if (h.start !== pos) throw new Error(`[${i}] "${cat}" @${s}-${e}: gap at ${pos}`);
          pos = h.end;
        }
        if (pos !== e) throw new Error(`[${i}] "${cat}" @${s}-${e}: ends at ${pos}`);
      }
    }
    const present = Object.values(rec.gold).filter(v => !v.is_impossible).length;
    if (r.rows !== present) throw new Error(`[${i}] panel rows ${r.rows} != present ${present}`);
    totalSpans += expected;
    if (present > 0) contractsPresent++;
    if ((i + 1) % 100 === 0) console.log(`  ...${i + 1}/510 contracts checked (${totalSpans} spans so far)`);
  }
  await browser.close();
  console.log(`\nFULL SWEEP PASSED: 510/510 contracts, ${contractsPresent} with categories, ${totalSpans} spans verified exactly.`);
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
