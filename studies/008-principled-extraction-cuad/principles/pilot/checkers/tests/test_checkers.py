import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDY = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(STUDY / "scripts"))

from checkers.checkers import REGISTRY  # noqa: E402
from checkers.span_predicates import (  # noqa: E402
    g05_entitlement_signal,
    g05_entitlement_signal_repaired,
    g06_administration_only,
)
from checkers.textutil import normalise, sentences  # noqa: E402


@dataclass
class Span:
    start: int
    end: int
    text: str


@dataclass
class Label:
    category: str
    is_impossible: bool
    spans: list = field(default_factory=list)


@dataclass
class Fake:
    text: str
    gold: dict
    contract_id: str = "FAKE"
    n_tokens: int = 100


def build(text, marks):
    gold = {}
    for category, ranges in marks.items():
        spans = [Span(start, end, text[start:end]) for start, end in ranges]
        gold[category] = Label(category, not spans, spans)
    return Fake(text=text, gold=gold)


def test_sentences_cover_text():
    text = "One. Two; three.\n\nFour."
    got = sentences(text)
    assert [body for _, _, body in got] == ["One.", "Two;", "three.", "Four."]
    for start, end, body in got:
        assert text[start:end] == body


def test_normalise_folds_whitespace_and_quotes():
    assert normalise("The  “Fee”\nis") == 'the "fee" is'


def test_g01_fires_only_on_present_yes_no_categories():
    text = "The parties agree. Consent is required for assignment."
    instance = build(text, {"Anti-Assignment": [(19, 54)], "Agreement Date": [(0, 4)]})
    checker = REGISTRY["g01"]
    assert checker.applies(instance, "Anti-Assignment")
    assert not checker.applies(instance, "Agreement Date")


def test_g01_does_not_fire_on_absent_category():
    instance = build("Nothing here.", {"Anti-Assignment": []})
    assert not REGISTRY["g01"].applies(instance, "Anti-Assignment")


def test_g02_requires_the_literal_marker():
    text = "A clause <omitted> continues."
    instance = build(text, {"Exclusivity": [(0, len(text))]})
    assert REGISTRY["g02"].applies(instance, "Exclusivity")
    plain = build("A clause continues.", {"Exclusivity": [(0, 19)]})
    assert not REGISTRY["g02"].applies(plain, "Exclusivity")


def test_g03_fires_on_shared_span_text():
    text = "Party shall share 10% of revenue."
    instance = build(text, {"Exclusivity": [(0, 32)], "License Grant": [(0, 32)]})
    assert REGISTRY["g03"].applies(instance, "Exclusivity")
    assert REGISTRY["g03"].applies(instance, "License Grant")


def test_g04_fires_on_venue_language_only():
    venue = build("The parties submit to the jurisdiction of Delaware courts.", {})
    assert REGISTRY["g04"].applies(venue, "Governing Law")
    plain = build("This Agreement is governed by the laws of Delaware.", {})
    assert not REGISTRY["g04"].applies(plain, "Governing Law")


def test_g04_is_scope_limited():
    venue = build("Exclusive jurisdiction lies in Denver.", {})
    assert not REGISTRY["g04"].applies(venue, "Exclusivity")


def test_g05_applicability_needs_payment_plus_amount():
    hit = build("Licensee shall pay a royalty of 5% of Net Sales.", {})
    assert REGISTRY["g05"].applies(hit, "Revenue/Profit Sharing")
    miss = build("Licensee shall act in good faith at all times.", {})
    assert not REGISTRY["g05"].applies(miss, "Revenue/Profit Sharing")


def test_g05_span_predicate_branches():
    assert g05_entitlement_signal("a royalty of 5% of Net Sales") == "percentage_of_revenue"
    assert g05_entitlement_signal("a fee for each unit sold") == "per_unit"
    assert g05_entitlement_signal("a fixed fee of $500 per month") is None


def test_g05_equity_branch_matches_the_verb_share():
    assert g05_entitlement_signal("The parties shall share certain revenues.") == "equity"
    assert g05_entitlement_signal_repaired(
        "The parties shall share certain revenues."
    ) == "revenue_entitlement"


def test_g05_repaired_handles_redacted_rates():
    text = "Depomed shall pay King [***]% of the Net Sales for each such quarter."
    assert g05_entitlement_signal(text) is None
    assert g05_entitlement_signal_repaired(text) == "percentage_of_revenue"


def test_g06_administration_predicate():
    admin = "GSK shall submit a written report setting forth Net Sales each quarter."
    assert g06_administration_only(admin)
    entitlement = "GSK shall pay 15% of Net Sales."
    assert not g06_administration_only(entitlement)


def test_g07_tracks_gold_presence():
    present = build("Dated January 1, 2020.", {"Agreement Date": [(6, 21)]})
    assert REGISTRY["g07"].applies(present, "Agreement Date")
    absent = build("No date here.", {"Agreement Date": []})
    assert not REGISTRY["g07"].applies(absent, "Agreement Date")


def test_g08_fires_on_blank_date_constructs():
    blank = build("Made this ____ day of January, 2020 by and between.", {})
    assert REGISTRY["g08"].applies(blank, "Agreement Date")
    clean = build("Made this 4th day of January, 2020 by and between.", {})
    assert not REGISTRY["g08"].applies(clean, "Agreement Date")


def test_d01_requires_short_clipped_date_spans():
    text = "This Agreement is entered into as of January 1, 2020 by the parties."
    instance = build(text, {"Agreement Date": [(37, 52)]})
    assert REGISTRY["d01"].applies(instance, "Agreement Date")
    whole = build(text, {"Agreement Date": [(0, len(text))]})
    assert not REGISTRY["d01"].applies(whole, "Agreement Date")


def test_d02_requires_offset_overlap():
    text = "Share 10% of revenue with the counterparty each quarter for all goods."
    same = build(text, {"Exclusivity": [(0, 40)], "Revenue/Profit Sharing": [(0, 40)]})
    assert REGISTRY["d02"].applies(same, "Exclusivity")
    apart = build(text, {"Exclusivity": [(0, 20)], "Revenue/Profit Sharing": [(41, 60)]})
    assert not REGISTRY["d02"].applies(apart, "Exclusivity")


def test_d03_fires_on_share_bearing_gold_span():
    text = "Licensee shall pay 10% of net revenue."
    instance = build(text, {"Revenue/Profit Sharing": [(0, len(text))]})
    assert REGISTRY["d03"].applies(instance, "Minimum Commitment")
    flat = build("Licensee shall pay $500.", {"Revenue/Profit Sharing": [(0, 24)]})
    assert not REGISTRY["d03"].applies(flat, "Minimum Commitment")


def test_d04_as_written_misses_performance_floors():
    supply = build("Excite will supply a minimum of 5,000 records each month.", {})
    assert REGISTRY["d04"].applies(supply, "Minimum Commitment")
    effort = build(
        "Company shall deploy a sales force of at least 25 Sales Representatives.", {}
    )
    assert not REGISTRY["d04"].applies(effort, "Minimum Commitment")
    variant = REGISTRY["d04"].variants["widened_verbs"]
    assert REGISTRY["d04"].applies(effort, "Minimum Commitment", **variant)


def test_d04_excludes_purchase_side_sentences():
    purchase = build("Buyer shall purchase a minimum of 100 units per year.", {})
    assert not REGISTRY["d04"].applies(purchase, "Minimum Commitment")


def test_d05_fires_on_either_bound_cue():
    lower = build("Distributor shall order a minimum of 500 units.", {})
    upper = build("Fees increase if usage exceeds 500 units.", {})
    neither = build("The parties shall cooperate in good faith.", {})
    assert REGISTRY["d05"].applies(lower, "Minimum Commitment")
    assert REGISTRY["d05"].applies(upper, "Volume Restriction")
    assert not REGISTRY["d05"].applies(neither, "Volume Restriction")


def test_d06_requires_gold_absence_and_a_near_miss_date():
    text = "Effective Date: April 17, 2017. The parties agree as follows."
    instance = build(text, {"Agreement Date": []})
    assert REGISTRY["d06"].applies(instance, "Agreement Date")
    dated = build("Entered into as of April 17, 2017.", {"Agreement Date": []})
    assert not REGISTRY["d06"].applies(dated, "Agreement Date")


def test_d07_needs_furniture_strictly_inside_a_gold_span():
    text = "The party shall pay\n\nPage 12\n\nall amounts due on demand."
    inside = build(text, {"Minimum Commitment": [(0, len(text))]})
    assert REGISTRY["d07"].applies(inside, "Minimum Commitment")
    clipped = build(text, {"Minimum Commitment": [(0, 19)]})
    assert not REGISTRY["d07"].applies(clipped, "Minimum Commitment")


def test_d08_requires_absence_and_an_unquantified_undertaking():
    text = "Licensee commits to promote the Product diligently."
    instance = build(text, {"Minimum Commitment": []})
    assert REGISTRY["d08"].applies(instance, "Minimum Commitment")
    quantified = build(
        "Licensee commits to promote 500 units of the Product.", {"Minimum Commitment": []}
    )
    assert not REGISTRY["d08"].applies(quantified, "Minimum Commitment")
    present = build(text, {"Minimum Commitment": [(0, 20)]})
    assert not REGISTRY["d08"].applies(present, "Minimum Commitment")


def test_every_registered_checker_has_a_scope_and_is_callable():
    empty = build("Nothing at all here.", {})
    for pid, checker in REGISTRY.items():
        assert checker.id == pid
        for category in ("Agreement Date", "Minimum Commitment", "Governing Law"):
            assert isinstance(checker.applies(empty, category), bool)


def test_dev_footprint_regression():
    from cuad_dataset import CuadDataset

    from checkers.run_footprints import evaluate, footprint

    dataset = CuadDataset()
    rows, categories = evaluate(dataset, "harness_val")
    assert len(rows) == 480
    expected = {
        "g01": 108,
        "g02": 0,
        "g03": 12,
        "g04": 21,
        "g05": 23,
        "g06": 5,
        "g07": 38,
        "g08": 5,
        "d01": 28,
        "d02": 12,
        "d03": 12,
        "d04": 14,
        "d05": 60,
        "d06": 1,
        "d07": 0,
        "d08": 22,
    }
    for pid, checker in REGISTRY.items():
        assert footprint(checker, rows, categories)["n_applicable"] == expected[pid], pid
