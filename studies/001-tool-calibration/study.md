---
id: studies/001-tool-calibration
title: Tool calibration (matched-pair)
status: in-progress
parents: []
children:
  - studies/001-tool-calibration/investigations/001-foundations
related: []
axes:
  llm_capability: medium
  human_capability: high
tags:
  - tool-use
  - calibration
  - matched-pair
created: 2026-05-11
updated: 2026-05-11
---

# Study 1 — Tool calibration (matched-pair)

## Question

When do LLMs reach for tools, and when *should* they? We want to probe the
gap between an LLM's tool-call behavior and the behavior a calibrated agent
would exhibit, using matched-pair prompts that vary one factor at a time
(difficulty, affordance) so that we can attribute behavior changes cleanly.

## Why matched-pair

A pair holds everything fixed except the dimension under test. A Type A
pair varies *task difficulty* while the tool affordance stays constant; a
Type B pair varies the *available tools* while the task stays constant.
Single-variable manipulation lets us avoid confounds like length, register,
or keyword leakage.

## Investigations

- `001-foundations` — define the tool palette, metadata schema, ID scheme,
  system-prompt structure, and a seed prompt set of 10–20 hand-curated
  matched pairs. In-progress.

Planned follow-ons (not yet investigations):

- `002-difficulty-axes` — define per-tool difficulty axes that produce
  reliable model failures at the "hard" end and reliable successes at the
  "easy" end (corresponds to Phase A2 in the source plan).
- `003-bulk-generation` — generate a larger prompt corpus from the seed set
  and verified axes (Phase A3).
- `004-empirical-calibration` — run the corpus through target models, log
  call/no-call decisions, fit calibration curves (Phase A4).
- `005-cross-model-eval` — sweep across model families and harness
  variations.

## Repository policy

- Prompt corpora live under `data/` and are checked in until size becomes
  an issue. Model output logs (likely large) will be gitignored and
  archived externally; only summaries and aggregates check in.
- Figures regenerate from scripts in `scripts/` and check in alongside.
- Per-investigation seed/spec files (palette, schema, seed prompts) check
  in.

## Forward-looking

This study is the substrate for several downstream questions:

- How does tool calibration shift with model size, RLHF generation, and
  prompting style?
- Does providing more tools improve or degrade calibration?
- Is there a "tool-use temperature" — a single parameter that captures an
  agent's eagerness to delegate?
- **Tool-failure recognition** (planned as `investigations/004-tool-failure-recognition`):
  when a tool is called but returns nothing useful, does the model
  recognize the tool failed and report "I can't" — or confabulate?
  This is a distinct *post-call* calibration moment, complementary to
  the pre-call calibration A1 probes. Inherits the A1 substrate
  (palette, schema, KBs, IDs); pair variation is `tool_helped` /
  `tool_insufficient`.

### Categorization variance on human_feasibility (blog-sized writeup)

The `human_feasibility` label on each seed (Decision 18) is a
modal-adult hypothesis, not a universal claim. During seed review the
human reviewer (born 1995) flagged that they don't actually know the
1966 World Cup winner despite the trivial half of pair 12 being
labeled `unaided`. That disagreement is itself signal — it bounds how
much an LLM's "underperformance" on a prompt should be read as model
deficiency vs. how much is just below the modal-adult baseline. Worth
a short blog post / mini-investigation surveying a handful of
reviewers across the seed corpus and reporting variance per pair.

```yaml
llm_assessment:
  model: claude-opus-4-7
  date: 2026-05-11
  llm_capability: high
  human_capability: medium
  confidence: medium
  reasoning: |
    LLM-feasible: small survey design, light analysis, ~20 reviewers
    × 32 seed halves of unaided/aided labels. The hard work is
    recruiting and the prose interpretation, both of which a human
    drives. Confidence medium because the framing matters — the
    interesting writeup compares LLM-labeled feasibility vs.
    distribution of human-reported feasibility, which requires
    careful question wording.

human_assessment: null

divergence_notes: null
```

## Open questions

- How aggressively should the seed set cover edge cases vs. mainline?
  Phase A1 targets 60/40 common/edge; revisit after seeing model behavior.
- Should we publish the schema externally so other research can reuse it?
  Probably yes once stable.
- `metadata.schema.json` is currently strict (`additionalProperties:
  false`) — revisit when the corpus exceeds ~500 records or once
  bulk generation (A3) is producing records routinely. If schema-bump
  friction starts outweighing typo-protection, loosen at that point
  and use a separate `extra:` object for analysis-only annotations.

## Observations carried forward from A1

- **Curator-LLM arithmetic errors validate seed design.** During
  Phase A1 seed prep the curator-LLM (claude-opus-4-7) made a
  mental-arithmetic error on a seed it was simultaneously annotating
  (claimed 4782 × 1847 = 8,832,754; actual 8,832,354). Caught on
  python self-check. The seed is therefore not testing an artificial
  difficulty — it's testing a real one, since the curator-LLM failed
  exactly the way a calibrated agent should recognize it would and
  reach for the calculator. See Decision 17 in
  `investigations/001-foundations/investigation.md`. Worth tracking
  across the study: when the curator makes the same kind of error a
  target model would, the prompt is well-calibrated for the cognitive
  moment it claims to probe. Complementary to Decision 16 (curator-
  LLM confabulated when it should have used WebSearch) — both
  observations reinforce that the study's own scaffolding work is a
  preview of the calibration failure modes it intends to measure.
