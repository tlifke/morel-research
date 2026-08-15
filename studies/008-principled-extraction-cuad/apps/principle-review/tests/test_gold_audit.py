from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from review_app import record_types, yaml_io
from review_app.service import Config, Service

APP_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = APP_DIR / "scripts"
FIXTURE = APP_DIR / "fixtures" / "gold_audit.sample.yaml"


def make_service(tmp_path: Path, source: Path | None = None) -> Service:
    config = Config(
        source=source or FIXTURE,
        db=tmp_path / "audit.sqlite3",
        record_type="gold_audit",
        reviewer="tyler",
        export_path=tmp_path / "audited.yaml",
    )
    service = Service(config)
    service.sync_from_disk()
    return service


def test_fixture_matches_declared_schema():
    rt = record_types.get("gold_audit")
    records = yaml_io.load_records(FIXTURE)
    assert records
    for record in records:
        for key in ("id", "contract_id", "split", "category", "span_text",
                    "context_before", "context_after", "start", "end"):
            assert key in record
        assert record["split"] in ("dev", "holdout")
        assert record["span_text"]
        assert record["end"] - record["start"] == record["n_chars"]
        assert record_types.dotted(record, "sample.seed") is not None
    assert rt.edit_decision is None
    assert "clean" in rt.decision_names()


def test_import_export_is_lossless(tmp_path):
    service = make_service(tmp_path)
    service.export()
    assert yaml_io.canonical_dump(yaml_io.load_records(FIXTURE)) == yaml_io.canonical_dump(
        yaml_io.load_records(tmp_path / "audited.yaml")
    )


def test_defect_decisions_round_trip(tmp_path):
    service = make_service(tmp_path)
    ids = [r["record_id"] for r in service.store.records(service.config.queue_id)]
    calls = [
        (ids[0], "clean", "span is the governing-law sentence, nothing else"),
        (ids[1], "artifact_split", "page footer splits one sentence into two spans"),
        (ids[2], "mislabeled", "span is a heading fragment, not a license grant"),
        (ids[3], "boundary_jitter", "starts two chars into the date"),
        (ids[4], "defer", "need the sibling span to decide"),
    ]
    for record_id, decision, rationale in calls:
        service.save_review({
            "record_id": record_id, "decision": decision, "rationale": rationale
        })
    out = service.export()
    assert out["counts"]["clean"] == 1
    assert out["counts"]["artifact_split"] == 1

    exported = {r["id"]: r for r in yaml_io.load_records(tmp_path / "audited.yaml")}
    assert exported[ids[1]]["review"]["decision"] == "artifact_split"
    assert exported[ids[1]]["review"]["reviewer"] == "tyler"
    assert exported[ids[1]]["review"]["rationale"].startswith("page footer")
    assert "edited_from" not in exported[ids[0]]["review"]
    assert list(exported[ids[0]].keys())[:5] == [
        "id", "contract_id", "title", "split", "category"
    ]
    assert exported[ids[0]]["span_text"] == yaml_io.load_records(FIXTURE)[0]["span_text"]

    revived = make_service(tmp_path / "again", source=tmp_path / "audited.yaml")
    revived.export()
    assert yaml_io.canonical_dump(
        yaml_io.load_records(tmp_path / "audited.yaml")
    ) == yaml_io.canonical_dump(
        yaml_io.load_records(tmp_path / "again" / "audited.yaml")
    )


def test_rationale_required_and_vocabulary_enforced(tmp_path):
    service = make_service(tmp_path)
    record_id = service.store.records(service.config.queue_id)[0]["record_id"]
    with pytest.raises(ValueError):
        service.save_review({
            "record_id": record_id, "decision": "clean", "rationale": "  "
        })
    with pytest.raises(ValueError):
        service.save_review({
            "record_id": record_id, "decision": "accept", "rationale": "wrong vocabulary"
        })


def test_edits_are_inert_without_an_edit_decision(tmp_path):
    service = make_service(tmp_path)
    record_id = service.store.records(service.config.queue_id)[0]["record_id"]
    original = yaml_io.load_records(FIXTURE)[0]["span_text"]
    service.save_review({
        "record_id": record_id,
        "decision": "mislabeled",
        "rationale": "gold text is not editable in this workflow",
        "edits": {"span_text": "tampered"},
    })
    service.export()
    exported = {r["id"]: r for r in yaml_io.load_records(tmp_path / "audited.yaml")}
    assert exported[record_id]["span_text"] == original


def test_persistence_survives_restart(tmp_path):
    service = make_service(tmp_path)
    record_id = service.store.records(service.config.queue_id)[0]["record_id"]
    service.save_review({
        "record_id": record_id, "decision": "redaction_dependent",
        "rationale": "decisive clause body is *****",
    })
    service.store.close()
    revived = make_service(tmp_path)
    rows = {r["record_id"]: r for r in revived.store.records(revived.config.queue_id)}
    assert rows[record_id]["review"]["decision"] == "redaction_dependent"


def test_aggregation_artifact(tmp_path):
    service = make_service(tmp_path)
    ids = [r["record_id"] for r in service.store.records(service.config.queue_id)]
    decisions = [
        "clean", "clean", "artifact_split", "mislabeled", "boundary_jitter", "defer",
    ]
    for record_id, decision in zip(ids, decisions):
        service.save_review({
            "record_id": record_id, "decision": decision, "rationale": f"{decision} call"
        })
    service.export()

    out = tmp_path / "noise_floor.yaml"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "aggregate_audit.py"),
         str(tmp_path / "audited.yaml"), "--out", str(out)],
        capture_output=True, text=True, cwd=str(APP_DIR),
    )
    assert result.returncode == 0, result.stderr
    report = yaml.safe_load(out.read_text())

    assert report["overall"]["n_adjudicated"] == 5
    assert report["overall"]["n_defective"] == 3
    assert report["overall"]["defect_rate"] == 0.6
    assert report["denominator"]["n_sampled"] == len(ids)
    assert report["denominator"]["n_unreviewed"] == len(ids) - len(decisions)
    assert report["provenance"]["sampler_seeds"] == [20260815]
    assert report["provenance"]["reviewers"] == ["tyler"]
    assert "defer" not in report["per_defect"]
    assert report["per_defect"]["artifact_split"]["n"] == 1
    assert set(report["per_split"]) <= {"dev", "holdout"}

    def keys(node):
        if isinstance(node, dict):
            return set(node) | {k for v in node.values() for k in keys(v)}
        if isinstance(node, list):
            return {k for v in node for k in keys(v)}
        return set()

    assert not any(
        "f1" in k.lower() or "ceiling" in k.lower() for k in keys(report)
    )
    assert "deliberately not performed" in report["note"]
