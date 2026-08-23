from __future__ import annotations

import json
import sys
from pathlib import Path

INV = Path(__file__).resolve().parents[1]
STUDY = INV.parents[1]
sys.path.insert(0, str(STUDY))
sys.path.insert(0, str(INV))

from harness.models import Principle, PrincipleSet

from loop.ledger import TrialKey
from loop.models import LoopDecision, LoopOutput
from loop.prompt import TaskDefinition, build, render_principles


def test_predicted_present_requires_both_kind_and_spans():
    assert LoopDecision(category="X", kind="extraction", spans=["a"]).predicted_present
    assert not LoopDecision(category="X", kind="extraction").predicted_present
    assert not LoopDecision(category="X", kind="absence", spans=["a"]).predicted_present


def test_inconsistency_is_counted_not_rejected():
    out = LoopOutput(
        decisions=[
            LoopDecision(category="A", kind="extraction"),
            LoopDecision(category="B", kind="absence", spans=["x"]),
            LoopDecision(category="A", kind="absence"),
        ]
    )
    c = out.conformance(["A", "B", "C"])
    assert c["n_kind_span_inconsistent"] == 2
    assert c["n_duplicate"] == 1
    assert c["missing"] == ["C"]


def test_prompt_uses_frozen_instruction_verbatim():
    task = TaskDefinition.load()
    p = build(task, "CONTRACT", None)
    assert p.system == task.instruction_text
    assert "CONTRACT" in p.user
    for question in task.questions.values():
        assert question in p.user


def test_arms_differ_only_in_the_principles_block():
    task = TaskDefinition.load()
    ps = PrincipleSet(
        version="t1",
        principles=[
            Principle(
                id="w99",
                statement="S.",
                trigger_guidance="T.",
                type="constraint",
                provenance=["authored"],
            )
        ],
    )
    without = build(task, "CONTRACT", None).user
    with_ = build(task, "CONTRACT", ps).user
    assert without.replace(render_principles(None), render_principles(ps)) == with_


def test_trial_id_is_stable_and_key_sensitive():
    base = dict(
        task_definition_version="v1",
        task_definition_sha256="abc",
        principle_set_version="empty",
        arm="baseline",
        model="m",
        contract_id="c",
        repeat_idx=0,
    )
    assert TrialKey(**base).trial_id == TrialKey(**base).trial_id
    assert TrialKey(**{**base, "repeat_idx": 1}).trial_id != TrialKey(**base).trial_id
    assert TrialKey(**{**base, "arm": "candidate"}).trial_id != TrialKey(**base).trial_id


def test_slice_contracts_are_all_principle_train():
    members = {
        s.strip()
        for s in (STUDY / "data/processed/splits/principle_train.txt").read_text().splitlines()
        if s.strip()
    }
    sl = json.loads((INV / "mvp_slice.json").read_text())
    assert len(sl["contracts"]) == 5
    for c in sl["contracts"]:
        assert c["contract_id"] in members


def _write_run(tmp_path, run_id, failures, f2_by_contract):
    import loop.ledger as L

    d = tmp_path / run_id
    d.mkdir(parents=True)
    (d / "failures.jsonl").write_text(
        "".join(json.dumps(f) + "\n" for f in failures)
    )
    (d / "score.json").write_text(
        json.dumps(
            {
                "per_trial": [
                    {"outcome": "ok", "contract_id": c, "repeat_idx": i, "detection_micro": {"f2": v}}
                    for c, vals in f2_by_contract.items()
                    for i, v in enumerate(vals)
                ]
            }
        )
    )
    L.RUNS = tmp_path
    return run_id


def test_ladder_requires_majority_fix_and_bounded_collateral(tmp_path, monkeypatch):
    import loop.ladder as ladder
    import loop.ledger as L

    monkeypatch.setattr(L, "RUNS", tmp_path)
    monkeypatch.setattr(L.Ledger, "__init__", lambda self, run_id, root=tmp_path: (
        setattr(self, "run_id", run_id),
        setattr(self, "dir", tmp_path / run_id),
        setattr(self, "path", tmp_path / run_id / "trials.jsonl"),
        None,
    )[-1])

    target = {"contract_id": "A", "category": "Agreement Date", "failure_class": "false_absent"}
    _write_run(tmp_path, "ctl", [target, target, target], {"A": [0.80, 0.80, 0.80]})
    _write_run(tmp_path, "cand", [], {"A": [0.85, 0.85, 0.85]})

    res = ladder.evaluate(1, "ctl", "cand", [ladder.Cell("A", "Agreement Date")])
    assert res.passed
    assert res.targets_fixed and not res.targets_still_failing

    other = {"contract_id": "A", "category": "Insurance", "failure_class": "false_present"}
    _write_run(tmp_path, "cand2", [other, other, other, other, other, other], {"A": [0.85, 0.85, 0.85]})
    res2 = ladder.evaluate(1, "ctl", "cand2", [ladder.Cell("A", "Agreement Date")])
    assert not res2.passed
    assert any("collateral" in r for r in res2.reasons)


def test_ladder_rung2_fails_on_f2_decrease(tmp_path, monkeypatch):
    import loop.ladder as ladder
    import loop.ledger as L

    monkeypatch.setattr(L.Ledger, "__init__", lambda self, run_id, root=tmp_path: (
        setattr(self, "run_id", run_id),
        setattr(self, "dir", tmp_path / run_id),
        setattr(self, "path", tmp_path / run_id / "trials.jsonl"),
        None,
    )[-1])

    target = {"contract_id": "A", "category": "Agreement Date", "failure_class": "false_absent"}
    _write_run(tmp_path, "ctl2", [target, target, target], {"A": [0.90, 0.90, 0.90]})
    _write_run(tmp_path, "cand3", [], {"A": [0.70, 0.70, 0.70]})

    res = ladder.evaluate(2, "ctl2", "cand3", [ladder.Cell("A", "Agreement Date")])
    assert not res.passed
    assert any("F2 fell" in r for r in res.reasons)
