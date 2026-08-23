from __future__ import annotations

import collections
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from loop.ledger import Ledger

MAJORITY = 2
REPEATS = 3
MAX_NEW_FAILING_CELLS = 1.0


@dataclass(frozen=True)
class Cell:
    contract_id: str
    category: str


def failing_cells(run_id: str) -> dict[Cell, int]:
    path = Ledger(run_id).dir / "failures.jsonl"
    counts: dict[Cell, int] = collections.Counter()
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        f = json.loads(line)
        counts[Cell(f["contract_id"], f["category"])] += 1
    return dict(counts)


def failing_by_majority(run_id: str, majority: int = MAJORITY) -> set[Cell]:
    return {c for c, n in failing_cells(run_id).items() if n >= majority}


def failure_class_map(run_id: str) -> dict[Cell, str]:
    path = Ledger(run_id).dir / "failures.jsonl"
    out: dict[Cell, list[str]] = collections.defaultdict(list)
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        f = json.loads(line)
        out[Cell(f["contract_id"], f["category"])].append(f["failure_class"])
    return {c: collections.Counter(v).most_common(1)[0][0] for c, v in out.items()}


def mean_detection_f2(run_id: str) -> dict[str, float]:
    score = json.loads((Ledger(run_id).dir / "score.json").read_text())
    by_contract: dict[str, list[float]] = collections.defaultdict(list)
    for t in score["per_trial"]:
        if t.get("outcome") != "ok":
            continue
        f2 = t["detection_micro"].get("f2")
        if f2 is not None:
            by_contract[t["contract_id"]].append(f2)
    return {c: sum(v) / len(v) for c, v in by_contract.items() if v}


@dataclass
class RungResult:
    rung: int
    passed: bool
    targets: list[dict[str, str]]
    targets_fixed: list[dict[str, str]]
    targets_still_failing: list[dict[str, str]]
    new_failing_cells_per_contract: dict[str, float]
    f2_control: dict[str, float]
    f2_candidate: dict[str, float]
    mean_f2_delta: Optional[float]
    reasons: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {**self.__dict__}


def evaluate(
    rung: int,
    control_run: str,
    candidate_run: str,
    targets: list[Cell],
    repeats: int = REPEATS,
) -> RungResult:
    control_fail = failing_by_majority(control_run)
    cand_counts = failing_cells(candidate_run)
    cand_fail = {c for c, n in cand_counts.items() if n >= MAJORITY}

    fixed = [t for t in targets if t in control_fail and t not in cand_fail]
    still = [t for t in targets if t not in set(fixed)]

    contracts = sorted({t.contract_id for t in targets})
    new_cells: dict[str, float] = {}
    for cid in contracts:
        introduced = [
            c for c in cand_counts
            if c.contract_id == cid and c not in control_fail and c not in set(targets)
        ]
        new_cells[cid] = round(sum(cand_counts[c] for c in introduced) / repeats, 2)

    f2c = mean_detection_f2(control_run)
    f2k = mean_detection_f2(candidate_run)
    shared = [c for c in contracts if c in f2c and c in f2k]
    delta = (
        sum(f2k[c] - f2c[c] for c in shared) / len(shared) if shared else None
    )

    reasons: list[str] = []
    if still:
        reasons.append(f"{len(still)} of {len(targets)} target cells not fixed under the 2-of-3 rule")
    over = {c: v for c, v in new_cells.items() if v > MAX_NEW_FAILING_CELLS}
    if over:
        reasons.append(f"collateral damage over threshold on {sorted(over)}")
    if rung >= 2 and delta is not None and delta < 0:
        reasons.append(f"mean detection F2 fell by {abs(delta):.4f}")

    return RungResult(
        rung=rung,
        passed=not reasons,
        targets=[t.__dict__ for t in targets],
        targets_fixed=[t.__dict__ for t in fixed],
        targets_still_failing=[t.__dict__ for t in still],
        new_failing_cells_per_contract=new_cells,
        f2_control={c: round(f2c[c], 4) for c in shared},
        f2_candidate={c: round(f2k[c], 4) for c in shared},
        mean_f2_delta=round(delta, 4) if delta is not None else None,
        reasons=reasons,
    )
