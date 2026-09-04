import json, os, re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def main():
    cid = 'ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT'
    with open('contract_text/'+cid+'.txt', 'r', encoding='utf-8') as f:
        text = f.read()
    with open('contract_ground_truth', 'r', encoding='utf-8') as f:
        truth = None
        for line in f:
            d = json.loads(line)
            if d['contract_id'] == cid:
                truth = d['gold']
                break
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1200, "height": 900})
        page.goto("file://" + os.path.abspath('index.html'))
        page.wait_for_selector('#contractText', timeout=10000)
        page.wait_for_timeout(1000)
        page.select_option('#contractSelect', cid)
        page.wait_for_timeout(500)
        html = page.inner_html('#contractText')
        browser.close()
    soup = BeautifulSoup(html, 'html.parser')
    rebuilt = ''
    highlights = []
    for node in soup.contents:
        if isinstance(node, str):
            rebuilt += node
        else:
            rebuilt += node.get_text()
            # approximate range using rebuilt length before this node? Better to pair with original text
    # Actually to verify precisely, we can parse the original text and find spans that are wrapped.
    # Since text inside spans is exact substring, we can find them by scanning rebuilt text and matching with original.
    # But rebuilt may have extra whitespace? It shouldn't.
    # Let's just check rebuilt equals original text.
    print('Rebuilt equals original:', rebuilt == text)
    # Count spans
    spans = soup.find_all('span')
    print('Rendered spans:', len(spans))
    # Verify each span text is present in original and has a title (category info)
    missing_title = 0
    for s in spans:
        txt = s.get_text()
        if txt not in text:
            print('Span text missing!', txt[:200])
        title = s.get('title')
        if not title:
            missing_title += 1
    print('Spans missing title:', missing_title)
    # Check that all non-impossible spans are represented
    expected_spans = []
    for cat, info in truth.items():
        if not info['is_impossible']:
            for span_range in info['spans']:
                expected_spans.append((span_range[0], span_range[1], cat))
    # We can approximate coverage: count how many expected ranges have their text present as a span.
    # For simplicity, check that number of rendered spans >= number of expected ranges (some overlaps may reduce count)
    print('Expected range count:', len(expected_spans))
    # Check that all category badges appear

if __name__ == '__main__':
    main()
