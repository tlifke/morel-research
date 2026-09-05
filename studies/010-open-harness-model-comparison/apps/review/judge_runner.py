"""Judge job runner (SPEC 10 addendum).

Server-side batch execution of agent_judge.py over a queue of runs.
Jobs live in Postgres, so browser navigation is irrelevant to them and a
page reload never affects progress.

Lifecycle:  queued -> running -> (paused <-> running) -> completed | failed | cancelled
Pause:      no NEW items start; the in-flight run is allowed to finish.
Cancel:     the in-flight subprocess is terminated; remaining items -> cancelled.
Startup:    recover_stuck_jobs() flips jobs stuck in `running` (from a
            previous process) to `paused`, and their `running` items back to
            `queued` — see AS_BUILT.

One job runs at a time (global runner). A paused job releases the runner: a
different queued job may start; resuming puts the paused job back in queue
order (by created_at).
"""

import os
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone

from sqlalchemy import select

from db import SessionLocal
from models import Answer, JudgeJob, JudgeJobItem

POLL_INTERVAL_S = 0.5
PROC_POLL_S = 0.5

_thread: threading.Thread | None = None
_thread_lock = threading.Lock()
# job_id -> in-flight subprocess (for cancel), guarded by _proc_lock
_procs: dict[int, subprocess.Popen] = {}
_proc_lock = threading.Lock()
_job_env: dict[int, dict[str, str]] = {}  # job_id -> extra env for subprocesses (testing affordance)


def utcnow():
    return datetime.now(timezone.utc)


def recover_stuck_jobs() -> int:
    """Startup recovery: a `running` job from a dead process cannot continue
    (its subprocess is gone). Flip running->paused and running items->queued
    so the owner can resume deliberately. Returns number of jobs recovered."""
    db = SessionLocal()
    recovered = 0
    try:
        jobs = list(db.scalars(select(JudgeJob).where(JudgeJob.status == "running")))
        for job in jobs:
            job.status = "paused"
            for item in job.items:
                if item.status == "running":
                    item.status = "queued"
                    item.started_at = None
            recovered += 1
        if recovered:
            db.commit()
    finally:
        db.close()
    return recovered


def create_job(run_ids: list[str], model: str, stub_delay: int | None = None, stub: bool = False) -> JudgeJob:
    """Create a queued job with one item per run. Validates runs exist and
    deduplicates. Does NOT start the thread twice (start_runner is idempotent)."""
    db = SessionLocal()
    try:
        from models import Run

        found = list(db.scalars(select(Run).where(Run.id.in_(run_ids))))
        found_ids = {r.id for r in found}
        missing = [r for r in run_ids if r not in found_ids]
        if missing:
            raise ValueError(f"unknown runs: {missing}")
        deduped = list(dict.fromkeys(run_ids))
        job = JudgeJob(model=model, stub=stub, total_items=len(deduped), status="queued")
        db.add(job)
        db.flush()
        job_env = {}
        if stub:
            job_env["AGENT_JUDGE_STUB"] = "1"
        if stub_delay:
            job_env["AGENT_JUDGE_STUB_DELAY"] = str(stub_delay)
        if job_env:
            _job_env[job.id] = job_env
        for rid in deduped:
            db.add(JudgeJobItem(job_id=job.id, run_id=rid, status="queued"))
        db.commit()
        db.refresh(job)
    finally:
        db.close()
    start_runner()
    return job


def start_runner() -> None:
    global _thread
    with _thread_lock:
        if _thread and _thread.is_alive():
            return
        _thread = threading.Thread(target=_run_loop, daemon=True, name="judge-job-runner")
        _thread.start()


def _pick_job(db) -> JudgeJob | None:
    """First queued-or-running job in creation order. Paused jobs are skipped
    (they re-enter the queue via resume -> queued)."""
    return db.scalars(
        select(JudgeJob)
        .where(JudgeJob.status.in_(["queued", "running"]))
        .order_by(JudgeJob.created_at, JudgeJob.id)
    ).first()


def _next_item(db, job_id: int) -> JudgeJobItem | None:
    return db.scalars(
        select(JudgeJobItem)
        .where(JudgeJobItem.job_id == job_id, JudgeJobItem.status == "queued")
        .order_by(JudgeJobItem.id)
    ).first()


def _has_agent_answers(db, run_id: str) -> bool:
    return db.scalar(
        select(Answer.id).where(Answer.run_id == run_id, Answer.judge == "agent").limit(1)
    ) is not None


def _finish_job(db, job: JudgeJob, status: str, error: str | None = None) -> None:
    job.status = status
    job.finished_at = utcnow()
    if error:
        job.error = error
    db.commit()


def _run_loop() -> None:
    while True:
        # --- pick a job (single flight) ---
        db = SessionLocal()
        try:
            job = _pick_job(db)
            if job is None:
                time.sleep(POLL_INTERVAL_S)
                continue
            if job.status == "queued":
                job.status = "running"
                job.started_at = job.started_at or utcnow()
                db.commit()
                job_id, model = job.id, job.model
            else:  # already running (e.g. previous item just finished)
                job_id, model = job.id, job.model
        finally:
            db.close()

        # --- paused jobs hold the queue ---
        db = SessionLocal()
        try:
            job = db.get(JudgeJob, job_id)
            if job is None or job.status in ("paused", "cancelled", "completed", "failed"):
                time.sleep(POLL_INTERVAL_S)
                continue
            item = _next_item(db, job_id)
            if item is None:
                running_left = db.scalar(
                    select(JudgeJobItem.id).where(
                        JudgeJobItem.job_id == job_id, JudgeJobItem.status == "running"
                    ).limit(1)
                )
                if running_left is None:
                    _finish_job(db, job_id, "completed")
                time.sleep(POLL_INTERVAL_S)
                continue
            item.status = "running"
            item.started_at = utcnow()
            db.commit()
        finally:
            db.close()

        # --- execute outside the db session (subprocess takes minutes) ---
        rc, err = _execute_item(job_id, run_id=_item_run_id(job_id), model=model)

        # --- record outcome ---
        db = SessionLocal()
        try:
            item = db.scalars(
                select(JudgeJobItem).where(
                    JudgeJobItem.job_id == job_id, JudgeJobItem.status == "running"
                ).order_by(JudgeJobItem.id)
            ).first()
            job = db.get(JudgeJob, job_id)
            if item is None or job is None:
                continue
            if job.status == "cancelled":
                if item.status == "running":
                    item.status = "cancelled"
                    item.finished_at = utcnow()
                db.commit()
                continue
            if rc == 0:
                ok = _has_agent_answers(db, item.run_id)
                item.status = "done" if ok else "failed"
                item.error = None if ok else "exited 0 but no agent answers were recorded"
            else:
                item.status = "failed"
                item.error = (err or f"exit code {rc}")[:2000]
            item.finished_at = utcnow()
            db.commit()
        finally:
            db.close()


def _item_run_id(job_id: int) -> str:
    """The run_id of the item currently marked running for this job."""
    db = SessionLocal()
    try:
        item = db.scalars(
            select(JudgeJobItem).where(
                JudgeJobItem.job_id == job_id, JudgeJobItem.status == "running"
            ).order_by(JudgeJobItem.id)
        ).first()
        if item:
            return item.run_id
        raise RuntimeError(f"no running item for job {job_id}")
    finally:
        db.close()


def _finish_job(db, job_id: int, status: str, error: str | None = None) -> None:
    job = db.get(JudgeJob, job_id)
    if job is None:
        return
    job.status = status
    job.finished_at = utcnow()
    if error:
        job.error = error
    db.commit()


def _execute_item(job_id: int, run_id: str, model: str) -> tuple[int, str | None]:
    """Spawn agent_judge.py for one run; wait, honoring cancel."""
    cmd = [sys.executable, str(( __import__("pathlib").Path(__file__).parent / "agent_judge.py")), run_id, "--model", model]
    # stub mode is strictly per-job (job.stub / job creation body); never
    # inherit AGENT_JUDGE_STUB from the server environment — a clean server
    # must never stub a real judging job by accident.
    env = {k: v for k, v in os.environ.items() if k != "AGENT_JUDGE_STUB"}
    env.update(_job_env.get(job_id, {}))
    proc = subprocess.Popen(
        cmd,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
    )
    with _proc_lock:
        _procs[job_id] = proc
    try:
        while True:
            rc = proc.poll()
            if rc is not None:
                return rc, None
            # cancel check
            db = SessionLocal()
            try:
                status = db.get(JudgeJob, job_id).status
            finally:
                db.close()
            if status == "cancelled":
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
                return -9, "cancelled by owner"
            time.sleep(PROC_POLL_S)
    finally:
        with _proc_lock:
            _procs.pop(job_id, None)


def cancel_active(job_id: int) -> None:
    """Terminate the in-flight subprocess for this job, if any."""
    with _proc_lock:
        proc = _procs.get(job_id)
    if proc and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
