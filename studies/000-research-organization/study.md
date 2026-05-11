---
id: studies/000-research-organization
title: Research organization
status: in-progress
parents: []
children:
  - studies/000-research-organization/investigations/001-initial-scaffold
related: []
axes:
  llm_capability: medium
  human_capability: high
tags:
  - meta
  - infrastructure
created: 2026-05-11
updated: 2026-05-11
---

# Study 0 — Research organization

## Question

How do we organize automated and semi-automated research such that:

- studies and investigations are discoverable and addressable,
- lineage between work is captured without ceremony,
- bulk-generated artifacts and human-written artifacts coexist cleanly,
- Claude's role boundaries are explicit and auditable,
- the structure is flexible enough to evolve without churning everything?

This is the meta-study. Every change to the taxonomy or repo conventions is
an investigation under it.

## Why it's Study 0

Everything else depends on these decisions. Getting them roughly right
matters more than getting them perfectly right — the convention here is
"adjust as needed, log the adjustment."

## Investigations

- `001-initial-scaffold` — first pass at directory layout, file conventions,
  one-pager template, capability map, lineage handling. In-progress.

## Repository policy

This study's artifacts are all text and small enough to live entirely in
git. No data/ or assets/ exclusions.

## Future directions

- Validation: a CI check that frontmatter is well-formed and parents exist.
- Visualization: a rendered lineage graph (DOT/Mermaid) generated from
  `lineage.yaml`.
- Cross-study indexing: tag-based search across all `study.md` /
  `investigation.md` files.
- Investigation templates: a `new-investigation` script that scaffolds the
  frontmatter and standard sections.
- Multi-agent coordination: conventions for parallel work on different
  investigations without lineage merge conflicts (the
  frontmatter-as-source-of-truth design is already aimed at this).

## Open questions

- Should `study.md` carry a "results so far" section that aggregates across
  investigations, or do we rely on readers descending into each one?
- Where do replication artifacts live when an investigation has been
  superseded but its data is still cited?
- How do we mark a study as "complete" without erasing its living-doc
  nature?
