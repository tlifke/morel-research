"""Run ingestion + question seeding (SPEC 2, 3.2). Idempotent."""

import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from db import DATA_DIR
from models import Question, Run

RUNS_DIR = DATA_DIR / "runs"

STUDY = "010-open-harness-model-comparison"

SEED_QUESTIONS = [
    {"code": "docs_describe_launch", "text": "Does the app's documentation tell us how to launch it?", "answered_by": "both", "value_type": "bool", "sort_order": 1},
    {"code": "launches_per_docs", "text": "Does the app launch properly in compliance with those instructions?", "answered_by": "both", "value_type": "bool", "sort_order": 2},
    {"code": "launches_at_all", "text": "Does the app launch in general, regardless of documentation?", "answered_by": "both", "value_type": "bool", "sort_order": 3},
    {"code": "fulfills_functions", "text": "Does the app fulfill the required functions?", "answered_by": "human", "value_type": "bool", "sort_order": 4},
    {"code": "fulfills_well", "text": "Does the app fulfill those functions well?", "answered_by": "human", "value_type": "bool", "sort_order": 5},
]


def seed_questions(db: Session) -> list[str]:
    seeded = []
    for q in SEED_QUESTIONS:
        stmt = pg_insert(Question).values(**q).on_conflict_do_nothing(index_elements=["code"])
        db.execute(stmt)
        seeded.append(q["code"])
    db.commit()
    return seeded


def find_run_dirs() -> tuple[list[Path], list[Path]]:
    """Return (valid run dirs, skipped dirs). A valid run dir has run-summary.json."""
    valid, skipped = [], []
    if not RUNS_DIR.exists():
        return valid, skipped
    for run_dir in sorted(p for p in RUNS_DIR.glob("*/*/*") if p.is_dir()):
        if (run_dir / "run-summary.json").exists():
            valid.append(run_dir)
        else:
            skipped.append(run_dir)
    return valid, skipped


def import_runs(db: Session) -> dict:
    valid, skipped = find_run_dirs()
    upserted = 0
    for run_dir in valid:
        summary = json.loads((run_dir / "run-summary.json").read_text())
        session_file = None
        candidates = sorted(run_dir.glob("*.jsonl"))
        if candidates:
            session_file = str(candidates[0])
        audit = {}
        audit_path = run_dir / "audit.json"
        if audit_path.exists():
            audit = json.loads(audit_path.read_text())

        values = dict(
            id=summary.get("runId") or run_dir.name,
            study=STUDY,
            condition=summary.get("condition") or run_dir.parent.parent.name,
            model=summary.get("model") or "unknown",
            spec=summary.get("spec"),
            tag=summary.get("tag"),
            run_dir=str(run_dir),
            workspace_dir=str(run_dir / "workspace"),
            session_file=session_file,
            tokens_input=summary.get("tokens", {}).get("input", 0),
            tokens_output=summary.get("tokens", {}).get("output", 0),
            tokens_reasoning=summary.get("tokens", {}).get("reasoning", 0),
            tokens_cache_read=summary.get("tokens", {}).get("cacheRead", 0),
            tokens_cache_write=summary.get("tokens", {}).get("cacheWrite", 0),
            estimated_cost_usd=summary.get("estimatedCostUsd"),
            pricing_source=summary.get("pricingSource"),
            audit_clean=bool(audit.get("clean", True)),
            audit_violations=audit.get("violations"),
        )
        stmt = pg_insert(Run).values(**values)
        update_cols = {c: stmt.excluded[c] for c in values if c != "id"}
        stmt = stmt.on_conflict_do_update(index_elements=["id"], set_=update_cols)
        db.execute(stmt)
        upserted += 1
    db.commit()
    return {
        "runs_found": len(valid),
        "runs_upserted": upserted,
        "runs_skipped": [str(p.relative_to(RUNS_DIR)) for p in skipped],
        "questions_seeded": seed_questions(db),
    }
