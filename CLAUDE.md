# CLAUDE.md — Conventions for this repo

This file is the working agreement between the human researcher and Claude
Code. Read it at the start of every session. When something here is wrong,
flag it — don't silently work around it.

## What this repo is

A public-facing research repo for studies probing what LLMs can and can't do,
how that shifts with harness and model changes, and adjacent questions. Most
work is human-driven with Claude as a collaborator; the boundary varies by
artifact (see "Claude's role" below).

## Taxonomy

**Study** — a long-lived line of inquiry with a coherent question. Lives at
`studies/NNN-slug/` and has a canonical `study.md`.

**Investigation** — a bounded unit of work inside a study. Lives at
`studies/NNN-.../investigations/NNN-slug/` and has a canonical
`investigation.md`. An investigation has a defined scope and reaches a
definite end (results, abandonment, or graduation to a follow-on).

**Future direction** — an unrealized branch. Either a section in the relevant
`study.md` (when it's attached to a known study) or an entry in the top-level
`future-directions.md` (when it isn't).

**Study 0** (`studies/000-research-organization/`) is the meta-study about how
we organize research. Every change to this taxonomy is an investigation
under it.

### IDs

- Directories use `NNN-slug` (zero-padded, three digits, lowercase kebab).
- The full ID of a thing is its path from the repo root, e.g.
  `studies/001-tool-calibration/investigations/001-foundations`.
- Shorthand aliases (e.g. "A1") may appear inside docs but the directory
  path is the source of truth.

## Lineage

Every `study.md` and `investigation.md` carries YAML frontmatter:

```yaml
---
id: studies/001-tool-calibration/investigations/001-foundations
title: Foundations
status: planned          # planned | in-progress | complete | blocked | abandoned
parents:                 # things this descends from
  - studies/001-tool-calibration
children: []             # things spawned from this
related: []              # cross-links without parent/child semantics
axes:                    # see "Capability axes" below; rough labels OK
  llm_capability: medium
  human_capability: high
tags: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

The root `lineage.yaml` is **derived** from these frontmatter blocks by
`scripts/update_lineage.py`. Never edit `lineage.yaml` by hand. Run the
script (or wire it as a hook) after touching frontmatter.

## Capability axes

All research here lives in some position on two rough axes:

- **LLM capability** — how well current LLMs do this task autonomously
  (with whatever harness is being studied).
- **Human capability** — how well a skilled human does it autonomously.

These are deliberately rough (qualitative labels `low | medium | high` are
fine; numeric 0–1 is fine when we want plot coordinates). The point is to be
able to slice work later, not to pretend we have a calibrated scale.

We maintain a running **capability map** at `capability-map/` showing where
specific research tasks fall and their status (done by LLM in our work,
in-progress, hypothesized, human-only, blocked). This map will evolve —
treat it as living, not authoritative.

Status values for capability-map tasks:

- `done` — completed in this repo, with link to the investigation
- `in-progress` — currently being worked
- `hypothesized` — we think it lands here; not yet attempted
- `human-only` — Claude should not attempt (e.g. one-pager prose)
- `blocked` — attempted, hit a wall, documented why

## Studies — internal structure

A study directory typically contains:

```
studies/NNN-slug/
├── study.md                  # canonical running doc; frontmatter required
├── investigations/
│   └── NNN-slug/
│       ├── investigation.md  # canonical doc; frontmatter required
│       └── ...               # whatever the investigation needs
├── one-pagers/               # if the study itself publishes one(s); optional
├── assets/                   # figures, diagrams; optional
├── data/                     # gitignore selectively per-study
└── scripts/                  # study-level code
```

Investigations may also hold their own `one-pagers/` subdir if they publish
a paper themselves. Key investigations usually get one-pagers; studies that
aggregate many investigations may have a study-level one-pager that draws
on its children. Use judgment.

What goes in git per study is a local decision — document it in `study.md`
under a "Repository policy" section if it deviates from the default.

## One-pagers

The standard publishing unit. LaTeX, single page, fixed structure:

1. Title, authors, date
2. Research question
3. Methods
4. Results
5. Forward-looking statement (brief)
6. One figure that carries the message
7. 3–5 takeaway bullets, with:
   - at least one bullet linked to the figure,
   - at least one bullet on key limitations,
   - additional bullets for results that didn't make the figure.

**Claude does not write one-pagers.** Claude scaffolds the file from the
template, may suggest figure choices and structure, may give feedback and
questions during drafting — but the prose is the human's. The human decides
which feedback to incorporate.

Template lives at `one-pagers/template/`. Compiled outputs and per-paper
sources live next to their study or investigation.

## Conventions

- Dates as `YYYY-MM-DD`.
- Slugs lowercase kebab.
- Markdown for all running docs; YAML for structured metadata; JSON only
  when a schema demands it.
- No spreadsheets or notebooks as the source of truth for anything; export
  to text formats and check those in.
- Prefer plain-text artifacts over binary; check in figures alongside
  the scripts that regenerate them.

### Figures

- **Plotly is preferred over matplotlib** for most figures in this repo.
  Reach for it first; reach for matplotlib only when there's a concrete
  reason (e.g. a specific publication-style plot Plotly handles awkwardly).
- Check in the figure as both:
  - the source script (always regenerable from data),
  - a PNG (and optionally HTML for Plotly interactive views).
- For one-pager inclusion: export to PDF or PNG via Plotly's static export
  (`fig.write_image(..., engine="kaleido")`). The LaTeX template expects
  a static image.
- Keep figure data files (`tasks.yaml`, etc.) separate from rendering code
  so plots can be regenerated when the data changes.

## Claude's role boundaries

| Artifact                                  | Claude can do                              |
|-------------------------------------------|--------------------------------------------|
| Scaffolding directories, schemas, configs | Yes, with principles from the human        |
| Drafting code, schemas, prompts           | Yes, surface assumptions explicitly        |
| Bulk generation (e.g. synthetic prompts)  | Yes, after seeds approved by human         |
| One-pager prose                           | **No.** Scaffold + feedback only.          |
| Capability-map task entries               | Propose; human approves status changes     |
| Editing `lineage.yaml` by hand            | **No.** Run the script.                    |

When making a non-trivial design call, list options with tradeoffs and ask
rather than guess.

When producing drafts, return a "things I made up that you should review"
list alongside the artifact — surface assumptions, don't bury them.
