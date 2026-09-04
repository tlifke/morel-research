#!/usr/bin/env python3
"""End-to-end verification of index.html using headless Chromium."""
import json
import os
import random
from playwright.sync_api import sync_playwright

HERE = os.path.dirname(os.path.abspath(__file__))
URL = "file://" + os.path.join(HERE, "index.html")

gold = {}
order = []
with open(os.path.join(HERE, "contract_ground_truth"), encoding="utf-8") as f:
    for line in f:
        if line.strip():
            rec = json.loads(line)
            gold[rec["contract_id"]] = rec["gold"]
            order.append(rec["contract_id"])

# pick a deterministic sample: first, last, a few random, plus find one with overlapping spans
def spans_overlap(g):
    sp = [tuple(s) for info in g.values() for s in info["spans"]]
    sp.sort()
    return any(sp[i][1] > sp[i+1][0] for i in range(len(sp)-1) if sp[i][1] > sp[i+1][0] and sp[i][0] <= sp[i+1][0])

overlap_ids = [cid for cid in order if spans_overlap(gold[cid])]
print(f"contracts with overlapping spans: {len(overlap_ids)}")

sample = {order[0], order[-1], order[250]} | set(random.Random(42).sample(order, 4)) | set(overlap_ids[:3])
sample = [cid for cid in order if cid in sample]

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1500, "height": 1000})
    console_errors = []
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: console_errors.append(str(e)))
    page.goto(URL)
    page.wait_for_selector("#contract-list li", timeout=60000)

    n = page.evaluate("contracts.length")
    print(f"loaded contracts in app: {n}")
    assert n == 510, f"expected 510, got {n}"
    assert page.evaluate("DATA.categories.length") == 41

    total_marks = 0
    for cid in sample:
        idx = page.evaluate(f"byId.get({json.dumps(cid)})")
        page.evaluate(f"select({idx})")
        page.wait_for_timeout(150)

        # check header shows the right contract
        shown = page.text_content("#contract-name").strip()
        assert shown == cid, (shown, cid)

        g = gold[cid]
        expected = {c: len(i["spans"]) for c, i in g.items() if not i["is_impossible"]}
        absent = {c for c, i in g.items() if i["is_impossible"]}

        # category panel: counts of present/absent chips
        got_present, got_absent = page.evaluate("""(() => {
            const present = {}, absent = [];
            document.querySelectorAll('.cat-chip').forEach(ch => {
                const name = ch.querySelector('.cat-name').textContent;
                if (ch.classList.contains('absent')) absent.push(name);
                else present[name] = parseInt(ch.querySelector('.count').textContent);
            });
            return [present, absent];
        })()""")
        if got_present != expected:
            errors.append((cid, "category counts mismatch", expected, got_present))
        if set(got_absent) != absent:
            errors.append((cid, "absent set mismatch"))

        # highlights in text: per data-cat (multi-cat marks list cats joined by |)
        got_spans = page.evaluate("""(() => {
            const out = {};
            document.querySelectorAll('#contract-text mark.hl').forEach(m => {
                const cats = m.dataset.cat.split('|');
                cats.forEach(c => { out[c] = (out[c] || 0) + 1; });
            });
            return out;
        })()""")
        # overlapping segments mean a category with k overlapping spans may yield
        # more than k marks; verify via segment reconstruction instead: recompute
        # union coverage from DOM marks and compare with expected union coverage.
        marks = page.evaluate("""(() => [...document.querySelectorAll('#contract-text mark.hl')]
            .map(m => ({cats: m.dataset.cat, text: m.textContent})))()""")
        total_marks += len(marks)

        # rebuild coverage set per category from DOM
        text = page.evaluate(f"contracts[byId.get({json.dumps(cid)})].text")
        # compute offsets of each mark by walking the DOM in order
        offsets = page.evaluate("""(() => {
            const res = [];
            const pre = document.querySelector('#contract-text');
            let pos = 0;
            for (const node of pre.childNodes) {
                if (node.nodeType === 3) { pos += node.textContent.length; }
                else if (node.nodeType === 1) {
                    const len = node.textContent.length;
                    res.push({cat: node.dataset.cat, s: pos, e: pos + len, text: node.textContent});
                    pos += len;
                }
            }
            return res;
        })()""")

        # expected coverage per category from ground truth
        def coverage(span_list):
            cov = set()
            for s, e in span_list:
                cov.update(range(s, e))
            return cov

        got_cov = {}
        for m in offsets:
            for c in m["cat"].split("|"):
                got_cov.setdefault(c, set()).update(range(m["s"], m["e"]))

        expected_cov = {c: coverage(i["spans"]) for c, i in g.items() if not i["is_impossible"]}
        if set(got_cov) != set(expected_cov):
            errors.append((cid, "coverage categories mismatch", set(expected_cov) ^ set(got_cov)))
        for c in expected_cov:
            if got_cov.get(c) != expected_cov[c]:
                errors.append((cid, f"coverage mismatch for {c}"))

        # verify every expected span string is rendered: the DOM segments of that
        # category must exactly tile [s,e) and concatenate to the gold span text
        for c, i in g.items():
            if i["is_impossible"]:
                continue
            segs = [(m["s"], m["e"], m["text"]) for m in offsets if c in m["cat"].split("|")]
            for s, e in i["spans"]:
                tile = sorted(x for x in segs if x[0] < e and x[1] > s)
                ok = tile and tile[0][0] == s and tile[-1][1] == e and all(
                    tile[j][1] == tile[j + 1][0] for j in range(len(tile) - 1))
                if not ok or "".join(t[2] for t in tile) != text[s:e]:
                    errors.append((cid, f"span of {c} not rendered as highlight", text[s:e][:60]))

    print(f"sample size: {len(sample)}, total marks rendered: {total_marks}")

    # UI interactions: search, next button, chip click, toggle
    page.fill("#search", "distributor")
    page.wait_for_timeout(200)
    visible = page.evaluate("[...document.querySelectorAll('#contract-list li')].filter(li => li.style.display !== 'none').length")
    print(f"search 'distributor' -> {visible} visible")
    assert visible > 0 and visible < 510

    page.fill("#search", "")
    cur = page.evaluate("current")
    page.click("#prev")
    page.click("#next")
    assert page.evaluate("current") == cur
    assert page.text_content("#progress").strip() == f"{cur + 1} / 510"

    # chip click scrolls to a highlight
    first_chip = page.evaluate("catChips.findIndex(c => c.present)")
    page.evaluate(f"catChips[{first_chip}].el.click()")
    page.wait_for_timeout(200)
    marks_after = page.evaluate("document.querySelectorAll('#contract-text mark.hl').length")
    assert marks_after > 0

    # toggle highlights off/on
    page.uncheck("#show-all")
    dim = page.evaluate("document.querySelectorAll('#contract-text mark.hl.dim').length")
    assert dim == marks_after
    page.check("#show-all")

    # screenshot for visual check
    page.evaluate("select(0)")
    page.wait_for_timeout(200)
    page.screenshot(path=os.path.join(HERE, "verification_screenshot.png"), full_page=False)

    if console_errors:
        errors.append(("console", console_errors[:5]))
    browser.close()

if errors:
    print("FAILURES:")
    for e in errors:
        print(" ", e)
    raise SystemExit(1)
print("ALL CHECKS PASSED")
