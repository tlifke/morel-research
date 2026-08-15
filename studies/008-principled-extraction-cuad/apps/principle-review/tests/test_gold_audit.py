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
                    "context_before", "context_after", "start", "end",
                    "duplicate_counterparts", "has_counterpart",
                    "n_contracts_with_passage", "detected_by"):
            assert key in record
        assert record["split"] in ("dev", "holdout")
        assert record["span_text"]
        assert record["end"] - record["start"] == record["n_chars"]
        assert record_types.dotted(record, "sample.seed") is not None
    assert rt.edit_decision is None
    assert "clean" in rt.decision_names()
    assert "inconsistent_across_duplicates" in rt.decision_names()
    hotkeys = [d.hotkey for d in rt.decisions]
    assert len(hotkeys) == len(set(hotkeys))
    assert not ({"j", "k", "u", "i", "/"} & set(hotkeys))


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
    ids = [
        r["record_id"] for r in service.store.records(service.config.queue_id)
        if record_types.dotted(r["source"], "sample.draw") == "random"
    ]
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


def counterpart_record(records: list[dict]) -> dict:
    for record in records:
        if any(
            c["twin_label"] in ("marked_absent", "not_annotated")
            for c in record.get("duplicate_counterparts") or []
        ):
            return record
    raise AssertionError("fixture has no disagreeing counterpart to adjudicate")


def test_counterpart_evidence_is_present_and_judgeable():
    records = yaml_io.load_records(FIXTURE)
    record = counterpart_record(records)
    assert record["has_counterpart"] == "yes"
    assert record_types.dotted(record, "sample.draw") == "duplicate_census"
    counterpart = record["duplicate_counterparts"][0]
    for key in ("contract_id", "split", "twin_label", "doc_containment",
                "offsets", "passage"):
        assert key in counterpart
    assert counterpart["contract_id"] != record["contract_id"]
    assert counterpart["passage"].split()
    assert " ".join(counterpart["passage"].split()).lower() in " ".join(
        record["span_text"].split()
    ).lower()
    assert record["n_contracts_with_passage"] >= 1
    assert all(
        r["has_counterpart"] == ("yes" if r["duplicate_counterparts"] else "no")
        for r in records
    )


def test_inconsistent_across_duplicates_round_trips(tmp_path):
    service = make_service(tmp_path)
    record_id = counterpart_record(yaml_io.load_records(FIXTURE))["id"]
    service.save_review({
        "record_id": record_id,
        "decision": "inconsistent_across_duplicates",
        "rationale": "identical clause is marked absent in the near-twin filing",
    })
    service.export()
    exported = {r["id"]: r for r in yaml_io.load_records(tmp_path / "audited.yaml")}
    assert exported[record_id]["review"]["decision"] == "inconsistent_across_duplicates"
    assert exported[record_id]["duplicate_counterparts"] == (
        {r["id"]: r for r in yaml_io.load_records(FIXTURE)}[record_id]
    )["duplicate_counterparts"]

    revived = make_service(tmp_path / "again", source=tmp_path / "audited.yaml")
    revived.export()
    assert yaml_io.canonical_dump(
        yaml_io.load_records(tmp_path / "audited.yaml")
    ) == yaml_io.canonical_dump(
        yaml_io.load_records(tmp_path / "again" / "audited.yaml")
    )


def test_census_records_never_enter_the_random_rate(tmp_path):
    service = make_service(tmp_path)
    rows = service.store.records(service.config.queue_id)
    random_ids = [
        r["record_id"] for r in rows
        if record_types.dotted(r["source"], "sample.draw") == "random"
    ]
    census_ids = [
        r["record_id"] for r in rows
        if record_types.dotted(r["source"], "sample.draw") == "duplicate_census"
    ]
    assert random_ids and census_ids

    for record_id in random_ids:
        service.save_review({
            "record_id": record_id, "decision": "clean", "rationale": "fine"
        })
    for record_id in census_ids:
        service.save_review({
            "record_id": record_id,
            "decision": "inconsistent_across_duplicates",
            "rationale": "twin disagrees",
        })
    service.export()

    out = tmp_path / "nf.yaml"
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "aggregate_audit.py"),
         str(tmp_path / "audited.yaml"), "--out", str(out)],
        capture_output=True, text=True, cwd=str(APP_DIR),
    )
    assert result.returncode == 0, result.stderr
    report = yaml.safe_load(out.read_text())

    assert report["overall"]["defect_rate"] == 0.0
    assert report["overall"]["n_adjudicated"] == len(random_ids)
    assert report["denominator"]["n_sampled"] == len(random_ids)
    assert report["denominator"]["n_records_in_file"] == len(rows)
    assert report["duplicate_census"]["n_records"] == len(census_ids)
    assert report["duplicate_census"]["decisions"] == {
        "inconsistent_across_duplicates": len(census_ids)
    }
    assert report["duplicate_census"]["is_a_rate"] is False
    assert "inconsistent_across_duplicates" not in report["overall"]["decisions"]


def test_unruled_classes_are_reported_separately(tmp_path):
    service = make_service(tmp_path)
    rows = service.store.records(service.config.queue_id)
    random_ids = [
        r["record_id"] for r in rows
        if record_types.dotted(r["source"], "sample.draw") == "random"
    ]
    decisions = ["clean", "mislabeled", "redaction_dependent",
                 "cross_category_overlap", "clean", "clean"]
    for record_id, decision in zip(random_ids, decisions):
        service.save_review({
            "record_id": record_id, "decision": decision, "rationale": f"{decision}"
        })
    service.export()
    out = tmp_path / "nf2.yaml"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "aggregate_audit.py"),
         str(tmp_path / "audited.yaml"), "--out", str(out)],
        capture_output=True, text=True, cwd=str(APP_DIR), check=True,
    )
    report = yaml.safe_load(out.read_text())
    n = len(random_ids)
    assert report["overall"]["n_defective"] == 3
    assert report["overall"]["defect_rate"] == round(3 / n, 4)
    assert report["overall"]["n_in_unruled_classes"] == 2
    assert report["overall"]["defect_rate_excluding_unruled"] == round(1 / n, 4)
    assert set(report["provenance"]["unruled_classes"]) == {
        "redaction_dependent", "cross_category_overlap",
        "inconsistent_across_duplicates",
    }


DETECTORS = {"exact_normalized", "fuzzy_idf_jaccard"}


def test_counterparts_carry_detector_provenance():
    records = yaml_io.load_records(FIXTURE)
    census = [
        r for r in records
        if record_types.dotted(r, "sample.draw") == "duplicate_census"
    ]
    assert census
    for record in census:
        counterparts = record["duplicate_counterparts"]
        assert counterparts
        detectors = set()
        for counterpart in counterparts:
            assert counterpart["detector"] in DETECTORS
            assert 0.0 < counterpart["similarity"] <= 1.0
            assert counterpart["doc_containment"] is not None
            detectors.add(counterpart["detector"])
        assert set(record["detected_by"].split(", ")) == detectors
        if counterpart["detector"] == "exact_normalized":
            assert counterpart["similarity"] == 1.0

    found = {d for r in census for d in r["detected_by"].split(", ")}
    assert found == DETECTORS, f"fixture should exercise both detectors, got {found}"


def test_fuzzy_only_records_exist_and_are_gated():
    records = yaml_io.load_records(FIXTURE)
    fuzzy_only = [
        r for r in records if r["detected_by"] == "fuzzy_idf_jaccard"
    ]
    assert fuzzy_only, "fuzzy detector should contribute cases exact cannot find"
    for record in fuzzy_only:
        for counterpart in record["duplicate_counterparts"]:
            assert counterpart["doc_containment"] >= 0.15
            assert counterpart["twin_label"] in ("marked_absent", "not_annotated")


def test_two_detector_census_stays_out_of_the_headline_rate(tmp_path):
    service = make_service(tmp_path)
    rows = service.store.records(service.config.queue_id)
    random_ids = [
        r["record_id"] for r in rows
        if record_types.dotted(r["source"], "sample.draw") == "random"
    ]
    census_rows = [
        r for r in rows
        if record_types.dotted(r["source"], "sample.draw") == "duplicate_census"
    ]
    assert random_ids and census_rows
    detectors = {r["source"]["detected_by"] for r in census_rows}
    assert len(detectors) > 1

    for record_id in random_ids:
        service.save_review({
            "record_id": record_id, "decision": "clean", "rationale": "fine"
        })
    for row in census_rows:
        service.save_review({
            "record_id": row["record_id"],
            "decision": "inconsistent_across_duplicates",
            "rationale": "twin disagrees",
        })
    service.export()

    out = tmp_path / "nf3.yaml"
    subprocess.run(
        [sys.executable, str(SCRIPTS / "aggregate_audit.py"),
         str(tmp_path / "audited.yaml"), "--out", str(out)],
        capture_output=True, text=True, cwd=str(APP_DIR), check=True,
    )
    report = yaml.safe_load(out.read_text())

    assert report["overall"]["defect_rate"] == 0.0
    assert report["denominator"]["n_sampled"] == len(random_ids)
    assert report["duplicate_census"]["n_records"] == len(census_rows)
    by_detector = report["duplicate_census"]["by_detector"]
    assert set(by_detector) == detectors
    assert sum(
        sum(counts.values()) for counts in by_detector.values()
    ) == len(census_rows)
    assert "inconsistent_across_duplicates" not in report["overall"]["decisions"]
