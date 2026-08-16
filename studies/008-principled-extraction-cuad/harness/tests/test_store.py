import json

import pytest

from harness.backends.fake_backend import FakeBackend
from harness.envs.fake_env import FakeEnvironment
from harness.runner import RunConfig, run_grid
from harness.store import DuplicateRowError, ResultsStore

PAYLOAD = {
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


def _base_trial(trial_id="t1"):
    return {
        "trial_id": trial_id,
        "contract_id": "X",
        "condition": "C1",
        "model": "m",
        "seed": 0,
        "schema_variant": "field_present",
        "run_id": "r",
        "prompt_template_version": "v1",
        "principle_set_version": "v1",
        "temperature": 0.7,
        "outcome": "ok",
        "n_contract_tokens": 100,
        "length_bucket": "0-4k",
        "split": "harness_val",
    }


def test_trial_id_uniqueness_is_enforced(tmp_path):
    store = ResultsStore(tmp_path)
    store.write_trial(_base_trial())
    with pytest.raises(DuplicateRowError):
        store.write_trial(_base_trial())


def test_trial_decision_pair_uniqueness_is_enforced(tmp_path):
    store = ResultsStore(tmp_path)
    row = {"trial_id": "t1", "decision_idx": 0, "decision_kind": "absence", "target": "A"}
    store.write_decision(row)
    with pytest.raises(DuplicateRowError):
        store.write_decision(dict(row))
    store.write_decision({**row, "decision_idx": 1})


def test_store_is_append_only_and_reloads_seen_keys(tmp_path):
    store = ResultsStore(tmp_path)
    store.write_trial(_base_trial())
    reopened = ResultsStore(tmp_path)
    assert reopened.has_trial("t1")
    with pytest.raises(DuplicateRowError):
        reopened.write_trial(_base_trial())
    reopened.write_trial(_base_trial("t2"))
    assert len(reopened.read_trials()) == 2


def test_rows_are_json_lines_matching_the_schema(tmp_path):
    store = ResultsStore(tmp_path)
    store.write_trial(_base_trial())
    lines = (tmp_path / "trials.jsonl").read_text().strip().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    for key in (
        "trial_id",
        "contract_id",
        "condition",
        "model",
        "seed",
        "schema_variant",
        "run_id",
        "prompt_template_version",
        "principle_set_version",
        "harness_git_sha",
        "temperature",
        "response_sha256",
        "n_prompt_tokens",
        "n_completion_tokens",
        "latency_ms",
        "outcome",
        "n_repair_attempts",
        "failure_detail",
        "n_contract_tokens",
        "length_bucket",
        "split",
        "answer",
        "compliance",
        "citation",
        "leakage",
    ):
        assert key in row


def test_run_grid_writes_both_files_and_skips_existing(tmp_path):
    env = FakeEnvironment()
    instances = env.load_instances("harness_val")
    backend = FakeBackend(lambda messages, idx: json.dumps(PAYLOAD), context_limit=100000)
    store = ResultsStore(tmp_path)
    config = RunConfig(run_id="grid-test", max_output_tokens=256, principle_set_version="fake-v1")

    first = run_grid(
        env=env,
        backend=backend,
        instances=instances,
        conditions=["C1", "C3"],
        seeds=[0, 1],
        schema_variants=["field_present"],
        principle_set=env.principle_set(),
        config=config,
        store=store,
    )
    assert len(first) == len(instances) * 2 * 2
    assert len(store.read_trials()) == len(first)
    assert len(store.read_decisions()) == len(first) * 4

    second = run_grid(
        env=env,
        backend=backend,
        instances=instances,
        conditions=["C1", "C3"],
        seeds=[0, 1],
        schema_variants=["field_present"],
        principle_set=env.principle_set(),
        config=config,
        store=store,
    )
    assert second == []


def test_non_ok_trials_still_write_rows_through_the_grid(tmp_path):
    env = FakeEnvironment()
    instances = env.load_instances("harness_val")
    backend = FakeBackend(lambda messages, idx: "not json", context_limit=100000)
    store = ResultsStore(tmp_path)
    config = RunConfig(run_id="fail-test", max_output_tokens=256, max_repair_attempts=1)
    run_grid(
        env=env,
        backend=backend,
        instances=instances,
        conditions=["C1"],
        seeds=[0],
        schema_variants=["field_present"],
        principle_set=env.principle_set(),
        config=config,
        store=store,
    )
    trials = store.read_trials()
    decisions = store.read_decisions()
    assert all(t["outcome"] == "parse_failure" for t in trials)
    assert all(t["answer"] is None for t in trials)
    assert len(decisions) == len(trials) * 4
    assert all(d["answer_score"] is None for d in decisions)


def test_exactly_one_decision_row_per_target_for_every_trial_outcome(tmp_path):
    env = FakeEnvironment()
    targets = env.task_definition().targets
    instances = env.load_instances("harness_val")

    scripts = {
        "ok": lambda messages, idx: json.dumps(PAYLOAD),
        "parse_failure": lambda messages, idx: "not json",
        "coverage": lambda messages, idx: json.dumps(
            {"extractions": [], "absent": [{"category": targets[0], "principles_cited": []}]}
        ),
    }
    for name, script in scripts.items():
        store = ResultsStore(tmp_path / name)
        run_grid(
            env=env,
            backend=FakeBackend(script, context_limit=100000),
            instances=instances,
            conditions=["C3"],
            seeds=[0],
            schema_variants=["field_present"],
            principle_set=env.principle_set(),
            config=RunConfig(run_id=name, max_output_tokens=256, max_repair_attempts=1),
            store=store,
        )
        trials = store.read_trials()
        decisions = store.read_decisions()
        assert len(decisions) == len(trials) * len(targets), name
        for trial in trials:
            rows = [d for d in decisions if d["trial_id"] == trial["trial_id"]]
            assert [d["target"] for d in rows] == targets, name
            assert len({d["decision_idx"] for d in rows}) == len(targets), name


def test_infeasible_trials_also_write_one_row_per_target(tmp_path):
    env = FakeEnvironment()
    targets = env.task_definition().targets
    store = ResultsStore(tmp_path)
    run_grid(
        env=env,
        backend=FakeBackend(lambda messages, idx: json.dumps(PAYLOAD), context_limit=32),
        instances=env.load_instances("harness_val"),
        conditions=["C1"],
        seeds=[0],
        schema_variants=["field_present"],
        principle_set=env.principle_set(),
        config=RunConfig(run_id="infeasible", max_output_tokens=16),
        store=store,
    )
    trials = store.read_trials()
    assert trials and all(t["outcome"] == "infeasible_at_length" for t in trials)
    assert len(store.read_decisions()) == len(trials) * len(targets)
