from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    page.goto("file://" + __import__('os').path.abspath('index.html'))
    page.wait_for_selector('#contractText', timeout=10000)
    page.wait_for_timeout(1000)
    # Choose first contract for variety
    page.select_option('#contractSelect', '2ThemartComInc_19990826_10-12G_EX-10.10_6700288_EX-10.10_Co-Branding Agreement_ Agency Agreement')
    page.wait_for_timeout(500)
    page.screenshot(path='contract_screenshot.png', full_page=True)
    browser.close()
    print('Screenshot saved')
