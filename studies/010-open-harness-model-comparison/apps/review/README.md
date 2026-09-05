# Contract Lab — study 010 review app

Review agent runs, judge them against a rubric (questions-as-data), record
pairwise preferences and anchored written feedback, and export judgment
data in post-training-ready JSON shapes. See `SPEC.md` for the plan and
`docs/AS_BUILT.md` for deviations.

## Run it

```bash
cd studies/010-open-harness-model-comparison/apps/review
docker compose up -d            # postgres:16 on localhost:5433
uv run uvicorn main:app --port 8300   # from this directory
# open http://localhost:8300  → "Import runs" (idempotent)
```

Requires `DATABASE_URL` to point at the compose DB (default matches).
Judge agent additionally needs the pi SDK credentials (HF_TOKEN / tinker
auth) in the environment.

## Judge a run

- UI: Run detail → "Run agent judge" (background; auto-refresh when done),
  then the Judge tab: agree/disagree with agent answers, answer the
  human-only questions, Save.
- CLI: `uv run python agent_judge.py <run_id> [--model provider/id]`
  (requires the app server running).

## Docs

- `docs/DATA_MODEL.md` — tables + mermaid erDiagram (as built)
- `docs/API.md` — every route
- `docs/UI.md` — pages/elements
- `docs/AS_BUILT.md` — deviations from SPEC, bugs found, residual risks
