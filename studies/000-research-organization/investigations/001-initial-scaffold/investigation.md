---
id: studies/000-research-organization/investigations/001-initial-scaffold
title: Initial scaffold
status: in-progress
parents:
  - studies/000-research-organization
children: []
related:
  - studies/001-tool-calibration/investigations/001-foundations
axes:
  llm_capability: medium
  human_capability: high
tags:
  - meta
  - scaffolding
created: 2026-05-11
updated: 2026-05-11
---

# Initial scaffold

## Question

What's the minimal viable structure that supports the research patterns we
expect? Specifically:

- studies / investigations / future directions as first-class entities,
- one-pager publishing flow (LaTeX, human-written, fixed structure),
- capability map plotting tasks on LLM vs. human capability axes with status,
- lineage tracking that doesn't require central coordination,
- per-study discretion on what's checked into git.

## Methods

Working session with the human + Claude Code (Opus). Human supplied
principles and constraints; Claude proposed taxonomy options with
tradeoffs; human chose. Concrete decisions recorded in `CLAUDE.md`.

## Decisions made

| Question | Choice |
|----------|--------|
| Per-study log filename | `study.md` / `investigation.md` (file = concept) |
| Directory IDs | `NNN-slug` (zero-padded numeric, kebab-case slug) |
| One-pager location | Flexible — per-investigation or per-study, study decides |
| Lineage source of truth | YAML frontmatter on each doc; `lineage.yaml` is derived |

Rejected alternatives:
- `README.md` for the running log → conflates with repo overviews.
- Letter-prefixed IDs (`A`, `A1`) → don't scale past 26; kept as
  doc-internal aliases only.
- A single top-level `one-pagers/` collection → loses locality with the
  research it summarizes.
- Hand-edited `lineage.yaml` → drifts from the docs that reference it.

## Results

Scaffolded:

- `CLAUDE.md` — conventions, taxonomy, role boundaries.
- `README.md` — repo overview.
- `studies/000-research-organization/` — this meta-study.
- `studies/001-tool-calibration/` — Phase A1 slotted in as investigation 001.
- `one-pagers/template/` — LaTeX template + compile notes.
- `capability-map/` — `tasks.yaml`, `plot.py`, initial PNG.
- `scripts/update_lineage.py` — derives `lineage.yaml` from frontmatter.
- `future-directions.md` — empty placeholder for unattached ideas.

## Forward-looking

Next step is to assess fit by slotting the Phase A1 deliverables into
`studies/001-tool-calibration/investigations/001-foundations/` and noting
any friction. Likely follow-ons under this study:

- frontmatter validator (lint),
- lineage graph renderer,
- investigation scaffolding script (`scripts/new_investigation.py`),
- pre-commit hook to run `update_lineage.py` automatically.

## Things Claude made up that the human should review

- Status enum (`planned | in-progress | complete | blocked | abandoned`)
  — defensible but not validated against future needs.
- Axes labels (`low | medium | high` qualitative; `0.0–1.0` numeric for
  plotting) — chosen for low ceremony, may want refinement.
- Capability-map status values (`done | in-progress | hypothesized |
  human-only | blocked`) — picked to match the user's stated needs but
  not deeply considered.
- `future-directions.md` at repo root rather than `roadmap.md` or
  `backlog.md` — chosen to match the user's wording in the brief.
- The `.gitignore` is conservative; per-study data exclusions will need
  decisions as data accumulates.

## Limitations

- No validation yet — frontmatter typos will only surface when the
  lineage script fails or produces wrong output.
- No CI / hooks wired up — humans must remember to run
  `update_lineage.py` and `plot.py` after edits.
- The capability axes are intentionally rough; we have no calibration
  beyond intuition.
