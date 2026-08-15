from __future__ import annotations

from pathlib import Path

import pytest

from review_app import record_types, yaml_io
from review_app.service import Config, Service

APP_DIR = Path(__file__).resolve().parent.parent
FIXTURE = APP_DIR / "fixtures" / "candidates.sample.yaml"


def make_service(tmp_path: Path, source: Path | None = None) -> Service:
    src = source or FIXTURE
    config = Config(
        source=src,
        db=tmp_path / "review.sqlite3",
        record_type="principle",
        reviewer="tyler",
        export_path=tmp_path / "out.yaml",
    )
    service = Service(config)
    service.sync_from_disk()
    return service


def test_import_export_is_lossless(tmp_path):
    service = make_service(tmp_path)
    service.export()
    original = yaml_io.load_records(FIXTURE)
    exported = yaml_io.load_records(tmp_path / "out.yaml")
    assert yaml_io.canonical_dump(original) == yaml_io.canonical_dump(exported)


def test_review_roundtrip_and_reimport(tmp_path):
    service = make_service(tmp_path)
    service.save_review({
        "record_id": "sp01",
        "decision": "accept",
        "rationale": "real convention, checker is trivially computable",
    })
    service.save_review({
        "record_id": "sp02",
        "decision": "edit",
        "rationale": "narrowed to purchase quantity only; checker needed a real threshold",
        "edits": {
            "statement": "A floor on purchase quantity is Minimum Commitment.",
            "checker_sketch": "span matches the minimum-threshold lexicon -> applicable",
            "scope": ["minimum_commitment"],
            "trigger_guidance": "Consider whenever a span states a quantity floor.",
        },
    })
    service.save_review({
        "record_id": "sp06",
        "decision": "reject",
        "rationale": "not checkable without a parser we do not have",
    })
    service.save_review({
        "record_id": "sp05",
        "decision": "defer",
        "rationale": "need the guidelines PDF before deciding",
    })
    out = service.export()
    assert out["counts"] == {
        "accept": 1, "edit": 1, "reject": 1, "defer": 1, "unreviewed": 2
    }

    records = {r["id"]: r for r in yaml_io.load_records(tmp_path / "out.yaml")}
    assert len(records) == 6
    assert records["sp06"]["review"]["decision"] == "reject"
    assert records["sp01"]["review"]["reviewer"] == "tyler"
    assert records["sp01"]["review"]["rationale"].startswith("real convention")
    edited = records["sp02"]
    assert edited["statement"] == "A floor on purchase quantity is Minimum Commitment."
    prior = edited["review"]["edited_from"]
    assert set(prior) == {"statement", "checker_sketch", "scope", "trigger_guidance"}
    assert "even when the same sentence" in prior["statement"]
    assert prior["scope"] == ["minimum_commitment", "volume_restriction"]
    assert prior["checker_sketch"].startswith("span matched by the minimum-threshold")
    assert "type" not in prior
    assert list(records["sp01"].keys())[0] == "id"
    assert "edited_from" not in records["sp01"]["review"]
    assert "edited_from" not in records["sp06"]["review"]

    reimported = make_service(tmp_path / "second", source=tmp_path / "out.yaml")
    reimported.export()
    assert yaml_io.canonical_dump(
        yaml_io.load_records(tmp_path / "out.yaml")
    ) == yaml_io.canonical_dump(
        yaml_io.load_records(tmp_path / "second" / "out.yaml")
    )


def test_bare_string_edited_from_is_coerced_on_import(tmp_path):
    source = tmp_path / "legacy.yaml"
    records = yaml_io.load_records(FIXTURE)
    records[0]["review"] = {
        "decision": "edit",
        "reviewer": "tyler",
        "date": "2026-08-14",
        "rationale": "tightened wording",
        "edited_from": "the verbatim statement the model originally proposed",
    }
    source.write_text(
        yaml_io.dump_yaml(records, record_types.get("principle")), encoding="utf-8"
    )
    service = make_service(tmp_path, source=source)
    rows = {r["record_id"]: r for r in service.store.records(service.config.queue_id)}
    stored = rows["sp01"]["source"]["review"]["edited_from"]
    assert stored == {
        "statement": "the verbatim statement the model originally proposed"
    }
    service.export()
    exported = {r["id"]: r for r in yaml_io.load_records(tmp_path / "out.yaml")}
    assert exported["sp01"]["review"]["edited_from"] == stored


def test_rationale_is_required(tmp_path):
    service = make_service(tmp_path)
    for rationale in ("", "   ", None):
        with pytest.raises(ValueError):
            service.save_review({
                "record_id": "sp01", "decision": "accept", "rationale": rationale
            })
    with pytest.raises(ValueError):
        service.save_review({
            "record_id": "sp01", "decision": "banish", "rationale": "no"
        })
    with pytest.raises(ValueError):
        service.save_review({
            "record_id": "sp01", "decision": "edit", "rationale": "no change made"
        })


def test_persistence_survives_restart(tmp_path):
    service = make_service(tmp_path)
    service.save_review({
        "record_id": "sp03", "decision": "defer", "rationale": "ask Tyler about scope"
    })
    service.store.save_draft("x", "y", {"rationale": "half-typed thought"})
    service.store.save_draft(service.config.queue_id, "sp04",
                             {"rationale": "half-typed thought", "decision": None, "edits": {}})
    service.store.close()

    revived = make_service(tmp_path)
    rows = {r["record_id"]: r for r in revived.store.records(revived.config.queue_id)}
    assert rows["sp03"]["review"]["decision"] == "defer"
    assert rows["sp03"]["review"]["rationale"] == "ask Tyler about scope"
    assert rows["sp04"]["draft"]["rationale"] == "half-typed thought"
    assert rows["sp01"]["review"] is None


def test_decision_can_be_changed_and_history_kept(tmp_path):
    service = make_service(tmp_path)
    service.save_review({
        "record_id": "sp01", "decision": "reject", "rationale": "first pass: too vague"
    })
    service.save_review({
        "record_id": "sp01", "decision": "accept", "rationale": "second pass: fine as is"
    })
    rows = {r["record_id"]: r for r in service.store.records(service.config.queue_id)}
    assert rows["sp01"]["review"]["decision"] == "accept"
    history = service.history("sp01")
    assert [h["decision"] for h in history] == ["reject", "accept"]

    service.save_review({
        "record_id": "sp02", "decision": "edit", "rationale": "tighten",
        "edits": {"statement": "Tightened statement."},
    })
    service.save_review({
        "record_id": "sp02", "decision": "accept", "rationale": "original was fine"
    })
    service.export()
    exported = {r["id"]: r for r in yaml_io.load_records(tmp_path / "out.yaml")}
    assert "edited_from" not in exported["sp02"]["review"]
    assert exported["sp02"]["statement"].startswith("A floor on purchase quantity is")
    assert "even when the same sentence" in exported["sp02"]["statement"]


def test_reimport_preserves_reviews_and_picks_up_new_records(tmp_path):
    source = tmp_path / "candidates.yaml"
    source.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    service = make_service(tmp_path, source=source)
    service.save_review({
        "record_id": "sp01", "decision": "accept", "rationale": "keep"
    })
    records = yaml_io.load_records(source)
    records.append({
        "id": "sp07",
        "statement": "New candidate added after review started.",
        "trigger_guidance": "n/a",
        "type": "authored",
        "scope": [],
        "provenance": "authored",
        "evidence": ["none"],
        "checker_sketch": "n/a",
    })
    source.write_text(yaml_io.dump_yaml(records, service.rt), encoding="utf-8")
    counts = service.sync_from_disk()
    assert counts["added"] == 1
    rows = {r["record_id"]: r for r in service.store.records(service.config.queue_id)}
    assert rows["sp01"]["review"]["decision"] == "accept"
    assert rows["sp07"]["review"] is None
