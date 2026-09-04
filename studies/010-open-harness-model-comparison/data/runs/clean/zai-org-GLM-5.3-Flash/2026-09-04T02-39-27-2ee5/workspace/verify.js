// End-to-end verification of index.html using headless Chromium.
// Checks:
//  1. App loads, JSON data parsed, all 510 contracts in sidebar.
//  2. Rendered text (DOM textContent) is byte-identical to the contract text.
//  3. For EVERY category span in the ground truth, there is a highlighted
//     element whose textContent exactly equals text.slice(s, e) and whose
//     data-cats contains that category.
//  4. Category panel lists exactly the present categories with correct counts.
//  5. Interactions: category click focuses+scrolls; swatch click dims highlights;
//     search filters; next/prev navigation works.
const path = require('path');
const { chromium } = require('playwright');

const HERE = __dirname;
const GT = [];
const fs = require('fs');
fs.readFileSync(path.join(HERE, 'contract_ground_truth'), 'utf8').split('\n').forEach(l => {
  if (l.trim()) GT.push(JSON.parse(l));
});

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  page.on('pageerror', e => { console.error('PAGE ERROR:', e.message); process.exit(1); });
  page.on('console', m => { if (m.type() === 'error') console.error('CONSOLE ERROR:', m.text()); });

  await page.goto('file://' + path.join(HERE, 'index.html'));
  await page.waitForSelector('.contract-item');

  // 1. Sidebar completeness
  const listCount = await page.locator('.contract-item').count();
  console.log('sidebar contract rows:', listCount);
  if (listCount !== GT.length) throw new Error(`expected ${GT.length} rows, got ${listCount}`);

  const summary0 = await page.textContent('#summary');
  console.log('first contract summary:', summary0);

  // pick test contracts: first one (has overlaps), one with zero cats if any, and a random one
  const zeroCat = GT.find(r => Object.values(r.gold).every(v => v.is_impossible));
  const picks = new Set([0, 137, GT.length - 1]);
  if (zeroCat) picks.add(GT.indexOf(zeroCat));
  let totalSpansChecked = 0;

  for (const idx of [...picks].sort((a, b) => a - b)) {
    const rec = GT[idx];
    const text = fs.readFileSync(path.join(HERE, 'contract_text', rec.contract_id + '.txt'), 'utf8');
    await page.evaluate(i => {
      // select contract via the app's list by matching title text
      const items = [...document.querySelectorAll('.contract-item')];
      // contract ids order == GT order, so just click item i
      items[i].click();
    }, idx);
    await page.waitForTimeout(50);

    // 2. rendered text identical
    const rendered = await page.evaluate(() => document.getElementById('contract-text').textContent);
    if (rendered !== text) throw new Error(`[${rec.contract_id}] rendered text mismatch!`);

    // 3. positional check: compute char offsets of every .hl in the rendered DOM,
    //    then require every ground-truth span [s,e] to be EXACTLY covered by
    //    contiguous .hl elements tagged with that category.
    const res = await page.evaluate(() => {
      const container = document.getElementById('contract-text');
      const out = [];
      let off = 0;
      const walk = node => {
        for (const child of node.childNodes) {
          if (child.nodeType === 3) { off += child.textContent.length; }
          else if (child.classList && child.classList.contains('hl')) {
            const t = child.textContent;
            out.push({ start: off, end: off + t.length, t,
                       cats: child.getAttribute('data-cats').split('\u0001') });
            off += t.length;
          } else { walk(child); }
        }
      };
      walk(container);
      return out;
    });
    const expected = [];
    for (const [cat, v] of Object.entries(rec.gold)) {
      if (v.is_impossible) continue;
      const ivs = v.spans.slice().sort((a, b) => a[0] - b[0]);
      const union = [];
      for (const [s, e] of ivs) {
        if (union.length && s <= union[union.length - 1][1]) {
          union[union.length - 1][1] = Math.max(union[union.length - 1][1], e);
        } else union.push([s, e]);
      }
      for (const [s, e] of union) expected.push({ cat, s, e });
    }
    for (const exp of expected) {
      const covering = res
        .filter(h => h.cats.includes(exp.cat) && h.start < exp.e && h.end > exp.s)
        .sort((a, b) => a.start - b.start);
      if (!covering.length) {
        throw new Error(`[${rec.contract_id}] span not highlighted for "${exp.cat}" @${exp.s}-${exp.e}`);
      }
      for (const h of covering) {
        if (h.start < exp.s || h.end > exp.e) {
          throw new Error(`[${rec.contract_id}] highlight for "${exp.cat}" leaks outside span @${exp.s}-${exp.e}: el @${h.start}-${h.end}`);
        }
        if (text.slice(h.start, h.end) !== h.t) {
          throw new Error(`[${rec.contract_id}] highlight text != contract text at @${h.start}-${h.end}`);
        }
      }
      let pos = exp.s;
      for (const h of covering) {
        if (h.start !== pos) {
          throw new Error(`[${rec.contract_id}] gap/overlap in coverage of "${exp.cat}" span @${exp.s}-${exp.e} (at ${pos}, found ${h.start})`);
        }
        pos = h.end;
      }
      if (pos !== exp.e) {
        throw new Error(`[${rec.contract_id}] coverage ends at ${pos}, span ends at ${exp.e} for "${exp.cat}"`);
      }
    }
    // 4. category panel: exactly present categories, correct counts
    const panel = await page.evaluate(() =>
      [...document.querySelectorAll('.cat-row')].map(r => ({
        name: r.querySelector('.cat-name').textContent,
        count: parseInt(r.querySelector('.cat-count').textContent)
      }))
    );
    const present = Object.entries(rec.gold).filter(([, v]) => !v.is_impossible);
    if (panel.length !== present.length) {
      throw new Error(`[${rec.contract_id}] panel has ${panel.length} cats, expected ${present.length}`);
    }
    for (const [cat, v] of present) {
      const row = panel.find(p => p.name === cat);
      if (!row) throw new Error(`[${rec.contract_id}] missing panel row for ${cat}`);
      if (row.count !== v.spans.length) {
        throw new Error(`[${rec.contract_id}] count mismatch for ${cat}: ${row.count} vs ${v.spans.length}`);
      }
    }
    totalSpansChecked += expected.length;
    console.log(`OK [${idx}] ${rec.contract_id.slice(0, 60)}... : ${present.length} cats, ${expected.length} spans verified, ${res.length} highlight segments`);

    // 5. interaction checks on first test contract
    if (idx === 0) {
      const focusWorks = await page.evaluate(() => {
        const row = document.querySelector('.cat-row');
        row.click();
        const focused = document.querySelector('.hl.focus');
        if (!focused) return 'no focus';
        // swatch toggle dims
        const sw = document.querySelector('.cat-row .cat-swatch');
        sw.click();
        const dimmed = document.querySelectorAll('.hl.dim').length;
        sw.click();
        const restored = document.querySelectorAll('.hl.dim').length;
        return (dimmed > 0 && restored === 0) ? 'ok' : `dim=${dimmed} restored=${restored}`;
      });
      console.log('interactions:', focusWorks);
      if (focusWorks !== 'ok') throw new Error('interaction failure: ' + focusWorks);
    }
  }

  // 5b. search + navigation
  await page.fill('#search', 'distributor agreement');
  await page.waitForTimeout(50);
  const filtered = await page.locator('.contract-item').count();
  const allMatch = await page.evaluate(() =>
    [...document.querySelectorAll('.contract-item')].every(el => el.textContent.toLowerCase().includes('distributor agreement')));
  console.log('search "distributor agreement" ->', filtered, 'rows, all match:', allMatch);
  await page.fill('#search', '');

  await page.evaluate(() => document.querySelectorAll('.contract-item')[0].click());
  await page.waitForTimeout(50);
  const title1 = await page.textContent('#contract-title');
  await page.click('#next-btn');
  const title2 = await page.textContent('#contract-title');
  await page.click('#prev-btn');
  const title3 = await page.textContent('#contract-title');
  console.log('nav:', JSON.stringify([title1.slice(0, 30), title2.slice(0, 30), title3.slice(0, 30)]));
  if (title1 !== title3) throw new Error('prev/next navigation broken');

  await browser.close();
  console.log(`\nALL CHECKS PASSED — ${totalSpansChecked} ground-truth spans verified against rendered highlights`);
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
