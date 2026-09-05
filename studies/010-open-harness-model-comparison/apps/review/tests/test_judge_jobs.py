"""Judge-job lifecycle tests (SPEC 10 acceptance) using AGENT_JUDGE_STUB.

Requires the app running on :8300 STARTED WITH AGENT_JUDGE_STUB=1 so the
runner's agent_judge subprocesses stub out (no pi sessions, no API cost):

    AGENT_JUDGE_STUB=1 uv run uvicorn main:app --port 8300

Skips when the server is unreachable or not in stub mode. Cleans up all stub
answers + test jobs afterwards so real judgment data stays untouched.
"""

import os
import sys
import time
from pathlib import Path

import httpx
import pytest

# make the app modules (db, models) importable — pytest runs from repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

BASE_URL = os.environ.get("CONTRACTLAB_URL", "http://localhost:8300")
POLL_TIMEOUT_S = 60


def _server_stub_mode() -> bool:
    """Tests require the app running with AGENT_JUDGE_STUB=1 (see module
    docstring); the runner's subprocesses inherit the server's env, so the
    stub flag is a server-side setting, not a test-side one."""
    try:
        return httpx.get(f"{BASE_URL}/health", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _server_stub_mode(), reason="app not running on :8300")


def _wait_job(job_id: int, status: str, timeout_s: int = POLL_TIMEOUT_S) -> dict:
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        last = httpx.get(f"{BASE_URL}/api/judge-jobs/{job_id}", timeout=10).json()
        if last["status"] == status:
            return last
        time.sleep(0.5)
    raise AssertionError(f"job {job_id} did not reach '{status}'; last={last}")


def _cleanup(job_ids: list[int]) -> None:
    """Best-effort: cancel live jobs + delete stub answers and test jobs."""
    for jid in job_ids:
        try:
            httpx.post(f"{BASE_URL}/api/judge-jobs/{jid}/cancel", timeout=10)
        except httpx.HTTPError:
            pass
    try:
        from db import SessionLocal
        from models import Answer, JudgeJob

        db = SessionLocal()
        try:
            stub_answers = list(db.query(Answer).filter(Answer.judge_model == "stub").all())
            for a in stub_answers:
                db.delete(a)
            for jid in job_ids:
                job = db.get(JudgeJob, jid)
                if job:
                    for item in list(job.items):
                        db.delete(item)
                    db.delete(job)
            db.commit()
        finally:
            db.close()
    except Exception as e:  # noqa: BLE001 — cleanup is best-effort
        import traceback; print(f'[cleanup] incomplete: {traceback.format_exc()}')


@pytest.fixture(scope="module")
def run_ids() -> list[str]:
    runs = httpx.get(f"{BASE_URL}/api/runs", timeout=10).json()
    assert len(runs) >= 3, "need at least 3 imported runs"
    return [r["id"] for r in runs[:3]]


def test_bulk_job_completes_and_writes_agent_answers(run_ids):
    r = httpx.post(f"{BASE_URL}/api/judge-jobs", json={"run_ids": run_ids}, timeout=10)
    assert r.status_code == 201, r.text
    job = r.json()
    assert job["status"] in ("queued", "running")
    final = _wait_job(job["id"], "completed")
    assert final["done_items"] == 3
    assert all(i["status"] == "done" for i in final["items"])
    # agent answers actually written for each run
    for rid in run_ids:
        answers = httpx.get(f"{BASE_URL}/api/runs/{rid}/answers", timeout=10).json()
        agent = [a for a in answers if a["judge"] == "agent"]
        assert agent, f"no agent answers for {rid}"
        assert all(a["judge_model"] == "stub" for a in agent)
    _cleanup([job["id"]])


def test_pause_holds_queue_then_resume_completes(run_ids):
    r = httpx.post(f"{BASE_URL}/api/judge-jobs", json={"run_ids": run_ids, "stub": True, "stub_delay": 3}, timeout=10)
    job = r.json()
    try:
        _wait_job(job["id"], "running", timeout_s=15)
        # wait for first item to finish, then pause
        deadline = time.time() + 30
        while time.time() < deadline:
            detail = httpx.get(f"{BASE_URL}/api/judge-jobs/{job['id']}", timeout=10).json()
            done = sum(1 for i in detail["items"] if i["status"] == "done")
            if done >= 1:
                break
            time.sleep(0.5)
        p = httpx.post(f"{BASE_URL}/api/judge-jobs/{job['id']}/pause", timeout=10)
        assert p.status_code == 200, p.text
        assert p.json()["status"] == "paused"
        time.sleep(4)  # longer than the stub delay: no new item may start
        held = httpx.get(f"{BASE_URL}/api/judge-jobs/{job['id']}", timeout=10).json()
        started = [i for i in held["items"] if i["status"] in ("done", "running")]
        assert len(started) <= 2, f"pause did not hold queue: {held}"
        r2 = httpx.post(f"{BASE_URL}/api/judge-jobs/{job['id']}/resume", timeout=10)
        assert r2.status_code == 200
        final = _wait_job(job["id"], "completed")
        assert final["done_items"] == 3
    finally:
        _cleanup([job["id"]])


def test_cancel_terminates_and_cancels_remaining(run_ids):
    r = httpx.post(f"{BASE_URL}/api/judge-jobs", json={"run_ids": run_ids, "stub": True, "stub_delay": 5}, timeout=10)
    job = r.json()
    try:
        _wait_job(job["id"], "running", timeout_s=15)
        c = httpx.post(f"{BASE_URL}/api/judge-jobs/{job['id']}/cancel", timeout=10)
        assert c.status_code == 200, c.text
        final = _wait_job(job["id"], "cancelled", timeout_s=30)
        statuses = [i["status"] for i in final["items"]]
        assert "cancelled" in statuses
        assert all(s in ("done", "cancelled", "failed") for s in statuses)
        assert final["done_items"] < 3
    finally:
        _cleanup([job["id"]])
