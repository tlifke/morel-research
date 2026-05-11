"""Session-start status check for the morel-research repo.

Run by Claude Code as a SessionStart hook. Outputs a JSON object with a
`systemMessage` field that summarizes:

  - whether lineage.yaml is fresh relative to current frontmatter,
  - whether capability-map.png is fresh relative to tasks.yaml,
  - which studies and investigations are in-progress / blocked.

The script rebuilds lineage.yaml when it's stale so the rest of the
session works against the current view. It does NOT regenerate the
capability map automatically — the PostToolUse hook handles that on
edit, and forcing a Chrome launch at session start is too heavy.

Exits 0 in all normal cases (including stale-and-rebuilt). Exits 1 only
on an unrecoverable error; Claude Code surfaces that to the user.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
LINEAGE_PATH = REPO_ROOT / "lineage.yaml"
STUDIES_DIR = REPO_ROOT / "studies"
TASKS_PATH = REPO_ROOT / "capability-map" / "tasks.yaml"
MAP_PNG = REPO_ROOT / "capability-map" / "capability-map.png"
UPDATE_LINEAGE = REPO_ROOT / "scripts" / "update_lineage.py"

ACTIVE_STATUSES = {"in-progress", "planned", "blocked"}


def newest_frontmatter_mtime() -> float:
    paths = list(STUDIES_DIR.rglob("study.md")) + list(STUDIES_DIR.rglob("investigation.md"))
    if not paths:
        return 0.0
    return max(p.stat().st_mtime for p in paths)


def lineage_is_stale() -> bool:
    if not LINEAGE_PATH.exists():
        return True
    return newest_frontmatter_mtime() > LINEAGE_PATH.stat().st_mtime


def capability_map_is_stale() -> bool:
    if not TASKS_PATH.exists():
        return False
    if not MAP_PNG.exists():
        return True
    return TASKS_PATH.stat().st_mtime > MAP_PNG.stat().st_mtime


def rebuild_lineage() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(UPDATE_LINEAGE)],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    return result.returncode == 0, (result.stderr or result.stdout).strip()


def active_entries() -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Return (in_progress, blocked) lists of (id, title) tuples."""
    if not LINEAGE_PATH.exists():
        return [], []
    data = yaml.safe_load(LINEAGE_PATH.read_text()) or {}
    in_progress: list[tuple[str, str]] = []
    blocked: list[tuple[str, str]] = []
    for section in ("studies", "investigations"):
        for node_id, entry in (data.get(section) or {}).items():
            status = entry.get("status", "")
            title = entry.get("title", "")
            label = f"{node_id}  —  {title}"
            if status == "in-progress":
                in_progress.append((node_id, label))
            elif status == "blocked":
                blocked.append((node_id, label))
    in_progress.sort()
    blocked.sort()
    return in_progress, blocked


def format_message(
    stale_lineage: bool,
    rebuild_output: str | None,
    stale_map: bool,
    in_progress: list[tuple[str, str]],
    blocked: list[tuple[str, str]],
) -> str:
    lines: list[str] = ["morel-research session status:"]
    if stale_lineage:
        lines.append(
            "  lineage.yaml was stale — rebuilt from frontmatter."
        )
        if rebuild_output:
            lines.append(f"  ({rebuild_output})")
    else:
        lines.append("  lineage.yaml is current.")
    if stale_map:
        lines.append(
            "  capability-map.png is stale relative to tasks.yaml — "
            "run `python3 capability-map/plot.py` to refresh."
        )
    if in_progress:
        lines.append("")
        lines.append(f"  in-progress ({len(in_progress)}):")
        for _id, label in in_progress:
            lines.append(f"    - {label}")
    if blocked:
        lines.append("")
        lines.append(f"  blocked ({len(blocked)}):")
        for _id, label in blocked:
            lines.append(f"    - {label}")
    if not in_progress and not blocked:
        lines.append("  no in-progress or blocked work tracked.")
    return "\n".join(lines)


def main() -> int:
    stale = lineage_is_stale()
    rebuild_output: str | None = None
    if stale:
        ok, output = rebuild_lineage()
        rebuild_output = output
        if not ok:
            print(json.dumps({
                "systemMessage": (
                    "morel-research session status: lineage rebuild FAILED. "
                    "Fix the frontmatter and re-run scripts/update_lineage.py.\n"
                    + output
                ),
            }))
            return 0  # don't block the session; warn instead
    stale_map = capability_map_is_stale()
    in_progress, blocked = active_entries()
    msg = format_message(stale, rebuild_output, stale_map, in_progress, blocked)
    print(json.dumps({"systemMessage": msg}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
