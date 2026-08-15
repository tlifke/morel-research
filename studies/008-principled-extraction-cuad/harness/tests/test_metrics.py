import math

from harness import metrics


def approx(a, b, tol=1e-9):
    return abs(a - b) < tol


def test_token_f1_hand_computed():
    assert approx(metrics.token_f1("the quick brown fox", "the quick red fox"), 0.75)


def test_token_f1_edges():
    assert metrics.token_f1("", "") == 1.0
    assert metrics.token_f1("abc", "") == 0.0
    assert metrics.token_f1("", "abc") == 0.0
    assert metrics.token_f1("Governing LAW.", "governing law") == 1.0


def test_token_f1_is_multiset_based():
    assert approx(metrics.token_f1("a a b", "a b"), 2 * (2 / 3) * 1.0 / (2 / 3 + 1.0))


def test_best_span_f1_takes_the_max_gold():
    assert metrics.best_span_f1("a b", ["x y", "a b"]) == 1.0
    assert metrics.best_span_f1("a b", []) == 0.0


def test_decision_span_f1_hand_computed():
    assert metrics.decision_span_f1([], []) == 1.0
    assert metrics.decision_span_f1(["x"], []) == 0.0
    assert metrics.decision_span_f1([], ["x"]) == 0.0
    assert metrics.decision_span_f1(["a b c"], ["a b c"]) == 1.0
    assert approx(metrics.decision_span_f1(["a b", "c d"], ["a b"]), 2 / 3)


def test_citation_eval_hand_computed():
    ev = metrics.citation_eval(["p01", "p02"], ["p02", "p03"])
    assert ev.tp == ["p02"]
    assert ev.fp == ["p01"]
    assert ev.fn == ["p03"]
    assert approx(ev.precision, 0.5)
    assert approx(ev.recall, 0.5)
    assert approx(ev.f1, 0.5)


def test_citation_eval_empty_cases():
    ev = metrics.citation_eval([], [])
    assert ev.precision == 1.0 and ev.recall == 1.0 and ev.f1 == 1.0
    ev = metrics.citation_eval([], ["p01"])
    assert ev.precision == 0.0 and ev.recall == 0.0
    ev = metrics.citation_eval(["p01"], [])
    assert ev.precision == 0.0 and ev.recall == 1.0


def test_micro_citation_hand_computed():
    d1 = metrics.citation_eval(["p01", "p02"], ["p02", "p03"]).to_dict()
    d2 = metrics.citation_eval(["p01"], ["p01"]).to_dict()
    micro = metrics.micro_citation([d1, d2])
    assert micro["tp"] == 2 and micro["fp"] == 1 and micro["fn"] == 1
    assert approx(micro["precision"], 2 / 3)
    assert approx(micro["recall"], 2 / 3)
    assert approx(micro["f1"], 2 / 3)
    assert micro["micro_over_decisions"] is True


def test_confusion_pairs_pairs_fp_against_fn():
    rows = [
        {"citation_eval": metrics.citation_eval(["p01"], ["p02"]).to_dict()},
        {"citation_eval": metrics.citation_eval(["p01"], ["p02"]).to_dict()},
        {"citation_eval": None},
    ]
    pairs = metrics.confusion_pairs(rows)
    assert pairs[("p01", "p02")] == 2


def test_multi_span_decision_with_a_near_duplicate_pair():
    gold = [
        "This Agreement shall be governed by the laws of the State of Delaware.",
        "This Agreement shall be governed by the laws of the State of Delaware, "
        "without regard to its conflict of laws principles.",
    ]
    both = metrics.decision_span_f1(gold, gold)
    assert both == 1.0

    one_copy = metrics.decision_span_f1([gold[0]], gold)
    assert 0.0 < one_copy < 1.0
    assert approx(one_copy, 2 * 1.0 * ((1.0 + metrics.token_f1(gold[1], gold[0])) / 2)
                  / (1.0 + (1.0 + metrics.token_f1(gold[1], gold[0])) / 2))

    duplicated = metrics.decision_span_f1([gold[0], gold[0]], gold)
    assert duplicated < both


def test_length_buckets():
    assert metrics.length_bucket(0) == "0-4k"
    assert metrics.length_bucket(4095) == "0-4k"
    assert metrics.length_bucket(4096) == "4k-8k"
    assert metrics.length_bucket(8191) == "4k-8k"
    assert metrics.length_bucket(16383) == "8k-16k"
    assert metrics.length_bucket(16384) == ">16k"
    assert metrics.length_bucket(100000) == ">16k"


def test_summarize_compliance_principle_and_micro_levels():
    summary = metrics.summarize_compliance(
        [("p01", True), ("p01", False), ("p02", True)]
    )
    assert summary["per_principle"] == {"p01": False, "p02": True}
    assert summary["n_applicable"] == 2
    assert summary["n_passed"] == 1
    assert approx(summary["pass_rate"], 0.5)
    assert summary["n_applicable_pairs"] == 3
    assert approx(summary["pass_rate_micro"], 2 / 3)


def test_summarize_compliance_no_applicable_principles():
    summary = metrics.summarize_compliance([])
    assert summary["n_applicable"] == 0
    assert summary["pass_rate"] is None


def test_leakage_text_scan_ignores_the_citation_field():
    payload = {
        "extractions": [
            {"text": "per p03 this is governed", "principles_cited": ["p07"]},
            {"text": "see principle 4 above", "principles_cited": []},
        ]
    }
    assert metrics.scan_text_fields_for_principle_refs(payload) == 2


def _ok_row(span_f1, presence_f1, bucket="0-4k", **extra):
    return {
        "condition": "C1",
        "model": "m",
        "schema_variant": "field_present",
        "length_bucket": bucket,
        "outcome": "ok",
        "answer": {
            "level_a": {
                "macro_presence_class": {"f1": presence_f1},
                "macro_absent_class": {"f1": 1.0},
                "micro": {"absent_class_recall": 1.0, "decision_kind_accuracy": 1.0},
            },
            "level_b": {"span_f1": span_f1, "exact_match_rate": 1.0, "verbatim_fidelity_rate": 1.0},
        },
        "compliance": {"pass_rate": 1.0},
        "citation": None,
        **extra,
    }


def test_summarize_trials_only_scores_ok_rows_and_reports_outcome_rates():
    rows = [
        _ok_row(0.6, 0.5),
        _ok_row(0.8, 0.9),
        {"outcome": "parse_failure", "answer": None, "compliance": None, "citation": None,
         "repair_stages": ["coverage"]},
        {"outcome": "infeasible_at_length", "answer": None, "compliance": None, "citation": None},
    ]
    summary = metrics.summarize_trials(rows)
    assert summary["n_trials"] == 4
    assert approx(summary["parse_failure_rate"], 0.25)
    assert approx(summary["infeasible_rate"], 0.25)
    assert approx(summary["coverage_repair_rate"], 0.25)
    assert summary["span_f1"]["n"] == 2
    assert approx(summary["span_f1"]["mean"], 0.7)
    assert approx(summary["presence_f1_macro"]["mean"], 0.7)
    assert summary["citation_f1"]["n"] == 0


def test_outcome_rates_are_first_class_metrics():
    rows = [
        {"outcome": "ok", "repair_stages": ["coverage"], "n_repair_attempts": 1},
        {"outcome": "ok", "repair_stages": [], "n_repair_attempts": 0, "completion_truncated": True},
        {"outcome": "parse_failure", "repair_stages": ["json_decode", "json_decode"], "n_repair_attempts": 2},
        {"outcome": "infeasible_at_length"},
    ]
    rates = metrics.outcome_rates(rows)
    assert approx(rates["coverage_repair_rate"], 0.25)
    assert approx(rates["any_repair_rate"], 0.5)
    assert approx(rates["completion_truncated_rate"], 0.25)
    assert approx(rates["parse_failure_rate"], 0.25)
    assert approx(rates["infeasible_rate"], 0.25)


def test_every_primary_metric_comes_out_bucketed():
    rows = [_ok_row(1.0, 1.0, "0-4k"), _ok_row(0.0, 0.0, ">16k")]
    summary = metrics.stratified_summary(rows)
    group = summary["groups"][0]
    assert set(group["by_length_bucket"]) == {"0-4k", ">16k"}
    for bucket in group["by_length_bucket"].values():
        for name in ("span_f1", "presence_f1_macro", "absent_f1_macro",
                     "compliance_pass_rate", "citation_f1"):
            assert name in bucket["final"]
        assert "first_attempt" in bucket
    assert approx(group["overall"]["final"]["span_f1"]["mean"], 0.5)


def test_mean_normal_approx_ci95_shape_and_naming():
    out = metrics.mean_normal_approx_ci95([0.0, 1.0, 0.5])
    assert out["n"] == 3
    assert approx(out["mean"], 0.5)
    assert "ci95_normal_approx" in out
    assert "bootstrap" not in " ".join(out)
    assert out["ci95_normal_approx"][0] < 0.5 < out["ci95_normal_approx"][1]
    assert not math.isnan(out["ci95_normal_approx"][0])
    assert "NOT a bootstrap" in metrics.mean_normal_approx_ci95.__doc__
