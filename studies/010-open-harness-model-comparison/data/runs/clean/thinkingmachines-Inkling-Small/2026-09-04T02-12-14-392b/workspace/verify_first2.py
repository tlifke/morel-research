import os
from playwright.sync_api import sync_playwright

cid = '2ThemartComInc_19990826_10-12G_EX-10.10_6700288_EX-10.10_Co-Branding Agreement_ Agency Agreement'
with open('contract_text/'+cid+'.txt', 'r', encoding='utf-8') as f:
    text = f.read()
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    page.goto("file://" + os.path.abspath('index.html'))
    page.wait_for_selector('#contractText', timeout=10000)
    page.wait_for_timeout(1000)
    page.select_option('#contractSelect', cid)
    page.wait_for_timeout(500)
    inner = page.inner_text('#contractText')
    browser.close()
print('Inner text length:', len(inner), 'Original:', len(text), 'Equal:', inner == text)
# Find first diff
for i,(a,b) in enumerate(zip(inner, text)):
    if a!=b:
        print('First diff at', i, repr(a), repr(b))
        print('Context inner:', repr(inner[max(0,i-20):i+20]))
        print('Context orig:', repr(text[max(0,i-20):i+20]))
        break
else:
    if len(inner)!=len(text):
        print('Length diff only')
