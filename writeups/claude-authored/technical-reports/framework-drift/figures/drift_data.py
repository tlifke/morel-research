import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[5]
SNAPSHOT = REPO_ROOT / "studies/000-research-organization/drift-snapshot.tsv"
AUDIT_DATE = "2026-07-20"

STATUS_ORDER = ["planned", "in-progress", "complete"]


def _frontmatter_field(path, field):
    inside = False
    for line in path.read_text().splitlines():
        if line.strip() == "---":
            if inside:
                break
            inside = True
            continue
        if inside and line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip()
    return None


def load():
    rows = []
    with SNAPSHOT.open() as fh:
        for row in csv.DictReader(fh, delimiter="\t"):
            doc = REPO_ROOT / row["path"]
            reconciled = _frontmatter_field(doc, "status")
            rows.append(
                {
                    "path": row["path"],
                    "short": _short(row["path"]),
                    "declared": row["declared_status"],
                    "reconciled": reconciled,
                    "frontmatter_updated": row["frontmatter_updated"],
                    "last_body_date": row["last_dated_content_in_body"],
                    "last_commit": row["last_git_commit_touching"],
                    "mismatch": reconciled != row["declared_status"],
                }
            )
    return rows


def _short(path):
    parts = path.split("/")
    study = parts[1].split("-")[0]
    if "investigations" in parts:
        inv = parts[3]
        return f"{study}/{inv}"
    return f"{study}/study"


if __name__ == "__main__":
    rows = load()
    n = len(rows)
    mismatched = sum(r["mismatch"] for r in rows)
    planned_but_done = [r for r in rows if r["declared"] == "planned"]
    stale_updated = [
        r for r in rows if r["frontmatter_updated"] < max(r["last_body_date"], r["last_commit"])
    ]
    print(f"documents: {n}")
    print(f"declared != reconciled: {mismatched} ({mismatched / n:.0%})")
    print(f"declared planned: {len(planned_but_done)} ({len(planned_but_done) / n:.0%})")
    print(f"updated: predates newest evidence: {len(stale_updated)} ({len(stale_updated) / n:.0%})")
    for r in rows:
        if r["mismatch"]:
            print(f"  {r['short']:<32} {r['declared']:>12} -> {r['reconciled']}")
