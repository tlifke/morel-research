Session reference — pipeline visibility app (n1-visibility)
Files: view_iteration2.html (app), app_design.md, iteration2.md, loop_scripts/, intermediate/
Run: cd test_pipeline; python3 -m http.server 8765; open localhost:8765/view_iteration2.html
Interaction: click cards 1-10; pinned header + detail pane load via fetch()
User stories verified: (1) contract/prompt cards, (2) compare LLM/ground truth (4/5), (3) principles (8/9), (4) pre/post (10 via step4/test sources)
Validation: Playwright PASS, 15,710 chars full contract loaded at card 3; all cards now have fetch targets.
