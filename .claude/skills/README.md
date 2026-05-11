# Project-level skills

Skills shipped with this repo so the workflow is reproducible for
collaborators. Two categories: skills imported from the official Anthropic
plugin marketplace, and skills written for this repo.

## Imported from anthropics/claude-plugins-official

| Skill | Source plugin | When it triggers |
|-------|---------------|------------------|
| `skill-creator` | `skill-creator` | Creating, editing, or benchmarking custom skills. |
| `writing-hookify-rules` (dir: `writing-rules`) | `hookify` | Authoring rules for the hookify hook system. |
| `claude-md-improver` | `claude-md-management` | Auditing/updating `CLAUDE.md` files. |
| `session-report` | `session-report` | Generating an HTML report of session usage. |

## Written for this repo

| Skill | What it does |
|-------|--------------|
| `new-study` | Scaffold a top-level study directory + study.md with frontmatter; optionally scaffold its first investigation. |
| `new-investigation` | Scaffold a new investigation under an existing study with proper frontmatter; rebuild `lineage.yaml`. |
| `scaffold-one-pager` | Copy `one-pagers/template/` next to a study/investigation and prefill title-block macros. Never writes prose. |
| `capability-map-entry` | Add or update a task entry in `capability-map/tasks.yaml`; re-render `capability-map.png`. |

## Notes on partial installation

These directories contain only the **skills/** portion of each source
plugin. Plugins also ship commands, hooks, and agents that aren't picked
up by a plain copy — for the full experience install the plugin via the
official marketplace:

```text
/plugin marketplace add anthropics/claude-plugins-official
/plugin install <plugin-name>
```

In particular, `hookify` ships a `/hookify` command and supporting rules
that this skill alone can't run.

## Adding more

Open the plugin repo, copy `plugins/<name>/skills/<skill>/` into this
directory. Skills are self-describing via their `SKILL.md` frontmatter;
no separate registration step is needed.
