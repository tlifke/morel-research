# Git hooks (opt-in)

Optional git hooks that keep derived artifacts in sync. They're checked
into the repo but not auto-installed, so collaborators can choose whether
to use them.

## pre-commit

Watches for staged changes to any `study.md` / `investigation.md`. On
change:

1. Runs `scripts/update_lineage.py`, which validates frontmatter and
   rebuilds `lineage.yaml`.
2. Aborts the commit if validation fails.
3. Re-stages `lineage.yaml` if its contents changed.

Install once per clone:

```bash
ln -sf ../../scripts/hooks/pre-commit .git/hooks/pre-commit
```

Skip on a single commit if needed:

```bash
git commit --no-verify
```

(Avoid this habitually — when the hook complains, fix the frontmatter
rather than bypassing it.)

## Adding more

If a new derived artifact joins the repo (e.g. a lineage graph rendered
from `lineage.yaml`), extend `pre-commit` to regenerate it, or add a new
hook file. Keep hooks idempotent and fast — they run on every commit.
