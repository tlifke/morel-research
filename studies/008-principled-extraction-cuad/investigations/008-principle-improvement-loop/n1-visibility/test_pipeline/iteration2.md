Plan — lightweight reusable web app (not static generator, not terminal/desktop).
Why: multi-contract, multi-iteration ingestion; static HTML requires rebuild per run.
Layout: pinned header (contract + prompt), sidebar cards (10 steps + principle/gap summary), right pane (compare/diagnose/derive/test details + reasoning).
Source data: loop_scripts/ (step1-4) + test_pipeline/ intermediate/final.
Reusability: app ingests loop outputs per contract; no per-run script updates.
Next: view_iteration2.html scaffold / app entry.
