from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional

from pydantic import BaseModel

from . import metrics
from .backends.base import Backend, BackendError
from .env import ComplianceContext, Environment
from .models import DecisionRecord, Instance, PrincipleSet
from .output_schema import SchemaVariant
from .parsing import ParseFailure, parse_output
from .prompts import CONDITIONS, PROMPT_TEMPLATE_VERSION, build_prompt, PromptBundle
from .store import DecisionRow, ResultsStore, TrialRow

REPAIR_INSTRUCTION = (
    "Your previous reply could not be parsed as the required JSON object.\n"
    "Error: {error}\n"
    "Reply again with one JSON object and nothing else, validating against the "
    "schema you were given."
)

COVERAGE_REPAIR_INSTRUCTION = (
    "Your previous reply was valid JSON but did not cover the targets correctly.\n"
    "Problem: {error}\n"
    "Reply again with one JSON object and nothing else. Every target must appear "
    "exactly once, either in `extractions` or in `absent`, never in both and "
    "never omitted."
)


def new_run_id(tag: str = "run") -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") + "-" + tag


def harness_git_sha() -> Optional[str]:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=Path(__file__).resolve().parent,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:
        return None


@dataclass(frozen=True)
class TrialKey:
    contract_id: str
    condition: str
    model: str
    seed: int
    schema_variant: str

    def trial_id(self) -> str:
        payload = json.dumps(
            {
                "contract_id": self.contract_id,
                "condition": self.condition,
                "model": self.model,
                "seed": self.seed,
                "schema_variant": self.schema_variant,
            },
            sort_keys=True,
        )
        return hashlib.sha1(payload.encode()).hexdigest()


@dataclass
class RunConfig:
    run_id: str
    temperature: float = 0.7
    max_output_tokens: int = 4096
    max_repair_attempts: int = 2
    principle_set_version: str = "unset"
    prompt_template_version: str = PROMPT_TEMPLATE_VERSION
    harness_git_sha: Optional[str] = field(default_factory=harness_git_sha)
    raw_response_dir: Optional[Path] = None


@dataclass
class TrialResult:
    trial: TrialRow
    decisions: list[DecisionRow]


def _persist_raw(config: RunConfig, text: str) -> str:
    digest = hashlib.sha256(text.encode()).hexdigest()
    if config.raw_response_dir is not None:
        path = Path(config.raw_response_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / f"{digest}.txt").write_text(text, encoding="utf-8")
    return digest


def _sample_with_repair(
    backend: Backend,
    prompt: PromptBundle,
    output_model: type[BaseModel],
    seed: int,
    config: RunConfig,
    validate: Callable[[BaseModel], list[str]],
) -> tuple[Optional[BaseModel], Any, int, Optional[dict[str, Any]]]:
    messages = prompt.as_messages()
    attempts = 0
    last_result = None
    while True:
        result = backend.sample(
            messages=messages,
            json_schema=prompt.json_schema,
            temperature=config.temperature,
            seed=seed + attempts,
            max_tokens=config.max_output_tokens,
        )
        last_result = result
        try:
            parsed = parse_output(result.text, output_model)
            violations = validate(parsed)
            if violations:
                raise ParseFailure("coverage", "; ".join(violations))
            return parsed, result, attempts, None
        except ParseFailure as exc:
            if attempts >= config.max_repair_attempts:
                return (
                    None,
                    last_result,
                    attempts,
                    {"stage": exc.stage, "detail": exc.detail[:2000]},
                )
            template = (
                COVERAGE_REPAIR_INSTRUCTION
                if exc.stage == "coverage"
                else REPAIR_INSTRUCTION
            )
            messages = messages + [
                {"role": "assistant", "content": result.text},
                {
                    "role": "user",
                    "content": template.format(error=f"{exc.stage}: {exc.detail}"),
                },
            ]
            attempts += 1


def run_trial(
    env: Environment,
    backend: Backend,
    instance: Instance,
    condition: str,
    seed: int,
    schema_variant: SchemaVariant,
    principle_set: PrincipleSet,
    config: RunConfig,
) -> TrialResult:
    if condition not in CONDITIONS:
        raise ValueError(f"unknown condition {condition!r}")

    key = TrialKey(
        contract_id=instance.contract_id,
        condition=condition,
        model=backend.model_id,
        seed=seed,
        schema_variant=schema_variant,
    )
    trial_id = key.trial_id()
    output_model = env.output_model()
    spec = CONDITIONS[condition]

    prompt = build_prompt(
        task=env.task_definition(),
        principle_set=principle_set if spec.principles else None,
        condition=condition,
        schema_variant=schema_variant,
        instance=instance,
        output_model=output_model,
    )

    base_row: dict[str, Any] = {
        "trial_id": trial_id,
        "contract_id": instance.contract_id,
        "condition": condition,
        "model": backend.model_id,
        "seed": seed,
        "schema_variant": schema_variant,
        "run_id": config.run_id,
        "prompt_template_version": prompt.template_version,
        "principle_set_version": config.principle_set_version,
        "harness_git_sha": config.harness_git_sha,
        "temperature": config.temperature,
        "n_contract_tokens": instance.n_tokens,
        "length_bucket": metrics.length_bucket(instance.n_tokens),
        "split": instance.split,
        "leakage": {},
    }

    prompt_tokens_est = backend.count_tokens(prompt.full_text())
    budget = prompt_tokens_est + config.max_output_tokens
    if budget > backend.context_limit:
        row = TrialRow(
            **base_row,
            outcome="infeasible_at_length",
            n_repair_attempts=0,
            n_prompt_tokens=prompt_tokens_est,
            failure_detail={
                "prompt_tokens_estimate": prompt_tokens_est,
                "max_output_tokens": config.max_output_tokens,
                "context_limit": backend.context_limit,
                "token_count_method": backend.token_count_method,
            },
        )
        return TrialResult(trial=row, decisions=_unrealized_rows(env, instance, trial_id))

    try:
        parsed, result, n_repairs, failure = _sample_with_repair(
            backend,
            prompt,
            output_model,
            seed,
            config,
            validate=lambda out: env.validate_output(instance, out),
        )
    except BackendError as exc:
        row = TrialRow(
            **base_row,
            outcome="api_error",
            n_repair_attempts=0,
            n_prompt_tokens=prompt_tokens_est,
            failure_detail={"error": str(exc)[:2000]},
        )
        return TrialResult(trial=row, decisions=_unrealized_rows(env, instance, trial_id))

    response_sha = _persist_raw(config, result.text) if result is not None else None
    call_fields = {
        "response_sha256": response_sha,
        "n_prompt_tokens": (result.n_prompt_tokens if result else None) or prompt_tokens_est,
        "n_completion_tokens": result.n_completion_tokens if result else None,
        "latency_ms": result.latency_ms if result else None,
    }

    if parsed is None:
        finish_reason = result.finish_reason if result else None
        detail = dict(failure or {})
        detail["finish_reason"] = finish_reason
        detail["completion_truncated"] = finish_reason == "length"
        detail["n_reasoning_chars"] = (result.raw or {}).get("n_reasoning_chars") if result else None
        row = TrialRow(
            **base_row,
            **call_fields,
            outcome="parse_failure",
            n_repair_attempts=n_repairs,
            failure_detail=detail,
        )
        return TrialResult(trial=row, decisions=_unrealized_rows(env, instance, trial_id))

    return _score_trial(
        env=env,
        instance=instance,
        parsed=parsed,
        condition=condition,
        principle_set=principle_set,
        trial_id=trial_id,
        base_row=base_row,
        call_fields=call_fields,
        n_repairs=n_repairs,
    )


def _unrealized_rows(
    env: Environment, instance: Instance, trial_id: str
) -> list[DecisionRow]:
    rows = []
    for record in env.unrealized_decisions(instance):
        rows.append(
            DecisionRow(
                trial_id=trial_id,
                decision_idx=record.idx,
                decision_kind=record.kind,
                target=record.target,
                predicted=None,
                gold=env.gold_for_decision(instance, record),
                answer_score=None,
                principles_cited=[],
                gold_applicable=env.gold_applicable_for_decision(instance, record),
                citation_eval=None,
                compliance_eval=None,
            )
        )
    return rows


def _score_trial(
    env: Environment,
    instance: Instance,
    parsed: BaseModel,
    condition: str,
    principle_set: PrincipleSet,
    trial_id: str,
    base_row: dict[str, Any],
    call_fields: dict[str, Any],
    n_repairs: int,
) -> TrialResult:
    active_ids = set(principle_set.ids)
    checkers = env.compliance_checkers()
    decisions = env.iter_decisions(parsed)

    decision_rows: list[DecisionRow] = []
    citation_evals: list[dict[str, Any]] = []
    compliance_pairs: list[tuple[str, bool]] = []
    n_cited_decisions = 0

    for record in decisions:
        gold_applicable = [
            pid
            for pid in env.gold_applicable_for_decision(instance, record)
            if pid in active_ids
        ]
        cited = [pid for pid in record.principles_cited]
        if cited:
            n_cited_decisions += 1

        cite_eval = None
        if condition == "C3":
            ce = metrics.citation_eval(cited, gold_applicable)
            cite_eval = ce.to_dict()
            citation_evals.append(cite_eval)

        compliance_eval: dict[str, bool] = {}
        for pid in gold_applicable:
            checker = checkers.get(pid)
            if checker is None or checker.scope != "decision":
                continue
            passed = bool(
                checker.check(
                    ComplianceContext(
                        instance=instance,
                        gold=instance.gold,
                        output=parsed,
                        decision=record,
                    )
                )
            )
            compliance_eval[pid] = passed
            compliance_pairs.append((pid, passed))

        decision_rows.append(
            DecisionRow(
                trial_id=trial_id,
                decision_idx=record.idx,
                decision_kind=record.kind,
                target=record.target,
                predicted=record.predicted,
                gold=env.gold_for_decision(instance, record),
                answer_score=env.score_decision(instance, record),
                principles_cited=cited,
                gold_applicable=gold_applicable,
                citation_eval=cite_eval,
                compliance_eval=compliance_eval or None,
            )
        )

    instance_pairs: list[tuple[str, bool]] = []
    instance_applicable = [
        pid for pid in env.applicable_principles(instance) if pid in active_ids
    ]
    for pid in instance_applicable:
        checker = checkers.get(pid)
        if checker is None or checker.scope != "instance":
            continue
        passed = bool(
            checker.check(
                ComplianceContext(
                    instance=instance,
                    gold=instance.gold,
                    output=parsed,
                    decision=None,
                )
            )
        )
        instance_pairs.append((pid, passed))

    answer = env.score_answer(instance, parsed)
    compliance = metrics.summarize_compliance(compliance_pairs, instance_pairs)
    citation = metrics.micro_citation(citation_evals) if condition == "C3" else None

    dumped = parsed.model_dump()
    leakage = {
        "n_decisions_with_nonempty_cited": n_cited_decisions,
        "text_field_principle_refs": metrics.scan_text_fields_for_principle_refs(dumped),
        "n_decisions": len(decisions),
    }

    row = TrialRow(
        **{**base_row, "leakage": leakage},
        **call_fields,
        outcome="ok",
        n_repair_attempts=n_repairs,
        failure_detail=None,
        answer=answer.model_dump(),
        compliance=compliance,
        citation=citation,
    )
    return TrialResult(trial=row, decisions=decision_rows)


def run_grid(
    env: Environment,
    backend: Backend,
    instances: list[Instance],
    conditions: list[str],
    seeds: list[int],
    schema_variants: list[str],
    principle_set: PrincipleSet,
    config: RunConfig,
    store: ResultsStore,
    skip_existing: bool = True,
) -> list[TrialResult]:
    results: list[TrialResult] = []
    for instance in instances:
        for condition in conditions:
            for schema_variant in schema_variants:
                for seed in seeds:
                    key = TrialKey(
                        contract_id=instance.contract_id,
                        condition=condition,
                        model=backend.model_id,
                        seed=seed,
                        schema_variant=schema_variant,
                    )
                    if skip_existing and store.has_trial(key.trial_id()):
                        continue
                    result = run_trial(
                        env=env,
                        backend=backend,
                        instance=instance,
                        condition=condition,
                        seed=seed,
                        schema_variant=schema_variant,
                        principle_set=principle_set,
                        config=config,
                    )
                    store.write_trial(result.trial)
                    store.write_decisions(result.decisions)
                    results.append(result)
    return results
