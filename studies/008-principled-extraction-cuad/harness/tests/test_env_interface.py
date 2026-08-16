import inspect

from harness.env import Environment
from harness.envs.fake_env import FakeEnvironment
from harness.models import AbsenceClaim, TaskOutput

REQUIRED = {
    "load_instances",
    "task_definition",
    "principle_set",
    "applicable_principles",
    "gold_applicable_for_decision",
    "gold_for_decision",
    "score_answer",
    "score_decision",
    "compliance_checkers",
    "output_model",
    "validate_output",
    "iter_decisions",
    "unrealized_decisions",
}


def test_the_env_interface_surface_is_exactly_the_documented_set():
    abstract = {
        name
        for name, member in inspect.getmembers(Environment, inspect.isfunction)
        if getattr(member, "__isabstractmethod__", False)
    }
    assert abstract == REQUIRED


def test_fake_env_implements_every_abstract_method():
    env = FakeEnvironment()
    for name in REQUIRED:
        assert callable(getattr(env, name))


def test_instances_carry_the_loader_contract():
    env = FakeEnvironment()
    for instance in env.load_instances("harness_val"):
        assert instance.contract_id and instance.title and instance.text
        assert instance.n_tokens > 0
        assert instance.split == "harness_val"
        assert instance.gold.targets


def test_splits_are_disjoint_by_contract_id():
    env = FakeEnvironment()
    harness_val = {i.contract_id for i in env.load_instances("harness_val")}
    test = {i.contract_id for i in env.load_instances("test")}
    assert harness_val and test
    assert not (harness_val & test)


def test_decision_iterator_indices_are_dense_and_ordered():
    env = FakeEnvironment()
    instance = env.load_instances("harness_val")[0]
    records = env.unrealized_decisions(instance)
    assert [r.idx for r in records] == list(range(len(records)))


def test_decision_count_is_fixed_by_the_task_definition_not_the_output():
    env = FakeEnvironment()
    targets = env.task_definition().targets
    for instance in env.load_instances("harness_val"):
        assert len(env.unrealized_decisions(instance)) == len(targets)
        assert [r.target for r in env.unrealized_decisions(instance)] == targets


def test_decision_idx_is_the_target_position_so_it_is_stable_across_trials():
    env = FakeEnvironment()
    targets = env.task_definition().targets
    all_absent = TaskOutput(absent=[AbsenceClaim(category=t) for t in targets])
    shuffled = TaskOutput(
        absent=[AbsenceClaim(category=t) for t in reversed(targets)]
    )
    assert [(r.idx, r.target) for r in env.iter_decisions(all_absent)] == [
        (r.idx, r.target) for r in env.iter_decisions(shuffled)
    ]
    assert [r.target for r in env.iter_decisions(shuffled)] == targets


def test_compliance_checkers_declare_scope_and_match_principle_ids():
    env = FakeEnvironment()
    checkers = env.compliance_checkers()
    assert set(checkers) <= set(env.principle_set().ids)
    for pid, checker in checkers.items():
        assert checker.principle_id == pid
        assert checker.scope in ("instance", "decision")


def test_no_principle_enters_the_scored_set_without_a_checker():
    env = FakeEnvironment()
    checkers = env.compliance_checkers()
    for pid in env.principle_set().ids:
        assert pid in checkers


def test_principle_scope_matches_declared_applicability():
    env = FakeEnvironment()
    principles = env.principle_set()
    instance = env.load_instances("harness_val")[0]
    for target, pids in instance.gold.applicability.items():
        if target.startswith("__"):
            continue
        allowed = {p.id for p in principles.in_scope_for(target)}
        assert set(pids) <= allowed
