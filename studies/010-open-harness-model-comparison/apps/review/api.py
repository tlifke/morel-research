"""API router (SPEC 4). All state-changing rules enforced server-side."""

import json
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from db import get_db
from importer import import_runs
import app_launcher
from app_launcher import detect_components, manager as launch_manager
from models import Answer, Comparison, LaunchEvent, Question, Run, WrittenFeedback
from schemas import (
    AnswerCreate,
    AnswerOut,
    ComparisonCreate,
    ComparisonOut,
    ImportResult,
    QuestionCreate,
    QuestionOut,
    QuestionUpdate,
    LaunchEventOut,
    LaunchStart,
    LaunchStatus,
    RunOut,
    WrittenFeedbackCreate,
    WrittenFeedbackOut,
)
from trace import parse_session

router = APIRouter(prefix="/api")


# ---- import ----


@router.post("/import", response_model=ImportResult)
def run_import(db: Session = Depends(get_db)):
    return import_runs(db)


# ---- runs ----


def _get_run_or_404(db: Session, run_id: str) -> Run:
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, f"run not found: {run_id}")
    return run


@router.get("/runs", response_model=list[RunOut])
def list_runs(
    condition: str | None = None,
    model: str | None = None,
    tag: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(Run).order_by(Run.imported_at)
    if condition:
        stmt = stmt.where(Run.condition == condition)
    if model:
        stmt = stmt.where(Run.model.contains(model))
    if tag:
        stmt = stmt.where(Run.tag == tag)
    return list(db.scalars(stmt))


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: str, db: Session = Depends(get_db)):
    return _get_run_or_404(db, run_id)


@router.get("/runs/{run_id}/trace")
def get_trace(run_id: str, db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    if not run.session_file or not Path(run.session_file).exists():
        raise HTTPException(404, "session file missing")
    return parse_session(run.session_file)


# ---- agent judge trigger (background subprocess; SPEC 5) ----


@router.post("/runs/{run_id}/judge")
def start_judge(run_id: str, db: Session = Depends(get_db)):
    import subprocess
    import sys

    run = _get_run_or_404(db, run_id)
    log_path = Path(run.run_dir) / "judge.log"
    done_marker = Path(run.run_dir) / "judge.done"
    if done_marker.exists():
        done_marker.unlink()
    log = open(log_path, "w")
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / "agent_judge.py"), run_id],
        cwd=str(Path(__file__).parent),
        stdout=log, stderr=subprocess.STDOUT,
    )
    log.close()  # child holds its own dup of the fd; parent copy no longer needed
    (Path(run.run_dir) / "judge.pid").write_text(str(proc.pid))
    return {"ok": True, "message": f"judge started (pid {proc.pid}); log: {log_path}", "pid": proc.pid}


@router.get("/runs/{run_id}/judge/status")
def judge_status(run_id: str, db: Session = Depends(get_db)):
    import signal

    run = _get_run_or_404(db, run_id)
    pid_file = Path(run.run_dir) / "judge.pid"
    done_marker = Path(run.run_dir) / "judge.done"
    running, output = False, ""
    if pid_file.exists():
        pid = int(pid_file.read_text().strip())
        try:
            os.kill(pid, 0)
            running = True
        except OSError:
            running = False
    log_path = Path(run.run_dir) / "judge.log"
    if log_path.exists():
        output = log_path.read_text(errors="replace")[-2000:]
    if done_marker.exists():
        try:
            ok = bool(json.loads(done_marker.read_text()).get("ok", False))
        except (json.JSONDecodeError, OSError, ValueError):
            ok = False
    else:
        ok = False
    return {"running": running, "done": done_marker.exists(), "ok": ok, "log_tail": output}


# ---- workspace files (path-traversal safe) ----


def _safe_workspace_path(run: Run, rel: str) -> Path:
    workspace = Path(run.workspace_dir).resolve()
    candidate = (workspace / rel).resolve()
    if candidate != workspace and workspace not in candidate.parents:
        raise HTTPException(403, "path escapes workspace")
    return candidate


@router.get("/runs/{run_id}/files")
def list_files(run_id: str, db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    workspace = Path(run.workspace_dir)
    if not workspace.exists():
        raise HTTPException(404, "workspace missing")

    def build(dir_path: Path) -> list[dict]:
        nodes = []
        for child in sorted(dir_path.iterdir(), key=lambda p: (p.is_file(), p.name)):
            if child.name in ("contract_text",) and child.is_dir():
                nodes.append({"name": child.name, "type": "collapsed_dir", "count": len(list(child.glob("*")))})
                continue
            if child.is_dir():
                nodes.append({"name": child.name, "type": "dir", "children": build(child)})
            else:
                nodes.append({"name": child.name, "type": "file", "size": child.stat().st_size})
        return nodes

    return {"run_id": run_id, "tree": build(workspace)}


@router.get("/runs/{run_id}/files/content")
def file_content(run_id: str, path: str = Query(...), db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    target = _safe_workspace_path(run, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "file not found")
    if target.stat().st_size > 2_000_000:
        raise HTTPException(413, "file too large to display")
    return Response(
        content=target.read_text(errors="replace"),
        media_type="text/plain; charset=utf-8",
    )


_PREVIEW_MEDIA = {
    ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
    ".gif": "image/gif", ".webp": "image/webp", ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
}


@router.get("/runs/{run_id}/preview-file")
def preview_file(run_id: str, path: str = Query(...), db: Session = Depends(get_db)):
    """Serve workspace images/HTML for the preview tab. HTML responses carry a
    locked-down CSP so fetched apps cannot call home."""
    run = _get_run_or_404(db, run_id)
    target = _safe_workspace_path(run, path)
    if not target.exists() or not target.is_file():
        raise HTTPException(404, "file not found")
    # no size cap: agent-built apps may inline the whole dataset (observed ~27MB)
    media = _PREVIEW_MEDIA.get(target.suffix.lower(), "application/octet-stream")
    if target.suffix.lower() in (".html", ".htm"):
        content = target.read_text(errors="replace")
        return Response(
            content=content,
            media_type=media,
            headers={
                "Content-Security-Policy": (
                    "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
                    "img-src data:; font-src data:"
                )
            },
        )
    return Response(content=target.read_bytes(), media_type=media)


# ---- questions ----


@router.get("/questions", response_model=list[QuestionOut])
def list_questions(db: Session = Depends(get_db)):
    return list(db.scalars(select(Question).order_by(Question.sort_order, Question.id)))


@router.post("/questions", response_model=QuestionOut, status_code=201)
def create_question(body: QuestionCreate, db: Session = Depends(get_db)):
    if db.scalar(select(Question).where(Question.code == body.code)):
        raise HTTPException(409, f"question code exists: {body.code}")
    q = Question(**body.model_dump())
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


@router.patch("/questions/{question_id}", response_model=QuestionOut)
def update_question(question_id: int, body: QuestionUpdate, db: Session = Depends(get_db)):
    q = db.get(Question, question_id)
    if not q:
        raise HTTPException(404, "question not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(q, field, value)
    db.commit()
    db.refresh(q)
    return q


# ---- answers ----


@router.get("/runs/{run_id}/answers", response_model=list[AnswerOut])
def list_answers(run_id: str, db: Session = Depends(get_db)):
    _get_run_or_404(db, run_id)
    return list(
        db.scalars(
            select(Answer).options(joinedload(Answer.question)).where(Answer.run_id == run_id)
        )
    )


@router.post("/runs/{run_id}/answers", response_model=AnswerOut, status_code=201)
def upsert_answer(run_id: str, body: AnswerCreate, db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    q = db.get(Question, body.question_id)
    if not q:
        raise HTTPException(404, "question not found")
    if not q.active:
        raise HTTPException(409, f"question inactive: {q.code}")
    if body.judge == "agent" and q.answered_by == "human":
        raise HTTPException(
            403,
            f"question '{q.code}' is answered_by='human'; agent answers are not allowed",
        )
    value = _validated_value(q.value_type, body.value)

    existing = db.scalar(
        select(Answer).where(
            Answer.run_id == run_id,
            Answer.question_id == q.id,
            Answer.judge == body.judge,
        )
    )
    if existing:
        existing.value = value
        existing.evidence = body.evidence
        existing.judge_model = body.judge_model
        existing.notes = body.notes
        db.commit()
        db.refresh(existing)
        return existing
    ans = Answer(
        run_id=run.id,
        question_id=q.id,
        judge=body.judge,
        value=value,
        evidence=body.evidence,
        judge_model=body.judge_model,
        notes=body.notes,
    )
    db.add(ans)
    db.commit()
    db.refresh(ans)
    return ans


def _validated_value(value_type: str, value):
    if value is None:
        return None
    if value_type == "bool":
        if not isinstance(value, bool):
            raise HTTPException(422, f"expected bool, got {type(value).__name__}")
        return value
    if value_type == "int_1_5":
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 5:
            raise HTTPException(422, "expected int in [1..5]")
        return value
    if value_type == "text":
        return str(value)
    raise HTTPException(422, f"unknown value_type: {value_type}")


# ---- comparisons ----


@router.get("/comparisons", response_model=list[ComparisonOut])
def list_comparisons(db: Session = Depends(get_db)):
    return list(db.scalars(select(Comparison).order_by(Comparison.created_at.desc())))


@router.post("/comparisons", response_model=ComparisonOut, status_code=201)
def create_comparison(body: ComparisonCreate, db: Session = Depends(get_db)):
    _get_run_or_404(db, body.run_a_id)
    _get_run_or_404(db, body.run_b_id)
    comp = Comparison(**body.model_dump())
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp


# ---- written feedback ----


@router.get("/feedback", response_model=list[WrittenFeedbackOut])
def list_feedback(run_id: str | None = None, db: Session = Depends(get_db)):
    stmt = select(WrittenFeedback).order_by(WrittenFeedback.created_at.desc())
    if run_id:
        stmt = stmt.where(WrittenFeedback.run_id == run_id)
    return list(db.scalars(stmt))


@router.post("/feedback", response_model=WrittenFeedbackOut, status_code=201)
def create_feedback(body: WrittenFeedbackCreate, db: Session = Depends(get_db)):
    if body.run_id:
        _get_run_or_404(db, body.run_id)
    fb = WrittenFeedback(**body.model_dump())
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return fb



# ---- live app launcher (SPEC 9 addendum) ----


def _launch_event_sink(run_id: str, command: str, port: int | None, mode: str,
                       healthy: bool | None, log_excerpt: str) -> None:
    """Launcher thread callback: write/update launch_events rows (own session)."""
    from db import SessionLocal
    with SessionLocal() as db:
        row = (
            db.query(LaunchEvent)
            .filter(LaunchEvent.run_id == run_id, LaunchEvent.healthy.is_(None))
            .order_by(LaunchEvent.id.desc())
            .first()
        )
        if row is None:
            row = LaunchEvent(run_id=run_id, command=command, port=port, mode=mode)
            db.add(row)
        row.healthy = healthy
        row.log_excerpt = (log_excerpt or "")[:4000]
        db.commit()


app_launcher.event_sink = _launch_event_sink  # module-global sink, read by _emit


@router.post("/runs/{run_id}/launch", response_model=LaunchEventOut)
def launch_app(run_id: str, body: LaunchStart | None = None, db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    try:
        state = launch_manager.start(run.id, run.workspace_dir, body.command if body else None)
    except RuntimeError as e:
        raise HTTPException(409, str(e))
    event = LaunchEvent(run_id=run.id, command=state.command, port=state.port, mode=state.mode)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


@router.get("/runs/{run_id}/launch/status", response_model=LaunchStatus)
def launch_status(run_id: str, db: Session = Depends(get_db)):
    run = _get_run_or_404(db, run_id)
    status = launch_manager.status(run.id)
    status["components"] = (
        detect_components(Path(run.workspace_dir)) if Path(run.workspace_dir).exists() else []
    )
    return status


@router.post("/runs/{run_id}/launch/stop")
def launch_stop(run_id: str, db: Session = Depends(get_db)):
    _get_run_or_404(db, run_id)
    result = launch_manager.stop(run_id)
    if result.get("stopped"):
        row = (
            db.query(LaunchEvent)
            .filter(LaunchEvent.run_id == run_id, LaunchEvent.healthy.is_(None))
            .order_by(LaunchEvent.id.desc())
            .first()
        )
        if row:
            row.healthy = False
            row.log_excerpt = "stopped by user"
            db.commit()
    return result


# ---- exports (SPEC 7) ----



def _session_messages(run: Run, truncate: bool = True) -> list[dict]:
    parsed = parse_session(run.session_file, truncate=truncate)
    return [e for e in parsed["events"] if e["kind"] == "message"]


def _system_prompt_event(run: Run) -> dict | None:
    """System prompt from the session's pi-clean-experiment custom entry,
    as a message event shaped like the others (for DPO prompt assembly)."""
    parsed = parse_session(run.session_file)
    sys_prompt = (parsed.get("custom") or {}).get("systemPrompt")
    if sys_prompt is None:
        return None
    return {
        "kind": "message",
        "role": "system",
        "index": -1,
        "blocks": [{"kind": "text", "text": sys_prompt}],
        "timestamp": None,
    }


@router.get("/export/sft")
def export_sft(run_ids: str = Query(...), db: Session = Depends(get_db)):
    ids = [r.strip() for r in run_ids.split(",") if r.strip()]
    examples = []
    for rid in ids:
        run = _get_run_or_404(db, rid)
        if not run.session_file:
            raise HTTPException(404, f"no session file for run {rid}")
        examples.append({"run_id": rid, "messages": _session_messages(run, truncate=False)})
    return {"format": "sft", "renderer": "tml_v0", "effort": 0.9, "examples": examples}


@router.get("/export/dpo")
def export_dpo(db: Session = Depends(get_db)):
    comps = list(db.scalars(select(Comparison).where(Comparison.better != "tie")))
    out = []
    for c in comps:
        run_a, run_b = db.get(Run, c.run_a_id), db.get(Run, c.run_b_id)
        if not run_a or not run_b or not run_a.session_file or not run_b.session_file:
            continue
        winner, loser = (run_a, run_b) if c.better == "a" else (run_b, run_a)
        sys_event = _system_prompt_event(winner)
        prompt = [e for e in _session_messages(winner, truncate=False) if e["role"] == "user"]
        if sys_event:
            prompt = [sys_event] + prompt
        out.append(
            {
                "run_a": c.run_a_id,
                "run_b": c.run_b_id,
                "better": c.better,
                "prompt": prompt,
                "chosen": [e for e in _session_messages(winner, truncate=False) if e["role"] == "assistant"],
                "rejected": [e for e in _session_messages(loser, truncate=False) if e["role"] == "assistant"],
            }
        )
    return out


@router.get("/export/reward")
def export_reward(db: Session = Depends(get_db)):
    """Human answers -> per-run score.

    Documented placeholder formula: score = mean over the human-answered
    questions of (bool -> 0/1, int_1_5 -> x/5, text -> excluded).
    """
    runs = list(db.scalars(select(Run)))
    out = []
    for run in runs:
        human_answers = {
            a.question.code: a.value
            for a in db.scalars(select(Answer).options(joinedload(Answer.question)).where(
                Answer.run_id == run.id, Answer.judge == "human"
            ))
            if a.question is not None
        }
        if not human_answers:
            continue
        scores = []
        for code, value in human_answers.items():
            if isinstance(value, bool):
                scores.append(1.0 if value else 0.0)
            elif isinstance(value, (int, float)) and not isinstance(value, bool):
                scores.append(max(0.0, min(1.0, float(value) / 5.0)))
        out.append(
            {
                "run_id": run.id,
                "answers": human_answers,
                "score": round(sum(scores) / len(scores), 4) if scores else None,
                "trace_ref": run.session_file,
            }
        )
    return out


@router.get("/export/summary")
def export_summary(db: Session = Depends(get_db)):
    runs = list(db.scalars(select(Run)))
    per_run = []
    for run in runs:
        answers = list(db.scalars(select(Answer).where(Answer.run_id == run.id)))
        per_run.append(
            {
                "run_id": run.id,
                "condition": run.condition,
                "model": run.model,
                "tag": run.tag,
                "agent_answered": sorted({a.question_id for a in answers if a.judge == "agent"}),
                "human_answered": sorted({a.question_id for a in answers if a.judge == "human"}),
                "comparisons": db.scalar(
                    select(Comparison.id).where(
                        (Comparison.run_a_id == run.id) | (Comparison.run_b_id == run.id)
                    )
                )
                is not None,
                "written_feedback": len(
                    list(db.scalars(select(WrittenFeedback).where(WrittenFeedback.run_id == run.id)))
                ),
            }
        )
    return {"runs": per_run}
