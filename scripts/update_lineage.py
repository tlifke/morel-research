"""Rebuild lineage.yaml from frontmatter blocks in study.md / investigation.md.

Walks studies/, parses YAML frontmatter from every study.md and
investigation.md, and writes a deterministic lineage.yaml at the repo
root.

Run after editing any frontmatter:

    python3 scripts/update_lineage.py

Exits non-zero on any frontmatter parse error or on detected inconsistency
(e.g. a `parents` entry that doesn't exist). Suitable for use in a
pre-commit hook.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
STUDIES_DIR = REPO_ROOT / "studies"
OUT_PATH = REPO_ROOT / "lineage.yaml"

REQUIRED_FIELDS = ("id", "title", "status", "parents", "children")
VALID_STATUSES = {
    "planned", "in-progress", "complete", "blocked", "abandoned",
}


@dataclass
class Node:
    id: str
    title: str
    status: str
    kind: str  # "study" or "investigation"
    path: str
    parents: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def parse_frontmatter(path: Path) -> dict:
    text = path.read_text()
    if not text.startswith("---"):
        raise ValueError(f"{path}: missing frontmatter (no opening ---)")
    end = text.find("\n---", 3)
    if end == -1:
        raise ValueError(f"{path}: missing frontmatter (no closing ---)")
    block = text[3:end].strip()
    try:
        return yaml.safe_load(block) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"{path}: invalid YAML in frontmatter: {e}") from e


def collect_nodes() -> dict[str, Node]:
    nodes: dict[str, Node] = {}
    if not STUDIES_DIR.exists():
        return nodes

    for path in sorted(STUDIES_DIR.rglob("*.md")):
        if path.name not in ("study.md", "investigation.md"):
            continue
        fm = parse_frontmatter(path)
        missing = [f for f in REQUIRED_FIELDS if f not in fm]
        if missing:
            raise ValueError(
                f"{path}: missing required frontmatter fields: {missing}"
            )
        if fm["status"] not in VALID_STATUSES:
            raise ValueError(
                f"{path}: invalid status {fm['status']!r}; "
                f"expected one of {sorted(VALID_STATUSES)}"
            )
        kind = "study" if path.name == "study.md" else "investigation"
        node = Node(
            id=fm["id"],
            title=fm["title"],
            status=fm["status"],
            kind=kind,
            path=str(path.relative_to(REPO_ROOT)),
            parents=list(fm.get("parents") or []),
            children=list(fm.get("children") or []),
            related=list(fm.get("related") or []),
            tags=list(fm.get("tags") or []),
        )
        if node.id in nodes:
            raise ValueError(
                f"duplicate id {node.id!r} "
                f"(seen at {nodes[node.id].path} and {node.path})"
            )
        nodes[node.id] = node
    return nodes


def validate_references(nodes: dict[str, Node]) -> list[str]:
    errors: list[str] = []
    for node in nodes.values():
        for parent in node.parents:
            if parent not in nodes:
                errors.append(
                    f"{node.path}: declares parent {parent!r} which does not exist"
                )
        for child in node.children:
            if child not in nodes:
                errors.append(
                    f"{node.path}: declares child {child!r} which does not exist"
                )
        for rel in node.related:
            if rel not in nodes:
                errors.append(
                    f"{node.path}: declares related {rel!r} which does not exist"
                )
    return errors


def reciprocate_warnings(nodes: dict[str, Node]) -> list[str]:
    warnings: list[str] = []
    for node in nodes.values():
        for parent in node.parents:
            if parent in nodes and node.id not in nodes[parent].children:
                warnings.append(
                    f"{node.path}: parent {parent!r} does not list this as a child"
                )
    return warnings


def render(nodes: dict[str, Node]) -> dict:
    studies: dict[str, dict] = {}
    investigations: dict[str, dict] = {}
    for node in nodes.values():
        entry = {
            "title": node.title,
            "status": node.status,
            "path": node.path,
            "parents": node.parents,
            "children": node.children,
            "related": node.related,
            "tags": node.tags,
        }
        if node.kind == "study":
            studies[node.id] = entry
        else:
            investigations[node.id] = entry
    return {
        "_generated_by": "scripts/update_lineage.py",
        "_do_not_edit": (
            "This file is derived from frontmatter in study.md/investigation.md. "
            "Edit those, then re-run scripts/update_lineage.py."
        ),
        "studies": dict(sorted(studies.items())),
        "investigations": dict(sorted(investigations.items())),
    }


def main() -> int:
    try:
        nodes = collect_nodes()
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    errors = validate_references(nodes)
    if errors:
        for e in errors:
            print(f"error: {e}", file=sys.stderr)
        return 2

    warnings = reciprocate_warnings(nodes)
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)

    rendered = render(nodes)
    OUT_PATH.write_text(yaml.safe_dump(rendered, sort_keys=False, width=100))
    print(
        f"wrote {OUT_PATH.relative_to(REPO_ROOT)} "
        f"({len(rendered['studies'])} studies, "
        f"{len(rendered['investigations'])} investigations)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
