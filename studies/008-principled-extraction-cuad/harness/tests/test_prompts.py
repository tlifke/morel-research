import json

import pytest

from harness.envs.fake_env import FakeEnvironment
from harness.models import TaskOutput
from harness.output_schema import (
    json_schema_for,
    schema_category_enum,
    schema_has_citation_field,
)
from harness.prompts import (
    NO_CITATION_BLOCK,
    build_prompt,
    render_citation_block,
)


@pytest.fixture
def env():
    return FakeEnvironment()


@pytest.fixture
def instance(env):
    return env.load_instances("harness_val")[0]


def _prompt(env, instance, condition, variant="field_present"):
    return build_prompt(
        task=env.task_definition(),
        principle_set=env.principle_set(),
        condition=condition,
        schema_variant=variant,
        instance=instance,
        output_model=env.output_model(),
    )


def test_task_definition_present_in_all_conditions(env, instance):
    for condition in ("C1", "C2", "C3"):
        bundle = _prompt(env, instance, condition)
        assert "task_definition" in bundle.blocks
        assert "Governing Law" in bundle.blocks["task_definition"]


def test_task_definition_block_is_byte_identical_across_conditions(env, instance):
    blocks = {c: _prompt(env, instance, c).blocks["task_definition"] for c in ("C1", "C2", "C3")}
    assert blocks["C1"] == blocks["C2"] == blocks["C3"]


def test_principles_only_in_c2_and_c3(env, instance):
    assert "principles" not in _prompt(env, instance, "C1").blocks
    c2 = _prompt(env, instance, "C2").blocks["principles"]
    c3 = _prompt(env, instance, "C3").blocks["principles"]
    assert c2 == c3
    assert "[p03]" in c2


def test_citation_requirement_only_in_c3(env, instance):
    assert _prompt(env, instance, "C1").blocks["citation"] == NO_CITATION_BLOCK
    assert _prompt(env, instance, "C2").blocks["citation"] == NO_CITATION_BLOCK
    assert _prompt(env, instance, "C3").blocks["citation"] == render_citation_block(
        env.principle_set()
    )


def test_conditions_differ_only_by_documented_switches(env, instance):
    bundles = {c: _prompt(env, instance, c) for c in ("C1", "C2", "C3")}
    switched = {"principles", "citation"}
    shared_keys = {"task_definition", "output_format", "instance"}
    for key in shared_keys:
        values = {bundles[c].blocks[key] for c in bundles}
        assert len(values) == 1, key
    for c in bundles:
        assert set(bundles[c].blocks) - switched <= shared_keys


def test_field_absent_variant_removes_citation_field_only_from_schema(env, instance):
    present = _prompt(env, instance, "C1", "field_present")
    absent = _prompt(env, instance, "C1", "field_absent")
    assert schema_has_citation_field(present.json_schema)
    assert not schema_has_citation_field(absent.json_schema)
    assert present.blocks["task_definition"] == absent.blocks["task_definition"]
    assert present.blocks["instance"] == absent.blocks["instance"]


def test_field_absent_variant_drops_the_instructed_empty_sentence(env, instance):
    absent = _prompt(env, instance, "C1", "field_absent")
    assert "citation" not in absent.blocks
    assert "principles_cited" not in absent.user


def test_schema_strip_removes_required_entry_too():
    schema = json_schema_for(TaskOutput, "field_absent")
    for definition in schema.get("$defs", {}).values():
        assert "principles_cited" not in definition.get("properties", {})
        assert "principles_cited" not in definition.get("required", [])


def test_principle_set_is_data_not_hardcoded(env, instance):
    subset = env.principle_set().subset(["p03"], version="held-out-v1")
    bundle = build_prompt(
        task=env.task_definition(),
        principle_set=subset,
        condition="C2",
        schema_variant="field_present",
        instance=instance,
        output_model=env.output_model(),
    )
    assert "[p03]" in bundle.blocks["principles"]
    assert "[p01]" not in bundle.blocks["principles"]


def test_c2_without_principles_raises(env, instance):
    with pytest.raises(ValueError):
        build_prompt(
            task=env.task_definition(),
            principle_set=None,
            condition="C2",
            schema_variant="field_present",
            instance=instance,
            output_model=env.output_model(),
        )


def test_output_block_contains_valid_json_schema(env, instance):
    bundle = _prompt(env, instance, "C1")
    payload = bundle.blocks["output_format"].split("\n", 2)[2]
    assert json.loads(payload) == bundle.json_schema


def test_citation_exemplar_is_derived_from_the_loaded_set(env, instance):
    subset = env.principle_set().subset(["p03"], version="held-out-v1")
    bundle = build_prompt(
        task=env.task_definition(),
        principle_set=subset,
        condition="C3",
        schema_variant="field_present",
        instance=instance,
        output_model=env.output_model(),
    )
    assert 'for example "p03"' in bundle.blocks["citation"]
    assert 'for example "p01"' not in bundle.blocks["citation"]


def test_citation_exemplar_names_a_principle_that_is_in_the_prompt(env, instance):
    bundle = _prompt(env, instance, "C3")
    exemplar = bundle.blocks["citation"].split('for example "')[1].split('"')[0]
    assert f"[{exemplar}]" in bundle.blocks["principles"]


def test_document_block_has_a_title_but_no_id_line(env, instance):
    block = _prompt(env, instance, "C1").blocks["instance"]
    assert f"Title: {instance.title}" in block
    assert "\nId:" not in block


def test_attribution_is_not_in_the_instruction_stream(env, instance):
    bundle = _prompt(env, instance, "C1")
    attribution = env.task_definition().attribution
    assert attribution
    assert attribution not in bundle.user
    assert attribution not in bundle.system


def test_category_enum_is_stated_in_the_schema(env, instance):
    bundle = _prompt(env, instance, "C1")
    enums = schema_category_enum(bundle.json_schema)
    assert enums
    for values in enums:
        assert values == env.task_definition().targets
    assert "Governing Law" in bundle.blocks["output_format"]


def test_category_enum_is_omitted_when_no_categories_are_given():
    schema = json_schema_for(TaskOutput, "field_present")
    assert schema_category_enum(schema) == []
