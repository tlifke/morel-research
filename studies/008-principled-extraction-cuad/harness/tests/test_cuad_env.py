import json

import pytest

from harness.env import ComplianceChecker, Environment
from harness.envs.cuad_env import (
    INSTANCE_SCOPE_KEY,
    ApplicabilitySource,
    CuadEnvironment,
    load_category_definitions,
    load_category_subset,
)
from harness.models import (
    AbsenceClaim,
    Extraction,
    Principle,
    PrincipleSet,
    TaskOutput,
)
from harness.principles_io import load_principle_set
from harness.tests.test_env_interface import REQUIRED

SMOKE_SPLIT = "scratch"


def _principles() -> PrincipleSet:
    return PrincipleSet(
        version="test-v1",
        principles=[
            Principle(
                id="p01",
                statement="Quote spans verbatim.",
                trigger_guidance="Always.",
                type="constraint",
                scope=[],
                provenance="authored",
            ),
            Principle(
                id="p02",
                statement="Claim absence explicitly.",
                trigger_guidance="When nothing matches.",
                type="absence",
                scope=[],
                provenance="authored",
            ),
        ],
    )


@pytest.fixture(scope="module")
def env() -> CuadEnvironment:
    return CuadEnvironment(principle_set=_principles())


@pytest.fixture(scope="module")
def instances(env):
    return env.load_instances(SMOKE_SPLIT)


def _full_output(env, extracted: dict[str, list[str]], cited=None) -> TaskOutput:
    cited = cited or {}
    return TaskOutput(
        extractions=[
            Extraction(category=c, spans=s, principles_cited=cited.get(c, []))
            for c, s in extracted.items()
        ],
        absent=[
            AbsenceClaim(category=t, principles_cited=cited.get(t, []))
            for t in env.targets
            if t not in extracted
        ],
    )


def test_implements_every_abstract_method(env):
    assert isinstance(env, Environment)
    for name in REQUIRED:
        assert callable(getattr(env, name))


def test_targets_come_from_the_config_not_the_code(env):
    assert env.targets == load_category_subset()
    assert len(env.targets) == 12


def test_task_definition_has_a_one_line_definition_per_target(env):
    task = env.task_definition()
    assert task.targets == env.targets
    assert set(task.target_definitions) == set(env.targets)
    assert all(task.target_definitions[t].strip() for t in env.targets)
    assert "Atticus" in (task.attribution or "")


def test_category_definitions_cover_the_subset(env):
    definitions = load_category_definitions()
    for target in env.targets:
        assert target.lower() in definitions


def test_sealed_split_is_refused_by_default(env):
    with pytest.raises(PermissionError):
        env.load_instances("test")


def test_sealed_split_requires_an_explicit_override_and_logs(caplog):
    env = CuadEnvironment(principle_set=_principles(), allow_test=True)
    with caplog.at_level("WARNING"):
        loaded = env.load_instances("test")
    assert loaded
    assert any("SEALED SPLIT LOADED" in r.getMessage() for r in caplog.records)


def test_instances_carry_the_loader_contract(instances):
    assert len(instances) == 4
    for instance in instances:
        assert instance.contract_id and instance.title and instance.text
        assert instance.n_tokens > 0
        assert instance.split == SMOKE_SPLIT
        assert len(instance.gold.targets) == 12


def test_gold_spans_are_verbatim_slices_of_the_contract(instances):
    for instance in instances:
        for target in instance.gold.targets.values():
            for span in target.spans:
                assert instance.text[span.start : span.end] == span.text


def test_exactly_twelve_decisions_per_contract(env, instances):
    for instance in instances:
        records = env.unrealized_decisions(instance)
        assert len(records) == 12
        assert [r.idx for r in records] == list(range(12))
        assert [r.target for r in records] == env.targets


def test_decision_idx_is_stable_under_output_ordering(env, instances):
    forward = TaskOutput(absent=[AbsenceClaim(category=t) for t in env.targets])
    reversed_ = TaskOutput(
        absent=[AbsenceClaim(category=t) for t in reversed(env.targets)]
    )
    assert [(r.idx, r.target) for r in env.iter_decisions(forward)] == [
        (r.idx, r.target) for r in env.iter_decisions(reversed_)
    ]


def test_validate_output_accepts_exactly_once_coverage(env, instances):
    output = _full_output(env, {})
    assert env.validate_output(instances[0], output) == []


def test_validate_output_rejects_missing_target(env, instances):
    output = TaskOutput(
        absent=[AbsenceClaim(category=t) for t in env.targets[:-1]]
    )
    violations = env.validate_output(instances[0], output)
    assert any("no decision" in v for v in violations)


def test_validate_output_rejects_a_target_decided_twice(env, instances):
    output = _full_output(env, {env.targets[0]: ["x"]})
    output.absent.append(AbsenceClaim(category=env.targets[0]))
    violations = env.validate_output(instances[0], output)
    assert any("more than once" in v for v in violations)


def test_validate_output_rejects_unknown_targets(env, instances):
    output = _full_output(env, {})
    output.absent.append(AbsenceClaim(category="Not A Category"))
    violations = env.validate_output(instances[0], output)
    assert any("unknown target" in v for v in violations)


def test_score_answer_is_level_a_only(env, instances):
    instance = instances[0]
    present = [t for t, g in instance.gold.targets.items() if not g.is_impossible]
    gold_spans = {t: [s.text for s in instance.gold.targets[t].spans] for t in present}
    score = env.score_answer(instance, _full_output(env, gold_spans))
    assert score.level_b == {}
    assert set(score.level_a["per_category_cells"]) == set(env.targets)
    assert all(
        score.level_a["per_category_cells"][t] == "TP" for t in present
    )
    assert score.level_a["micro"]["counts"]["FP"] == 0
    assert score.level_a["micro"]["counts"]["FN"] == 0
    for entry in score.per_category.values():
        assert "span_f1" not in entry


def test_score_decision_reports_the_cell_and_span_f1_on_tp(env, instances):
    instance = next(i for i in instances if i.gold.positive_targets())
    target = instance.gold.positive_targets()[0]
    spans = [s.text for s in instance.gold.targets[target].spans]
    records = env.iter_decisions(_full_output(env, {target: spans}))
    record = next(r for r in records if r.target == target)
    score = env.score_decision(instance, record)
    assert score["cell"] == "TP"
    assert score["span_f1"] == pytest.approx(1.0)
    assert score["verbatim_fidelity"]["exact_rate"] == pytest.approx(1.0)


def test_score_decision_on_a_false_present_keeps_verbatim_but_not_f1(env, instances):
    instance = instances[0]
    absent_target = next(
        t for t, g in instance.gold.targets.items() if g.is_impossible
    )
    records = env.iter_decisions(
        _full_output(env, {absent_target: ["a span that is not in the contract"]})
    )
    record = next(r for r in records if r.target == absent_target)
    score = env.score_decision(instance, record)
    assert score["cell"] == "FP"
    assert score["span_f1"] is None
    assert score["verbatim_fidelity"]["n_not_found"] == 1


def test_applicability_is_unavailable_without_a_source(env, instances):
    assert env.applicability_available is False
    records = env.unrealized_decisions(instances[0])
    assert all(env.gold_applicable_for_decision(instances[0], r) == [] for r in records)
    assert env.applicable_principles(instances[0]) == []
    with pytest.raises(RuntimeError):
        env.assert_ready(["C1", "C3"])
    env.assert_ready(["C1", "C2"])


def test_applicability_is_read_from_the_injected_source(tmp_path, instances):
    contract_id = instances[0].contract_id
    payload = {
        "version": "app-test",
        "principle_set_version": "test-v1",
        "labeler": {"kind": "programmatic"},
        "instances": {
            contract_id: {
                INSTANCE_SCOPE_KEY: ["p02"],
                "Governing Law": ["p01"],
            }
        },
    }
    path = tmp_path / "applicability.json"
    path.write_text(json.dumps(payload))
    env = CuadEnvironment(
        principle_set=_principles(), applicability=ApplicabilitySource.load(path)
    )
    env.assert_ready(["C1", "C2", "C3"])
    instance = next(
        i for i in env.load_instances(SMOKE_SPLIT) if i.contract_id == contract_id
    )
    records = env.unrealized_decisions(instance)
    gov = next(r for r in records if r.target == "Governing Law")
    other = next(r for r in records if r.target == "Cap On Liability")
    assert env.gold_applicable_for_decision(instance, gov) == ["p01"]
    assert env.gold_applicable_for_decision(instance, other) == []
    assert sorted(env.applicable_principles(instance)) == ["p01", "p02"]


def test_applicability_source_rejects_targets_outside_the_subset(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(
        json.dumps(
            {
                "version": "v",
                "instances": {"anything": {"Parties": ["p01"]}},
            }
        )
    )
    with pytest.raises(ValueError):
        CuadEnvironment(
            principle_set=_principles(),
            applicability=ApplicabilitySource.load(path),
        )


def test_compliance_checkers_are_injected_not_hardcoded(env):
    assert env.compliance_checkers() == {}
    assert env.compliance_available is False
    checker = ComplianceChecker("p01", "decision", lambda ctx: True)
    injected = CuadEnvironment(
        principle_set=_principles(), compliance_checkers={"p01": checker}
    )
    assert injected.compliance_checkers() == {"p01": checker}
    assert injected.compliance_available is True


def test_principle_set_is_data(env):
    assert env.principle_set().version == "test-v1"
    other = PrincipleSet(version="other", principles=[])
    swapped = CuadEnvironment(principle_set=other)
    assert swapped.principle_set().version == "other"
    assert swapped.principle_set().ids == []


def test_principle_set_loader_reads_yaml_and_subsets():
    path = (
        __import__("pathlib").Path(__file__).resolve().parents[2]
        / "principles"
        / "pilot"
        / "candidates_round2.yaml"
    )
    full = load_principle_set(path, version="round2")
    assert len(full.principles) == 23
    subset = load_principle_set(path, version="round2-sub", ids=["p03", "p01"])
    assert subset.ids == ["p03", "p01"]
    with pytest.raises(KeyError):
        load_principle_set(path, ids=["nope"])


def test_principle_set_loader_accepts_the_mapping_form(tmp_path):
    import yaml

    path = tmp_path / "set.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "title": "wrapped",
                "principles": [
                    {
                        "id": "w01",
                        "statement": "s",
                        "trigger_guidance": "t",
                        "type": "constraint",
                        "scope": [],
                        "provenance": "authored",
                    }
                ],
            }
        )
    )
    assert load_principle_set(path, version="wrapped").ids == ["w01"]
