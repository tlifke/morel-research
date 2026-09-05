"""Server-rendered UI routes."""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import get_db
from models import Answer, Comparison, Question, Run, WrittenFeedback
from trace import parse_session

APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))
templates.env.filters["to_bool"] = lambda v: ("✓" if v else "✗") if isinstance(v, bool) else str(v)

router = APIRouter(include_in_schema=False)


def _answer_map(db: Session, run_id: str) -> dict[tuple[int, str], Answer]:
    rows = db.scalars(select(Answer).where(Answer.run_id == run_id)).all()
    return {(a.question_id, a.judge): a for a in rows}


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    runs = list(db.scalars(select(Run).order_by(Run.condition, Run.model, Run.id)))
    questions = list(db.scalars(select(Question).order_by(Question.sort_order)))
    all_answers = list(db.scalars(select(Answer)))
    by_run: dict[str, dict[str, set[int]]] = {}
    matrix: dict[str, dict[int, dict[str, object]]] = {}
    for a in all_answers:
        slot = by_run.setdefault(a.run_id, {"agent": set(), "human": set()})
        slot[a.judge].add(a.question_id)
        cell = matrix.setdefault(a.run_id, {}).setdefault(a.question_id, {})
        cell[a.judge] = a.value
    rows = [
        {
            "run": run,
            "agent_answered": by_run.get(run.id, {}).get("agent", set()),
            "human_answered": by_run.get(run.id, {}).get("human", set()),
            "answers": matrix.get(run.id, {}),
        }
        for run in runs
    ]
    comparisons = list(db.scalars(select(Comparison)))
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "rows": rows,
            "questions": questions,
            "comparison_count": len(comparisons),
        },
    )


@router.get("/judging", response_class=HTMLResponse)
def judging_page(request: Request, db: Session = Depends(get_db)):
    from models import JudgeJob

    jobs = list(db.scalars(select(JudgeJob).order_by(JudgeJob.created_at.desc())))
    runs = {r.id: r for r in db.scalars(select(Run))}
    cards = []
    for job in jobs:
        items = sorted(job.items, key=lambda i: i.id)
        current = next((i for i in items if i.status == "running"), None)
        cards.append(
            {
                "job": job,
                "items": items,
                "done": sum(1 for i in items if i.status == "done"),
                "failed": sum(1 for i in items if i.status == "failed"),
                "current_run": runs.get(current.run_id) if current else None,
            }
        )
    return templates.TemplateResponse(request, "judging.html", {"cards": cards})


@router.get("/runs/{run_id}", response_class=HTMLResponse)
def run_detail(request: Request, run_id: str, db: Session = Depends(get_db)):
    run = db.get(Run, run_id)
    if not run:
        raise HTTPException(404, "run not found")
    questions = list(db.scalars(select(Question).order_by(Question.sort_order)))
    answers = _answer_map(db, run_id)
    trace = parse_session(run.session_file) if run.session_file and Path(run.session_file).exists() else None
    feedback = list(
        db.scalars(select(WrittenFeedback).where(WrittenFeedback.run_id == run_id).order_by(WrittenFeedback.created_at.desc()))
    )
    return templates.TemplateResponse(
        request,
        "run_detail.html",
        {"run": run, "questions": questions, "answers": answers, "trace": trace, "feedback": feedback},
    )


@router.get("/compare", response_class=HTMLResponse)
def compare_page(request: Request, db: Session = Depends(get_db)):
    runs = list(db.scalars(select(Run).order_by(Run.condition, Run.model, Run.id)))
    comparisons = list(db.scalars(select(Comparison).order_by(Comparison.created_at.desc())))
    return templates.TemplateResponse(
        request, "compare.html", {"runs": runs, "comparisons": comparisons}
    )


@router.get("/questions", response_class=HTMLResponse)
def questions_page(request: Request, db: Session = Depends(get_db)):
    questions = list(db.scalars(select(Question).order_by(Question.sort_order)))
    return templates.TemplateResponse(request, "questions.html", {"questions": questions})


@router.get("/feedback", response_class=HTMLResponse)
def feedback_page(request: Request, db: Session = Depends(get_db)):
    feedback = list(db.scalars(select(WrittenFeedback).order_by(WrittenFeedback.created_at.desc())))
    comparisons = list(db.scalars(select(Comparison).order_by(Comparison.created_at.desc())))
    answers = list(db.scalars(select(Answer).order_by(Answer.created_at.desc())))
    return templates.TemplateResponse(
        request, "feedback.html", {"feedback": feedback, "comparisons": comparisons, "answers": answers}
    )
