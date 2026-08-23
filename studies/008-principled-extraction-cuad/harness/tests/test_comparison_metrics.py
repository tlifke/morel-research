import pytest

from harness.comparison_metrics import (
    GroundTruth,
    ModelOutput,
    PredSpan,
    Span,
    aggregate,
    contracteval_correct,
    dedupe_spans,
    detection_cell,
    fbeta,
    jaccard,
    localization_metrics,
    detection_metrics,
    score,
)

GOLD_A = "The term of this Agreement shall commence on the Effective Date"
GOLD_B = "and shall continue for a period of five years thereafter"


def gt(spans, category="Expiration Date", contract="C1"):
    return GroundTruth(
        contract_id=contract,
        category=category,
        gt_spans=tuple(Span(t) for t in spans),
    )


def out(texts, category="Expiration Date", contract="C1", raw=None):
    return ModelOutput(
        contract_id=contract,
        category=category,
        system="test",
        condition="smoke",
        run_id="r0",
        pred_spans=tuple(PredSpan(t) for t in texts),
        raw_response=raw if raw is not None else " ".join(texts),
    )


def test_exact_match_two_spans():
    r = score(gt([GOLD_A, GOLD_B]), out([GOLD_A, GOLD_B]))
    assert (r.tp, r.fp, r.fn) == (2, 0, 0)
    assert r.detection_cell == "tp"
    assert all(j == pytest.approx(1.0) for j in r.matched_jaccards)


def test_partial_below_and_above_threshold():
    low = "commence on the Effective Date of something entirely different here"
    assert jaccard(GOLD_A, low) < 0.5
    r = score(gt([GOLD_A]), out([low]))
    assert (r.tp, r.fp, r.fn) == (0, 1, 1)

    high = "The term of this Agreement shall commence on the Effective Date now"
    assert jaccard(GOLD_A, high) >= 0.5
    r2 = score(gt([GOLD_A]), out([high]))
    assert (r2.tp, r2.fp, r2.fn) == (1, 0, 0)


def test_over_extraction_matching_two_golds_is_two_tp_many_to_many():
    both = GOLD_A + " " + GOLD_B
    r = score(gt([GOLD_A, GOLD_B]), out([both]), dedupe=False)
    assert r.n_pred == 1
    assert r.tp == 2 and r.fp == 0 and r.fn == 0
    assert r.tp_oto == 1 and r.fn_oto == 1


def test_two_preds_one_gold_costs_no_fp_many_to_many():
    near = GOLD_A + " hereunder"
    r = score(gt([GOLD_A]), out([GOLD_A, near]), dedupe=False)
    assert r.n_pred == 2
    assert r.tp == 1 and r.fp == 0 and r.fn == 0
    assert r.tp_oto == 1 and r.fp_oto == 1


def test_empty_pred_is_false_empty():
    r = score(gt([GOLD_A]), out([]))
    assert r.detection_cell == "fn"
    assert (r.tp, r.fp, r.fn) == (0, 0, 1)
    m = detection_metrics([r])
    assert m["false_empty_rate"] == 1.0


def test_empty_gold_empty_pred_is_true_negative():
    r = score(gt([]), out([]))
    assert r.detection_cell == "tn"
    assert (r.tp, r.fp, r.fn) == (0, 0, 0)
    assert detection_metrics([r])["tn"] == 1


def test_empty_gold_with_pred_is_detection_fp():
    r = score(gt([]), out([GOLD_A]))
    assert r.detection_cell == "fp"
    assert r.fp == 1


def test_duplicate_text_at_two_offsets():
    g = GroundTruth(
        contract_id="C1",
        category="Governing Law",
        gt_spans=(Span("New York", 10), Span("New York", 500)),
    )
    o = ModelOutput(
        contract_id="C1",
        category="Governing Law",
        system="test",
        condition="smoke",
        run_id="r0",
        pred_spans=(PredSpan("New York", 10), PredSpan("New York", 500)),
        raw_response="New York",
    )
    r = score(g, o, dedupe=False)
    assert r.n_gt == 2 and r.n_pred == 2
    assert r.tp == 2 and r.fn == 0


def test_parties_substring_exception():
    gold = "Macy's, Inc."
    pred = "This agreement is by and between Macy's, Inc. and the Purchaser"
    assert jaccard(gold, pred) < 0.5
    r_other = score(gt([gold], category="Governing Law"), out([pred], category="Governing Law"))
    assert r_other.tp == 0
    r_parties = score(gt([gold], category="Parties"), out([pred], category="Parties"))
    assert r_parties.tp == 1


def test_dedupe_collapses_near_duplicates():
    near = GOLD_A + " hereunder"
    kept = dedupe_spans([PredSpan(GOLD_A), PredSpan(near), PredSpan(GOLD_B)])
    assert len(kept) == 2
    assert kept[0].text == GOLD_A


def test_dedupe_reduces_fp_on_gold_empty_question():
    near = GOLD_A + " hereunder"
    raw = score(gt([]), out([GOLD_A, near]), dedupe=False)
    ded = score(gt([]), out([GOLD_A, near]), dedupe=True)
    assert raw.fp == 2
    assert ded.fp == 1


def test_localization_defined_on_tp_cell_only():
    recs = [
        score(gt([GOLD_A], contract="C1"), out([GOLD_A], contract="C1")),
        score(gt([GOLD_A], contract="C2"), out([], contract="C2")),
        score(gt([], contract="C3"), out([GOLD_A], contract="C3")),
    ]
    m = localization_metrics(recs)
    assert m["tp_cell_size"] == 1
    assert m["tp"] == 1 and m["fp"] == 0 and m["fn"] == 0


def test_f2_weights_recall_above_precision():
    assert fbeta(0.5, 1.0, 2.0) > fbeta(1.0, 0.5, 2.0)
    assert fbeta(0.5, 1.0, 1.0) == pytest.approx(fbeta(1.0, 0.5, 1.0))
    assert fbeta(1.0, 1.0, 2.0) == pytest.approx(1.0)


def test_detection_cell_truth_table():
    assert detection_cell(True, True) == "tp"
    assert detection_cell(False, True) == "fn"
    assert detection_cell(True, False) == "fp"
    assert detection_cell(False, False) == "tn"


def test_contracteval_requires_all_spans_verbatim():
    g = gt([GOLD_A, GOLD_B])
    assert contracteval_correct(g, out([GOLD_A, GOLD_B], raw=GOLD_A + " " + GOLD_B))
    assert not contracteval_correct(g, out([GOLD_A], raw=GOLD_A))


def test_contracteval_whitespace_sensitivity():
    gold = "the term\nshall commence"
    g = gt([gold])
    assert contracteval_correct(g, out([gold], raw="X " + gold + " Y"))
    assert not contracteval_correct(g, out([gold], raw="X the term shall commence Y"))


def test_contracteval_declination_on_empty_gold_is_tn():
    r = score(gt([]), out([], raw="No related clause."))
    assert r.contracteval_correct is True


def test_key_mismatch_raises():
    with pytest.raises(ValueError):
        score(gt([GOLD_A], contract="C1"), out([GOLD_A], contract="C2"))


def test_aggregate_micro_and_macro_differ_under_imbalance():
    recs = []
    for i in range(10):
        recs.append(
            score(
                gt([GOLD_A], category="Parties", contract=f"P{i}"),
                out([GOLD_A], category="Parties", contract=f"P{i}"),
            )
        )
    recs.append(
        score(
            gt([GOLD_A], category="Insurance", contract="I0"),
            out([], category="Insurance", contract="I0"),
        )
    )
    agg = aggregate(recs)
    assert agg["n_categories"] == 2
    assert agg["micro"]["detection"]["recall"] == pytest.approx(10 / 11)
    assert agg["macro"]["detection"]["recall"] == pytest.approx(0.5)
