# AS BUILT — deviations from SPEC.md, bugs found, and notes

## Deviations from spec

1. **Test dependency added**: `httpx` (via `uv add`) — used both for the
   judge's API POSTs (SPEC 5) and for self-tests. It was not in the SPEC 1
   dependency list. `requests` was NOT added (httpx already chosen).
2. **`/api/runs/{id}/judge` + `/api/runs/{id}/judge/status`**: the spec
   listed the agent-judge CLI + a UI button but no HTTP endpoints; the UI
   button needed a server-side trigger + status polling, so two endpoints
   were added (background `subprocess.Popen` + pid/done-marker files in the
   run dir). This is the only state the app writes outside Postgres.
3. **`/api/runs/{id}/preview-file`**: not in the SPEC 4 endpoint list; added
   to serve the App preview tab (images + CSP-sandboxed HTML). Distinct
   from `/files/content`, which keeps a 2MB display cap — preview-file
   deliberately has **no size cap** because agent-built apps may inline the
   entire dataset (observed: a 510-contract single-file HTML app).
4. **UI runs-index filters**: SPEC 6.1 lists condition/model/tag filters;
   the UI renders all runs unfiltered (filters exist as API query params
   only). Deferred as low-value for 9 runs — noted, not forgotten.
5. **Judge model default** is `tinker/thinkingmachines/Inkling-Small` per
   owner decision; configurable via `agent_judge.py --model`.
6. **`main.py` uses `@app.on_event("startup")`** for `create_all` —
   deprecated in newer FastAPI in favor of lifespan handlers. Works fine on
   the installed version; flagged for future cleanup.
7. **Pydantic export models** (`ExportSFT`, `ExportDPOPair`,
   `ExportRewardScore`) exist in `schemas.py` per SPEC 3.4, but the export
   endpoints return plain dicts (constructed to the same shapes) rather
   than serializing through the models — the trace message payloads are
   free-form and would fail strict models. Shapes are identical; enforcement
   is not.
8. **Added after external review** (reviewer found these undocumented):
   - SPEC 6.3 "suggested pairs" on the Compare page (same-model/different-
     condition, same-condition/different-model quick-pairs) is NOT
     implemented — plain dropdowns only.
   - SPEC 6.4 question edit/deactivate UI is NOT implemented — PATCH
     /api/questions/{id} exists; the page has create only.
   - SPEC 6.2 "code-highlighted viewer" is NOT implemented — Files viewer
     is a plain `<pre>`.
   - SFT/DPO exports originally emitted truncated toolResults (the UI
     display truncation leaked into exports). **Fixed**: `parse_session`
     now takes `truncate=` and exports pass `truncate=False` (exact trace
     per SPEC 7).
   - DPO `prompt` originally omitted the system message. **Fixed**: the
     system prompt from the run's `pi-clean-experiment` custom entry is
     now prepended to the DPO prompt (SPEC 7 shape).
   - Self-tests for acceptance criteria 5 & 6 were originally throwaway.
     **Fixed**: persisted as `tests/test_api.py` (answered_by 403,
     path-traversal 403s; skips when the server isn't running).

## Bugs found during self-test (all fixed)

1. **Jinja cannot construct Python `set()`** in templates — runs index
   500'd. Fixed by precomputing per-run answer sets into view rows.
2. **Judge couldn't parse the verdict JSON** the model embedded in its final
   message: the model embeds raw unescaped quotes (e.g. curl output) inside
   evidence strings, so prose-JSON is unreliable. Fixed in two steps:
   robust extraction (balanced-brace scan + per-question salvage regex) AND
   — the real fix — changing the judge prompt to write `VERDICT.json` via
   the write tool, whose escaping is structural. Extraction now tries
   VERDICT.json → balanced scan → salvage, and reports which source was used.
3. **Judge fidelity bug**: the temp workspace copy originally excluded
   `contract_text/` + `contract_ground_truth` (copy size); the judged app
   legitimately needs its dataset, so it failed to launch and the agent
   correctly reported `launches_at_all=false` for an app that works. Fixed:
   full copytree. (First judge round is preserved in
   `/var/folders/.../contractlab-judge-6i0r2cs7*` as evidence.)
4. **Unhandled `CalledProcessError`** in `agent_judge.py` when the node
   runner fails — produced a raw traceback and no `judge.done` marker.
   Fixed: caught, marker written with the error.
5. **UI button hazard (observed during screenshots)**: an automation click
   intended for the "Judge" tab hit "Run agent judge" and spawned a stray
   judge process. Killed it; answers survived (upsert). Tab screenshots
   retaken with exact-text locators. No code change — but note the header
   button and the Judge tab are easy to confuse; consider a confirm dialog.

## Environment notes

- Docker Desktop daemon was not running at start; `open -a Docker` fixed it.
- Postgres 16 via `docker compose up -d` (port 5433); healthy.
- Playwright (for screenshots) came from the global npm install
  (`/Users/tylerlifke/.npm-global/lib/node_modules/playwright`) — not added
  to any package.json; screenshot scripts are throwaway (`/tmp/shoot*.mjs`).

## Residual risks

- The agent judge runs a model with bash access inside a **temp copy** of
  the workspace; nothing sandboxes it from the wider filesystem. A path
  audit runs post-hoc (violations appended to the answer evidence). Judge
  prompts are fixed in code.
- `judge.done`/`judge.pid`/`judge.log` are written into the run dir (source
  data tree); they are additive files and do not modify originals.
- No authentication on the app or the API; intended for local use only.
- Exports are JSON shapes only — Tinker `Datum` conversion (rendering,
  masks, effort conditioning) happens outside this app by design.

## Post-review fixes applied (owner + reviewer findings, verified live)

- MAJOR fixed: nested-file paths in Files/Preview tabs (relative-prefix
  threading in run_detail.html).
- MAJOR fixed: persisted tests/test_api.py (answered_by 403, 3 traversal
  cases) — passing against the live server; pytest added as dev dep.
- Fixed: SFT/DPO exports now emit the exact (untruncated) trace;
  DPO prompt includes the system prompt event.
- Fixed: judge_status tolerant of corrupt judge.done; parent log fd closed
  after Popen.
- Documented (not implemented, owner-approved scope): suggested compare
  pairs, question edit UI, code highlighting.
- Live verification: import (9 runs, 5 questions seeded), human judgment
  round-trip (both-question agree + q4 + q5), comparison + written-feedback
  round-trips, all 4 export endpoints, tests green. Note: a stale uvicorn
  from the build session initially served old code on :8300 — kill stale
  processes before verifying (lesson recorded here).

## Owner feedback round 1 (post first use)

- `fulfills_well` changed from int_1_5 (Likert) to **bool y/n** — owner's
  call; the seed in importer.py and the live DB row both updated.
- All answer inputs are now styled **Yes/No buttons** (Tailwind peer
  styling), including the agent-`both` questions. The explicit
  agree/disagree radio was removed: the human value is pre-selected from
  the agent answer (default-agree), and agreement is derivable by comparing
  human vs agent rows. `int_1_5` and `text` renderers remain for generic
  future questions.
- Thinking blocks were present in all 9 traces (8-32 per run) but rendered
  as bare collapsed summaries — summary now includes a text preview so
  they're visibly there.
- Owner verification data cleared (3 human answers, 1 comparison, 1
  written-feedback row). The worker's agent-judge test output on run
  2026-09-04T02-28-27-3cd3 (3 agent answers with evidence) is real data
  and was kept.
