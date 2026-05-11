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

| Artifact                       | Path                                              | Status               |
|--------------------------------|---------------------------------------------------|----------------------|
| Tool palette (Python)          | `tool_palette.py`                                 | drafted              |
| Tool palette (JSON manifest)   | `tool_palette.json`                               | drafted              |
| Metadata schema (JSON Schema)  | `metadata.schema.json`                            | drafted              |
| Schema test fixtures           | `metadata.fixtures.json`                          | drafted              |
| ID scheme helper               | `id_scheme.py`                                    | drafted              |
| System prompt templates        | `../../system_prompts/` (study-level)             | drafted (9 variants) |
| System prompt manifest         | `../../system_prompts/manifest.json`              | drafted              |
| User-knowledge KB              | `../../kb/user_knowledge.json`                    | drafted              |
| General-knowledge KB (fabricated) | `../../kb/general_knowledge.json`              | drafted              |
| General-knowledge KB (verified)   | `../../kb/general_knowledge_real.json`          | drafted              |
| Seed pair specification        | `seeds_spec.yaml`                                 | drafted (16 pairs)   |
| Seed builder                   | `build_seeds.py`                                  | drafted              |
| Seed corpus                    | `../../seeds.jsonl`                               | drafted (32 records) |

All Phase A1 deliverables (items 1–5) are now drafted and self-
validated end-to-end:
- Schema validation passes on all 32 seed records (via build_seeds.py
  `--validate`).
- ID round-trip passes for full tool names, the `none` control case,
  and the calculator example (id_scheme.py smoke test).
- Every seed prompt that references a KB entry has a corresponding
  entry in the relevant KB (verified manually during seed prep).

Items pending human review:
- 16 seed pairs awaiting pair-by-pair sign-off via
  `difficulty_label.human_review` blocks (currently all `null`).
- 4 system prompt variants (`sys_all_tools_proactive_v1`,
  `sys_dt_only_neutral_v1`, `sys_uc_only_neutral_v1`,
  `sys_ukl_only_neutral_v1`) are drafted in the manifest but not
  exercised by any seed pair in this batch — kept for A2/A3.

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

> **Decision 8 — split `knowledge_lookup` into two tools; palette grows to 6** (2026-05-11)
> Amends Decision 1. `knowledge_lookup` had a fuzzy success criterion
> and conflated two distinct cognitive moments: world-knowledge
> retrieval ("do you know you don't know?") and personal-context
> retrieval ("do you reach for the right channel when the answer is
> structurally outside your weights?"). Split into:
>
> - `general_knowledge_lookup(query: str)` — over a curated KB of
>   time-anchored facts (post-cutoff sports results, market data,
>   AI/tech announcements) across a small set of domains chosen up
>   front so seed prompts can be balanced.
> - `user_knowledge_lookup(query: str)` — over a fixed fake-persona
>   JSON (~30–50 fields: identity, family, calendar, preferences).
>
> Both tools mimic a real `web_search` tool: free-form `query: str`
> in, structured **ranked list** of result records out (`results: [...]`),
> empty list when nothing matches (no special `not_found` flag —
> hit and miss share the same shape, matching real search semantics).
> Top-K via simple deterministic ranking (BM25 / keyword + aliases)
> over snippet text — KBs are small enough that this is unambiguous.
>
> Result record shape:
> - general: `{id, date, domain, snippet}`
> - user: `{field, snippet}`
>
> **Multi-call enabled, one-shot by design.** The tool signature
> permits repeated calls (faithful to real web search), but Phase A1
> seed prompts are written so a single well-formed call suffices.
> Multi-call refinement — "does the model know it should re-query,
> particularly when the KB doesn't have the requested info?" — becomes
> a distinct calibration target for a later investigation rather than
> a confound here.
>
> Web search itself was considered as the tool and rejected:
> non-deterministic results break matched-pair reproducibility across
> re-runs. Curating two small closed-world KBs is bounded; living with
> drifting ground truth is not.

> **Decision 9 — canonical domains list as soft convention; sub_domain nests under domain** (2026-05-11)
> Amends Decision 2. `domain` stays free-form to avoid premature
> enumeration, but to head off label drift ("math" vs "mathematics"
> vs "arithmetic") we maintain a study-level soft-convention reference
> at [`../../canonical_domains.md`](../../canonical_domains.md).
> Curator rule: reuse before invent; if you add a new label, add a
> row in the same edit. `sub_domain` is treated as a hierarchical
> finer slice of its row's `domain`, never orthogonal — this preserves
> roll-up slicing as a real capability. Sub_domains themselves remain
> un-enumerated.

> **Decision 10 — `frequency_class` pinned to answer salience** (2026-05-11)
> Amends Decision 3. Enum unchanged (`common | uncommon | edge`) but
> meaning is now explicit: how well-known is the *answer* / fact being
> probed. NOT prompt-type frequency, NOT tool-need frequency.
> Schema description updated.

> **Decision 11 — register split into three orthogonal small enums** (2026-05-11)
> Supersedes Decision 4. The 7-value dominant-aspect enum mixed four
> dimensions (tone, form, length, vocabulary) and lost signal whenever
> a prompt spanned them. Replaced with:
> - `register_tone`: `neutral | formal | casual | technical`
> - `register_form`: `statement | question | imperative`
> - `register_length`: `terse | normal | verbose`
> Plus `register_notes` retained for nuance. Same total labeling cost;
> matched-pair register controls now have real leverage.

> **Decision 12 — ID separator switched to `-`; full tool names retained** (2026-05-11)
> Implements Decision 7's "full tool names" choice. Discovered mid-edit
> that the original `_`-only format silently mis-segmented multi-token
> tool names (`general_knowledge_lookup` parsed as
> tool=`general`/domain=`knowledge`/difficulty=`lookup`). Fixed by
> using `-` as the field separator and allowing `_` within field
> values:
>     `{tool}-{domain}-{difficulty}-{disambiguator}-{NNN}-{shortuuid}`
> Control prompts use `tool=none` literal. `id_scheme.py`, the schema
> regex, and example records all updated; smoke test extended to
> round-trip long tool names and the `none` control case.

> **Decision 13 — difficulty_label becomes signed object; difficulty_calibrated stores raw empirical signal** (2026-05-11)
> Amends item 1 of "Things Claude made up." Two structural changes:
>
> 1. The curator is an LLM by default (only a sample of records get
>    interactive human review). So `difficulty_label` is *itself* a
>    model prediction and must be signed. Refactored from a bare enum
>    to a nested object:
>    - `value`: 5-enum, authoritative for slicing.
>    - `llm_assessment`: required block with `model`, `date`, `value`,
>      `confidence`, `reasoning`. Set at record creation.
>    - `human_review`: optional asymmetric review block —
>      `reviewer`, `date`, `agreed`, `overridden_to`, `notes`. Null
>      until reviewed; non-null records gate on a human sign-off.
>    Asymmetric (not parallel dual-block) because reviewers stamp-
>    agree on most records and only need to write prose on overrides.
>    LLM-vs-human divergence becomes a research artifact in itself,
>    same intuition as the future-directions dual-assessment convention.
>
> 2. `difficulty_calibrated` no longer stores per-model enum buckets.
>    Replaced with raw empirical signal per model:
>    `{model_id: {success_rate, n, last_run}}`. Bucket assignment
>    moves to analysis time, governed by thresholds defined in the
>    planned A4 calibration methodology. This avoids locking
>    empirical observations into the same coarse buckets used for the
>    hypothesis, and makes re-bucketing a config change rather than
>    a data migration.
>
> Side effect: `calibration_status: contested` now has a crisper
> meaning — the empirical success_rate falls in a bucket different
> from `difficulty_label.value` under A4's thresholds.

> **Decision 14 — closing the rest of the "Things Claude made up" list** (2026-05-11)
>
> - **Item 5 (disambiguator)**: stays free-form. Added a soft
>   convention in `canonical_domains.md` — disambiguator should be a
>   *meaningful slug describing what makes this pair distinct within
>   its bucket*, not a random suffix (shortuuid already handles
>   uniqueness). Examples and anti-patterns documented inline.
> - **Item 6 (token_count)**: replaced single-int `token_count` with
>   tokenizer-keyed dict `token_counts: {tokenizer_id: int} | null`,
>   mirroring `difficulty_calibrated`'s per-model dict. Cheap now,
>   painful migration later. Fixtures updated.
> - **Item 8 (example records)**: renamed `metadata.examples.json` →
>   `metadata.fixtures.json`, top-level array renamed `examples` →
>   `fixtures`, added `_purpose` field clarifying these are schema
>   exercises and NOT part of the seed corpus. Prevents accidental
>   inclusion when slicing on `source: hand_curated`.
> - **Item 10 (additionalProperties: false)**: kept strict during
>   early iteration. Recorded a revisit note in `study.md` Open
>   questions tied to ~500-record corpus size and the arrival of
>   bulk generation (A3) — if schema-bump friction starts outweighing
>   typo-protection at that point, loosen and route analysis-only
>   annotations through a dedicated `extra:` object.

> **Decision 16 — parallel fabricated/real general-knowledge KBs** (2026-05-11)
> Surfaced mid-handoff during solo seed-prep work. The first draft of
> `kb/general_knowledge.json` was populated by Claude (claude-opus-4-7)
> with plausible-but-fabricated facts (Arsenal-City score, S&P close,
> Anthropic NLA paper, Claude Opus 4.7 release date, etc.). Web search
> against ground truth revealed that almost every specific value was
> wrong — wrong dates, wrong scores, wrong paper titles, sometimes
> events that never happened. The user explicitly chose to **keep the
> fabricated KB** and build a parallel `kb/general_knowledge_real.json`
> via WebSearch. The two KBs cover identical topics with divergent
> truth values.
>
> The parallel structure is itself a research artifact, separate from
> the matched-pair tool-calibration question this investigation
> targets: do models behave differently when `general_knowledge_lookup`
> returns plausible-but-false snippets vs. real-and-true snippets? Does
> the model have any independent check on the *truthfulness* of
> returned snippets, or does it trust the lookup tool wholesale? Worth
> a sibling investigation later (folded into the existing
> `004-tool-failure-recognition` direction, or its own).
>
> Side note for self: I had WebSearch available the whole time and
> didn't reach for it. The irony — a study about whether models
> recognize they should look things up, sabotaged at curation time by
> a model that didn't recognize it should look things up — is acute
> and worth flagging. Memory feedback note saved.

## Seed plan (Decision 15)

Agreed 2026-05-11 between human and Claude (Opus 4.7) as the contract
for solo execution of items 4–5.

### System prompt variants

Nine IDs, using short tool slugs (source-brief convention) since the
namespace is small and the IDs are referenced not parsed:

| ID                              | tool_set       | framing    |
|---------------------------------|----------------|------------|
| `sys_all_tools_neutral_v1`      | all 6 tools    | neutral    |
| `sys_no_tools_v1`               | none           | n/a        |
| `sys_all_tools_proactive_v1`    | all 6 tools    | proactive  |
| `sys_calc_only_neutral_v1`      | calculator     | neutral    |
| `sys_py_only_neutral_v1`        | python_execute | neutral    |
| `sys_dt_only_neutral_v1`        | datetime_now   | neutral    |
| `sys_uc_only_neutral_v1`        | unit_convert   | neutral    |
| `sys_gkl_only_neutral_v1`       | general_kn...  | neutral    |
| `sys_ukl_only_neutral_v1`       | user_kn...     | neutral    |

`proactive` is included in the matrix for infrastructure validation;
no matched pairs in this batch sweep it (framing manipulation deferred
to A2 — would require a `pair_type: C` if we want it in matched form).

### Seed allocation (16 pairs)

| # | Tool                     | Type | C/E | System prompts                       | Probes                                                  |
|---|--------------------------|------|-----|--------------------------------------|---------------------------------------------------------|
| 1 | calculator               | A    | C   | all_tools_neutral                     | Hard 4-digit mult vs trivial 1-digit mult               |
| 2 | calculator               | A    | C   | all_tools_neutral                     | Decimal precision division vs trivial division          |
| 3 | calculator               | B    | C   | all_tools_neutral / no_tools          | Same hard mult, affordance removed                      |
| 4 | calculator               | A    | E   | calc_only_neutral                     | Hard mult under per-tool isolation                      |
| 5 | python_execute           | A    | C   | all_tools_neutral                     | Loop/aggregation vs trivial expression                  |
| 6 | python_execute           | B    | E   | all_tools_neutral / no_tools          | Same string-manip task, affordance removed              |
| 7 | python_execute           | A    | E   | py_only_neutral                       | Per-tool isolation, multi-step computation              |
| 8 | datetime_now             | A    | C   | all_tools_neutral                     | "Today's date" (warrants call) vs in-prompt date (trivial) |
| 9 | datetime_now             | B    | E   | all_tools_neutral / no_tools          | "Today's date" with affordance removed                  |
| 10 | unit_convert            | A    | C   | all_tools_neutral                     | Cross-system convert vs trivial same-system             |
| 11 | unit_convert            | B    | E   | all_tools_neutral / no_tools          | Same convert, affordance removed                        |
| 12 | general_knowledge_lookup | A    | C   | all_tools_neutral                     | Post-cutoff fact vs well-known fact                     |
| 13 | general_knowledge_lookup | B    | C   | all_tools_neutral / no_tools          | Post-cutoff query, affordance removed                   |
| 14 | general_knowledge_lookup | A    | E   | gkl_only_neutral                      | Per-tool isolation, post-cutoff fact                    |
| 15 | user_knowledge_lookup    | A    | C   | all_tools_neutral                     | Personal fact (no possible weights) vs generic question |
| 16 | user_knowledge_lookup    | B    | E   | all_tools_neutral / no_tools          | Personal query, affordance removed                      |

Counts: A=9 / B=7 (≈50/50). Common=10 / Edge=6 (≈60/40). Tool coverage:
calc=4, py=3, dt=2, uc=2, gkl=3, ukl=2 — weighted toward calculator
and general_knowledge_lookup per source brief.

### Handoff scope (Claude solo)

Claude produces against this contract without further check-ins:

1. `system_prompts/` directory: 9 templates + `manifest.json`.
2. `kb/user_knowledge.json` — fake persona, fields driven by pair 15
   and 16's seed content.
3. `kb/general_knowledge.json` — time-anchored facts in sports /
   finance / ai_tech, driven by pairs 12–14's seed content.
4. `seeds.jsonl` — 32 records (16 pairs × 2 halves). Each record's
   `difficulty_label.llm_assessment` signed by `claude-opus-4-7` with
   reasoning; `human_review: null`.
5. A `build_seeds.py` script that expands a compact pair-spec
   (`seeds_spec.yaml`) into the JSONL, mirroring the eventual A3
   bulk-generation pipeline.
6. Validation: schema validation on every seed record; ID
   round-trip; KB-lookup-resolves-for-every-seed sanity check.

The human reviews seeds pair-by-pair in a subsequent session,
populating `difficulty_label.human_review` blocks.

## Results

- `tool_palette.py` + `tool_palette.json`: six tools (per Decision 8),
  frozen signatures, two example calls each. Cognitive-moment
  annotations make qualitative coverage explicit.
- `metadata.schema.json`: JSON Schema (draft 2020-12) covering the
  record shape. Validated runnable via `jsonschema` (Python).
- `metadata.fixtures.json`: 3 schema-exercise fixtures (Type A pair +
  Type B half) — all pass schema validation. Renamed from
  `metadata.examples.json` (Decision 14) with explicit `_purpose`
  note clarifying these are NOT seed corpus.
- `id_scheme.py`: `make_pair_id`, `make_prompt_id`, `parse_prompt_id`,
  `is_valid_*` helpers. Smoke test passes on the calculator example,
  long tool names (`general_knowledge_lookup`,
  `user_knowledge_lookup`), and the `none` control case. Uses `-`
  field separator per Decision 12.
- `../../system_prompts/`: 9 variants per Decision 15 — workhorse
  (`all_tools_neutral_v1`), control (`no_tools_v1`), framing probe
  (`all_tools_proactive_v1`), six per-tool-only variants. Manifest
  enumerates each with declared tool_set and framing.
- `../../kb/user_knowledge.json`: fake Maya Patel persona, 20 entries
  with aliases — identity, family, calendar, preferences, allergies.
  Drives pairs 15–16.
- `../../kb/general_knowledge.json` + `../../kb/general_knowledge_real.json`:
  parallel fabricated/verified KBs covering identical topics in
  sports, finance, ai_tech (Decision 16). The fabricated KB carries a
  `_provenance` flag; the verified KB is sourced via WebSearch as of
  2026-05-11. Pairs 12–14 reference these.
- `seeds_spec.yaml`: compact 16-pair spec — Type A:B = 10:6,
  common:edge = 9:7, all six tools covered with calculator and
  general_knowledge_lookup weighted heavier per source brief.
- `build_seeds.py`: spec → JSONL expander. Deterministic shortuuids
  via sha256(pair_id|half_index). Optional `--validate` runs
  jsonschema against every record.
- `../../seeds.jsonl`: 32 records (16 pairs × 2 halves). Every record
  signed by `claude-opus-4-7` in `difficulty_label.llm_assessment`;
  `human_review` set to null pending review.

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
- `004-tool-failure-recognition` — sibling line of inquiry probing a
  *different* calibration moment: when a tool is available and called
  but returns nothing useful (empty `results: []`, incompatible
  unit_convert, calculator-resistant expression, etc.), does the
  model recognize the tool failed and report it, or confabulate? This
  is interpretive (post-call) calibration vs. A1's anticipatory
  (pre-call) calibration. Inherits A1's palette, schema, KBs, and ID
  scheme; defines its own pair structure (`tool_helped` /
  `tool_insufficient` as the matched variation). Decision 8's
  empty-list-on-miss choice was made partly to enable this.

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
