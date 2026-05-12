---
id: studies/001-tool-calibration
title: Tool calibration (matched-pair)
status: in-progress
parents: []
children:
  - studies/001-tool-calibration/investigations/001-foundations
  - studies/001-tool-calibration/investigations/002-difficulty-axes
  - studies/001-tool-calibration/investigations/003-bulk-generation
  - studies/001-tool-calibration/investigations/004-calibration-pilot
  - studies/001-tool-calibration/investigations/005-tool-spec-optimization
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

### Routing classifier from the capability boundary

The 4B IT pilot showed that the model's tool-call behavior is highly
deterministic per record — failures are systematic, not stochastic.
That makes the per-prompt behavior potentially *predictable*: a
small classifier trained on prompt features could predict whether a
target model will under-call, over-call, or correctly invoke its
tools. Two uses:

1. **Quality assurance**: catch likely failures before deploying.
2. **Routing**: send prompts predicted to fail to a larger / more
   capable model, leaving the small model on prompts where it's
   reliable. Plausible cost/latency win if the boundary is
   characterizable.

The pilot data already shows the boundary is sharp: 4B IT does well
on calculator / datetime_now / unit_convert / sports-and-finance
lookups; struggles systematically on `user_knowledge_lookup` and
several `python_execute` verification cases. A classifier trained on
the A3 bulk corpus once available would have plenty of signal.

```yaml
llm_assessment:
  model: claude-opus-4-7
  date: 2026-05-12
  llm_capability: high
  human_capability: medium
  confidence: medium
  reasoning: |
    Classifier-on-prompt-features is LLM-friendly work — feature
    engineering, training, evaluation. The harder question is
    whether the boundary generalizes: does a classifier trained
    on A3 corpus prompts transfer to in-the-wild prompts? That's
    a question of corpus representativeness more than
    classification skill, and probably needs human judgment to
    frame. Confidence medium because the value depends entirely
    on whether the routing/QA application is real for someone
    using these models in production.

human_assessment: null

divergence_notes: null
```

### IT vs. base: does tool use live in the post-training layer or deeper?

Phase A4 is initially scoped to IT models only (Gemma 3 4B IT and 12B
IT). Base (pretrained, non-instruct) models are deferred — they're
not trained on a chat template or tool-call format, so grading them
on the same seeds needs a different prompt formatter and a more
permissive parser. But there's a mechanistic-interpretability
question worth probing once that infrastructure exists:

**Hypothesis:** if there are dedicated "tool use" circuits in a model,
they should show up in both IT and base variants — instruction
tuning would surface and condition them, not create them. If
post-training instead introduces tool-use behavior wholesale, only
the IT models would exhibit it on this corpus.

Resolution depends on what post-training actually does — full
fine-tuning that can rewrite deep-layer circuitry (LoRA + extensive
SFT/RLHF on tool-use traces could in principle reshape deeper than
"just the last few layers"), or shallower adaptation. Open question
worth a separate sub-investigation that runs both IT and base on the
same matched-pair corpus and looks at: (a) raw tool-call rates,
(b) activation patterns on tool-call vs. no-tool-call inputs (via
NLA-style techniques, given Anthropic's NLA paper at A1's runtime
anchor), (c) targeted ablations of identified circuits.

```yaml
llm_assessment:
  model: claude-opus-4-7
  date: 2026-05-11
  llm_capability: medium
  human_capability: high
  confidence: medium
  reasoning: |
    Behavioral comparison (a) is LLM-easy once the base-model
    harness exists. The interpretability work (b, c) is squarely
    human-driven research; LLM can run pipelines and surface
    correlations but the framing of "what counts as a tool-use
    circuit" is a research question that needs human judgment.
    Confidence medium because the upstream question — does
    post-training rewrite deep layers — is itself contested in the
    field; the experiment design depends on which prior the human
    starts from.

human_assessment: null

divergence_notes: null
```

### How performative are the per-tool difficulty axes? (probable sibling investigation)

Investigation 002 freezes a set of per-tool difficulty axes
(`difficulty_axes_proposal.md`) and uses them to label seeds. A
natural follow-on is to *test the axes themselves*: how well do the
axis-derived difficulty predictions correlate with empirical
calibration (`difficulty_calibrated.success_rate`)? If the axes are
performative — i.e. weakly related to actual model performance —
that's signal about what makes prompts hard that doesn't reduce to
the structural dimensions we picked. Likely lives as its own
sub-investigation under study 001, sometime after Phase A4 has
collected enough empirical signal.

```yaml
llm_assessment:
  model: claude-opus-4-7
  date: 2026-05-11
  llm_capability: medium
  human_capability: high
  confidence: medium
  reasoning: |
    LLM can run the correlation analysis and surface axis-by-axis
    predictive power once empirical data exists. Designing the
    follow-on experiment (which alternative axes to try if these
    fail) is more judgment-laden — human-led. Confidence medium
    because the result depends on having enough calibration data,
    which is a separate prereq.

human_assessment: null

divergence_notes: null
```

### Obscurity threshold for `general_knowledge_lookup` topic_salience

The `general_knowledge_lookup` difficulty axes (proposal) include a
`topic_salience` dimension with values `mainstream | niche | obscure`.
The LLM curator's intuition about what's "mainstream" is itself
worth probing — concrete reviewer prompt during pair-12 review:
"how obscure would a soccer match have to be to not be considered
mainstream? EPL? Championship? MLS? U18 US Mens Team? USL? Europa
League?" Likely a small mini-investigation: enumerate sports at
decreasing audience size, prompt a target model with a question about
each, measure where the model's confidence in answering without lookup
breaks. That breakpoint defines `mainstream` for that model.

```yaml
llm_assessment:
  model: claude-opus-4-7
  date: 2026-05-11
  llm_capability: medium
  human_capability: medium
  confidence: medium
  reasoning: |
    The probe design (sweep audience size) is LLM-feasible. The
    judgment about which sports to include (and how to map them to
    audience proxies — TV viewership? Wikipedia article length?
    Search interest?) is mixed-difficulty. Confidence medium because
    "audience size" is a hidden axis that may itself need empirical
    definition rather than a-priori ordering.

human_assessment: null

divergence_notes: null
```

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

## Observations carried forward from the A4 pilot (Gemma 3 4B IT, 2026-05-12)

First pilot run of the calibration harness produced findings worth
flagging at the study level (full breakdown in
`investigations/004-calibration-pilot/investigation.md`, with the
follow-on prompt-engineering work in
`investigations/005-tool-spec-optimization/`):

- **4B IT is decisive but mis-mapped.** 23/36 records perfectly
  calibrated, 11/36 perfectly miscalibrated, 2/36 boundary. Behavior
  is highly stable per record (same output 20/20 trials at
  temperature 0), so failures are systematic — not noise.
- **The failure modes are heterogeneous.** Five distinct patterns:
  tool-blind deferral, wrong-tool selection, confabulation, correct-
  without-verification, and trivial over-call. The current binary
  scoring (`success` vs `error_type`) conflates several of these.
- **Tool-blind deferral on `user_knowledge_lookup`.** All three
  hard halves (anniversary, daughter's school, Aunt Nina) failed
  20/20 in the initial pilot — model correctly recognizes it
  can't know personal info but doesn't invoke the persona-lookup
  tool that's in its available set. **Follow-on A/B experiment
  showed this is defeatable at the prompt layer**: replacing the
  tool description with prescriptive language ("REQUIRED whenever
  the user asks about themselves...") shifted success from 0/20
  baseline to 60/100 at n=10. Naming changes and epistemic
  framing alone did NOT work. Revised hypothesis: refusal prior
  is stronger than tool-use prior unless tool-use is made
  imperative. Practical implication: sweep prescriptive-language
  upgrades across the other tool descriptions before A3 bulk
  generation. See `investigations/002-difficulty-axes/
  investigation.md` Results section for full breakdown.
- **n=10 is sufficient for 4B IT on this corpus.** 34/36 records
  bucket-stable from n=5; n=20 added zero new bucket assignments.
  Future routine runs default to n=10 with n=20 reserved for known
  boundary cases.

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
