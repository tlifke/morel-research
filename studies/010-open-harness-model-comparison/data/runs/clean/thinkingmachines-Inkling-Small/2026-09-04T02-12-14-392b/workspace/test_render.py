from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1200, "height": 900})
    page.goto("file://" + __import__('os').path.abspath('index.html'))
    page.wait_for_selector('#contractText', timeout=10000)
    # Wait a bit for rendering
    page.wait_for_timeout(2000)
    # Select second contract maybe
    page.select_option('#contractSelect', 'ABILITYINC_06_15_2020-EX-4.25-SERVICES AGREEMENT')
    page.wait_for_timeout(500)
    # Take screenshot for verification
    page.screenshot(path='verify_screenshot.png', full_page=True)
    # Check that some span elements exist
    spans = page.query_selector_all('#contractText span')
    print('Span count:', len(spans))
    # Check that text is present
    text_content = page.inner_text('#contractText')
    print('Text length:', len(text_content))
    browser.close()
