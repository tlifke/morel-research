---
id: studies/001-tool-calibration/investigations/001-foundations
title: Foundations (Phase A1)
status: in-progress
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

## Working artifacts

| Artifact                       | Path                                 | Status      |
|--------------------------------|--------------------------------------|-------------|
| Tool palette (Python)          | `tool_palette.py`                    | draft       |
| Tool palette (JSON manifest)   | `tool_palette.json`                  | draft       |
| Metadata schema (JSON Schema)  | `metadata.schema.json`               | draft       |
| Schema example records         | `metadata.examples.json`             | draft       |
| ID scheme helper               | `id_scheme.py`                       | draft       |
| System prompt templates        | `system_prompts/`                    | planned     |
| System prompt manifest         | `system_prompts/manifest.json`       | planned     |
| Seed prompt set                | `seeds.jsonl`                        | planned     |

Items 1–3 (palette / schema / IDs) are drafted and self-validated. Items
4–5 (system prompts, seeds) are deferred — they need 1–3 frozen by the
human first.

## Methods (planned)

Per the source brief: bias toward Claude drafting from clear principles,
human reviewing and correcting. Claude surfaces assumptions explicitly.
Claude does not finalize seed pairs without human review (they're the
hardest and most valuable artifact downstream).

## Decisions

> **Decision 1 — palette frozen at five tools, signatures locked** (2026-05-11)
> calculator(expression: str), python_execute(code: str),
> datetime_now() (no args), unit_convert(value: float, from_unit: str,
> to_unit: str), knowledge_lookup(query: str). Each carries a one-line
> docstring and two example calls. Rationale: matches the source-brief
> "frozen" set; no signature drift.

> **Decision 2 — domain stays free-form; sub_domain added as optional**
> (2026-05-11)
> Source brief flagged `domain` as possibly too coarse. Rather than
> enumerate (premature) or split into two flat fields with unclear
> precedence, keep `domain` free-form and add an optional `sub_domain`
> for finer slices when one bucket loses important structure. We will
> revisit enumeration once we see real domain drift.

> **Decision 3 — frequency_class kept** (2026-05-11)
> Brief asked: useful or noise? Keep — `common | uncommon | edge` lets
> us check whether calibration degrades on edge cases, which is one of
> the implicit follow-on questions. Cheap to populate; reversible.

> **Decision 4 — register enumerated with free-form escape hatch**
> (2026-05-11)
> Enum: `neutral_formal | neutral_casual | technical | imperative |
> question | terse | verbose`. Plus `register_notes` for nuance the
> enum can't capture. Picked the dominant aspect rather than producing
> a multi-label scheme — simpler, easier to enforce matched-pair register
> constraints.

> **Decision 5 — expected_pair_behavior added** (2026-05-11)
> Brief asked whether to add this. Yes: a one-line description of how
> a record should differ from its pair_id sibling. Acts as a sanity
> check during curation ("if you can't write a one-liner here, the
> pair is probably confounded").

> **Decision 6 — calibration_status is a 3-state enum** (2026-05-11)
> `assumed | verified | contested`. Brief example had
> `"verified_2026_05"` baked into the value, which conflates state and
> date — split out `calibration_verified_on` (date). Lets us query for
> "all assumed records still needing calibration" cleanly.

> **Decision 7 — ID scheme: pair_id is id minus shortuuid** (2026-05-11)
> Format `{tool}_{domain}_{difficulty}_{disambiguator}_{NNN}_{shortuuid}`.
> Shared prefix down to NNN is the pair_id. shortuuid = first 8 hex
> chars of uuid4. Greppable, sortable, unambiguous. Validation regex
> in `id_scheme.py`; round-trips the three brief examples.

## Results

- `tool_palette.py` + `tool_palette.json`: five tools, frozen
  signatures, two example calls each. Cognitive-moment annotations
  to make the qualitative coverage explicit.
- `metadata.schema.json`: JSON Schema (draft 2020-12) covering 20
  fields. Validated runnable via `jsonschema` (Python).
- `metadata.examples.json`: 3 example records (Type A pair + Type B
  half) — all pass schema validation.
- `id_scheme.py`: `make_pair_id`, `make_prompt_id`, `parse_prompt_id`,
  `is_valid_*` helpers; smoke test passes on all three source-brief
  example IDs.

## Things Claude made up that the human should review

These are explicit assumptions the curator should accept, reject, or
amend before items 1–3 are considered frozen and item 5 (seed prompts)
begins.

1. **`difficulty_label` enum**: `trivial | easy | medium | hard |
   extreme`. Five levels chosen for symmetry around `medium` as the
   calibration boundary. Could also be 3 or 7. Reject if a different
   number is preferred.
2. **`source` enum**: `hand_curated | llm_generated | transformed |
   external`. `transformed` covers derivative records (Type B pair
   built from a Type A); `external` is a placeholder for any
   third-party corpus we might fold in.
3. **`register` enum** (see Decision 4) — the seven values cover what
   I think the matched-pair design needs, but real curation may find
   gaps (e.g., "playful", "formal-but-with-typos", etc.).
4. **`frequency_class` enum** — `common | uncommon | edge`. Three
   buckets, chosen for stratification. Could be more.
5. **ID `disambiguator` is free-form lowercase-snake** — I didn't try
   to enumerate it. If we want consistency (e.g., always reference
   the difficulty source like `3digit`, `relative_to_now`,
   `obscure_country`), say so and I'll constrain it.
6. **`token_count` is `int | null`** — left optional. Populating it
   requires committing to a tokenizer; that decision belongs to A2/A3.
7. **`tool_target: "none"`** — added to the enum so control prompts
   (where no tool should be called) can declare their target
   explicitly rather than via a null. Reject if you'd rather model it
   as a missing-field.
8. **Example records use `"hand_curated"`** — I wrote them as
   demonstrations of the schema, not as seed prompts. They should
   either be promoted into the seed set (after review) or removed
   from the corpus and kept solely as schema fixtures.
9. **`tool_palette.py` raises `NotImplementedError`** in each tool
   body. The brief said "no real execution needed" — I leaned into
   that with an explicit raise rather than `pass` or stubbed return
   values. Reject if you'd rather have callable stubs.
10. **Schema field `additionalProperties: false`** — strict. Catches
    typos but means adding fields later requires bumping the schema.
    Reject if you'd rather be permissive during early iteration.

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
