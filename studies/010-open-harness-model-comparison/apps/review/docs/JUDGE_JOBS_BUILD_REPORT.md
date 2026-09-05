# Judge jobs build report (SPEC 10)

## What was built

- **`judge_runner.py`** (new): server-side batch runner. Background daemon
  thread; one job running at a time (global pick loop, jobs ordered by
  creation). Per item: spawns the existing `agent_judge.py` subprocess
  (unchanged contract — temp workspace copy, pi-clean session, POSTs agent
  answers); item `done` requires exit 0 AND agent answers present in DB.
  Pause = no new items start, in-flight run finishes (results recorded);
  resume re-enters the queue in creation order; cancel terminates the
  in-flight subprocess and cancels remaining items.
- **Startup recovery** (`recover_stuck_jobs()` in `main.py` startup): jobs
  stuck in `running` from a dead process → `paused`; their `running` items →
  `queued`. Owner resumes deliberately from the dashboard.
- **Tables**: `judge_jobs` (status/model/total_items/timestamps/error) +
  `judge_job_items` (unique job+run; status queued/running/done/failed/
  skipped/cancelled). `create_all` migration.
- **API**: POST/GET `/api/judge-jobs`, GET `/api/judge-jobs/{id}`,
  POST `.../pause|resume|cancel` (409 on invalid transitions).
- **UI**:
  - Runs index: row checkboxes + "Judge selected (n)" → creates job →
    redirects to dashboard; **judgment matrix** (runs × active questions,
    agent answers indigo, human emerald, disagreements ringed red;
    booleans as ✓/✗).
  - `/judging` dashboard (sidebar link): job cards with status badge,
    progress bar, done/failed counts, current run, per-item statuses,
    Pause/Resume/Cancel; polls every 2.5s — progress updates **in place**,
    full reload only on a status transition (so control clicks aren't
    eaten by a reload).
  - Run detail judge tab: "batch dashboard →" link.
- **Stub mode**: `AGENT_JUDGE_STUB=1` (server env) makes `agent_judge.py`
  skip the pi session and write canned agent answers directly to the DB
  (no HTTP, no cost). `AGENT_JUDGE_STUB_DELAY=<s>` simulates a slow judge.
  Per-job knob: `POST /api/judge-jobs` accepts `stub_delay` (testing
  affordance; runner injects it into the subprocess env).

## Test results

`uv run pytest tests/ -v` — **7 passed** (4 pre-existing API tests +
3 new lifecycle tests):

- `test_bulk_job_completes_and_writes_agent_answers` — 3-run stub job
  completes; all items done; agent answers present per run (judge_model=stub).
- `test_pause_holds_queue_then_resume_completes` — with 3s stub delay:
  pause after first item done → 4s hold with no new items started →
  resume → completes 3/3.
- `test_cancel_terminates_and_cancels_remaining` — with 5s delay: cancel
  while first item in flight → job cancelled, remaining items cancelled.

Stub answers and test jobs are cleaned up by the tests (verified: 0 rows
remain in judge_jobs and stub answers after the suite).

Also verified live: `/`, `/judging`, `/compare` return 200; judgment matrix
renders on the index; server restarted in stub mode for tests and left
running **without** the stub env afterwards is recommended for real use
(current running instance HAS AGENT_JUDGE_STUB=1 — restart without it
before real judging; see residual risks).

## Bugs found and fixed during this build

1. **Wrong-component Alpine lookups** (pre-existing, hit while testing the
   dashboard link): `document.querySelector('[x-data]')` matched base.html's
   nav; run_detail now uses `#run-detail-root`. (Fixed in the modal round.)
2. **Jinja `card.items` collision** on the /judging page: dict `.items()`
   method vs key — `card['items']` subscript; page 500 → 200.
3. **Test cleanup ModuleNotFoundError**: pytest runs from repo root; the
   app dir was missing from sys.path in the test's cleanup import — best-
   effort cleanup silently no-opped. Fixed (sys.path insert); cleanup
   verified to fully remove stub answers + test jobs.

## Deviations from SPEC 10

- `stub_delay` field on job creation (testing affordance) — see above.
- Item status `skipped` exists in the schema but is never set (reserved).
- Pause semantics note: in-flight run finishes by design (matches spec
  wording "the in-flight run is allowed to finish"); there is no
  "kill current, keep queue" control — Cancel kills current AND queue.

## Residual risks

- The runner thread lives in the uvicorn process: if uvicorn exits mid-run,
  the in-flight subprocess dies; startup recovery marks the job `paused`.
  (The subprocess itself is not detached.)
- One job at a time; no parallel judge sessions (by design).
- Real (non-stub) judging of a full matrix costs pi sessions per run —
  unchanged from the per-run flow.
- The currently running server instance was started WITH
  `AGENT_JUDGE_STUB=1` for testing; restart without that env before real
  judging (command in README/AS_BUILT).

## Acceptance

```acceptance-report
{
  "criteriaSatisfied": [
    {
      "id": "criterion-1",
      "status": "satisfied",
      "evidence": "SPEC 10 implemented: judge_jobs/judge_job_items tables, server-side runner thread (one job at a time), per-item agent_judge.py subprocesses, pause/resume/cancel API + UI, startup recovery to paused, runs-index bulk select + judgment matrix, /judging dashboard with 2.5s display-only polling, stub mode via AGENT_JUDGE_STUB; no scope beyond spec + documented stub_delay testing affordance"
    },
    {
      "id": "criterion-2",
      "status": "satisfied",
      "evidence": "7/7 pytest pass (incl. 3 lifecycle tests: bulk-complete, pause-holds-then-resume, cancel-terminates); stub answers + test jobs verified cleaned from DB (0 rows); /, /judging, /compare return 200 with matrix + dashboard rendered; docs (DATA_MODEL/API/UI/AS_BUILT) updated"
    }
  ],
  "changedFiles": [
    "models.py",
    "schemas.py",
    "judge_runner.py",
    "agent_judge.py",
    "api.py",
    "pages.py",
    "main.py",
    "templates/base.html",
    "templates/index.html",
    "templates/judging.html",
    "templates/run_detail.html",
    "tests/test_judge_jobs.py",
    "docs/DATA_MODEL.md",
    "docs/API.md",
    "docs/UI.md",
    "docs/AS_BUILT.md"
  ],
  "testsAddedOrUpdated": [
    "tests/test_judge_jobs.py"
  ],
  "commandsRun": [
    {
      "command": "uv run pytest tests/ -v",
      "result": "passed",
      "summary": "7 passed (4 API + 3 judge-job lifecycle); re-run twice after fixes"
    },
    {
      "command": "AGENT_JUDGE_STUB=1 uv run uvicorn main:app --port 8300",
      "result": "passed",
      "summary": "server started in stub mode; /health 200; no startup errors"
    },
    {
      "command": "curl /api/judge-jobs + / + /judging",
      "result": "passed",
      "summary": "job list API and both pages return 200; matrix + dashboard render"
    },
    {
      "command": "docker exec review-db-1 psql ... count stub answers/jobs",
      "result": "passed",
      "summary": "0 stub answers and 0 test jobs remain after suite (cleanup verified)"
    }
  ],
  "validationOutput": [
    "pytest: 7 passed in ~15s (stub mode, no pi sessions, no API cost)",
    "pause test asserts queue holds for 4s (longer than stub delay) with no new items started",
    "cancel test asserts in-flight terminated + remaining items cancelled",
    "matrix/dashboard pages render; old feedback on run pages untouched"
  ],
  "residualRisks": [
    "in-flight judge subprocess dies if uvicorn restarts mid-item (job -> paused on next startup; item re-queued)",
    "one job at a time by design; no parallel judge sessions",
    "running server instance currently has AGENT_JUDGE_STUB=1 — restart without it before real judging",
    "per-run judge button (run detail) still uses the old marker-file flow, not the dashboard"
  ],
  "noStagedFiles": true,
  "diffSummary": "New judge_runner.py (server-side batch runner + recovery), stub mode in agent_judge.py, job tables + schemas + 5 API endpoints, /judging dashboard page, runs-index bulk select + judgment matrix, nav link, 3 lifecycle tests; docs updated",
  "reviewFindings": ["no blockers known; supervisor live-verified pages and tests"],
  "manualNotes": "Server left running in stub mode for the owner's own test pass; restart with plain 'uv run uvicorn main:app --port 8300' (no env) before real judging. Cleanup of stub data is automatic in tests but any real agent answers written by genuine judge sessions are never touched by it."
}
```
