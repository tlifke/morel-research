"""API acceptance tests (SPEC section 8, criteria 5 & 6).

Run against a live server:
    docker compose up -d
    uv run uvicorn main:app --port 8300   # from this directory
    uv run pytest tests/test_api.py -v

Skips (rather than fails) when the server isn't reachable, so `pytest` in a
cold checkout doesn't produce noise. All tests are non-mutating: the
answered_by check expects a 403 rejection before any DB write.
"""

import os

import httpx
import pytest

BASE_URL = os.environ.get("CONTRACTLAB_URL", "http://localhost:8300")


def _server_up() -> bool:
    try:
        return httpx.get(f"{BASE_URL}/api/runs", timeout=3).status_code == 200
    except httpx.HTTPError:
        return False


pytestmark = pytest.mark.skipif(not _server_up(), reason=f"app not running at {BASE_URL}")


@pytest.fixture(scope="module")
def any_run_id() -> str:
    runs = httpx.get(f"{BASE_URL}/api/runs", timeout=10).json()
    assert runs, "no runs imported — POST /api/import first"
    run = runs[0] if isinstance(runs, list) else runs["runs"][0]
    return run["id"]


@pytest.fixture(scope="module")
def questions_by_code() -> dict:
    questions = httpx.get(f"{BASE_URL}/api/questions", timeout=10).json()
    items = questions if isinstance(questions, list) else questions["questions"]
    return {q["code"]: q for q in items}


def test_agent_cannot_answer_human_only_question(any_run_id, questions_by_code):
    q = questions_by_code["fulfills_functions"]
    assert q["answered_by"] == "human"
    r = httpx.post(
        f"{BASE_URL}/api/runs/{any_run_id}/answers",
        json={"question_id": q["id"], "judge": "agent", "value": True},
        timeout=10,
    )
    assert r.status_code == 403, f"expected 403 for agent answer on human-only question, got {r.status_code}: {r.text}"


@pytest.mark.parametrize(
    "path",
    ["../../etc/passwd", "/etc/passwd", "../../../../Users/tylerlifke/.pi/agent/auth.json"],
)
def test_path_traversal_blocked(any_run_id, path):
    r = httpx.get(
        f"{BASE_URL}/api/runs/{any_run_id}/files/content",
        params={"path": path},
        timeout=10,
    )
    assert r.status_code in (403, 404), f"traversal via {path!r} not blocked: {r.status_code}"
    assert "<" not in r.text[:100] or r.status_code == 404  # never file contents
