import sys
from pathlib import Path

import pytest
import yaml

ROUND2 = Path(__file__).resolve().parents[2]
PILOT = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parents[5]
for path in (str(STUDY / "scripts"), str(PILOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from round2.checkers import checkers2 as C  # noqa: E402
from round2.checkers import lexicons2 as L2  # noqa: E402
from round2.checkers.run_footprints2 import (  # noqa: E402
    GOLD_DEPENDENCY,
    SEPARABILITY_VERDICT,
    STRUCTURAL_EMPTY,
    phi,
)


class Span:
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


class Label:
    def __init__(self, is_impossible=False, spans=()):
        self.is_impossible = is_impossible
        self.spans = list(spans)


class Fake:
    def __init__(self, text, gold=None, contract_id="c1", title="Agreement"):
        self.text = text
        self.title = title
        self.contract_id = contract_id
        self.n_tokens = len(text.split())
        self.gold = gold or {}


CANDIDATES = yaml.safe_load(
    (PILOT / "candidates_round2.yaml").read_text()
)
IDS = [record["id"] for record in CANDIDATES]


def test_every_candidate_has_a_checker():
    assert sorted(C.REGISTRY) == sorted(IDS)
    assert len(IDS) == 23


def test_matched_and_fresh_partition_the_set():
    assert set(C.MATCHED) | set(C.FRESH) == set(IDS)
    assert not set(C.MATCHED) & set(C.FRESH)


def test_declared_scope_matches_candidates_file():
    by_id = {record["id"]: record for record in CANDIDATES}
    for pid, checker in C.REGISTRY.items():
        declared = list(by_id[pid]["scope"] or [])
        if pid == "p12":
            assert set(checker.scope) == set(declared)
        elif declared:
            assert list(checker.scope) == declared
        else:
            assert checker.scope == []


def test_every_id_has_a_gold_dependency_and_verdict():
    for pid in IDS:
        assert pid in GOLD_DEPENDENCY
        assert GOLD_DEPENDENCY[pid] in STRUCTURAL_EMPTY
        assert GOLD_DEPENDENCY[pid] in SEPARABILITY_VERDICT


def test_phi_is_symmetric_and_bounded():
    assert phi(10, 0, 0, 10) == pytest.approx(1.0)
    assert phi(0, 10, 10, 0) == pytest.approx(-1.0)
    assert phi(5, 5, 5, 5) == pytest.approx(0.0)
    assert phi(1, 0, 0, 0) is None


def test_p05_is_universal():
    inst = Fake("anything")
    assert C.p05(inst, "Governing Law") is True


def test_p09_needs_quantity_and_ceiling_in_one_sentence():
    yes = Fake("Buyer shall not exceed 5,000 units per quarter. Other text.")
    no_quantity = Fake("Buyer shall not exceed the agreed maximum. Other text.")
    split_sentences = Fake("Buyer may order 5,000 units. Buyer shall not exceed the cap.")
    assert C.p09(yes, "Volume Restriction") is True
    assert C.p09(no_quantity, "Volume Restriction") is False
    assert C.p09(split_sentences, "Volume Restriction") is False


def test_p09_scope_is_enforced_by_the_registry():
    inst = Fake("Buyer shall not exceed 5,000 units per quarter.")
    checker = C.REGISTRY["p09"]
    assert checker.applies(inst, "Volume Restriction") is True
    assert checker.applies(inst, "Governing Law") is False


def test_p12_covers_the_three_single_value_categories_only():
    gold = {
        "Agreement Date": Label(spans=[Span(0, 5, "abcde")]),
        "Expiration Date": Label(spans=[Span(0, 5, "abcde")]),
        "Exclusivity": Label(spans=[Span(0, 5, "abcde")]),
    }
    inst = Fake("abcdefg", gold)
    assert C.p12(inst, "Agreement Date") is True
    assert C.p12(inst, "Expiration Date") is True
    assert C.p12(inst, "Exclusivity") is False


def test_p12_is_gated_on_gold_presence():
    inst = Fake("abcdefg", {"Agreement Date": Label(is_impossible=True)})
    assert C.p12(inst, "Agreement Date") is False


def test_p17_requires_a_conflicts_tail_near_a_governing_law_cue():
    text = (
        "This Agreement shall be governed by the laws of the State of New York, "
        "without regard to the conflicts of laws principles."
    )
    gold = {"Governing Law": Label(spans=[Span(0, 10, "This Agree")])}
    assert C.p17(Fake(text, gold), "Governing Law") is True
    far = Fake("A" * 4000 + text[:70] + "B" * 4000 + text[70:], gold)
    assert C.p17(far, "Governing Law") is False


def test_p17_as_written_misses_the_its_variant():
    text = (
        "This Agreement shall be governed by the laws of New York, without regard "
        "to its conflicts of laws principles."
    )
    gold = {"Governing Law": Label(spans=[Span(0, 10, "This Agree")])}
    assert C.p17(Fake(text, gold), "Governing Law") is False
    assert (
        C.p17(Fake(text, gold), "Governing Law", tail=L2.CONFLICTS_TAIL_WIDE) is True
    )


def test_p17_is_gated_on_gold_presence():
    text = (
        "This Agreement shall be governed by the laws of New York, without regard "
        "to the conflicts of laws principles."
    )
    inst = Fake(text, {"Governing Law": Label(is_impossible=True)})
    assert C.p17(inst, "Governing Law") is False


def test_p20_heading_must_follow_the_execution_block():
    before = (
        "EXHIBIT A\nPricing.\nIN WITNESS WHEREOF the parties have executed this Agreement.\n"
    )
    after = "IN WITNESS WHEREOF the parties have executed this Agreement.\nEXHIBIT B\nPricing.\n"
    gold = {"Governing Law": Label(spans=[Span(0, 5, "EXHIB")])}
    assert C.p20(Fake(after, gold), "Governing Law") is True
    assert C.p20(Fake(before, gold), "Governing Law") is False


def test_p20_requires_an_execution_block():
    text = "EXHIBIT B\nPricing.\n"
    gold = {"Governing Law": Label(spans=[Span(0, 5, "EXHIB")])}
    assert C.p20(Fake(text, gold), "Governing Law") is False


def test_p21_requires_a_date_after_the_execution_block():
    gold = {"Agreement Date": Label(spans=[Span(0, 4, "This")])}
    yes = "This Agreement. IN WITNESS WHEREOF, signed January 5, 2001 by the parties."
    no = "Dated January 5, 2001. IN WITNESS WHEREOF, the parties signed below."
    assert C.p21(Fake(yes, gold), "Agreement Date") is True
    assert C.p21(Fake(no, gold), "Agreement Date") is False


def test_p03_shared_substring_detection():
    common = "x" * 500
    texts = {
        "a": "AMENDMENT to the Prior Agreement. " + common,
        "b": "Unrelated preamble. " + common,
        "c": "AMENDMENT to something else entirely, with nothing in common.",
    }
    shared = C.set_corpus(texts)
    assert shared == {"a", "b"}
    assert C.p03(Fake(texts["a"], contract_id="a", title="Amendment"), "Governing Law") is True
    assert C.p03(Fake(texts["c"], contract_id="c", title="Amendment"), "Governing Law") is False
    assert (
        C.p03(
            Fake(texts["b"], contract_id="b", title="Supply Agreement"),
            "Governing Law",
        )
        is False
    )


def test_p03_raises_without_a_corpus():
    C.CORPUS["derivative_shared_ids"] = None
    with pytest.raises(RuntimeError):
        C.p03(Fake("AMENDMENT No. 1", contract_id="z", title="Amendment"), "Governing Law")


def test_lexicon_ceiling_widening_is_a_superset():
    sample = "shall not exceed the cap of 5,000 units, up to a maximum, in excess of the limit"
    narrow = set(L2.CEILING_CUE_NARROW.findall(sample))
    wide = set(L2.CEILING_CUE_WIDE.findall(sample))
    assert narrow <= wide


def test_sidecar_is_complete_and_conforms():
    path = ROUND2 / "footprint.yaml"
    if not path.exists():
        pytest.skip("footprint.yaml not generated yet")
    data = yaml.safe_load(path.read_text())
    assert data["schema_version"] == 1
    assert data["split"] == "dev"
    assert sorted(data["principles"]) == sorted(IDS)
    for pid, entry in data["principles"].items():
        assert entry["status"]
        assert entry["note"]
        app = entry["applicability"]
        assert app["n_units"] == 480
        assert 0.0 <= app["rate"] <= 1.0
        assert app["n_applicable"] <= app["n_units"]
        assert entry["distribution"]["by"] == "category"
        assert len(entry["distribution"]["rows"]) == 12
        assert entry["separability"]["verdict"] in {"pass", "fail", "partial", "pass-but-vacuous"}


def test_sidecar_structural_empties_are_actually_empty():
    path = ROUND2 / "footprint.yaml"
    if not path.exists():
        pytest.skip("footprint.yaml not generated yet")
    data = yaml.safe_load(path.read_text())
    for pid, entry in data["principles"].items():
        sep = entry["separability"]
        for cell in sep["structurally_empty_cells"]:
            assert sep["twobytwo_applicability_x_gold"][cell] == 0, (pid, cell)
