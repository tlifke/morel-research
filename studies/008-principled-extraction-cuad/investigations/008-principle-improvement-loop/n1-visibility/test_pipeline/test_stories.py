from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    page = p.chromium.launch().new_page()
    page.goto("file://" + __import__("os").path.abspath("studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop/n1-visibility/test_pipeline/view_iteration2.html"))
    # (1) Contract + prompt visible
    page.click("text=3 Contract text")
    assert "SPONSORSHIP AGREEMENT" in page.inner_text("#pinned")
    page.click("text=2 Prompt snippet")
    assert "intermediate/snippet" in page.inner_text("#pinned")
    # (2) Compare LLM output vs ground truth
    page.click("text=4 Compare — input")
    assert "step2" in page.inner_text("#pinned")
    page.click("text=5 Compare — LLM output")
    # (3) Principles proposed
    page.click("text=8 Derive — principle proposal")
    assert "derived-001" in page.inner_text("#pinned")
    # (4) Output changed due to principles (pre vs post)
    page.click("text=10 Test — pre vs post")
    print("All 4 stories pass: contract/prompt visible, compare accessible, principles shown, test/pre-post linkable.")
