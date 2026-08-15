import json

import pytest

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
def dev(env):
    return {i.contract_id: i for i in env.load_instances("dev")}


@pytest.fixture
def config(tmp_path):
    return RunConfig(
        run_id="test-run",
        temperature=0.7,
        max_output_tokens=256,
        max_repair_attempts=2,
        principle_set_version="fake-v1",
        raw_response_dir=tmp_path / "responses",
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


def test_ok_trial_scores_and_emits_one_row_per_decision(env, dev, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config)
    assert result.trial.outcome == "ok"
    assert result.trial.answer["span_f1_macro"] == 1.0
    assert len(result.decisions) == 4
    assert result.trial.compliance["pass_rate"] == 1.0
    assert result.trial.citation["precision"] == 1.0
    assert result.trial.response_sha256


def test_absence_is_an_explicit_row_for_every_non_extracted_category(env, dev, config):
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
    result = _run(env, backend, dev["FAKE_0002"], config)
    kinds = [d.decision_kind for d in result.decisions]
    assert kinds.count("absence") == 3
    assert {d.decision_idx for d in result.decisions} == {0, 1, 2, 3}
    assert result.trial.answer["absence_accuracy"] == 1.0


def test_infeasible_at_length_triggers_without_an_api_call(env, dev, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=64)
    result = _run(env, backend, dev["FAKE_0001"], config)
    assert result.trial.outcome == "infeasible_at_length"
    assert backend.calls == []
    detail = result.trial.failure_detail
    assert detail["context_limit"] == 64
    assert detail["prompt_tokens_estimate"] > 64
    assert result.trial.answer is None


def test_infeasible_trial_still_writes_decision_rows_with_null_scores(env, dev, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=64)
    result = _run(env, backend, dev["FAKE_0001"], config)
    assert len(result.decisions) == 4
    for row in result.decisions:
        assert row.answer_score is None
        assert row.predicted is None
        assert row.gold is not None


def test_repair_policy_is_bounded(env, dev, config):
    backend = FakeBackend(["not json at all"] * 10, context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.n_repair_attempts == config.max_repair_attempts
    assert len(backend.calls) == config.max_repair_attempts + 1
    assert result.trial.failure_detail["stage"] == "json_decode"


def test_repair_policy_succeeds_within_budget(env, dev, config):
    backend = FakeBackend(["garbage", json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config)
    assert result.trial.outcome == "ok"
    assert result.trial.n_repair_attempts == 1
    assert len(backend.calls) == 2


def test_zero_repair_budget_makes_a_single_call(env, dev, config):
    config.max_repair_attempts = 0
    backend = FakeBackend(["garbage"], context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config)
    assert result.trial.outcome == "parse_failure"
    assert len(backend.calls) == 1


def test_schema_validation_failure_is_a_parse_failure(env, dev, config):
    backend = FakeBackend(['{"extractions": [{"category": "X"}], "absent": []}'] * 5, context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["stage"] == "schema_validation"


def test_api_error_is_recorded_with_rows(env, dev, config):
    backend = FakeBackend([], context_limit=100000, raise_on_call=BackendError("boom"))
    result = _run(env, backend, dev["FAKE_0001"], config)
    assert result.trial.outcome == "api_error"
    assert "boom" in result.trial.failure_detail["error"]
    assert len(result.decisions) == 4


def test_compliance_is_measured_in_c1(env, dev, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config, condition="C1")
    assert result.trial.compliance["n_applicable"] > 0
    assert result.trial.citation is None


def test_citation_is_null_outside_c3(env, dev, config):
    backend = FakeBackend([json.dumps(PERFECT)] * 2, context_limit=100000)
    for condition in ("C1", "C2"):
        result = _run(env, backend, dev["FAKE_0001"], config, condition=condition)
        assert result.trial.citation is None
        for row in result.decisions:
            assert row.citation_eval is None


def test_gold_applicable_is_the_scope_relevant_slice(env, dev, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config)
    by_target = {d.target: d.gold_applicable for d in result.decisions}
    assert by_target["Governing Law"] == ["p01"]
    assert by_target["Minimum Commitment"] == ["p01", "p03"]
    for applicable in by_target.values():
        assert "p04" not in applicable


def test_compliance_failure_is_detected(env, dev, config):
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
    result = _run(env, backend, dev["FAKE_0001"], config)
    per_principle = result.trial.compliance["per_principle"]
    assert per_principle["p01"] is False
    assert per_principle["p03"] is False
    assert per_principle["p04"] is False


def test_leakage_instrument_counts_cited_decisions_and_text_refs(env, dev, config):
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
    result = _run(env, backend, dev["FAKE_0002"], config, condition="C1")
    assert result.trial.leakage["n_decisions_with_nonempty_cited"] == 1
    assert result.trial.leakage["text_field_principle_refs"] == 1
    assert result.trial.leakage["n_decisions"] == 4


def test_held_out_principle_subset_narrows_gold_applicable(env, dev, config):
    subset = env.principle_set().subset(["p01"], version="held-out")
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = run_trial(
        env=env,
        backend=backend,
        instance=dev["FAKE_0001"],
        condition="C3",
        seed=0,
        schema_variant="field_present",
        principle_set=subset,
        config=config,
    )
    for row in result.decisions:
        assert row.gold_applicable == ["p01"]
    assert set(result.trial.compliance["per_principle"]) == {"p01"}


def test_prompt_carries_the_json_schema_to_the_backend(env, dev, config):
    backend = FakeBackend([json.dumps(PERFECT)] * 2, context_limit=100000)
    _run(env, backend, dev["FAKE_0001"], config, variant="field_absent")
    schema = backend.calls[0]["json_schema"]
    assert "principles_cited" not in json.dumps(schema)


def test_feasibility_is_measured_on_the_assembled_prompt_not_the_contract(env, dev, config):
    instance = dev["FAKE_0001"]
    limits = {}
    for condition in ("C1", "C2", "C3"):
        backend = FakeBackend([json.dumps(PERFECT)], context_limit=10**9)
        _run(env, backend, instance, config, condition=condition)
        limits[condition] = backend.calls[0]["messages"][1]["content"]
    assert len(limits["C2"]) > len(limits["C1"])
    assert len(limits["C3"]) > len(limits["C2"])


def test_principles_can_make_c2_infeasible_where_c1_is_feasible(env, dev, config):
    instance = dev["FAKE_0001"]
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


def test_length_bucket_comes_from_the_reference_tokenizer_not_the_backend(env, dev, config):
    instance = dev["FAKE_0001"]
    small = FakeBackend([json.dumps(PERFECT)], context_limit=10**9)
    a = _run(env, small, instance, config, condition="C1")
    b = _run(env, FakeBackend([json.dumps(PERFECT)], context_limit=64), instance, config, condition="C1")
    assert a.trial.length_bucket == b.trial.length_bucket
    assert a.trial.n_contract_tokens == instance.n_tokens


ONE_SPAN_GL = "This Agreement shall be governed by the laws of the State of Delaware."


def _coverage_payload(extractions, absent):
    return json.dumps({"extractions": extractions, "absent": absent})


def test_a_valid_output_covers_every_target_exactly_once(env, dev, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config)
    assert result.trial.outcome == "ok"
    targets = env.task_definition().targets
    assert [d.target for d in result.decisions] == targets
    assert len(result.decisions) == len(targets)


def test_missing_target_is_repairable_then_terminal_as_parse_failure(env, dev, config):
    bad = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}],
        [{"category": "Agreement Date", "principles_cited": []}],
    )
    backend = FakeBackend([bad] * 10, context_limit=100000)
    result = _run(env, backend, dev["FAKE_0002"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["stage"] == "coverage"
    assert "no decision" in result.trial.failure_detail["detail"]
    assert result.trial.n_repair_attempts == config.max_repair_attempts
    assert len(backend.calls) == config.max_repair_attempts + 1


def test_duplicate_target_across_extractions_and_absent_is_a_coverage_violation(env, dev, config):
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
    result = _run(env, backend, dev["FAKE_0002"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["stage"] == "coverage"
    assert "more than once" in result.trial.failure_detail["detail"]


def test_coverage_violation_is_repaired_within_budget(env, dev, config):
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
    result = _run(env, backend, dev["FAKE_0002"], config)
    assert result.trial.outcome == "ok"
    assert result.trial.n_repair_attempts == 1
    assert "exactly once" in backend.calls[1]["messages"][-1]["content"]


def test_coverage_repair_uses_the_same_bounded_budget_as_parse_repair(env, dev, config):
    config.max_repair_attempts = 0
    bad = _coverage_payload(
        [{"category": "Governing Law", "spans": [ONE_SPAN_GL], "principles_cited": []}], []
    )
    backend = FakeBackend([bad] * 5, context_limit=100000)
    result = _run(env, backend, dev["FAKE_0002"], config)
    assert result.trial.outcome == "parse_failure"
    assert len(backend.calls) == 1


def test_an_empty_span_list_is_rejected_by_the_schema(env, dev, config):
    bad = _coverage_payload(
        [{"category": "Governing Law", "spans": [], "principles_cited": []}],
        [
            {"category": "Agreement Date", "principles_cited": []},
            {"category": "Minimum Commitment", "principles_cited": []},
            {"category": "Volume Restriction", "principles_cited": []},
        ],
    )
    backend = FakeBackend([bad] * 5, context_limit=100000)
    result = _run(env, backend, dev["FAKE_0002"], config)
    assert result.trial.outcome == "parse_failure"
    assert result.trial.failure_detail["stage"] == "schema_validation"


def test_decision_row_carries_the_full_span_list_and_within_decision_f1(env, dev, config):
    backend = FakeBackend([json.dumps(PERFECT)], context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config)
    gl = next(d for d in result.decisions if d.target == "Governing Law")
    assert len(gl.predicted["spans"]) == 2
    assert len(gl.gold["spans"]) == 2
    assert gl.answer_score["span_f1"] == 1.0


def test_missing_one_of_two_gold_spans_costs_score_but_not_the_decision(env, dev, config):
    payload = json.loads(json.dumps(PERFECT))
    payload["extractions"][0]["spans"] = [ONE_SPAN_GL]
    backend = FakeBackend([json.dumps(payload)], context_limit=100000)
    result = _run(env, backend, dev["FAKE_0001"], config)
    gl = next(d for d in result.decisions if d.target == "Governing Law")
    assert 0.0 < gl.answer_score["span_f1"] < 1.0
    assert gl.decision_kind == "extraction"
    assert len(result.decisions) == 4
