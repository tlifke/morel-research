import gzip
import json

import pytest

from harness.backends.base import BackendError, SamplingResult
from harness.backends.fake_backend import FakeBackend
from harness.envs.fake_env import FakeEnvironment
from harness.runner import RunConfig, run_grid, run_trial
from harness.store import ResultsStore
from harness.trace_store import TraceExistsError, TraceReader, TraceStore

PAYLOAD = {
    "extractions": [
        {
            "category": "Governing Law",
            "spans": ["This Agreement shall be governed by the laws of the State of Delaware."],
            "principles_cited": ["p01"],
        }
    ],
    "absent": [
        {"category": "Agreement Date", "principles_cited": ["p02"]},
        {"category": "Minimum Commitment", "principles_cited": ["p02"]},
        {"category": "Volume Restriction", "principles_cited": ["p02"]},
    ],
}


class ReasoningBackend(FakeBackend):
    def sample(self, messages, json_schema, temperature, seed, max_tokens):
        result = super().sample(messages, json_schema, temperature, seed, max_tokens)
        result.raw = {
            **result.raw,
            "choices": [{"message": {"reasoning_content": "I considered p01 first."}}],
        }
        return result


@pytest.fixture
def env():
    return FakeEnvironment()


@pytest.fixture
def instance(env):
    return {i.contract_id: i for i in env.load_instances("harness_val")}["FAKE_0002"]


def _config(tmp_path, **kw):
    return RunConfig(
        run_id="trace-test",
        max_output_tokens=kw.pop("max_output_tokens", 4096),
        trace_root=tmp_path / "traces",
        principle_set_version="fake-v1",
        **kw,
    )


def _run(env, backend, instance, config, condition="C3"):
    return run_trial(
        env=env,
        backend=backend,
        instance=instance,
        condition=condition,
        seed=0,
        schema_variant="field_present",
        principle_set=env.principle_set(),
        config=config,
    )


def test_trace_records_one_attempt_per_sample(env, instance, tmp_path):
    backend = FakeBackend(["garbage", json.dumps(PAYLOAD)], context_limit=100000)
    result = _run(env, backend, instance, _config(tmp_path, max_repair_attempts=2))
    assert result.trial.outcome == "ok"
    assert [a.attempt_idx for a in result.trace.attempts] == [0, 1]
    assert result.trace.attempts[0].parse_outcome == "failed"
    assert result.trace.attempts[1].parse_outcome == "ok"


def test_trace_stores_the_exact_assembled_prompt_as_sent(env, instance, tmp_path):
    backend = FakeBackend([json.dumps(PAYLOAD)], context_limit=100000)
    result = _run(env, backend, instance, _config(tmp_path))
    sent = backend.calls[0]["messages"]
    assert result.trace.attempts[0].prompt_sent == sent
    assert instance.text in result.trace.attempts[0].prompt_sent[1]["content"]
    assert "[p01]" in result.trace.attempts[0].prompt_sent[1]["content"]


def test_repair_turns_carry_the_growing_prompt_and_the_repair_message(env, instance, tmp_path):
    backend = FakeBackend(["garbage", json.dumps(PAYLOAD)], context_limit=100000)
    result = _run(env, backend, instance, _config(tmp_path, max_repair_attempts=2))
    first, second = result.trace.attempts
    assert first.repair_message_sent is not None
    assert "could not be parsed" in first.repair_message_sent
    assert len(second.prompt_sent) > len(first.prompt_sent)
    assert second.prompt_sent[-1]["content"] == first.repair_message_sent


def test_trace_keeps_the_raw_body_and_reasoning_content(env, instance, tmp_path):
    backend = ReasoningBackend([json.dumps(PAYLOAD)], context_limit=100000)
    result = _run(env, backend, instance, _config(tmp_path))
    attempt = result.trace.attempts[0]
    assert attempt.reasoning_content == "I considered p01 first."
    assert attempt.raw_response_body is not None
    assert attempt.response_text == json.dumps(PAYLOAD)
    assert attempt.response_sha256 == result.trial.response_sha256


def test_trace_records_truncation_and_usage(env, instance, tmp_path):
    class TruncatingBackend(FakeBackend):
        def sample(self, messages, json_schema, temperature, seed, max_tokens):
            result = super().sample(messages, json_schema, temperature, seed, max_tokens)
            result.finish_reason = "length"
            return result

    backend = TruncatingBackend([""] * 5, context_limit=100000)
    result = _run(env, backend, instance, _config(tmp_path))
    attempt = result.trace.attempts[0]
    assert attempt.completion_truncated is True
    assert attempt.finish_reason == "length"
    assert attempt.n_prompt_tokens is not None
    assert attempt.latency_ms is not None


def test_traces_are_written_compressed_and_read_back(env, tmp_path):
    store = ResultsStore(tmp_path / "results")
    config = _config(tmp_path)
    run_grid(
        env=env,
        backend=FakeBackend(lambda m, i: json.dumps(PAYLOAD), context_limit=100000),
        instances=env.load_instances("harness_val"),
        conditions=["C3"],
        seeds=[0],
        schema_variants=["field_present"],
        principle_set=env.principle_set(),
        config=config,
        store=store,
    )
    reader = TraceReader(tmp_path / "traces")
    assert reader.run_ids() == ["trace-test"]
    trial_ids = reader.trial_ids("trace-test")
    assert len(trial_ids) == 3
    for path in (tmp_path / "traces" / "trace-test").iterdir():
        assert path.name.endswith(".json.gz")
        with gzip.open(path, "rt") as handle:
            json.load(handle)
    loaded = reader.load_run("trace-test")
    assert {t.trial_id for t in loaded} == set(trial_ids)
    assert all(t.attempts for t in loaded)


def test_reader_joins_traces_to_trials_and_verifies_sha(env, tmp_path):
    store = ResultsStore(tmp_path / "results")
    config = _config(tmp_path)
    run_grid(
        env=env,
        backend=FakeBackend(lambda m, i: json.dumps(PAYLOAD), context_limit=100000),
        instances=env.load_instances("harness_val"),
        conditions=["C1"],
        seeds=[0],
        schema_variants=["field_present"],
        principle_set=env.principle_set(),
        config=config,
        store=store,
    )
    report = TraceReader(tmp_path / "traces").verify_against_trials(
        "trace-test", store.read_trials()
    )
    assert report["ok"] is True
    assert report["n_trials"] == report["n_traces"] == 3
    assert report["response_sha256_mismatch"] == []


def test_trace_store_is_append_only(env, instance, tmp_path):
    backend = FakeBackend([json.dumps(PAYLOAD)] * 2, context_limit=100000)
    config = _config(tmp_path)
    result = _run(env, backend, instance, config)
    ts = TraceStore(tmp_path / "traces", config.run_id)
    ts.write(result.trace)
    with pytest.raises(TraceExistsError):
        ts.write(result.trace)


def test_a_rerun_under_a_fresh_run_id_never_rewrites(env, instance, tmp_path):
    backend = FakeBackend([json.dumps(PAYLOAD)] * 4, context_limit=100000)
    first = _run(env, backend, instance, _config(tmp_path))
    TraceStore(tmp_path / "traces", "run-a").write(first.trace)
    second = _run(env, backend, instance, _config(tmp_path))
    TraceStore(tmp_path / "traces", "run-b").write(second.trace)
    reader = TraceReader(tmp_path / "traces")
    assert reader.run_ids() == ["run-a", "run-b"]
    assert reader.load("run-a", first.trial.trial_id).trial_id == first.trial.trial_id


def test_infeasible_and_api_error_trials_still_leave_a_trace(env, instance, tmp_path):
    infeasible = _run(env, FakeBackend([], context_limit=32), instance, _config(tmp_path))
    assert infeasible.trace.outcome == "infeasible_at_length"
    assert infeasible.trace.attempts == []
    assert infeasible.trace.backend["context_limit"] == 32

    failing = _run(
        env,
        FakeBackend([], context_limit=100000, raise_on_call=BackendError("boom")),
        instance,
        _config(tmp_path),
    )
    assert failing.trace.outcome == "api_error"
    assert failing.trace.attempts[0].error is not None
    assert failing.trace.attempts[0].prompt_sent


def test_trace_carries_enough_to_reanalyse_without_rerunning(env, instance, tmp_path):
    backend = ReasoningBackend([json.dumps(PAYLOAD)], context_limit=100000)
    config = _config(tmp_path)
    result = _run(env, backend, instance, config)
    trace = result.trace
    assert trace.max_output_tokens == config.max_output_tokens
    assert trace.temperature == config.temperature
    assert trace.principle_set_version == "fake-v1"
    assert trace.backend["model"] == backend.model_id
    assert trace.condition == "C3"
    assert trace.n_contract_tokens == instance.n_tokens


def test_attempt_trace_records_the_request_params_actually_sent(env, instance, tmp_path):
    class ParamEchoBackend(FakeBackend):
        def sample(self, messages, json_schema, temperature, seed, max_tokens):
            result = super().sample(messages, json_schema, temperature, seed, max_tokens)
            result.request_params = {
                "model": self.model_id,
                "temperature": temperature,
                "seed": seed,
                "separate_reasoning": True,
            }
            return result

    backend = ParamEchoBackend([json.dumps(PAYLOAD)], context_limit=100000)
    result = _run(env, backend, instance, _config(tmp_path))
    params = result.trace.attempts[0].request_params
    assert params["separate_reasoning"] is True
    assert params["seed"] == 0
    assert "response_format" not in params


def test_trial_row_and_trace_carry_the_backend_contract(env, instance, tmp_path):
    backend = FakeBackend([json.dumps(PAYLOAD)], context_limit=100000)
    result = _run(env, backend, instance, _config(tmp_path))
    assert result.trial.backend_params["structured_output"] == backend.structured_output
    assert result.trial.seed_honored is backend.seed_honored
    assert result.trace.backend["structured_output"] == backend.structured_output


def test_seed_is_documented_as_a_repetition_label_not_a_reproducibility_handle():
    from harness.runner import TrialKey

    doc = TrialKey.__doc__
    assert "REPETITION LABEL" in doc
    assert "not a reproducibility handle" in doc
    assert "trace store" in doc
