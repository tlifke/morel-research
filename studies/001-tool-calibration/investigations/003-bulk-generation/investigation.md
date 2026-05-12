---
id: studies/001-tool-calibration/investigations/003-bulk-generation
title: Bulk corpus generation (Phase A3)
status: in-progress
parents:
  - studies/001-tool-calibration
children: []
related:
  - studies/001-tool-calibration/investigations/001-foundations
  - studies/001-tool-calibration/investigations/002-difficulty-axes
axes:
  llm_capability: high
  human_capability: low
tags:
  - bulk-generation
  - corpus
  - axes
aliases:
  - A3
  - phase-a3
created: 2026-05-11
updated: 2026-05-12
---

# Investigation 3 — Bulk corpus generation (Phase A3)

## Scope

Given the difficulty axes frozen in A2 (Decision 1 in
`../002-difficulty-axes/investigation.md`), generate a larger corpus
of matched-pair prompts at *known* difficulty coordinates. The A1
seed set is 18 hand-curated pairs; A3 expands to a target size of
~200–500 pairs covering the tool × axis-value grid more densely.

Goals:

1. For each (tool, axis-value combination), produce N matched pairs
   that hit the predicted difficulty bucket.
2. Maintain matched-pair integrity (single-variable manipulation per
   pair) automatically.
3. Validate every generated record against the schema and the
   canonical_domains convention.
4. Reach distribution targets — Type A:B ≈ 50:50, common:edge per
   tool, all 5 difficulty bands populated.

A1 design substrate (palette, schema, KBs, ID scheme, system prompts)
is reused as-is. A3 only adds the generation pipeline + the corpus.

## Methods (planned)

1. **Axis-to-prompt-template mapping.** For each tool, build a tiny
   library of prompt templates parameterized by axis values. E.g.
   calculator: `"Compute {a} {op} {b}{precision_clause}"` with
   `{a}, {b}` drawn from digit-count buckets and `{op}` drawn from
   the operation axis.

2. **Generator + validator loop.** For each (tool, target difficulty,
   target axis values), generate N candidate pairs; validate each
   against the schema; re-roll on failure. LLM-led drafting with
   programmatic validation.

3. **Spot review.** Sample ~5% of generated pairs for human review
   (versus 100% for A1 seeds). Track override rate per tool — high
   override rate means the axes or templates need adjustment.

4. **Difficulty hypothesis recording.** Each generated record gets
   `difficulty_label` per the axis prediction; `human_review` left
   null pending Phase A4 empirical calibration.

## Decisions

> **Decision 1 — `expected_tool_call` convention canonicalized** (2026-05-12)
> The A3 subagent introduced a more conservative convention: a
> warranted half's `expected_tool_call` is True only when
> `difficulty_label.value ∈ {medium, hard, extreme}` — trivial- and
> easy-difficulty warranted halves get False. A1 hand-curated seeds
> happen to satisfy this convention already (every A1 warranted half
> is medium-or-higher), so no A1 retrofit is needed. Adopted as
> canonical across the study; future generations and analyses
> follow this rule.

> **Decision 2 — datetime_now × extreme records relabeled to python_execute** (2026-05-12)
> 9 records originally generated as `tool_target: datetime_now` at
> extreme difficulty (cross-timezone scheduling with DST; "200
> business days excluding US federal holidays"; etc.) actually
> require python_execute — `datetime_now()` returns the current
> ISO timestamp but doesn't do date arithmetic. **Patched
> `bulk_seeds.jsonl` in place** to flip `tool_target` to
> `python_execute`. All records still validate against the schema.
> Note: the record IDs still contain `datetime_now` in the {tool}
> slug — this is an accepted ID-vs-field inconsistency (the ID is
> just an identifier; downstream code uses the `tool_target` field
> for dispatch). Subsequent corpora should generate IDs to match.
>
> Post-relabel distribution: `python_execute × extreme` rose from
> 13 to 22 records. `datetime_now × extreme` is now empty.

> **Decision 3 — UKL composite-query amendment to 002 axes** (2026-05-12)
> The 5 UKL hard/extreme records (composite multi-field queries)
> are accepted as an axis-refinement and codified in Decision 1a
> of `../002-difficulty-axes/investigation.md`. Reviewer accepted
> the extension; A2 proposal's medium cap on UKL is superseded.

## Known limitations (added 2026-05-12)

- **GKL trivial siblings cycle over ~8 well-known facts** (1966
  World Cup, Hamlet's author, etc.) across many pairs. Matched-pair
  structure is sound — the warranted half varies per pair, the
  trivial half is consistent within its rotation pool. But the
  trivial-side variety is low. If Phase A4 grading reveals model
  behavior on the trivial halves is dominated by these specific
  facts (likely 100% across all of them since they're well-known),
  expand `_GKL_TRIVIALS` and regenerate the trivial-half slot of
  affected pairs. Cost is low.

## Results

### Pipeline (2026-05-12)

Three artifacts under this directory:

- `axis_templates.py` — per-tool prompt-template library. Each tool
  exposes a generator function that takes a random source and an
  axis-value dict, returns warranted + trivial prompts plus
  difficulty/reasoning/feasibility metadata. Lookup tools
  (`general_knowledge_lookup`, `user_knowledge_lookup`) are anchored
  to the existing real KBs — every warranted prompt references an
  existing entry id/field. No new KB entries were created.
- `bulk_seeds_spec.yaml` — declarative spec. 32 generation cells across
  the six tools, weighted toward calculator (10 cells, 47 pairs),
  general_knowledge_lookup (3 cells, 29 pairs), and user_knowledge_lookup
  (3 cells, 24 pairs). Each cell carries pair_type, system_prompt_ids
  for the two halves, register triplet, frequency_class, and target count.
- `generate.py` — runner. Reads the spec, expands cells via
  `axis_templates`, validates against the A1 schema (strict,
  additionalProperties: false), enforces anti-leakage on Type A trivial
  halves, and writes `../../bulk_seeds.jsonl` plus `spot_review.yaml`.

### Corpus output

`studies/001-tool-calibration/bulk_seeds.jsonl`:

- **183 matched pairs / 366 records.**
- All records validate against `metadata.schema.json` (strict).
- All records carry `source: llm_generated`,
  `difficulty_label.llm_assessment.{model,date} = (claude-opus-4-7, 2026-05-12)`,
  and `human_review: null` pending Phase A4 / spot review.

Distribution per (tool × difficulty.value):

| tool                          | trivial | easy | medium | hard | extreme |
|-------------------------------|---------|------|--------|------|---------|
| calculator                    | 37      | 0    | 13     | 24   | 44      |
| python_execute                | 14      | 3    | 12     | 14   | 13      |
| datetime_now                  | 8       | 5    | 3      | 9    | 9       |
| unit_convert                  | 19      | 3    | 12     | 16   | 2       |
| general_knowledge_lookup      | 17      | 0    | 5      | 31   | 5       |
| user_knowledge_lookup         | 14      | 0    | 29     | 2    | 3       |

(values are *records*, not pairs; trivial counts include the
trivial-sibling halves of every Type A pair.)

- **Type A : Type B = 106 : 77 pairs** (≈58:42), within the 50:50 ±10%
  target.
- **frequency_class common : edge = 108 : 75 pairs** (≈59:41), matches
  the 60:40 target.
- All five difficulty bands populated.

### Anti-leakage

The runner enforces a hard rule: Type A trivial halves
(`condition == "tool_trivial"`) must not contain the surface keywords
`calculator`, `compute`, `search`, or `lookup`. The check passes for
all 183 pairs.

Type B `no_tools_available` halves are *exempt* by design — Type B
holds the user_prompt constant across halves to manipulate only the
affordance, so leakage keywords on those halves are inherited from
the warranted half (matching the A1 hand-curated convention; see
`seeds.jsonl` pair `calculator-math-hard-mult_affordance-001`).

### Skipped / infeasible combinations

- **unit_convert × extreme** — only two entries (amu → kg, US fl_oz → imperial
  fl_oz). The proposal's `precision_decimals = 6+` bucket interacted
  with `unit_system = cross_system_specialty` to land here, but there
  are not many natural prompts at that intersection; we cap at 2 cells
  rather than fabricate awkward conversions.
- **datetime_now × trivial** — the proposal's worked example flagged
  this: datetime_now's difficulty floor is `easy` (current date/time
  request) since the calibration point is *knowability without runtime
  info*, not date math. Trivials with in-prompt anchor land at
  `trivial` for the sibling but no "trivial warranted half" cell exists.
- **user_knowledge_lookup × hard, extreme** — extended `_UKL_ENTRIES`
  with derived (two-field) and composite (three-field) queries that
  reuse existing persona fields. Three composite extreme records exist;
  more would require new persona fields (deferred — bulk corpus aims
  to stay coherent with A1's Maya Patel persona without amending it).
- **calculator add_sub at operand_digits=1** — original spec cell
  removed: the "warranted" half would have been "Compute 9 + 3" which
  is trivial, making the matched pair structurally degenerate. Bumped
  to `operand_digits=4, add_sub`.

### Spot review

`spot_review.yaml`: 10 pairs (~5% of 183) selected via the runner's
sampler. Selection logic biases toward boundary cases:

- ~25% from the `extreme` difficulty band (boundary at the top of the scale)
- ~25% from Type B affordance pairs (the refusal-vs-fabrication framing
  is the trickiest call)
- ~25% from KB-grounded pairs (verify that entry resolves correctly under
  the live KB ranking)
- Remaining random across the corpus

### `expected_tool_call` convention

For bulk records, the warranted-half `expected_tool_call` is True only
when `difficulty_label.value ∈ {medium, hard, extreme}`. For trivial
and easy warranted halves it is False — a calibrated agent wouldn't
call on those, so the metric matches reality. This differs slightly
from the A1 seed convention where every "tool_warranted" half is True
by curation choice; the bulk corpus is more conservative.

### Things to surface to the human

1. **GKL trivial halves repeat across cells.** Each gkl cell shuffles
   the trivial-list independently, so the same eight well-known
   historical facts recur as siblings across many gkl pairs. This is
   fine for matched-pair structure (the warranted half differs) but
   the trivial-side population isn't diverse. Consider expanding
   `_GKL_TRIVIALS` if downstream analysis wants more trivial-side
   variety.
2. **UKL derived/composite queries** (hard, extreme bands) are
   author-introduced compositions over existing persona fields. They
   were not in the proposal's UKL axis sketch (which capped at
   medium); flagging so reviewer can accept or reject as part of axis
   refinement.
3. **datetime_now extreme** uses a cross-timezone + DST prompt and a
   "200 business days excluding US federal holidays" prompt. Both are
   genuinely python-solvable but exceed pure `datetime_now()` — they
   structurally probe whether the model recognizes `datetime_now`
   alone isn't enough. May warrant relabeling `tool_target` to
   `python_execute` or accepting the mismatch as a calibration signal.
4. **calculator extreme band over-represented** (22 pairs) relative
   to the proposal's caps. Comes from the operand_digits×precision
   interaction (band-additive arithmetic). Within the proposal's "cap
   shifts at +2" rule but still produces a heavier tail than the
   distribution targets suggested. Recommend the reviewer either
   accept or trim spec.

## Forward-looking

- Phase A4 — empirical calibration runs against target models to
  populate `difficulty_calibrated`. The bulk corpus is the substrate
  for A4.
- Sibling investigation testing axes performativity (study.md
  Forward-looking) — runs on the A3 corpus once A4 produces enough
  signal.

## Things to flag

- Generated prompts risk being too template-formulaic; matched-pair
  curation specifically wanted *natural* prompts that probe natural
  cognitive moments. May need diversification via paraphrase.
- Axis interactions: if axes don't factorize cleanly, bulk
  generation by axis-value combination over-counts or
  under-represents certain regions of difficulty space.
- Anti-leakage: avoid surface keywords ("calculator", "search",
  "compute") in user_prompts that bias models toward calling vs.
  not calling. A1 source brief flagged this as a hard constraint.

## Limitations

- Heavy LLM authorship invites the same fact-grounding /
  arithmetic-error failure modes the curator hit in A1 (Decisions 16,
  17). Mitigations: every quantitative claim in generated prompts
  goes through python first; every general-knowledge prompt resolves
  to an entry in `general_knowledge_real.json` (Decision 19).
