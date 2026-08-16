from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import yaml

from .models import Principle, PrincipleSet


def load_principle_set(
    path: Path | str,
    version: Optional[str] = None,
    ids: Optional[Iterable[str]] = None,
) -> PrincipleSet:
    rows = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    principles = [Principle.model_validate(row) for row in rows]
    if ids is not None:
        keep = list(ids)
        known = {p.id for p in principles}
        unknown = [pid for pid in keep if pid not in known]
        if unknown:
            raise KeyError(f"principle id(s) not in {path}: {', '.join(unknown)}")
        order = {pid: i for i, pid in enumerate(keep)}
        principles = sorted(
            (p for p in principles if p.id in order), key=lambda p: order[p.id]
        )
    return PrincipleSet(
        version=version or Path(path).stem, principles=principles
    )
