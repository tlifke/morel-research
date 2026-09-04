import json, os
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

cid = '2ThemartComInc_19990826_10-12G_EX-10.10_6700288_EX-10.10_Co-Branding Agreement_ Agency Agreement'
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
rebuilt = ''.join(node.get_text() if hasattr(node, 'get_text') else str(node) for node in soup.contents)
# Actually need to reconstruct properly
rebuilt = ''
for node in soup.descendants:
    pass  # simpler: use soup.get_text() but that loses structure; we only need text equality.
# soup.get_text() should equal original if no extra whitespace added by tags
rebuilt = soup.get_text()
print('Rebuilt length:', len(rebuilt), 'Original:', len(text), 'Equal:', rebuilt == text)
spans = soup.find_all('span')
print('Rendered spans:', len(spans))
expected = 0
for cat,v in truth.items():
    if not v['is_impossible']:
        expected += len(v['spans'])
print('Expected ranges:', expected)
# Check titles
missing_title = sum(1 for s in spans if not s.get('title'))
print('Missing title:', missing_title)
