# KNOWN ISSUES — Contract Lab, first-pass ship (2026-09-05)

State at ship: judge-job dashboard functional end-to-end (jobs create, run,
pause mid-batch, complete; matrix + bulk select live). Lifecycle TESTS are
red on timing assumptions. This document is the handoff list — owner
prioritizes what moves to the next agent.

## P1 — Judge subprocess cold start (~30s per item)

**Symptom**: stub items (3s canned work) took ~30s each; lifecycle tests
time out at 15–60s assumptions.
**Root cause (confirmed by code read)**: NOT the runner loop (poll intervals
are 0.5s). Each item spawns a fresh `agent_judge.py` which pays the full
import cost of the pi/SDK stack every time (~25–30s).
**Why it matters**: every real judged run carries a ~30s dead tax; bulk
judging N runs pays it N times; any timeout-based test or UI assumption
built against "fast judge" will break.
**Fix direction**: measure first (time a bare `import` of the judge's SDK
path). Then either (a) keep a warm long-lived judge worker process that
handles items over stdin/stdout, or (b) restructure agent_judge to defer
heavy imports until after the stub short-circuit, or (c) batch items into
one process per job.
**Also**: raise the lifecycle tests' timeouts to measured reality in the
meantime, or they stay red and teach everyone to ignore red.

## P1 — Test/production path divergence

The stub writes answers **directly to the DB**; the real judge **POSTs to
the API**. So the green test suite never exercises the production code path
(parsing, evidence extraction, HTTP round-trip, partial-failure handling).
The one real end-to-end data point is the worker's single manual run.
**Fix direction**: stub should go through the same POST path (or the runner
should verify answers through one shared code path). Real-path integration
test gated behind an env flag/cost ack.

## P2 — Answer provenance

Answers carry `judge_model` but not *how/why* they were created. The 9 real
agent answers written by accidental test runs are indistinguishable from
deliberate dashboard judgments. For future training data this is an
integrity gap.
**Fix direction**: `answers.created_via` ('job', 'manual-run',
'accident-recovered') + `job_id` FK nullable on answers; surface in the
matrix/exports.

## P2 — Schema migrations are manual

`create_all` does not ALTER existing tables — the `stub` column already
required a hand-run ALTER, and psql multi-statement `-c` transactions
rolled one back silently (cost an hour). Any schema change will hit this.
**Fix direction**: introduce Alembic (or at minimum a startup check that
compares models to DB and refuses to boot on drift).

## P2 — Process lifecycle on server restart

Launcher state is in-memory: uvicorn restart mid-launch orphans the app
subprocess (documented). Judge subprocesses die with the parent but their
jobs only recover to `paused` at next startup (good), and the launcher has
no janitor.
**Fix direction**: pidfiles + startup sweep that kills orphaned launch
processes; or move launcher to detached process groups with a registry
table.

## P3 — Pause/cancel race windows

Pause is honored between items only; cancel during the "subprocess exited,
verifying answers in DB" window can mark an item cancelled while its
answers were already written (partial state). Untested.
**Fix direction**: make item terminal-state transition idempotent and
verify-after-cancel (if answers landed, record done-with-note).

## P3 — Config surface

Behavior toggles are scattered: server env (stub historically), per-job
fields (stub, stub_delay, model), hardcoded ports/polls. The stub accident
came from exactly this.
**Fix direction**: single settings object, logged at startup ("running in
REAL judging mode; stub available per-job"), so mode is visible at a glance.

## P3 — Security posture (pre-deploy blockers only)

App executes agent-written code unsandboxed (launcher + judge) and has no
auth. Fine for local single-user; **blockers for any deployment**. If
deploying: auth first, then sandbox (container per launch — see pi's
containerization docs), then expose.

## Non-issues (checked, fine)

- Runner poll intervals (0.5s) — not the slowness cause.
- Path traversal guards (tested), answered_by enforcement (tested),
  export shapes (verified), matrix/dashboard rendering (verified live).

## Live data notes

- 9 real agent answers exist from the accidental test-run sessions
  (runs 392b / ac0a / 28-27, model Inkling-Small). They are genuine judge
  outputs and were kept deliberately; owner may disagree with them via UI.
  Indistinguishable from dashboard-initiated ones until P2 provenance ships.
