---
id: studies/001-tool-calibration/investigations/001-foundations
title: Foundations (Phase A1)
status: planned
parents:
  - studies/001-tool-calibration
children: []
related:
  - studies/000-research-organization/investigations/001-initial-scaffold
axes:
  llm_capability: medium
  human_capability: high
tags:
  - foundations
  - tool-palette
  - schema
  - seed-prompts
aliases:
  - A1
  - phase-a1
created: 2026-05-11
updated: 2026-05-11
---

# Investigation 1 — Foundations (Phase A1)

The source brief lives at [`source_brief.md`](./source_brief.md) and is the
authoritative spec for this investigation's deliverables. This file is the
running record.

## Scope

Produce the design substrate for the matched-pair tool-calibration study.
Five deliverables, in priority order:

1. **Tool palette spec** — five tools with frozen signatures.
2. **Metadata schema** — JSON spec with field definitions.
3. **ID scheme** — slug + UUID format with conventions.
4. **System prompt library structure** — variants and composition rules.
5. **Seed prompt set** — 10–20 hand-curated matched pairs.

Items 1–3 are essential; 4–5 may complete in a later session.

## Working artifacts (to be filled in)

| Artifact                       | Path                                | Status   |
|--------------------------------|-------------------------------------|----------|
| Tool palette spec              | `tool_palette.md`                   | planned  |
| Metadata schema (JSON Schema)  | `metadata.schema.json`              | planned  |
| Schema example records         | `metadata.examples.json`            | planned  |
| ID scheme helper               | `id_scheme.py`                      | planned  |
| System prompt templates        | `system_prompts/`                   | planned  |
| System prompt manifest         | `system_prompts/manifest.json`      | planned  |
| Seed prompt set                | `seeds.jsonl`                       | planned  |

When the human kicks off work on any of these, update the status here and
add a section under "Decisions" capturing what was chosen and why.

## Methods (planned)

Per the source brief: bias toward Claude drafting from clear principles,
human reviewing and correcting. Claude surfaces assumptions explicitly.
Claude does not finalize seed pairs without human review (they're the
hardest and most valuable artifact downstream).

## Decisions

_To be populated as work proceeds. Format:_

> **Decision N — short title** (date)
> What was chosen, the alternatives considered, why this won.

## Results

_To be populated. Will reference the working artifacts above._

## Forward-looking

After this investigation completes:

- `002-difficulty-axes` — per-tool difficulty calibration so we can generate
  prompts at known difficulty levels.
- `003-bulk-generation` — generate the corpus from seeds + axes.

## Things Claude should flag to the human

- The source brief lists fields to push back on (`domain`, `frequency_class`,
  `register`, `expected_pair_behavior`). Make these explicit decision points
  before freezing the schema.
- The source brief asks: is the palette frozen, or still tempted to add a
  sixth tool? Surface this before drafting signatures.
- Calibration status (`verified_2026_05` in the example) implies an
  empirical step (Phase A4) — clarify whether seeds are tagged "assumed"
  initially and re-tagged after calibration, or left blank.

## Limitations (anticipated)

- Difficulty labels in the seed set are necessarily *assumed* until A4
  empirically verifies them; this investigation produces hypotheses, not
  validated calibrations.
- Hand-curated seed sets reflect the curator's blind spots; downstream
  bulk generation will need to deliberately probe outside that envelope.
