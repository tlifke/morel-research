from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator, Optional

from pydantic import BaseModel, Field

TRIALS_FILE = "trials.jsonl"
DECISIONS_FILE = "decisions.jsonl"


class TrialRow(BaseModel):
    trial_id: str
    contract_id: str
    condition: str
    model: str
    seed: int
    schema_variant: str

    run_id: str
    prompt_template_version: str
    principle_set_version: str
    harness_git_sha: Optional[str] = None
    temperature: float
    max_output_tokens: Optional[int] = None
    correctness_thresholds: dict[str, Any] = Field(default_factory=dict)
    response_sha256: Optional[str] = None
    n_prompt_tokens: Optional[int] = None
    n_completion_tokens: Optional[int] = None
    latency_ms: Optional[int] = None
    completion_truncated: bool = False

    outcome: str
    n_repair_attempts: int = 0
    repair_stages: list[str] = Field(default_factory=list)
    failure_detail: Optional[dict[str, Any]] = None

    n_contract_tokens: int
    length_bucket: str
    split: str

    answer: Optional[dict[str, Any]] = None
    compliance: Optional[dict[str, Any]] = None
    citation: Optional[dict[str, Any]] = None
    leakage: dict[str, Any] = Field(default_factory=dict)
    first_attempt: Optional[dict[str, Any]] = None


class DecisionRow(BaseModel):
    trial_id: str
    decision_idx: int
    decision_kind: Optional[str]
    target: Optional[str]

    predicted: Optional[dict[str, Any]] = None
    gold: Optional[dict[str, Any]] = None

    answer_score: Optional[dict[str, Any]] = None

    principles_cited: list[str] = Field(default_factory=list)
    gold_applicable: list[str] = Field(default_factory=list)
    citation_eval: Optional[dict[str, Any]] = None
    citation_x_correctness: Optional[dict[str, Any]] = None
    compliance_eval: Optional[dict[str, Any]] = None


class DuplicateRowError(RuntimeError):
    pass


class ResultsStore:
    def __init__(self, root: Path | str, strict: bool = True) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.trials_path = self.root / TRIALS_FILE
        self.decisions_path = self.root / DECISIONS_FILE
        self.strict = strict
        self._seen_trials: set[str] = set()
        self._seen_decisions: set[tuple[str, int]] = set()
        self._reload()

    def _reload(self) -> None:
        for row in self.read_trials():
            self._seen_trials.add(row["trial_id"])
        for row in self.read_decisions():
            self._seen_decisions.add((row["trial_id"], row["decision_idx"]))

    def _append(self, path: Path, payload: dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True) + "\n")

    def has_trial(self, trial_id: str) -> bool:
        return trial_id in self._seen_trials

    def write_trial(self, row: TrialRow | dict[str, Any]) -> None:
        model = TrialRow.model_validate(row) if isinstance(row, dict) else row
        if model.trial_id in self._seen_trials:
            if self.strict:
                raise DuplicateRowError(f"trial_id {model.trial_id} already written")
            return
        self._seen_trials.add(model.trial_id)
        self._append(self.trials_path, model.model_dump())

    def write_decision(self, row: DecisionRow | dict[str, Any]) -> None:
        model = DecisionRow.model_validate(row) if isinstance(row, dict) else row
        key = (model.trial_id, model.decision_idx)
        if key in self._seen_decisions:
            if self.strict:
                raise DuplicateRowError(f"(trial_id, decision_idx) {key} already written")
            return
        self._seen_decisions.add(key)
        self._append(self.decisions_path, model.model_dump())

    def write_decisions(self, rows: list[DecisionRow | dict[str, Any]]) -> None:
        for row in rows:
            self.write_decision(row)

    def _read(self, path: Path) -> Iterator[dict[str, Any]]:
        if not path.exists():
            return
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def read_trials(self) -> list[dict[str, Any]]:
        return list(self._read(self.trials_path))

    def read_decisions(self) -> list[dict[str, Any]]:
        return list(self._read(self.decisions_path))
