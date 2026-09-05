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

### Follow-up: empty thinking blocks (owner-reported, fixed)

pi stores assistant reasoning as `{"type":"thinking","thinking":"...",
"thinkingSignature":"reasoning_content"}` — the payload key is `thinking`,
not `text`. `trace.py` read `text`, so every thinking block rendered empty
(summary said "thinking —" with nothing after it) and SFT/DPO exports
carried empty thinking text. Fixed: `parse_session` reads `thinking` first,
falls back to `text`. Verified: 30/30 thinking blocks non-empty in the
pi/Inkling trace and in the SFT export for that run.

### Follow-up: written-feedback form UX (owner feedback)

The anchor coordinates (JSON) were exposed as a raw input; the anchor-button
flow now shows a human-readable chip ("Anchored to: bash call - msg 3") with
a clear button; manual anchoring (whole run / file / advanced tool-call JSON)
is the fallback row. Existing-feedback list renders human-readable anchors.
Storage schema unchanged (anchor_type + anchor_ref JSONB).

### Follow-up: feedback modal replaces the Feedback tab (owner feedback)

Anchored feedback no longer switches tabs: the trace anchor buttons open an
in-page modal (chip + textarea, Esc/click-outside to close). The run-detail
Feedback tab is removed; existing feedback shows as a compact collapsible
"Run feedback (N)" section at the bottom of the run page (+ run-level add
button); the global /feedback page remains the full log. Manual file/
tool-call anchoring moved into an "advanced" section inside the modal.
Storage schema unchanged.

### Follow-up: broken feedback modal (owner-reported, root-caused, fixed)

Three stacked bugs, all fixed and verified with an automated browser test:
1. Wrong Alpine component: `document.querySelector('[x-data]')` matched the
   sidebar nav's empty `x-data` in base.html, not the run-detail component —
   fbOpen (and the judge poller's judging/judgeStatus) were set on the wrong
   scope. All lookups now go through `#run-detail-root`.
2. Alpine `x-show` + `@click.outside` self-close: the modal existed in the
   DOM while hidden, and the microtask checkpoint after the opening button's
   onclick meant the just-attached document-level outside listener fired for
   the SAME click, closing the modal instantly. Switched to
   `template x-if` (modal absent when closed) and removed @click.outside;
   Esc / ✕ / Cancel close it.
3. Chicken-and-egg with x-if: openFeedbackModal set input values before the
   modal existed. Now opens first, populates fields on the next tick.
Verified end-to-end via Playwright: anchor click opens modal with readable
chip, Esc closes, save persists and appears in the run feedback list.

## Launcher (SPEC 9 addendum)

### What was built
- `app_launcher.py`: in-process manager — temp-copy creation, free-port
  allocation (8450+), `shell=True` subprocess with `PORT`/`BROWSER=/usr/bin/true`
  (suppresses agent apps calling `webbrowser.open()`) /`PYTHONUNBUFFERED=1`,
  1s health-probe polling (60s budget), log tail (last 40 lines), one active
  launch per run, stop with terminate→kill + temp-dir cleanup.
- Launch-command resolution: README fenced-code extraction first, then
  `run.sh` → `app.py`/`server.py`/`main.py` heuristics, then
  `python3 -m http.server <port>` for static-only runs (uniform UX).
  Extracted commands keep their README-declared ports; probe URLs include
  README-declared `localhost:<port>` values.
- Three health modes: `http` (URL probe AND our process alive),
  `desktop` (process alive after 4s grace — GUI opens on host), `static`.
- `launch_events` table + Pydantic mirror + the three endpoints; a module
  -level `event_sink` callback writes rows from the polling thread.
- Preview tab: launch panel for ALL runs (component chips, editable resolved
  command, Launch/Stop/Open app, status badge, log tail), static preview below.

### Test results (real runs)
- `clean/Inkling-Small/02-28-27` (app.py server): resolved `python3 app.py`
  from README; healthy; `GET http://localhost:8765/` → 200. Note: the app
  hardcodes 8765; the allocated port (8450) is recorded but unused by it.
- `clean/GLM-5.3-Flash/02-42-10` (static): resolved `python3 -m http.server
  8000` from README; healthy; serves index.html. Override command
  (`python3 -m http.server 8460`) also verified.
- `pi/Inkling-Small/02-32-35` (visualizer.py + run.sh): resolved
  `python3 visualizer.py` from README; mode `desktop`; the app loaded all
  510 contracts then crashed at GUI init (see environment gap below) —
  launcher reported `failed` with the traceback, as designed. Desktop
  healthy branch verified separately with a long-lived process
  (process-alive → healthy).
- All test launches stopped afterward; no listeners left on 8765/8000.

### Deviations from SPEC 9
1. **desktop mode added** — spec assumed everything is HTTP; one run built a
   tkinter desktop app. Health = process-alive (no URL to probe).
2. **Health requires our process alive** — hardened after observing a false
   positive: a stale `app.py` from the build session was squatting on the
   README-declared port 8765, and the probe mistook it for our launch.
3. **Event-sink wiring bug (found in testing, fixed)**: api.py initially set
   the sink as an instance attribute while `_emit` reads the module global —
   resolution updates never landed. Fixed (`app_launcher.event_sink = ...`).
4. **Orphaned processes on server restart**: launch state is in-memory; if
   uvicorn restarts mid-launch the subprocess keeps running and the Stop
   button can't reach it (must kill manually). Known limitation.
5. **Environment gap (not a launcher bug)**: tkinter is unusable on this
   host — uv-managed Python 3.14 venv lacks Tcl init files; system
   /usr/bin/python3's tkinter requires macOS 26 SDK (host: 16). The desktop
   run therefore cannot be visually reviewed here until one of those is
   fixed (e.g. `brew install python-tk`). Everything except the GUI window
   (data loading, command resolution, health reporting) verified working.

### Safety caveat
Launching executes agent-written code on the host from a temp copy — no
sandbox, same trust level as the agent judge. Original workspace artifacts
are never executed or modified. Documented in README.
# SPEC 10 as-built notes (judge job dashboard)

## Deviations from spec
- `JudgeJobCreate.stub_delay` (int, optional): a testing affordance not in
  the spec — seconds the stub judge sleeps before writing its verdict, so
  pause/cancel are deterministic in tests. Passed to the subprocess env by
  the runner; harmless in real (non-stub) runs.
- Item `skipped` status exists in the schema but is never set by the runner
  (reserved; cancel marks items `cancelled`).
- Pause is graceful by design: the in-flight run finishes (its subprocess
  keeps running; results are recorded); only new items are held. Mid-run
  hard-stop = Cancel. This matches SPEC 10's wording but is worth stating:
  there is no "kill current run but keep queue" control.

## Startup recovery (documented behavior)
On uvicorn startup, `recover_stuck_jobs()` flips any job stuck in `running`
(from a previous dead process — its subprocess died with it) to `paused`,
and its `running` items back to `queued`. The owner resumes deliberately
from the dashboard. The runner thread itself is a daemon started at startup
and after each job creation.

## Limitations
- One job runs at a time (global runner). A paused job releases the runner:
  a different queued job may start; resume re-enters the queue in creation
  order.
- Job state survives page navigation and uvicorn restarts (Postgres), but
  the in-flight SUBPROCESS does not survive a restart — hence the recovery
  behavior above.
- Run detail's per-run judge button still uses the old per-run flow (its
  state lives in run-dir marker files); it does not appear on the
  dashboard. Prefer the dashboard/bulk flow.

### Follow-up: stub-answer cleanup archaeology
During verification, 9 stub answers + 3 jobs were found left over from the
first test run: the test's cleanup imported `db` without the app dir on
sys.path (pytest runs from repo root) — ModuleNotFoundError swallowed by
best-effort cleanup. Fixed: tests insert the app dir into sys.path; cleanup
verified to fully remove stub answers and test jobs.

## Ship decision (2026-09-05)

Shipped as first pass per owner decision: dashboard + job system live,
lifecycle tests red on timing assumptions (see docs/KNOWN_ISSUES.md — the
canonical handoff list, with P1/P2/P3 priorities and fix directions). Test
jobs cleaned; accidental real agent answers kept and documented there.
