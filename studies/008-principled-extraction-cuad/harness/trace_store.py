from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path
from typing import Any, Iterator, Optional

from pydantic import BaseModel, Field

TRACE_FORMAT_VERSION = 1


class AttemptTrace(BaseModel):
    attempt_idx: int
    prompt_sent: list[dict[str, str]]
    prompt_sent_sha256: str
    request_params: Optional[dict[str, Any]] = None
    raw_response_body: Optional[dict[str, Any]] = None
    response_text: str = ""
    response_sha256: Optional[str] = None
    reasoning_content: Optional[str] = None
    finish_reason: Optional[str] = None
    completion_truncated: bool = False
    n_prompt_tokens: Optional[int] = None
    n_completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    parse_outcome: str = "ok"
    parse_stage: Optional[str] = None
    parse_detail: Optional[str] = None
    repair_message_sent: Optional[str] = None
    error: Optional[str] = None


class TrialTrace(BaseModel):
    trace_format_version: int = TRACE_FORMAT_VERSION
    trial_id: str
    run_id: str
    contract_id: str
    condition: str
    model: str
    seed: int
    schema_variant: str
    split: str
    n_contract_tokens: int
    prompt_template_version: str
    principle_set_version: str
    harness_git_sha: Optional[str] = None
    temperature: float
    max_output_tokens: int
    backend: dict[str, Any] = Field(default_factory=dict)
    outcome: Optional[str] = None
    response_sha256: Optional[str] = None
    attempts: list[AttemptTrace] = Field(default_factory=list)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def sha256_messages(messages: list[dict[str, str]]) -> str:
    return sha256_text(json.dumps(messages, sort_keys=True))


class TraceExistsError(RuntimeError):
    pass


class TraceCollector:
    def __init__(self, trial: TrialTrace) -> None:
        self.trial = trial

    def record(self, attempt: AttemptTrace) -> None:
        self.trial.attempts.append(attempt)

    def set_repair_message(self, message: str) -> None:
        if self.trial.attempts:
            self.trial.attempts[-1].repair_message_sent = message

    def finish(self, outcome: str, response_sha256: Optional[str]) -> TrialTrace:
        self.trial.outcome = outcome
        self.trial.response_sha256 = response_sha256
        return self.trial

    @property
    def first_attempt(self) -> Optional[AttemptTrace]:
        return self.trial.attempts[0] if self.trial.attempts else None


class TraceStore:
    def __init__(self, root: Path | str, run_id: str, compress: bool = True) -> None:
        self.root = Path(root)
        self.run_id = run_id
        self.compress = compress
        self.run_dir = self.root / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, trial_id: str) -> Path:
        suffix = ".json.gz" if self.compress else ".json"
        return self.run_dir / f"{trial_id}{suffix}"

    def has(self, trial_id: str) -> bool:
        return (
            (self.run_dir / f"{trial_id}.json.gz").exists()
            or (self.run_dir / f"{trial_id}.json").exists()
        )

    def write(self, trace: TrialTrace) -> Path:
        if self.has(trace.trial_id):
            raise TraceExistsError(
                f"trace for {trace.trial_id} already exists in run {self.run_id}; "
                f"traces are append-only, a re-run needs a fresh run_id"
            )
        path = self.path_for(trace.trial_id)
        payload = json.dumps(trace.model_dump(), sort_keys=True)
        if self.compress:
            with gzip.open(path, "wt", encoding="utf-8") as handle:
                handle.write(payload)
        else:
            path.write_text(payload, encoding="utf-8")
        return path


class TraceReader:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def run_ids(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(p.name for p in self.root.iterdir() if p.is_dir())

    def _paths(self, run_id: str) -> list[Path]:
        run_dir = self.root / run_id
        if not run_dir.exists():
            return []
        return sorted(
            p for p in run_dir.iterdir() if p.name.endswith((".json", ".json.gz"))
        )

    def trial_ids(self, run_id: str) -> list[str]:
        return [p.name.split(".json")[0] for p in self._paths(run_id)]

    @staticmethod
    def _read(path: Path) -> TrialTrace:
        if path.name.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                payload = json.load(handle)
        else:
            payload = json.loads(path.read_text(encoding="utf-8"))
        return TrialTrace.model_validate(payload)

    def load(self, run_id: str, trial_id: str) -> TrialTrace:
        for suffix in (".json.gz", ".json"):
            path = self.root / run_id / f"{trial_id}{suffix}"
            if path.exists():
                return self._read(path)
        raise FileNotFoundError(f"no trace for {trial_id} in run {run_id}")

    def iter_run(self, run_id: str) -> Iterator[TrialTrace]:
        for path in self._paths(run_id):
            yield self._read(path)

    def load_run(self, run_id: str) -> list[TrialTrace]:
        return list(self.iter_run(run_id))

    def verify_against_trials(
        self, run_id: str, trial_rows: list[dict[str, Any]]
    ) -> dict[str, Any]:
        traces = {t.trial_id: t for t in self.iter_run(run_id)}
        rows = {r["trial_id"]: r for r in trial_rows if r.get("run_id") == run_id}
        missing_trace = sorted(set(rows) - set(traces))
        orphan_trace = sorted(set(traces) - set(rows))
        sha_mismatch = [
            tid
            for tid in set(rows) & set(traces)
            if rows[tid].get("response_sha256") != traces[tid].response_sha256
        ]
        return {
            "n_trials": len(rows),
            "n_traces": len(traces),
            "missing_trace": missing_trace,
            "orphan_trace": orphan_trace,
            "response_sha256_mismatch": sorted(sha_mismatch),
            "ok": not (missing_trace or orphan_trace or sha_mismatch),
        }


def load_run(root: Path | str, run_id: str) -> list[TrialTrace]:
    return TraceReader(root).load_run(run_id)


def load_trace(root: Path | str, run_id: str, trial_id: str) -> TrialTrace:
    return TraceReader(root).load(run_id, trial_id)


def latest_run_id(root: Path | str) -> Optional[str]:
    runs = TraceReader(root).run_ids()
    return runs[-1] if runs else None
