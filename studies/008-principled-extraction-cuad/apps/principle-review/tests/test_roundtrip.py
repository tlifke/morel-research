from __future__ import annotations

from pathlib import Path

import pytest

from review_app import record_types, sidecars, yaml_io
from review_app.service import Config, Service

APP_DIR = Path(__file__).resolve().parent.parent
FIXTURE = APP_DIR / "fixtures" / "candidates.sample.yaml"
PAIRS = APP_DIR / "fixtures" / "mined_pairs.jsonl"
FOOTPRINT = APP_DIR / "fixtures" / "footprint.yaml"
PILOT = (
    APP_DIR.parent.parent / "principles" / "pilot" / "candidates_pilot.reviewed.yaml"
)


def make_service(
    tmp_path: Path,
    source: Path | None = None,
    pairs: Path | None = None,
    footprint: Path | None = None,
) -> Service:
    src = source or FIXTURE
    config = Config(
        source=src,
        db=tmp_path / "review.sqlite3",
        record_type="principle",
        reviewer="tyler",
        export_path=tmp_path / "out.yaml",
        pairs_path=pairs,
        footprint_path=footprint,
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
        "accept": 1, "edit": 1, "reject": 1, "defer": 1, "unclear": 0, "unreviewed": 2
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


def test_unclear_is_a_distinct_decision_from_defer(tmp_path):
    rt = record_types.get("principle")
    assert "unclear" in rt.decision_names()
    assert "unclear" in rt.pending_decisions
    assert "defer" in rt.pending_decisions

    service = make_service(tmp_path)
    service.save_review({
        "record_id": "sp01",
        "decision": "unclear",
        "rationale": "cannot tell what 'role designator' is meant to cover",
    })
    service.save_review({
        "record_id": "sp02",
        "decision": "defer",
        "rationale": "clear enough, but I want the footprint first",
    })
    out = service.export()
    assert out["counts"]["unclear"] == 1
    assert out["counts"]["defer"] == 1

    exported = {r["id"]: r for r in yaml_io.load_records(tmp_path / "out.yaml")}
    assert exported["sp01"]["review"]["decision"] == "unclear"
    assert exported["sp02"]["review"]["decision"] == "defer"

    revived = make_service(tmp_path / "second", source=tmp_path / "out.yaml")
    rows = {r["record_id"]: r for r in revived.store.records(revived.config.queue_id)}
    assert rows["sp01"]["source"]["review"]["decision"] == "unclear"
    assert rows["sp02"]["source"]["review"]["decision"] == "defer"


def test_unclear_requires_a_rationale(tmp_path):
    service = make_service(tmp_path)
    with pytest.raises(ValueError):
        service.save_review({
            "record_id": "sp01", "decision": "unclear", "rationale": "  "
        })


def test_export_counts_list_every_decision_even_at_zero(tmp_path):
    service = make_service(tmp_path)
    counts = service.export()["counts"]
    for name in record_types.get("principle").decision_names():
        assert name in counts
    assert counts["reject"] == 0
    assert counts["unclear"] == 0


def test_pairs_sidecar_is_indexed_by_pair_id(tmp_path):
    service = make_service(tmp_path, pairs=PAIRS, footprint=FOOTPRINT)
    state = service.state()
    pairs = state["sidecars"]["pairs"]
    assert "pair-0412" in pairs
    left = pairs["pair-0412"]["left"]
    right = pairs["pair-0412"]["right"]
    assert left["category"] != right["category"]
    assert left["text"] and right["text"]
    cited = set()
    for row in state["records"]:
        for item in row["merged"].get("evidence") or []:
            if isinstance(item, str) and item.startswith("pair-"):
                cited.add(item)
    assert cited & set(pairs)
    assert state["sidecar_paths"]["pairs"] == str(PAIRS)


def test_footprint_sidecar_shape(tmp_path):
    service = make_service(tmp_path, pairs=PAIRS, footprint=FOOTPRINT)
    fp = service.state()["sidecars"]["footprint"]
    assert fp["split"] == "dev"
    assert fp["population"]["n_units"] == 732
    entry = fp["principles"]["sp01"]
    assert entry["applicability"]["n_applicable"] == 143
    assert entry["distribution"]["rows"][0]["key"]
    assert entry["discrimination"]["pass_rate_positive"] == 0.86
    assert fp["principles"]["sp02"]["status"] == "not_implementable"


def test_sidecars_absent_degrade_to_empty(tmp_path):
    service = make_service(tmp_path)
    state = service.state()
    assert state["sidecars"] == {"pairs": {}, "footprint": {}}
    assert state["sidecar_paths"] == {"pairs": None, "footprint": None}


def test_footprint_accepts_a_bare_id_keyed_mapping(tmp_path):
    path = tmp_path / "fp.yaml"
    path.write_text(
        "sp01:\n  applicability:\n    n_applicable: 3\n    n_units: 10\n",
        encoding="utf-8",
    )
    loaded = sidecars.load_footprint(path)
    assert loaded["principles"]["sp01"]["applicability"]["n_units"] == 10


def test_footprint_is_reloaded_when_the_file_changes(tmp_path):
    path = tmp_path / "fp.yaml"
    path.write_text("principles:\n  sp01:\n    note: first\n", encoding="utf-8")
    service = make_service(tmp_path, footprint=path)
    assert service.state()["sidecars"]["footprint"]["principles"]["sp01"]["note"] == "first"
    path.write_text("principles:\n  sp01:\n    note: second\n", encoding="utf-8")
    assert service.state()["sidecars"]["footprint"]["principles"]["sp01"]["note"] == "second"


def test_round_one_pilot_decisions_survive_reimport(tmp_path):
    if not PILOT.exists():
        pytest.skip("pilot review file not present")
    raw = PILOT.read_text(encoding="utf-8")
    before = yaml_io.load_records(PILOT)
    service = make_service(tmp_path, source=PILOT, pairs=PAIRS, footprint=FOOTPRINT)
    service.export()
    after = yaml_io.load_records(tmp_path / "out.yaml")
    assert yaml_io.canonical_dump(before) == yaml_io.canonical_dump(after)
    assert PILOT.read_text(encoding="utf-8") == raw
    reviews = {r["id"]: (r.get("review") or {}).get("decision") for r in after}
    assert reviews == {
        r["id"]: (r.get("review") or {}).get("decision") for r in before
    }
    assert set(reviews.values()) <= set(service.rt.decision_names()) | {None}
