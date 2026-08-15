from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from review_app import yaml_io
from review_app.record_types import get
from review_app.service import Config, ExportWouldLoseDecisions, Service

APP_DIR = Path(__file__).resolve().parent.parent
FIXTURE = APP_DIR / "fixtures" / "candidates.sample.yaml"
CONSOLE = APP_DIR / ".venv" / "bin" / "principle-review"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def launch(source: Path, db: Path, export: Path, port: int) -> subprocess.Popen:
    cmd = (
        [str(CONSOLE)]
        if CONSOLE.exists()
        else [sys.executable, "-m", "review_app.cli"]
    )
    cmd += [
        str(source),
        "--db", str(db),
        "--export", str(export),
        "--port", str(port),
        "--no-browser",
    ]
    env = dict(os.environ, PYTHONPATH=str(APP_DIR))
    return subprocess.Popen(
        cmd, cwd=str(APP_DIR), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )


def wait_up(port: int, proc: subprocess.Popen, timeout: float = 25.0) -> dict:
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        if proc.poll() is not None:
            pytest.fail(f"server exited early: {proc.communicate()[0]}")
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/api/state", timeout=2
            ) as fh:
                return json.load(fh)
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            last = exc
            time.sleep(0.25)
    pytest.fail(f"server never came up on {port}: {last}")


def post(port: int, path: str, payload: dict) -> tuple[int, dict]:
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as fh:
            return fh.status, json.load(fh)
    except urllib.error.HTTPError as exc:
        return exc.code, json.load(exc)


def decisions_of(state: dict) -> dict[str, str]:
    return {
        r["record_id"]: r["review"]["decision"]
        for r in state["records"]
        if r["review"]
    }


def kill_hard(proc: subprocess.Popen, sig: int) -> None:
    proc.send_signal(sig)
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=15)


@pytest.mark.parametrize("sig", [signal.SIGKILL, signal.SIGTERM])
def test_decisions_survive_an_unclean_kill_and_a_real_cli_relaunch(tmp_path, sig):
    source = tmp_path / "candidates.yaml"
    source.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    db = tmp_path / "state" / "review.sqlite3"
    export = tmp_path / "out.yaml"
    port = free_port()

    proc = launch(source, db, export, port)
    try:
        wait_up(port, proc)
        status, _ = post(port, "/api/review", {
            "record_id": "sp01",
            "decision": "accept",
            "rationale": "saved just before the process dies",
        })
        assert status == 200
        status, _ = post(port, "/api/review", {
            "record_id": "sp03",
            "decision": "unclear",
            "rationale": "cannot parse this statement at all",
        })
        assert status == 200
    finally:
        kill_hard(proc, sig)

    assert db.exists()
    port2 = free_port()
    proc2 = launch(source, db, export, port2)
    try:
        state = wait_up(port2, proc2)
        assert decisions_of(state) == {"sp01": "accept", "sp03": "unclear"}
        rationales = {
            r["record_id"]: r["review"]["rationale"]
            for r in state["records"] if r["review"]
        }
        assert rationales["sp01"] == "saved just before the process dies"
    finally:
        kill_hard(proc2, signal.SIGKILL)


def test_main_db_file_is_self_contained_without_its_wal(tmp_path):
    source = tmp_path / "candidates.yaml"
    source.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    db = tmp_path / "state" / "review.sqlite3"
    port = free_port()
    proc = launch(source, db, tmp_path / "out.yaml", port)
    try:
        wait_up(port, proc)
        post(port, "/api/review", {
            "record_id": "sp01", "decision": "accept", "rationale": "checkpointed?"
        })
    finally:
        kill_hard(proc, signal.SIGKILL)

    lone = tmp_path / "lone.sqlite3"
    shutil.copyfile(db, lone)
    wal = Path(str(db) + "-wal")
    assert not wal.exists() or wal.stat().st_size == 0

    service = Service(Config(
        source=source, db=lone, record_type="principle",
        reviewer="tyler", export_path=tmp_path / "lone_out.yaml",
    ))
    rows = {r["record_id"]: r for r in service.store.records(str(source.resolve()))}
    assert rows["sp01"]["review"]["decision"] == "accept"


def test_losing_the_entire_state_dir_is_recoverable_from_the_exported_yaml(tmp_path):
    source = tmp_path / "candidates.yaml"
    source.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    state = tmp_path / "state"
    export = tmp_path / "candidates.reviewed.yaml"

    first = Service(Config(
        source=source, db=state / "review.sqlite3", record_type="principle",
        reviewer="tyler", export_path=export,
    ))
    first.sync_from_disk()
    first.save_review({
        "record_id": "sp01", "decision": "accept", "rationale": "real convention"
    })
    first.save_review({
        "record_id": "sp02", "decision": "edit", "rationale": "narrowed the scope",
        "edits": {"statement": "A floor on purchase quantity is Minimum Commitment."},
    })
    first.save_review({
        "record_id": "sp03", "decision": "defer", "rationale": "need the footprint"
    })
    first.save_review({
        "record_id": "sp04", "decision": "unclear", "rationale": "unparseable"
    })
    first.export()
    before = yaml_io.load_records(export)
    first.store.close()

    shutil.rmtree(state)
    assert not state.exists()

    revived = Service(Config(
        source=export, db=state / "review.sqlite3", record_type="principle",
        reviewer="tyler", export_path=tmp_path / "again.yaml",
    ))
    report = revived.sync_from_disk()
    assert sorted(report["adopted_from_file"]) == ["sp01", "sp02", "sp03", "sp04"]
    assert report["kept_from_db"] == []
    assert report["conflicts"] == []

    rows = {r["record_id"]: r for r in revived.store.records(revived.config.queue_id)}
    assert rows["sp01"]["review"]["decision"] == "accept"
    assert rows["sp01"]["review"]["rationale"] == "real convention"
    assert rows["sp04"]["review"]["decision"] == "unclear"

    revived.export()
    assert yaml_io.canonical_dump(before) == yaml_io.canonical_dump(
        yaml_io.load_records(tmp_path / "again.yaml")
    )


def test_adopted_edit_reconstructs_edited_from_and_the_original_source(tmp_path):
    source = tmp_path / "candidates.yaml"
    source.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    export = tmp_path / "reviewed.yaml"
    first = Service(Config(
        source=source, db=tmp_path / "a.sqlite3", record_type="principle",
        reviewer="tyler", export_path=export,
    ))
    first.sync_from_disk()
    first.save_review({
        "record_id": "sp02", "decision": "edit", "rationale": "tightened",
        "edits": {
            "statement": "A floor on purchase quantity is Minimum Commitment.",
            "scope": ["minimum_commitment"],
        },
    })
    first.export()

    revived = Service(Config(
        source=export, db=tmp_path / "b.sqlite3", record_type="principle",
        reviewer="tyler", export_path=tmp_path / "again.yaml",
    ))
    revived.sync_from_disk()
    row = {r["record_id"]: r for r in revived.store.records(revived.config.queue_id)}["sp02"]
    assert "even when the same sentence" in row["source"]["statement"]
    assert row["source"]["scope"] == ["minimum_commitment", "volume_restriction"]
    assert row["edits"]["statement"].startswith("A floor on purchase quantity is")

    revived.export()
    out = {r["id"]: r for r in yaml_io.load_records(tmp_path / "again.yaml")}["sp02"]
    assert out["statement"] == "A floor on purchase quantity is Minimum Commitment."
    assert out["scope"] == ["minimum_commitment"]
    prior = out["review"]["edited_from"]
    assert "even when the same sentence" in prior["statement"]
    assert prior["scope"] == ["minimum_commitment", "volume_restriction"]


def test_the_store_wins_over_the_file_and_the_disagreement_is_reported(tmp_path):
    source = tmp_path / "candidates.yaml"
    records = yaml_io.load_records(FIXTURE)
    for record in records[:2]:
        record["review"] = {
            "decision": "accept",
            "reviewer": "tyler",
            "date": "2026-08-14",
            "rationale": "decided in a previous session",
        }
    source.write_text(yaml_io.dump_yaml(records, get("principle")), encoding="utf-8")

    service = Service(Config(
        source=source, db=tmp_path / "review.sqlite3", record_type="principle",
        reviewer="tyler", export_path=tmp_path / "out.yaml",
    ))
    report = service.sync_from_disk()
    assert sorted(report["adopted_from_file"]) == ["sp01", "sp02"]

    service.save_review({
        "record_id": "sp01", "decision": "reject", "rationale": "changed my mind"
    })
    report = service.sync_from_disk()
    assert report["adopted_from_file"] == []
    assert sorted(report["kept_from_db"]) == ["sp01", "sp02"]
    assert report["conflicts"] == [{
        "record_id": "sp01",
        "kept_from_db": "reject",
        "ignored_from_file": "accept",
    }]
    rows = {r["record_id"]: r for r in service.store.records(service.config.queue_id)}
    assert rows["sp01"]["review"]["decision"] == "reject"


def test_adoption_preserves_the_original_review_date_and_is_marked_in_history(tmp_path):
    source = tmp_path / "candidates.yaml"
    records = yaml_io.load_records(FIXTURE)
    records[0]["review"] = {
        "decision": "accept", "reviewer": "tyler",
        "date": "2026-08-14", "rationale": "from round one",
    }
    source.write_text(yaml_io.dump_yaml(records, get("principle")), encoding="utf-8")
    service = Service(Config(
        source=source, db=tmp_path / "review.sqlite3", record_type="principle",
        reviewer="tyler", export_path=tmp_path / "out.yaml",
    ))
    service.sync_from_disk()
    history = service.history("sp01")
    assert len(history) == 1
    assert history[0]["review_date"] == "2026-08-14"
    assert history[0]["origin"] == "import"

    service.save_review({
        "record_id": "sp01", "decision": "reject", "rationale": "on reflection, no"
    })
    history = service.history("sp01")
    assert [h["origin"] for h in history] == ["import", "app"]


def test_export_refuses_to_replace_a_file_that_holds_more_decisions(tmp_path):
    source = tmp_path / "candidates.yaml"
    source.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    export = tmp_path / "reviewed.yaml"

    first = Service(Config(
        source=source, db=tmp_path / "a.sqlite3", record_type="principle",
        reviewer="tyler", export_path=export,
    ))
    first.sync_from_disk()
    for rid in ("sp01", "sp02", "sp03"):
        first.save_review({
            "record_id": rid, "decision": "accept", "rationale": "fine"
        })
    first.export()
    before = export.read_text(encoding="utf-8")

    empty = Service(Config(
        source=source, db=tmp_path / "b.sqlite3", record_type="principle",
        reviewer="tyler", export_path=export,
    ))
    empty.sync_from_disk()
    with pytest.raises(ExportWouldLoseDecisions) as excinfo:
        empty.export()
    assert "3 decided" in str(excinfo.value)
    assert export.read_text(encoding="utf-8") == before

    result = empty.export(force=True)
    assert result["n"] == 6
    assert export.read_text(encoding="utf-8") != before


def test_export_guard_allows_equal_or_growing_decision_counts(tmp_path):
    source = tmp_path / "candidates.yaml"
    source.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    export = tmp_path / "reviewed.yaml"
    service = Service(Config(
        source=source, db=tmp_path / "a.sqlite3", record_type="principle",
        reviewer="tyler", export_path=export,
    ))
    service.sync_from_disk()
    service.save_review({
        "record_id": "sp01", "decision": "accept", "rationale": "fine"
    })
    service.export()
    service.export()
    service.save_review({
        "record_id": "sp02", "decision": "defer", "rationale": "later"
    })
    assert service.export()["counts"]["defer"] == 1


def test_export_over_an_empty_target_and_a_fresh_path_is_unguarded(tmp_path):
    source = tmp_path / "candidates.yaml"
    source.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    service = Service(Config(
        source=source, db=tmp_path / "a.sqlite3", record_type="principle",
        reviewer="tyler", export_path=tmp_path / "fresh.yaml",
    ))
    service.sync_from_disk()
    assert service.export()["n"] == 6
    blank = tmp_path / "blank.yaml"
    blank.write_text("[]\n", encoding="utf-8")
    assert service.export(str(blank))["n"] == 6
