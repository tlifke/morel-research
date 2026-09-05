"""Agent judge orchestrator (SPEC 5).

Copies the run workspace to a fresh temp dir, runs the Node/pi-SDK judging
session (judge_runner.mjs) under the pi-clean harness, validates verdicts,
and POSTs one `answers` row per agent/both question to the API.

Usage:  uv run python agent_judge.py <run_id>
Requires: the review app server running (default http://localhost:8300),
          env HF_TOKEN/TINKER credentials available to the pi SDK.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx
from sqlalchemy import select

from db import SessionLocal
from models import Answer, Question, Run

APP_DIR = Path(__file__).resolve().parent
API_BASE = os.environ.get("CONTRACTLAB_API", "http://localhost:8300")
DEFAULT_MODEL = "tinker/thinkingmachines/Inkling-Small"
JUDGE_TIMEOUT_S = 45 * 60


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_id")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    args = parser.parse_args()
    run_id, model_spec = args.run_id, args.model

    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if not run:
            print(f"run not found: {run_id}", file=sys.stderr)
            return 1
        questions = list(
            db.scalars(
                select(Question).where(
                    Question.active.is_(True),
                    Question.answered_by.in_(["agent", "both"]),
                )
            )
        )
        questions = sorted(questions, key=lambda q: q.sort_order)

        # 1. copy workspace to fresh temp dir (FULL copy: the artifact may
        # legitimately read its dataset copies; excluding them would unfairly
        # fail launches — learned from the first judge round)
        tmp = Path(tempfile.mkdtemp(prefix="contractlab-judge-"))
        workcopy = tmp / "workspace"
        shutil.copytree(run.workspace_dir, workcopy)
        print(f"[judge] workspace copy: {workcopy}")

        # 2. run node judging session
        questions_file = tmp / "questions.json"
        questions_file.write_text(json.dumps([{"code": q.code, "text": q.text, "value_type": q.value_type} for q in questions]))
        out_file = tmp / "verdict.json"
        cmd = ["node", str(APP_DIR / "judge_runner.mjs"), str(workcopy), str(questions_file), model_spec, str(out_file)]
        print(f"[judge] running: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, check=True, timeout=JUDGE_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            print(f"[judge] TIMEOUT after {JUDGE_TIMEOUT_S}s", file=sys.stderr)
            (Path(run.run_dir) / "judge.done").write_text(json.dumps({"ok": False, "error": "timeout"}))
            return 2
        except subprocess.CalledProcessError as e:
            print(f"[judge] runner exited non-zero: {e.returncode}", file=sys.stderr)
            (Path(run.run_dir) / "judge.done").write_text(json.dumps({"ok": False, "error": f"runner exit {e.returncode}"}))
            return 3
        verdict = json.loads(out_file.read_text())
        if not verdict.get("ok"):
            print(f"[judge] runner reported failure: {verdict.get('error')}", file=sys.stderr)
            (Path(run.run_dir) / "judge.done").write_text(json.dumps({"ok": False, "error": verdict.get("error")}))
            return 3

        # 3. path audit on the judge session
        audit_note = ""
        judge_session = verdict.get("session_file")
        if judge_session and Path(judge_session).exists():
            violations = _audit_session(judge_session, str(workcopy))
            if violations:
                audit_note = f"\n\n[path audit] {len(violations)} violation(s): {json.dumps(violations)[:1000]}"

        # 4. POST answers
        posted = 0
        judge_model = verdict.get("model", model_spec)
        summary = verdict.get("summary", "")
        with httpx.Client(base_url=API_BASE, timeout=30) as client:
            for q in questions:
                v = verdict["verdicts"].get(q.code)
                if v is None:
                    print(f"[judge] no verdict for {q.code}; skipping")
                    continue
                value = v.get("value")
                if q.value_type == "bool":
                    value = bool(value)
                elif q.value_type == "int_1_5":
                    value = int(value)
                else:
                    value = str(value)
                evidence = (v.get("evidence") or "") + audit_note + (f"\n\n[judge summary] {summary}" if summary else "")
                # upsert: POST replaces any existing agent answer for this question
                resp = client.post(
                    f"/api/runs/{run_id}/answers",
                    json={"question_id": q.id, "judge": "agent", "value": value, "evidence": evidence, "judge_model": judge_model},
                )
                if resp.status_code in (200, 201):
                    posted += 1
                else:
                    print(f"[judge] POST failed for {q.code}: {resp.status_code} {resp.text[:200]}", file=sys.stderr)
        print(f"[judge] posted {posted}/{len(questions)} answers")
        (Path(run.run_dir) / "judge.done").write_text(json.dumps({"ok": True, "posted": posted}))
        print(f"[judge] done marker written; workspace copy retained at {workcopy} for inspection")
        return 0
    finally:
        db.close()


def _audit_session(session_file: str, allowed_root: str) -> list[dict]:
    """Flag tool calls that referenced paths outside the judge's copy."""
    violations = []
    for line in Path(session_file).read_text(errors="replace").splitlines():
        try:
            e = json.loads(line)
        except json.JSONDecodeError:
            continue
        if e.get("type") != "message" or e.get("message", {}).get("role") != "assistant":
            continue
        for block in e["message"].get("content") or []:
            if block.get("type") != "toolCall":
                continue
            name, a = block.get("name"), block.get("arguments") or {}
            if name in ("read", "write", "edit") and a.get("path"):
                p = Path(a["path"])
                if p.is_absolute() and not str(p).startswith(allowed_root):
                    violations.append({"tool": name, "reason": "absolute path outside judge copy", "path": str(p)[:200]})
            if name == "bash" and isinstance(a.get("command"), str):
                cmd = a["command"]
                if ("/Users/" in cmd or "/home/" in cmd) and allowed_root not in cmd:
                    violations.append({"tool": name, "reason": "bash references path outside judge copy", "detail": cmd[:200]})
    return violations


if __name__ == "__main__":
    sys.exit(main())
