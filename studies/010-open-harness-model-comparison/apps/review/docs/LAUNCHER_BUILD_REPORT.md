# Launcher build report (SPEC 9 addendum)

## What was built

- **`app_launcher.py`** (new): in-process launch manager. Temp-copy creation
  (`shutil.copytree`, `__pycache__` excluded), free-port allocation (8450–8499),
  `shell=True` subprocess with `PORT` + `BROWSER=/usr/bin/true` (suppresses
  agent apps calling `webbrowser.open()`) + `PYTHONUNBUFFERED=1`, 1s health
  polling (60s budget), 40-line log tail, one active launch per run, stop
  with terminate→kill + temp-dir cleanup.
- **Command resolution**: README fenced-code extraction first, then `run.sh`,
  then `app.py`/`server.py`/`main.py`, then static fallback
  (`python3 -m http.server <allocated port>`). README-declared
  `localhost:<port>` values become additional health-probe URLs.
- **Three health modes**: `http` (URL probe AND our process alive at
  resolution), `desktop` (process alive after 4s grace — GUI opens on host;
  added beyond spec because one run built a tkinter app), `static`.
- **`launch_events` table** + Pydantic (`LaunchStart`, `LaunchEventOut`,
  `LaunchStatus`) + endpoints `POST /launch`, `GET /launch/status`,
  `POST /launch/stop`. Resolution updates land via a module-global
  `event_sink` callback written from the polling thread (own DB session).
- **Preview tab**: launch panel on every run — component chips
  (frontend/backend/database), editable auto-resolved command, Launch/Stop/
  Open app ↗ buttons, status badge, live log tail; static preview below.
- **Docs**: DATA_MODEL.md (mermaid + table section), API.md (3 endpoints),
  AS_BUILT.md (Launcher section), README safety note.

## Test results (real runs, per acceptance bar)

| Run | Command resolved | Result |
|---|---|---|
| `clean/Inkling-Small/02-28-27` (app.py) | `python3 app.py` (README) | ✅ healthy; `GET http://localhost:8765/` → 200. App hardcodes 8765; allocated port recorded but unused by the app. |
| `clean/GLM-5.3-Flash/02-42-10` (static) | `python3 -m http.server 8000` (README) | ✅ healthy; serves index.html. Explicit override (`http.server 8460`) also verified. |
| `pi/Inkling-Small/02-32-35` (visualizer.py + run.sh) | `python3 visualizer.py` (README) | ⚠️ mode `desktop`; app loaded all 510 contracts, then crashed at GUI init — **tkinter is broken on this host** (see residual risks). Launcher reported `failed` with the traceback, as designed. Desktop healthy branch verified separately (long-lived process → healthy). |

All test launches stopped afterward; no listeners remain on 8765/8000; no
visualizer processes remain.

## Bugs found during testing (fixed)

1. **False-positive health on squatted ports**: a stale `app.py` from the
   build session was listening on README-declared port 8765; the probe
   marked our launch healthy although our process had died on bind failure.
   Health now additionally requires our process alive at resolution.
2. **Event-sink wiring**: api.py set the sink as an instance attribute
   (`launch_manager.event_sink`) while `_emit` reads the module global —
   resolution updates never reached the DB. Fixed (`app_launcher.event_sink = ...`).

## Deviations from SPEC 9

- `desktop` mode added (spec assumed all apps are HTTP).
- Health resolution requires our process alive (hardening; spec silent).
- Launch state is in-memory: if uvicorn restarts mid-launch, the subprocess
  is orphaned and Stop can't reach it (manual kill required). Known limitation.

## Residual risks

- Launching executes agent-written code on the host from a temp copy —
  unsandboxed, same trust level as the agent judge. Documented in README.
- tkinter unusable on this host (uv venv lacks Tcl; system python tkinter
  requires macOS 26 SDK, host is 16) — the desktop run cannot be visually
  reviewed until fixed (e.g. `brew install python-tk`). All non-GUI behavior
  (resolution, data loading, health reporting) verified working.
- Extracted commands may bind hardcoded README ports (e.g. 8765); a second
  concurrent launch of the same app would fail on bind — surfaced in the log
  tail, not silently swallowed.

## Acceptance

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "app_launcher.py + launch_events table + 3 API endpoints + Preview-tab launch panel implemented per SPEC 9; tested against all three real run types (http server run healthy on 8765 with 200 response, static run serving index.html via http.server, desktop run resolved from README with process-alive health model; tkinter GUI itself blocked by a host environment gap documented in AS_BUILT); all test launches stopped, no leftover listeners; docs updated (DATA_MODEL mermaid + table, API.md, AS_BUILT, README)"
    }
  ],
  "changedFiles": [
    "apps/review/app_launcher.py",
    "apps/review/models.py",
    "apps/review/schemas.py",
    "apps/review/api.py",
    "apps/review/templates/run_detail.html",
    "apps/review/docs/DATA_MODEL.md",
    "apps/review/docs/API.md",
    "apps/review/docs/AS_BUILT.md",
    "apps/review/README.md"
  ],
  "testsAddedOrUpdated": [],
  "commandsRun": [
    { "command": "POST /api/runs/2026-09-04T02-28-27-3cd3/launch (app.py run) + status + GET url", "result": "passed", "summary": "resolved 'python3 app.py' from README, healthy, GET http://localhost:8765/ -> 200" },
    { "command": "POST /api/runs/2026-09-04T02-42-10-0173/launch (static run) + status + GET url", "result": "passed", "summary": "resolved 'python3 -m http.server 8000' from README, healthy, serves index.html; override command also verified" },
    { "command": "POST /api/runs/2026-09-04T02-32-35-7733/launch (visualizer.py desktop run)", "result": "passed", "summary": "resolved 'python3 visualizer.py' from README, mode desktop; app loaded 510 contracts then crashed at tkinter init (host env gap); launcher reported failed with traceback; desktop healthy branch verified separately" },
    { "command": "docker exec review-db-1 psql -c 'SELECT ... FROM launch_events'", "result": "passed", "summary": "6+ events recorded; healthy resolution lands in DB after event-sink wiring fix" },
    { "command": "pkill/stop endpoints + lsof port checks", "result": "passed", "summary": "all test launches stopped; no listeners on 8765/8000; no visualizer processes" }
  ],
  "validationOutput": [
    "ast.parse syntax checks on all modified python files: OK",
    "uvicorn serves /health ok after restart; launch_events table auto-created via create_all",
    "Playwright not used; verification via curl + psql + direct python unit check of desktop health branch"
  ],
  "residualRisks": [
    "agent-written code executes on the host unsandboxed (temp copy; documented in README + AS_BUILT)",
    "launch state is in-memory: uvicorn restart mid-launch orphans the subprocess (manual kill required)",
    "tkinter unusable on this host (uv venv lacks Tcl; system python tkinter requires macOS 26 SDK) — the desktop run cannot be visually reviewed here"
  ],
  "noStagedFiles": true,
  "diffSummary": "new launcher subsystem: app_launcher.py manager (temp-copy launches, port allocation, http/desktop/static health modes), launch_events table + schemas + 3 endpoints with event-sink DB writer, Preview-tab launch panel UI, docs updated (DATA_MODEL/API/AS_BUILT/README)",
  "reviewFindings": [
    "no blockers; two self-found bugs fixed during testing (squatted-port false positive, event-sink wiring) and documented"
  ],
  "manualNotes": "desktop run cannot be visually reviewed on this host until tkinter works (brew install python-tk or fix uv venv); suggestion recorded in AS_BUILT"
}
```
