import json

import pytest

from harness import metrics
from harness.backends.base import BackendError
from harness.backends.fake_backend import FakeBackend
from harness.envs.fake_env import FakeEnvironment
from harness.runner import RunConfig, TrialKey, run_trial

PERFECT = {
    "extractions": [
        {
            "category": "Governing Law",
            "spans": [
                "This Agreement shall be governed by the laws of the State of Delaware.",
                "This Agreement shall be governed by the laws of the State of Delaware, "
                "without regard to its conflict of laws principles.",
            ],
            "principles_cited": ["p01"],
        },
        {
            "category": "Agreement Date",
            "spans": ["This Agreement is entered into as of March 3, 2019."],
            "principles_cited": ["p01"],
        },
        {
            "category": "Minimum Commitment",
            "spans": ["Buyer shall purchase at least 10,000 units per calendar year."],
            "principles_cited": ["p01", "p03"],
        },
        {
            "category": "Volume Restriction",
            "spans": ["Buyer shall order no more than 50,000 units in any calendar quarter."],
            "principles_cited": ["p01", "p03"],
        },
    ],
    "absent": [],
}


@pytest.fixture
def env():
    return FakeEnvironment()


@pytest.fixture
def harness_val(env):
    return {i.contract_id: i for i in env.load_instances("harness_val")}


@pytest.fixture
def config(tmp_path):
    return RunConfig(
        run_id="test-run",
        temperature=0.7,
        max_output_tokens=256,
        max_repair_attempts=2,
        principle_set_version="fake-v1",
        trace_root=tmp_path / "traces",
    )


def _run(env, backend, instance, config, condition="C3", variant="field_present", seed=0):
    return run_trial(
        env=env,
        backend=backend,
        instance=instance,
        condition=condition,
        seed=seed,
        schema_variant=variant,
        principle_set=env.principle_set(),
        config=config,
    )


def test_trial_id_is_stable_and_key_sensitive():
    a = TrialKey("X", "C1", "m", 0, "field_present")
    b = TrialKey("X", "C1", "m", 0, "field_present")
    c = TrialKey("X", "C2", "m", 0, "field_present")
    assert a.trial_id() == b.trial_id()
    assert a.trial_id() != c.trial_id()


def test_ok_trial_scores_and_emits_one_row_per_decision(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "ok"
    assert result.trial.answer["level_a"]["micro"]["counts"] == {"TP": 4, "FP": 0, "FN": 0, "TN": 0}
    assert result.trial.answer["level_b"]["span_f1"] == 1.0
    assert len(result.decisions) == 4
    assert result.trial.compliance["pass_rate"] == 1.0
    assert result.trial.citation["precision"] == 1.0
    assert result.trial.response_sha256


def test_absence_is_an_explicit_row_for_every_non_extracted_category(env, harness_val, config):
    payload = {
        "extractions": [
            {
                "category": "Governing Law",
                "spans": [
                    "This Agreement shall be governed by the laws of the State of Delaware."
                ],
                "principles_cited": ["p01"],
            }
        ],
        "absent": [
            {"category": "Agreement Date", "principles_cited": ["p02"]},
            {"category": "Minimum Commitment", "principles_cited": ["p02"]},
            {"category": "Volume Restriction", "principles_cited": ["p02"]},
        ],
    }
    backend = FakeBackend([json.dumps(payload)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config)
    kinds = [d.decision_kind for d in result.decisions]
    assert kinds.count("absence") == 3
    assert {d.decision_idx for d in result.decisions} == {0, 1, 2, 3}
    micro = result.trial.answer["level_a"]["micro"]
    assert micro["counts"] == {"TP": 1, "FP": 0, "FN": 0, "TN": 3}
    assert micro["absent_class_recall"] == 1.0


def test_infeasible_at_length_triggers_without_an_api_call(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=64)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "infeasible_at_length"
    assert backend.calls == []
    detail = result.trial.failure_detail
    assert detail["context_limit"] == 64
    assert detail["prompt_tokens_estimate"] > 64
    assert result.trial.answer is None


def test_infeasible_trial_still_writes_decision_rows_with_null_scores(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=64)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert len(result.decisions) == 4
    for row in result.decisions:
        assert row.answer_score is None
        assert row.predicted is None
        assert row.gold is not None


def test_repair_policy_is_bounded(env, harness_val, config):
    backend = FakeBackend(["not json at all"] * 10, context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.n_repair_attempts == config.max_repair_attempts
    assert len(backend.calls) == config.max_repair_attempts + 1
    assert result.trial.failure_detail["stage"] == "json_decode"


def test_repair_policy_succeeds_within_budget(env, harness_val, config):
    backend = FakeBackend(["garbage", json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "ok"
    assert result.trial.n_repair_attempts == 1
    assert len(backend.calls) == 2


def test_zero_repair_budget_makes_a_single_call(env, harness_val, config):
    config.max_repair_attempts = 0
    backend = FakeBackend(["garbage"], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "parse_failure"
    assert len(backend.calls) == 1


def test_schema_validation_failure_is_a_parse_failure(env, harness_val, config):
    backend = FakeBackend(['{"extractions": [{"category": "X"}], "absent": []}'] * 5, context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["stage"] == "schema_validation"


def test_api_error_is_recorded_with_rows(env, harness_val, config):
    backend = FakeBackend([], context_limit=100000, raise_on_call=BackendError("boom"))
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "api_error"
    assert "boom" in result.trial.failure_detail["error"]
    assert len(result.decisions) == 4


def test_compliance_is_measured_in_c1(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config, condition="C1")
    assert result.trial.compliance["n_applicable"] > 0
    assert result.trial.citation is None


def test_citation_is_null_outside_c3(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)] * 2, context_limit=100000)
    for condition in ("C1", "C2"):
        result = _run(env, backend, harness_val["FAKE_0001"], config, condition=condition)
        assert result.trial.citation is None
        for row in result.decisions:
            assert row.citation_eval is None


def test_gold_applicable_is_the_scope_relevant_slice(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    by_target = {d.target: d.gold_applicable for d in result.decisions}
    assert by_target["Governing Law"] == ["p01"]
    assert by_target["Minimum Commitment"] == ["p01", "p03"]
    for applicable in by_target.values():
        assert "p04" not in applicable


def test_compliance_failure_is_detected(env, harness_val, config):
    payload = {
        "extractions": [
            {
                "category": "Governing Law",
                "spans": ["governed by Delaware law", "governed by Delaware law"],
                "principles_cited": ["p01"],
            },
            {
                "category": "Agreement Date",
                "spans": ["This Agreement is entered into as of March 3, 2019."],
                "principles_cited": ["p01"],
            },
            {
                "category": "Minimum Commitment",
                "spans": [
                    "Buyer shall order no more than 50,000 units in any calendar quarter."
                ],
                "principles_cited": ["p03"],
            },
            {
                "category": "Volume Restriction",
                "spans": [
                    "Buyer shall order no more than 50,000 units in any calendar quarter."
                ],
                "principles_cited": ["p03"],
            },
        ],
        "absent": [],
    }
    backend = FakeBackend([json.dumps(payload)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    per_principle = result.trial.compliance["per_principle"]
    assert per_principle["p01"] is False
    assert per_principle["p03"] is False
    assert per_principle["p04"] is False


def test_leakage_instrument_counts_cited_decisions_and_text_refs(env, harness_val, config):
    payload = {
        "extractions": [
            {
                "category": "Governing Law",
                "spans": ["per p03, governed by Delaware"],
                "principles_cited": ["p01"],
            }
        ],
        "absent": [
            {"category": "Agreement Date", "principles_cited": []},
            {"category": "Minimum Commitment", "principles_cited": []},
            {"category": "Volume Restriction", "principles_cited": []},
        ],
    }
    backend = FakeBackend([json.dumps(payload)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config, condition="C1")
    assert result.trial.leakage["n_decisions_with_nonempty_cited"] == 1
    assert result.trial.leakage["text_field_principle_refs"] == 1
    assert result.trial.leakage["n_decisions"] == 4


def test_held_out_principle_subset_narrows_gold_applicable(env, harness_val, config):
    subset = env.principle_set().subset(["p01"], version="held-out")
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = run_trial(
        env=env,
        backend=backend,
        instance=harness_val["FAKE_0001"],
        condition="C3",
        seed=0,
        schema_variant="field_present",
        principle_set=subset,
        config=config,
    )
    for row in result.decisions:
        assert row.gold_applicable == ["p01"]
    assert set(result.trial.compliance["per_principle"]) == {"p01"}


def test_prompt_carries_the_json_schema_to_the_backend(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)] * 2, context_limit=100000)
    _run(env, backend, harness_val["FAKE_0001"], config, variant="field_absent")
    schema = backend.calls[0]["json_schema"]
    assert "principles_cited" not in json.dumps(schema)


def test_feasibility_is_measured_on_the_assembled_prompt_not_the_contract(env, harness_val, config):
    instance = harness_val["FAKE_0001"]
    limits = {}
    for condition in ("C1", "C2", "C3"):
        backend = FakeBackend([json.dumps(PERFECT)], context_limit=10**9)
        _run(env, backend, instance, config, condition=condition)
        limits[condition] = backend.calls[0]["messages"][1]["content"]
    assert len(limits["C2"]) > len(limits["C1"])
    assert len(limits["C3"]) > len(limits["C2"])


def test_principles_can_make_c2_infeasible_where_c1_is_feasible(env, harness_val, config):
    instance = harness_val["FAKE_0001"]
    probe = FakeBackend([json.dumps(PERFECT)], context_limit=10**9)
    _run(env, probe, instance, config, condition="C1")
    c1_tokens = probe.count_tokens(
        "".join(m["content"] for m in probe.calls[0]["messages"])
    )
    limit = c1_tokens + config.max_output_tokens + 10

    c1 = _run(env, FakeBackend([json.dumps(PERFECT)], context_limit=limit), instance, config, condition="C1")
    c2 = _run(env, FakeBackend([json.dumps(PERFECT)], context_limit=limit), instance, config, condition="C2")
    assert c1.trial.outcome == "ok"
    assert c2.trial.outcome == "infeasible_at_length"


def test_length_bucket_comes_from_the_reference_tokenizer_not_the_backend(env, harness_val, config):
    instance = harness_val["FAKE_0001"]
    small = FakeBackend([json.dumps(PERFECT)], context_limit=10**9)
    a = _run(env, small, instance, config, condition="C1")
    b = _run(env, FakeBackend([json.dumps(PERFECT)], context_limit=64), instance, config, condition="C1")
    assert a.trial.length_bucket == b.trial.length_bucket
    assert a.trial.n_contract_tokens == instance.n_tokens


ONE_SPAN_GL = "This Agreement shall be governed by the laws of the State of Delaware."


def _coverage_payload(extractions, absent):
    return json.dumps({"extractions": extractions, "absent": absent})


def test_a_valid_output_covers_every_target_exactly_once(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "ok"
    targets = env.task_definition().targets
    assert [d.target for d in result.decisions] == targets
    assert len(result.decisions) == len(targets)


def test_missing_target_is_repairable_then_terminal_as_parse_failure(env, harness_val, config):
    bad = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}],
        [{"category": "Agreement Date", "principles_cited": []}],
    )
    backend = FakeBackend([bad] * 10, context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["stage"] == "coverage"
    assert "no decision" in result.trial.failure_detail["detail"]
    assert result.trial.n_repair_attempts == config.max_repair_attempts
    assert len(backend.calls) == config.max_repair_attempts + 1


def test_duplicate_target_across_extractions_and_absent_is_a_coverage_violation(env, harness_val, config):
    bad = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}],
        [
            {"category": "Governing Law", "principles_cited": []},
            {"category": "Agreement Date", "principles_cited": []},
            {"category": "Minimum Commitment", "principles_cited": []},
            {"category": "Volume Restriction", "principles_cited": []},
        ],
    )
    backend = FakeBackend([bad] * 10, context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["stage"] == "coverage"
    assert "more than once" in result.trial.failure_detail["detail"]


def test_coverage_violation_is_repaired_within_budget(env, harness_val, config):
    bad = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}], []
    )
    good = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}],
        [
            {"category": "Agreement Date", "principles_cited": []},
            {"category": "Minimum Commitment", "principles_cited": []},
            {"category": "Volume Restriction", "principles_cited": []},
        ],
    )
    backend = FakeBackend([bad, good], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config)
    assert result.trial.outcome == "ok"
    assert result.trial.n_repair_attempts == 1
    assert "exactly once" in backend.calls[1]["messages"][-1]["content"]


def test_coverage_repair_uses_the_same_bounded_budget_as_parse_repair(env, harness_val, config):
    config.max_repair_attempts = 0
    bad = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}], []
    )
    backend = FakeBackend([bad] * 5, context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config)
    assert result.trial.outcome == "parse_failure"
    assert len(backend.calls) == 1


def test_an_empty_span_list_is_rejected_by_the_schema(env, harness_val, config):
    bad = _coverage_payload(
        [{"category": "Governing Law", "spans": [], "principles_cited": []}],
        [
            {"category": "Agreement Date", "principles_cited": []},
            {"category": "Minimum Commitment", "principles_cited": []},
            {"category": "Volume Restriction", "principles_cited": []},
        ],
    )
    backend = FakeBackend([bad] * 5, context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["stage"] == "schema_validation"


def test_decision_row_carries_the_full_span_list_and_within_decision_f1(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    gl = next(d for d in result.decisions if d.target == "Governing Law")
    assert len(gl.predicted["spans"]) == 2
    assert len(gl.gold["spans"]) == 2
    assert gl.answer_score["span_f1"] == 1.0


def test_missing_one_of_two_gold_spans_costs_score_but_not_the_decision(env, harness_val, config):
    payload = json.loads(json.dumps(PERFECT))
    payload["extractions"][0]["spans"] = [ONE_SPAN_GL]
    backend = FakeBackend([json.dumps(payload)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    gl = next(d for d in result.decisions if d.target == "Governing Law")
    assert 0.0 < gl.answer_score["span_f1"] < 1.0
    assert gl.decision_kind == "extraction"
    assert len(result.decisions) == 4


def test_repair_stages_are_recorded_even_when_the_trial_recovers(env, harness_val, config):
    bad_coverage = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}], []
    )
    good = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}],
        [
            {"category": "Agreement Date", "principles_cited": []},
            {"category": "Minimum Commitment", "principles_cited": []},
            {"category": "Volume Restriction", "principles_cited": []},
        ],
    )
    backend = FakeBackend(["not json", bad_coverage, good], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config)
    assert result.trial.outcome == "ok"
    assert result.trial.repair_stages == ["json_decode", "coverage"]
    assert result.trial.n_repair_attempts == 2


def test_truncated_completion_is_distinguished_from_a_formatting_defect(env, harness_val, config):
    class TruncatingBackend(FakeBackend):
        def sample(self, messages, json_schema, temperature, seed, max_tokens):
            result = super().sample(messages, json_schema, temperature, seed, max_tokens)
            result.finish_reason = "length"
            result.raw = {**result.raw, "n_reasoning_chars": 14998}
            return result

    backend = TruncatingBackend([""] * 5, context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["completion_truncated"] is True
    assert result.trial.failure_detail["finish_reason"] == "length"
    assert result.trial.failure_detail["n_reasoning_chars"] == 14998


def test_first_attempt_and_final_are_identical_when_no_repair_was_needed(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.n_repair_attempts == 0
    first = result.trial.first_attempt
    assert first["parsed"] is True
    assert first["answer"] == result.trial.answer
    assert first["citation"] == result.trial.citation
    assert first["compliance"] == result.trial.compliance


def test_first_attempt_and_final_diverge_on_a_repaired_trial(env, harness_val, config):
    good = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": ["p01"]}],
        [
            {"category": "Agreement Date", "principles_cited": ["p02"]},
            {"category": "Minimum Commitment", "principles_cited": ["p02"]},
            {"category": "Volume Restriction", "principles_cited": ["p02"]},
        ],
    )
    backend = FakeBackend(["not json", good], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config)
    assert result.trial.outcome == "ok"
    assert result.trial.n_repair_attempts == 1
    assert result.trial.answer is not None
    first = result.trial.first_attempt
    assert first["parsed"] is False
    assert first["failure_stage"] == "json_decode"
    assert first["answer"] is None
    assert first != {"parsed": True}


def test_first_attempt_records_the_unassisted_defect_class(env, harness_val, config):
    bad_coverage = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}], []
    )
    good = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}],
        [
            {"category": "Agreement Date", "principles_cited": []},
            {"category": "Minimum Commitment", "principles_cited": []},
            {"category": "Volume Restriction", "principles_cited": []},
        ],
    )
    backend = FakeBackend([bad_coverage, good], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config, condition="C1")
    assert result.trial.first_attempt["failure_stage"] == "coverage"


def test_first_attempt_aggregate_excludes_trials_that_needed_help(env, harness_val, config):
    unassisted = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    assisted = FakeBackend(["not json", json.dumps(PERFECT)], context_limit=100000)
    rows = [
        _run(env, unassisted, harness_val["FAKE_0001"], config).trial.model_dump(),
        _run(env, assisted, harness_val["FAKE_0001"], config).trial.model_dump(),
    ]
    final = metrics.summarize_trials(rows, "final")
    first = metrics.summarize_trials(rows, "first_attempt")
    assert final["n_scored"] == 2
    assert first["n_scored"] == 1
    assert first["scope"] == "first_attempt"
    assert approx_equal(final["any_repair_rate"], 0.5)


def approx_equal(a, b, tol=1e-9):
    return abs(a - b) < tol


def test_generous_output_budget_is_the_default_and_is_recorded(env, harness_val):
    from harness.runner import DEFAULT_MAX_OUTPUT_TOKENS

    default_config = RunConfig(run_id="budget")
    assert default_config.max_output_tokens == DEFAULT_MAX_OUTPUT_TOKENS
    assert DEFAULT_MAX_OUTPUT_TOKENS >= 8192
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=10**9)
    result = _run(env, backend, harness_val["FAKE_0001"], default_config)
    assert result.trial.max_output_tokens == DEFAULT_MAX_OUTPUT_TOKENS
    assert backend.calls[0]["max_tokens"] == DEFAULT_MAX_OUTPUT_TOKENS


def test_correctness_thresholds_are_recorded_on_the_trial(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.correctness_thresholds["headline_span_f1_correct"] == 0.5
    assert result.trial.correctness_thresholds["span_f1_is_swept"] is True
    assert result.trial.correctness_thresholds["sweep_span_f1_thresholds"][0] == 0.1
    assert result.trial.correctness_thresholds["citation_requires_exact_set"] is True


def test_decision_rows_carry_the_crosstab_cell_in_c3(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    for row in result.decisions:
        assert row.citation_x_correctness is not None
        assert set(row.citation_x_correctness) == {
            "cell", "span_f1", "citation_correct", "answer_correct_at_headline",
        }
    sweep = result.trial.citation["x_answer_correctness_sweep"]
    assert sum(sweep["headline"]["counts"].values()) == 4


def test_sweep_recomputed_from_decisions_matches_the_trial_row(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    stored_rows = [d.model_dump() for d in result.decisions]
    recomputed = metrics.citation_correctness_sweep(stored_rows, config.thresholds)
    assert recomputed == result.trial.citation["x_answer_correctness_sweep"]


def test_decision_rows_keep_the_raw_ingredients_of_the_sweep(env, harness_val, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    for row in result.decisions:
        assert row.answer_score["cell"] in ("TP", "FP", "FN", "TN")
        assert "span_f1" in row.answer_score
        assert row.citation_eval is not None
        assert set(row.citation_eval) >= {"tp", "fp", "fn"}


def test_three_way_verbatim_reaches_the_trial_row(env, harness_val, config):
    payload = json.loads(json.dumps(PERFECT))
    payload["extractions"][1]["spans"] = ["This Agreement was signed in March of 2019."]
    backend = FakeBackend([json.dumps(payload)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    level_b = result.trial.answer["level_b"]
    assert level_b["verbatim_exact_rate"] is not None
    assert level_b["verbatim_not_found_rate"] > 0.0
    assert level_b["n_not_found_spans"] == 1
    assert level_b["verbatim_cosmetic_gap"] == level_b["verbatim_normalized_only_rate"]


def test_repair_is_disabled_by_default():
    from harness.runner import DEFAULT_MAX_REPAIR_ATTEMPTS, REPAIR_DISABLED_NOTE

    assert DEFAULT_MAX_REPAIR_ATTEMPTS == 0
    assert RunConfig(run_id="x").max_repair_attempts == 0
    assert "deliberately DISABLED" in REPAIR_DISABLED_NOTE
    assert "prompt artifact" in REPAIR_DISABLED_NOTE
    assert "Re-enabling is a config change" in REPAIR_DISABLED_NOTE


def test_a_nonconforming_output_is_terminal_by_default(env, harness_val):
    config = RunConfig(run_id="no-repair", max_output_tokens=256)
    backend = FakeBackend(["not json"] * 5, context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.n_repair_attempts == 0
    assert result.trial.repair_stages == ["json_decode"]
    assert len(backend.calls) == 1


def test_coverage_failure_is_terminal_by_default(env, harness_val):
    config = RunConfig(run_id="no-repair", max_output_tokens=256)
    bad = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}], []
    )
    backend = FakeBackend([bad] * 5, context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0002"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["stage"] == "coverage"
    assert len(backend.calls) == 1


def test_repair_machinery_still_works_when_re_enabled(env, harness_val):
    config = RunConfig(run_id="repair-on", max_output_tokens=256, max_repair_attempts=2)
    backend = FakeBackend(["not json", json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.outcome == "ok"
    assert result.trial.n_repair_attempts == 1
    assert len(backend.calls) == 2
    assert result.trial.max_repair_attempts == 2


def test_first_attempt_equals_final_when_repair_is_off(env, harness_val):
    config = RunConfig(run_id="no-repair", max_output_tokens=256)
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, harness_val["FAKE_0001"], config)
    assert result.trial.first_attempt["parsed"] is True
    assert result.trial.first_attempt["answer"] == result.trial.answer
    assert result.trial.first_attempt["citation"] == result.trial.citation


def test_summaries_flag_that_the_two_scopes_are_not_independent(env, harness_val):
    config = RunConfig(run_id="no-repair", max_output_tokens=256)
    rows = [
        _run(env, FakeBackend([json.dumps(PERFECT)], context_limit=100000),
             harness_val["FAKE_0001"], config).trial.model_dump(),
        _run(env, FakeBackend(["not json"], context_limit=100000),
             harness_val["FAKE_0002"], config).trial.model_dump(),
    ]
    assert metrics.repair_is_enabled(rows) is False
    final = metrics.summarize_trials(rows, "final")
    first = metrics.summarize_trials(rows, "first_attempt")
    assert final["scopes_are_independent"] is False
    assert final["n_scored"] == first["n_scored"] == 1
    assert "not independent measurements" in metrics.summarize_trials.__doc__


def test_parse_failure_stage_breakdown_is_the_conformance_result(env, harness_val):
    config = RunConfig(run_id="conf", max_output_tokens=256)
    bad_coverage = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}], []
    )
    rows = [
        _run(env, FakeBackend([json.dumps(PERFECT)], context_limit=100000),
             harness_val["FAKE_0001"], config).trial.model_dump(),
        _run(env, FakeBackend(["not json"], context_limit=100000),
             harness_val["FAKE_0001"], config, condition="C1").trial.model_dump(),
        _run(env, FakeBackend([bad_coverage], context_limit=100000),
             harness_val["FAKE_0002"], config).trial.model_dump(),
        _run(env, FakeBackend([json.dumps(PERFECT)], context_limit=32),
             harness_val["FAKE_0001"], config, condition="C2").trial.model_dump(),
    ]
    conformance = metrics.outcome_rates(rows)["conformance"]
    assert conformance["n_attempted"] == 3
    assert conformance["n_conformant"] == 1
    assert approx_equal(conformance["conformance_rate"], 1 / 3)
    assert conformance["parse_failure_by_stage"]["json_decode"] == 1
    assert conformance["parse_failure_by_stage"]["coverage"] == 1
    assert conformance["parse_failure_by_stage"]["schema_validation"] == 0


def test_conformance_breakdown_is_reachable_per_bucket_and_condition(env, harness_val):
    config = RunConfig(run_id="conf2", max_output_tokens=256)
    rows = [
        _run(env, FakeBackend(["not json"], context_limit=100000),
             harness_val["FAKE_0001"], config).trial.model_dump(),
        _run(env, FakeBackend(["not json"], context_limit=100000),
             harness_val["FAKE_0002"], config).trial.model_dump(),
    ]
    summary = metrics.stratified_summary(rows)
    group = summary["groups"][0]
    assert group["overall"]["scopes_are_independent"] is False
    for bucket in group["by_length_bucket"].values():
        breakdown = bucket["final"]["conformance"]["parse_failure_by_stage"]
        assert breakdown["json_decode"] == 1


def test_citation_is_unavailable_when_the_env_has_no_applicability(harness_val, config):
    env = FakeEnvironment(applicability_available=False)
    instance = env.load_instances("harness_val")[0]
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, instance, config, condition="C3")
    assert result.trial.outcome == "ok"
    assert result.trial.citation["available"] is False
    assert result.trial.citation["reason"]
    assert "precision" not in result.trial.citation
    for row in result.decisions:
        assert row.citation_eval["available"] is False
        assert row.citation_x_correctness is None


def test_citing_nothing_does_not_score_perfect_without_applicability(harness_val, config):
    env = FakeEnvironment(applicability_available=False)
    instance = env.load_instances("harness_val")[0]
    silent = json.loads(json.dumps(PERFECT))
    for item in silent["extractions"]:
        item["principles_cited"] = []
    backend = FakeBackend([json.dumps(silent)], context_limit=100000)
    result = _run(env, backend, instance, config, condition="C3")
    assert result.trial.citation.get("precision") is None
    assert result.trial.citation["available"] is False


def test_legitimately_empty_gold_still_scores_when_applicability_is_present(
    env, harness_val, config
):
    silent = json.loads(json.dumps(PERFECT))
    for item in silent["extractions"]:
        item["principles_cited"] = []
    backend = FakeBackend([json.dumps(silent)], context_limit=100000)
    result = run_trial(
        env=env,
        backend=backend,
        instance=harness_val["FAKE_0001"],
        condition="C3",
        seed=0,
        schema_variant="field_present",
        principle_set=env.principle_set().subset(["p02"]),
        config=config,
    )
    assert result.trial.citation["available"] is True
    empty_gold = [r for r in result.decisions if not r.gold_applicable]
    assert empty_gold
    for row in empty_gold:
        assert row.citation_eval["available"] is True
        assert row.citation_eval["precision"] == 1.0
        assert row.citation_eval["recall"] == 1.0
        assert row.citation_eval["f1"] == 1.0


def test_summary_excludes_unavailable_citation_trials(harness_val, config):
    env = FakeEnvironment(applicability_available=False)
    instance = env.load_instances("harness_val")[0]
    measured = FakeEnvironment()
    rows = [
        _run(env, FakeBackend([json.dumps(PERFECT)], context_limit=100000),
             instance, config, condition="C3").trial.model_dump(),
        _run(measured, FakeBackend([json.dumps(PERFECT)], context_limit=100000),
             measured.load_instances("harness_val")[0], config, condition="C3",
             seed=1).trial.model_dump(),
    ]
    summary = metrics.summarize_trials(rows)
    assert summary["citation_availability"]["n_available"] == 1
    assert summary["citation_availability"]["n_unavailable"] == 1
    assert summary["citation_f1"]["n"] == 1
