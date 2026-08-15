from harness import metrics


def approx(a, b, tol=1e-9):
    return abs(a - b) < tol


def test_level_a_derives_everything_from_the_raw_2x2():
    counts = {"TP": 6, "FP": 2, "FN": 4, "TN": 8}
    out = metrics.level_a_from_counts(counts)
    assert out["counts"] == counts
    assert approx(out["presence_class"]["precision"], 6 / 8)
    assert approx(out["presence_class"]["recall"], 6 / 10)
    assert approx(out["presence_class"]["f1"], 2 * 0.75 * 0.6 / 1.35)
    assert approx(out["absent_class_recall"], 8 / 10)
    assert approx(out["absent_class_precision"], 8 / 12)
    assert approx(out["decision_kind_accuracy"], 14 / 20)
    assert out["false_present"] == 2
    assert out["false_absent"] == 4


def test_rare_category_where_always_absent_beats_the_model():
    counts = {"TP": 1, "FP": 4, "FN": 0, "TN": 97}
    model = metrics.level_a_from_counts(counts)
    baselines = metrics.trivial_baselines(counts)
    always_absent = baselines["always_absent"]
    always_present = baselines["always_present"]

    assert model["n"] == 102
    assert model["n_gold_present"] == 1
    assert approx(model["decision_kind_accuracy"], 98 / 102)
    assert approx(model["presence_class"]["precision"], 0.2)
    assert approx(model["presence_class"]["recall"], 1.0)
    assert approx(model["presence_class"]["f1"], 1 / 3)

    assert always_absent["counts"] == {"TP": 0, "FP": 0, "FN": 1, "TN": 101}
    assert approx(always_absent["decision_kind_accuracy"], 101 / 102)
    assert always_absent["decision_kind_accuracy"] > model["decision_kind_accuracy"]
    assert always_absent["presence_class"]["f1"] == 0.0
    assert model["presence_class"]["f1"] > always_absent["presence_class"]["f1"]

    assert approx(always_present["decision_kind_accuracy"], 1 / 102)


def test_common_category_where_always_present_scores_high():
    counts = {"TP": 90, "FP": 6, "FN": 3, "TN": 3}
    baselines = metrics.trivial_baselines(counts)
    always_present = baselines["always_present"]
    assert always_present["counts"] == {"TP": 93, "FP": 9, "FN": 0, "TN": 0}
    assert approx(always_present["decision_kind_accuracy"], 93 / 102)
    assert always_present["absent_class"]["f1"] == 0.0


def test_the_two_classes_are_macro_averaged_separately():
    agg = metrics.aggregate_level_a(
        {
            "Rare": {"TP": 1, "FP": 4, "FN": 0, "TN": 97},
            "Common": {"TP": 90, "FP": 6, "FN": 3, "TN": 3},
        }
    )
    rare = agg["per_category"]["Rare"]
    common = agg["per_category"]["Common"]
    assert approx(
        agg["macro_presence_class"]["f1"],
        (rare["presence_class"]["f1"] + common["presence_class"]["f1"]) / 2,
    )
    assert approx(
        agg["macro_absent_class"]["f1"],
        (rare["absent_class"]["f1"] + common["absent_class"]["f1"]) / 2,
    )
    assert agg["macro_presence_class"]["f1"] != agg["macro_absent_class"]["f1"]
    assert agg["micro"]["counts"] == {"TP": 91, "FP": 10, "FN": 3, "TN": 100}
    assert "trivial_baselines" in rare


def test_every_category_carries_its_trivial_baselines():
    agg = metrics.aggregate_level_a({"A": {"TP": 1, "FP": 0, "FN": 1, "TN": 8}})
    baselines = agg["per_category"]["A"]["trivial_baselines"]
    assert set(baselines) == {"always_absent", "always_present"}
    assert baselines["always_absent"]["counts"]["TN"] == 8


DOC = "Section 9. This Agreement shall be governed by the laws of Delaware. End."


def test_verbatim_fidelity_true_case_with_position():
    verbatim, offset = metrics.verbatim_locate("governed by the laws of Delaware", DOC)
    assert verbatim is True
    assert offset == DOC.index("governed by the laws of Delaware")


def test_verbatim_fidelity_false_case_for_a_paraphrase():
    verbatim, offset = metrics.verbatim_locate("Delaware law governs this contract", DOC)
    assert verbatim is False
    assert offset is None


def test_span_report_separates_verbatim_fidelity_from_token_f1():
    gold = ["This Agreement shall be governed by the laws of Delaware."]
    paraphrase = ["This agreement is governed by Delaware laws."]
    report = metrics.span_report(paraphrase, gold, DOC)
    assert report["verbatim_fidelity"]["exact_rate"] == 0.0
    assert report["verbatim_fidelity"]["not_found_rate"] == 1.0
    assert report["span_f1"] > 0.0
    assert report["exact_match_rate"] == 0.0
    assert report["span_positions"][0]["char_offset"] is None


def test_span_report_exact_match_and_offsets():
    gold = ["This Agreement shall be governed by the laws of Delaware."]
    report = metrics.span_report(gold, gold, DOC)
    assert report["verbatim_fidelity"]["exact_rate"] == 1.0
    assert report["verbatim_fidelity"]["not_found_rate"] == 0.0
    assert report["exact_match_rate"] == 1.0
    assert report["span_f1"] == 1.0
    position = report["span_positions"][0]
    assert position["char_offset"] == DOC.index(gold[0])
    assert 0.0 < position["relative_offset"] < 1.0


def test_multi_span_recovery_counts():
    report = metrics.span_report(["a", "b"], ["a", "b", "c"], "a b c")
    assert report["multi_span_recovery"] == {
        "n_predicted": 2,
        "n_gold": 3,
        "ratio": 2 / 3,
    }


def test_level_b_aggregate_reports_its_tp_denominator():
    rows = [
        {
            "answer_score": {
                "cell": "TP",
                "span_f1": 1.0,
                "soft": {"precision": 1.0, "recall": 1.0},
                "exact_match_rate": 1.0,
                "verbatim_fidelity": {"n_spans": 2, "n_exact": 2, "n_normalized_only": 0, "n_not_found": 0},
                "multi_span_recovery": {"n_predicted": 2, "n_gold": 2, "ratio": 1.0},
                "span_positions": [{"relative_offset": 0.1}, {"relative_offset": 0.3}],
            }
        },
        {
            "answer_score": {
                "cell": "FP",
                "verbatim_fidelity": {"n_spans": 1, "n_exact": 0, "n_normalized_only": 0, "n_not_found": 1},
                "span_positions": [],
            }
        },
        {"answer_score": {"cell": "FN"}},
        {"answer_score": {"cell": "TN"}},
    ]
    agg = metrics.aggregate_level_b(rows)
    assert agg["tp_denominator"] == 1
    assert agg["span_f1"] == 1.0
    assert agg["n_spans"] == 2
    assert agg["verbatim_not_found_rate"] == 0.0
    assert agg["verbatim_exact_rate"] == 1.0
    assert approx(agg["mean_relative_offset"], 0.2)
    assert agg["false_present_cell"]["n_not_found"] == 1
    assert agg["false_present_cell"]["verbatim_not_found_rate"] == 1.0


def test_level_b_is_undefined_without_a_tp_cell():
    agg = metrics.aggregate_level_b([{"answer_score": {"cell": "FN"}}])
    assert agg["tp_denominator"] == 0
    assert "undefined" in agg["note"]


def _decision(cell, span_f1, cited, gold):
    ev = metrics.citation_eval(cited, gold).to_dict()
    return {
        "answer_score": {"cell": cell, "span_f1": span_f1},
        "citation_eval": ev,
    }


def test_citation_cross_tabulated_by_answer_correctness():
    rows = [
        _decision("TP", 1.0, ["p01"], ["p01"]),
        _decision("TP", 1.0, ["p02"], ["p01"]),
        _decision("FP", None, ["p01"], ["p01"]),
        _decision("FN", None, ["p02"], ["p01"]),
        _decision("TN", None, ["p01"], ["p01"]),
    ]
    table = metrics.citation_correctness_crosstab(rows)
    counts = table["counts"]
    assert counts["right_answer_right_citation"] == 2
    assert counts["right_answer_wrong_citation"] == 1
    assert counts["wrong_answer_right_citation"] == 1
    assert counts["wrong_answer_wrong_citation"] == 1
    assert table["n_scored_decisions"] == 5
    assert approx(table["rates"]["right_answer_wrong_citation"], 0.2)
    assert table["span_f1_threshold"] == metrics.HEADLINE_SPAN_F1_THRESHOLD


def test_right_answer_wrong_reason_is_visible_where_marginal_f1_hides_it():
    rows = [
        _decision("TP", 1.0, ["p02"], ["p01"]),
        _decision("FN", None, ["p01"], ["p01"]),
    ]
    micro = metrics.micro_citation([r["citation_eval"] for r in rows])
    table = metrics.citation_correctness_crosstab(rows)
    assert approx(micro["f1"], 0.5)
    assert table["counts"]["right_answer_wrong_citation"] == 1
    assert table["counts"]["wrong_answer_right_citation"] == 1


def test_answer_correctness_threshold_moves_the_cells():
    rows = [_decision("TP", 0.4, ["p01"], ["p01"])]
    strict = metrics.citation_correctness_crosstab(rows, span_f1_threshold=0.5)
    lenient = metrics.citation_correctness_crosstab(rows, span_f1_threshold=0.3)
    assert strict["counts"]["wrong_answer_right_citation"] == 1
    assert lenient["counts"]["right_answer_right_citation"] == 1
    assert lenient["span_f1_threshold"] == 0.3


def test_per_principle_marginals_are_hand_computable():
    rows = [
        _decision("TP", 1.0, ["p01", "p02"], ["p01"]),
        _decision("TP", 1.0, ["p02"], ["p01", "p03"]),
    ]
    marginals = metrics.per_principle_marginals(rows)
    assert marginals["p01"]["tp"] == 1 and marginals["p01"]["fn"] == 1
    assert approx(marginals["p01"]["recall"], 0.5)
    assert approx(marginals["p01"]["precision"], 1.0)
    assert marginals["p02"]["fp"] == 2
    assert marginals["p02"]["precision"] == 0.0
    assert marginals["p03"]["fn"] == 1


def test_citation_f1_not_recall_so_cite_everything_cannot_win():
    everything = metrics.citation_eval(["p01", "p02", "p03", "p04"], ["p01"])
    precise = metrics.citation_eval(["p01"], ["p01"])
    assert everything.recall == 1.0
    assert everything.f1 < precise.f1


def test_corpus_level_a_recomputes_from_stored_cells():
    rows = [
        {
            "outcome": "ok",
            "answer": {
                "level_a": {
                    "per_category_cells": {"Rare": "TN", "Common": "TP"},
                }
            },
        },
        {
            "outcome": "ok",
            "answer": {
                "level_a": {
                    "per_category_cells": {"Rare": "FP", "Common": "FN"},
                }
            },
        },
    ]
    corpus = metrics.corpus_level_a(rows)
    assert corpus["per_category"]["Rare"]["counts"] == {"TP": 0, "FP": 1, "FN": 0, "TN": 1}
    assert corpus["per_category"]["Common"]["counts"] == {"TP": 1, "FP": 0, "FN": 1, "TN": 0}
    assert corpus["micro"]["counts"] == {"TP": 1, "FP": 1, "FN": 1, "TN": 1}
    assert "trivial_baselines" in corpus["per_category"]["Rare"]


def test_corpus_level_a_can_be_recomputed_for_first_attempt_scope():
    rows = [
        {
            "outcome": "ok",
            "answer": {"level_a": {"per_category_cells": {"A": "TP"}}},
            "first_attempt": {
                "parsed": True,
                "answer": {"level_a": {"per_category_cells": {"A": "FN"}}},
            },
        }
    ]
    assert metrics.corpus_level_a(rows, "final")["micro"]["counts"]["TP"] == 1
    assert metrics.corpus_level_a(rows, "first_attempt")["micro"]["counts"]["FN"] == 1


CONTRACT = (
    "ARTICLE 9. GOVERNING LAW.\n"
    "This Agreement shall be govern-\ning by the “laws” of the State of\n"
    "Delaware — without regard to conflicts.\n"
    "Source: LOHACORP, 10-K, 3/3/2019\n"
    "\f Page 12 of 87\n"
    "Buyer shall purchase at least 10,000 units."
)


def test_verbatim_class_exact():
    verdict = metrics.classify_span_verbatim(
        "Buyer shall purchase at least 10,000 units.", CONTRACT
    )
    assert verdict["verbatim_class"] == metrics.VERBATIM_EXACT
    assert verdict["char_offset"] == CONTRACT.index("Buyer shall purchase")


def test_verbatim_class_normalized_only_for_a_hyphen_linebreak():
    verdict = metrics.classify_span_verbatim(
        "This Agreement shall be governing by the “laws” of the State of Delaware",
        CONTRACT,
    )
    assert verdict["verbatim_class"] == metrics.VERBATIM_NORMALIZED_ONLY
    assert verdict["char_offset"] is None
    assert verdict["normalized_char_offset"] is not None


def test_verbatim_class_normalized_only_for_curly_quotes_and_dashes():
    verdict = metrics.classify_span_verbatim(
        'the "laws" of the State of Delaware - without regard to conflicts.', CONTRACT
    )
    assert verdict["verbatim_class"] == metrics.VERBATIM_NORMALIZED_ONLY


def test_verbatim_class_not_found_for_invented_language():
    verdict = metrics.classify_span_verbatim(
        "The parties submit to the exclusive jurisdiction of the New York courts.",
        CONTRACT,
    )
    assert verdict["verbatim_class"] == metrics.VERBATIM_NOT_FOUND
    assert verdict["char_offset"] is None
    assert verdict["normalized_char_offset"] is None


def test_normalisation_does_not_strip_ocr_page_furniture():
    normalized = metrics.normalize_for_matching(CONTRACT)
    assert "Source: LOHACORP, 10-K, 3/3/2019" in normalized
    assert "Page 12 of 87" in normalized
    clean_only = metrics.classify_span_verbatim(
        "Delaware - without regard to conflicts. Buyer shall purchase at least 10,000 units.",
        CONTRACT,
    )
    assert clean_only["verbatim_class"] == metrics.VERBATIM_NOT_FOUND


def test_three_way_rates_and_their_framing():
    rates = metrics.verbatim_rates(
        [
            metrics.VERBATIM_EXACT,
            metrics.VERBATIM_EXACT,
            metrics.VERBATIM_NORMALIZED_ONLY,
            metrics.VERBATIM_NOT_FOUND,
        ]
    )
    assert rates["exact_rate"] == 0.5
    assert rates["normalized_only_rate"] == 0.25
    assert rates["not_found_rate"] == 0.25
    assert rates["cosmetic_gap"] == rates["normalized_only_rate"]
    assert rates["invented_language_rate"] == rates["not_found_rate"]
    assert rates["exact_or_normalized_rate"] == 0.75


def test_span_report_classifies_all_three_in_one_pass():
    report = metrics.span_report(
        [
            "Buyer shall purchase at least 10,000 units.",
            'the "laws" of the State of Delaware',
            "The parties submit to New York courts.",
        ],
        ["Buyer shall purchase at least 10,000 units."],
        CONTRACT,
    )
    vf = report["verbatim_fidelity"]
    assert (vf["n_exact"], vf["n_normalized_only"], vf["n_not_found"]) == (1, 1, 1)
    assert approx(vf["not_found_rate"], 1 / 3)


def _sweep_rows():
    return [
        _decision("TP", 0.95, ["p01"], ["p01"]),
        _decision("TP", 0.65, ["p02"], ["p01"]),
        _decision("TP", 0.35, ["p01"], ["p01"]),
        _decision("TP", 0.05, ["p02"], ["p01"]),
        _decision("TN", None, ["p01"], ["p01"]),
        _decision("FN", None, ["p02"], ["p01"]),
    ]


def test_sweep_shape_is_a_full_artifact_not_a_chosen_point():
    sweep = metrics.citation_correctness_sweep(_sweep_rows())
    assert sweep["span_f1_thresholds"] == [round(0.1 * i, 1) for i in range(1, 11)]
    assert len(sweep["points"]) == 10
    for point in sweep["points"]:
        assert set(point["counts"]) == {
            "right_answer_right_citation",
            "right_answer_wrong_citation",
            "wrong_answer_right_citation",
            "wrong_answer_wrong_citation",
        }
        assert point["n_scored_decisions"] == 6
        assert sum(point["counts"].values()) == 6
    assert sweep["n_decisions"] == 6
    assert sweep["citation_rule"]["requires_exact_set"] is True


def test_answer_correct_count_is_monotonically_non_increasing_in_t():
    sweep = metrics.citation_correctness_sweep(_sweep_rows())
    counts = [p["n_answer_correct"] for p in sweep["points"]]
    assert counts == sorted(counts, reverse=True)
    assert all(a >= b for a, b in zip(counts, counts[1:]))
    assert counts[0] > counts[-1]


def test_headline_is_derived_from_the_sweep_not_hardcoded():
    sweep = metrics.citation_correctness_sweep(_sweep_rows())
    headline = sweep["headline"]
    assert headline["span_f1_threshold"] == metrics.HEADLINE_SPAN_F1_THRESHOLD
    assert headline in sweep["points"]
    assert metrics.headline_from_sweep(sweep, 0.9) == sweep["points"][8]
    assert metrics.headline_from_sweep(sweep, 0.42) is None


def test_sweep_is_recomputable_from_decision_rows_alone():
    rows = _sweep_rows()
    stored = [
        {"answer_score": r["answer_score"], "citation_eval": r["citation_eval"]}
        for r in rows
    ]
    assert metrics.citation_correctness_sweep(stored) == metrics.citation_correctness_sweep(rows)


def test_optional_2d_surface_sweeps_the_citation_threshold_too():
    sweep = metrics.citation_correctness_sweep(
        _sweep_rows(), citation_f1_thresholds=[0.5, 1.0]
    )
    assert len(sweep["surface"]) == 2
    assert sweep["surface"][0]["citation_f1_threshold"] == 0.5
    assert len(sweep["surface"][0]["points"]) == 10
