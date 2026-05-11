# Project-level skills

These skills were copied from
[`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official)
and live in this repo so the workflow is reproducible for collaborators.

| Skill | Source plugin | When it triggers |
|-------|---------------|------------------|
| `skill-creator` | `skill-creator` | Creating, editing, or benchmarking custom skills. |
| `writing-hookify-rules` (dir: `writing-rules`) | `hookify` | Authoring rules for the hookify hook system. |
| `claude-md-improver` | `claude-md-management` | Auditing/updating `CLAUDE.md` files. |
| `session-report` | `session-report` | Generating an HTML report of session usage. |

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
