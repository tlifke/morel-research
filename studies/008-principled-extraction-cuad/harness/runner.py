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
from .backends.base import Backend, BackendError, SamplingResult
from .env import ComplianceContext, Environment
from .metrics import DEFAULT_THRESHOLDS, CorrectnessThresholds
from .models import DecisionRecord, Instance, PrincipleSet
from .output_schema import SchemaVariant
from .parsing import ParseFailure, parse_output
from .prompts import CONDITIONS, PROMPT_TEMPLATE_VERSION, PromptBundle, build_prompt
from .store import DecisionRow, ResultsStore, TrialRow
from .trace_store import (
    AttemptTrace,
    TraceCollector,
    TraceStore,
    TrialTrace,
    sha256_messages,
    sha256_text,
)

DEFAULT_MAX_OUTPUT_TOKENS = 16384

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
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ") + "-" + tag


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
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS
    max_repair_attempts: int = 2
    principle_set_version: str = "unset"
    prompt_template_version: str = PROMPT_TEMPLATE_VERSION
    harness_git_sha: Optional[str] = field(default_factory=harness_git_sha)
    trace_root: Optional[Path] = None
    compress_traces: bool = True
    thresholds: CorrectnessThresholds = DEFAULT_THRESHOLDS


@dataclass
class TrialResult:
    trial: TrialRow
    decisions: list[DecisionRow]
    trace: Optional[TrialTrace] = None


@dataclass
class SampleOutcome:
    parsed: Optional[BaseModel] = None
    result: Optional[SamplingResult] = None
    n_repairs: int = 0
    stages: list[str] = field(default_factory=list)
    failure: Optional[dict[str, Any]] = None
    first_parsed: Optional[BaseModel] = None
    first_failure: Optional[dict[str, Any]] = None


def _attempt_trace(
    idx: int,
    messages: list[dict[str, str]],
    result: Optional[SamplingResult],
    parse_outcome: str,
    stage: Optional[str] = None,
    detail: Optional[str] = None,
    error: Optional[str] = None,
) -> AttemptTrace:
    raw = dict(result.raw) if result and isinstance(result.raw, dict) else None
    reasoning = None
    if raw:
        choices = raw.get("choices") or []
        if choices:
            reasoning = (choices[0].get("message") or {}).get("reasoning_content")
        if reasoning is None:
            reasoning = raw.get("reasoning_content")
    return AttemptTrace(
        attempt_idx=idx,
        prompt_sent=messages,
        prompt_sent_sha256=sha256_messages(messages),
        raw_response_body=raw,
        response_text=result.text if result else "",
        response_sha256=sha256_text(result.text) if result else None,
        reasoning_content=reasoning,
        finish_reason=result.finish_reason if result else None,
        completion_truncated=bool(result and result.finish_reason == "length"),
        n_prompt_tokens=result.n_prompt_tokens if result else None,
        n_completion_tokens=result.n_completion_tokens if result else None,
        latency_ms=result.latency_ms if result else None,
        parse_outcome=parse_outcome,
        parse_stage=stage,
        parse_detail=detail[:4000] if detail else None,
        error=error,
    )


def _sample_with_repair(
    backend: Backend,
    prompt: PromptBundle,
    output_model: type[BaseModel],
    seed: int,
    config: RunConfig,
    validate: Callable[[BaseModel], list[str]],
    collector: Optional[TraceCollector] = None,
) -> SampleOutcome:
    messages = prompt.as_messages()
    outcome = SampleOutcome()
    attempts = 0
    while True:
        result = backend.sample(
            messages=messages,
            json_schema=prompt.json_schema,
            temperature=config.temperature,
            seed=seed + attempts,
            max_tokens=config.max_output_tokens,
        )
        outcome.result = result
        try:
            parsed = parse_output(result.text, output_model)
            violations = validate(parsed)
            if violations:
                raise ParseFailure("coverage", "; ".join(violations))
        except ParseFailure as exc:
            outcome.stages.append(exc.stage)
            failure = {"stage": exc.stage, "detail": exc.detail[:2000]}
            if attempts == 0:
                outcome.first_failure = failure
            if collector is not None:
                collector.record(
                    _attempt_trace(
                        attempts, messages, result, "failed", exc.stage, exc.detail
                    )
                )
            if attempts >= config.max_repair_attempts:
                outcome.n_repairs = attempts
                outcome.failure = failure
                return outcome
            template = (
                COVERAGE_REPAIR_INSTRUCTION
                if exc.stage == "coverage"
                else REPAIR_INSTRUCTION
            )
            repair_message = template.format(error=f"{exc.stage}: {exc.detail}")
            if collector is not None:
                collector.set_repair_message(repair_message)
            messages = messages + [
                {"role": "assistant", "content": result.text},
                {"role": "user", "content": repair_message},
            ]
            attempts += 1
            continue

        if collector is not None:
            collector.record(_attempt_trace(attempts, messages, result, "ok"))
        if attempts == 0:
            outcome.first_parsed = parsed
        outcome.parsed = parsed
        outcome.n_repairs = attempts
        return outcome


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
        "max_output_tokens": config.max_output_tokens,
        "correctness_thresholds": config.thresholds.to_dict(),
        "n_contract_tokens": instance.n_tokens,
        "length_bucket": metrics.length_bucket(instance.n_tokens),
        "split": instance.split,
        "leakage": {},
    }

    collector = TraceCollector(
        TrialTrace(
            trial_id=trial_id,
            run_id=config.run_id,
            contract_id=instance.contract_id,
            condition=condition,
            model=backend.model_id,
            seed=seed,
            schema_variant=schema_variant,
            split=instance.split,
            n_contract_tokens=instance.n_tokens,
            prompt_template_version=prompt.template_version,
            principle_set_version=config.principle_set_version,
            harness_git_sha=config.harness_git_sha,
            temperature=config.temperature,
            max_output_tokens=config.max_output_tokens,
            backend=backend.describe(),
        )
    )

    prompt_tokens_est = backend.count_tokens(prompt.full_text())
    budget = prompt_tokens_est + config.max_output_tokens
    if budget > backend.context_limit:
        row = TrialRow(
            **base_row,
            outcome="infeasible_at_length",
            n_repair_attempts=0,
            repair_stages=[],
            n_prompt_tokens=prompt_tokens_est,
            failure_detail={
                "prompt_tokens_estimate": prompt_tokens_est,
                "max_output_tokens": config.max_output_tokens,
                "context_limit": backend.context_limit,
                "token_count_method": backend.token_count_method,
            },
        )
        return TrialResult(
            trial=row,
            decisions=_unrealized_rows(env, instance, trial_id),
            trace=collector.finish("infeasible_at_length", None),
        )

    try:
        outcome = _sample_with_repair(
            backend,
            prompt,
            output_model,
            seed,
            config,
            validate=lambda out: env.validate_output(instance, out),
            collector=collector,
        )
    except BackendError as exc:
        collector.record(
            _attempt_trace(
                len(collector.trial.attempts), prompt.as_messages(), None, "error",
                error=str(exc)[:2000],
            )
        )
        row = TrialRow(
            **base_row,
            outcome="api_error",
            n_repair_attempts=0,
            repair_stages=[],
            n_prompt_tokens=prompt_tokens_est,
            failure_detail={"error": str(exc)[:2000]},
        )
        return TrialResult(
            trial=row,
            decisions=_unrealized_rows(env, instance, trial_id),
            trace=collector.finish("api_error", None),
        )

    result = outcome.result
    response_sha = sha256_text(result.text) if result else None
    call_fields = {
        "response_sha256": response_sha,
        "n_prompt_tokens": (result.n_prompt_tokens if result else None) or prompt_tokens_est,
        "n_completion_tokens": result.n_completion_tokens if result else None,
        "latency_ms": result.latency_ms if result else None,
        "completion_truncated": bool(result and result.finish_reason == "length"),
    }

    first_block = _first_attempt_block(
        env, instance, outcome, condition, principle_set, config
    )

    if outcome.parsed is None:
        detail = dict(outcome.failure or {})
        detail["finish_reason"] = result.finish_reason if result else None
        detail["completion_truncated"] = bool(result and result.finish_reason == "length")
        detail["n_reasoning_chars"] = (
            (result.raw or {}).get("n_reasoning_chars") if result else None
        )
        row = TrialRow(
            **base_row,
            **call_fields,
            outcome="parse_failure",
            n_repair_attempts=outcome.n_repairs,
            repair_stages=outcome.stages,
            failure_detail=detail,
            first_attempt=first_block,
        )
        return TrialResult(
            trial=row,
            decisions=_unrealized_rows(env, instance, trial_id),
            trace=collector.finish("parse_failure", response_sha),
        )

    blocks, decision_rows = _score_output(
        env=env,
        instance=instance,
        parsed=outcome.parsed,
        condition=condition,
        principle_set=principle_set,
        trial_id=trial_id,
        thresholds=config.thresholds,
    )
    row = TrialRow(
        **{**base_row, "leakage": blocks["leakage"]},
        **call_fields,
        outcome="ok",
        n_repair_attempts=outcome.n_repairs,
        repair_stages=outcome.stages,
        failure_detail=None,
        answer=blocks["answer"],
        compliance=blocks["compliance"],
        citation=blocks["citation"],
        first_attempt=first_block,
    )
    return TrialResult(
        trial=row,
        decisions=decision_rows,
        trace=collector.finish("ok", response_sha),
    )


def _first_attempt_block(
    env: Environment,
    instance: Instance,
    outcome: SampleOutcome,
    condition: str,
    principle_set: PrincipleSet,
    config: RunConfig,
) -> dict[str, Any]:
    if outcome.first_parsed is None:
        return {
            "parsed": False,
            "failure_stage": (outcome.first_failure or {}).get("stage"),
            "answer": None,
            "compliance": None,
            "citation": None,
            "leakage": None,
        }
    blocks, _ = _score_output(
        env=env,
        instance=instance,
        parsed=outcome.first_parsed,
        condition=condition,
        principle_set=principle_set,
        trial_id="first-attempt",
        thresholds=config.thresholds,
    )
    return {
        "parsed": True,
        "failure_stage": None,
        "answer": blocks["answer"],
        "compliance": blocks["compliance"],
        "citation": blocks["citation"],
        "leakage": blocks["leakage"],
    }


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


def _score_output(
    env: Environment,
    instance: Instance,
    parsed: BaseModel,
    condition: str,
    principle_set: PrincipleSet,
    trial_id: str,
    thresholds: CorrectnessThresholds,
) -> tuple[dict[str, Any], list[DecisionRow]]:
    active_ids = set(principle_set.ids)
    checkers = env.compliance_checkers()
    decisions = env.iter_decisions(parsed)

    decision_rows: list[DecisionRow] = []
    raw_rows: list[dict[str, Any]] = []
    citation_evals: list[dict[str, Any]] = []
    compliance_pairs: list[tuple[str, bool]] = []
    n_cited_decisions = 0

    for record in decisions:
        gold_applicable = [
            pid
            for pid in env.gold_applicable_for_decision(instance, record)
            if pid in active_ids
        ]
        cited = list(record.principles_cited)
        if cited:
            n_cited_decisions += 1

        answer_score = env.score_decision(instance, record)

        cite_eval = None
        crosstab_cell = None
        if condition == "C3":
            ce = metrics.citation_eval(cited, gold_applicable)
            cite_eval = ce.to_dict()
            citation_evals.append(cite_eval)
            crosstab_cell = {
                "cell": answer_score.get("cell"),
                "span_f1": answer_score.get("span_f1"),
                "citation_correct": metrics.decision_citation_correct(cite_eval, thresholds),
                "answer_correct_at_headline": metrics.decision_answer_correct(
                    answer_score, thresholds
                ),
            }

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

        row = DecisionRow(
            trial_id=trial_id,
            decision_idx=record.idx,
            decision_kind=record.kind,
            target=record.target,
            predicted=record.predicted,
            gold=env.gold_for_decision(instance, record),
            answer_score=answer_score,
            principles_cited=cited,
            gold_applicable=gold_applicable,
            citation_eval=cite_eval,
            citation_x_correctness=crosstab_cell,
            compliance_eval=compliance_eval or None,
        )
        decision_rows.append(row)
        raw_rows.append(row.model_dump())

    instance_pairs: list[tuple[str, bool]] = []
    for pid in [p for p in env.applicable_principles(instance) if p in active_ids]:
        checker = checkers.get(pid)
        if checker is None or checker.scope != "instance":
            continue
        instance_pairs.append(
            (
                pid,
                bool(
                    checker.check(
                        ComplianceContext(
                            instance=instance,
                            gold=instance.gold,
                            output=parsed,
                            decision=None,
                        )
                    )
                ),
            )
        )

    answer = env.score_answer(instance, parsed)
    answer_block = answer.model_dump()
    answer_block["level_b"] = metrics.aggregate_level_b(raw_rows)

    citation_block = None
    if condition == "C3":
        citation_block = {
            **metrics.micro_citation(citation_evals),
            "per_principle": metrics.per_principle_marginals(raw_rows),
            "confusion_pairs": {
                f"{cited}->{missed}": n
                for (cited, missed), n in metrics.confusion_pairs(raw_rows).items()
            },
            "x_answer_correctness_sweep": metrics.citation_correctness_sweep(
                raw_rows, thresholds
            ),
        }

    dumped = parsed.model_dump()
    blocks = {
        "answer": answer_block,
        "compliance": metrics.summarize_compliance(compliance_pairs, instance_pairs),
        "citation": citation_block,
        "leakage": {
            "n_decisions_with_nonempty_cited": n_cited_decisions,
            "text_field_principle_refs": metrics.scan_text_fields_for_principle_refs(dumped),
            "n_decisions": len(decisions),
        },
    }
    return blocks, decision_rows


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
    trace_store = (
        TraceStore(config.trace_root, config.run_id, compress=config.compress_traces)
        if config.trace_root is not None
        else None
    )
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
                    if trace_store is not None and result.trace is not None:
                        trace_store.write(result.trace)
                    results.append(result)
    return results
