from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

INV = Path(__file__).resolve().parents[1]
RUNS = INV / "runs"


@dataclass(frozen=True)
class TrialKey:
    task_definition_version: str
    task_definition_sha256: str
    principle_set_version: str
    arm: str
    model: str
    contract_id: str
    repeat_idx: int

    @property
    def trial_id(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class QuestionTrialKey:
    task_definition_version: str
    task_definition_sha256: str
    principle_set_version: str
    arm: str
    model: str
    contract_id: str
    category: str
    repeat_idx: int

    @property
    def trial_id(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]


@dataclass
class TrialRecord:
    key: Any
    run_id: str
    outcome: str
    temperature: float
    top_p: Optional[float]
    max_output_tokens: int
    n_prompt_tokens: Optional[int]
    n_completion_tokens: Optional[int]
    finish_reason: Optional[str]
    latency_ms: int
    response_sha256: Optional[str] = None
    parsed: bool = False
    output: Optional[dict[str, Any]] = None
    failure_detail: Optional[str] = None
    notes: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["key"] = asdict(self.key)
        d["trial_id"] = self.key.trial_id
        return d


class Ledger:
    def __init__(self, run_id: str, root: Path = RUNS) -> None:
        self.run_id = run_id
        self.dir = root / run_id
        self.dir.mkdir(parents=True, exist_ok=True)
        self.path = self.dir / "trials.jsonl"

    def done(self) -> set[str]:
        if not self.path.exists():
            return set()
        return {
            json.loads(line)["trial_id"]
            for line in self.path.read_text().splitlines()
            if line.strip()
        }

    def append(self, record: TrialRecord) -> None:
        with self.path.open("a") as fh:
            fh.write(json.dumps(record.to_json(), sort_keys=True) + "\n")

    def read(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text().splitlines() if l.strip()]

    def write_manifest(self, manifest: dict[str, Any]) -> None:
        (self.dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
