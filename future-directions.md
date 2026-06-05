# Future directions

Cross-cutting ideas not yet attached to a specific study. Once an idea
grows enough scope to deserve its own study, move it into
`studies/NNN-slug/` and link back from here.

Per-study future work lives in the relevant `study.md` under its own
"Future directions" section — that's the right home when the idea is
already attached to a line of inquiry. This file is for orphans.

## Format

Every entry has:

1. A `###`-level title (short, descriptive).
2. One paragraph of prose describing the direction and why it matters.
3. **Two parallel YAML assessment blocks** along the capability axes:
   one filled by an LLM (signed with the model identifier), one filled
   by a human. Either may be `null` when not yet assessed. Both blocks
   use the same shape so they can be compared directly.

The dual-block design is deliberate. The capability axes are *the
research question*; treating LLM self-assessment and human assessment
as parallel evidence — rather than collapsing them — yields a
calibration dataset for the act of categorization itself. Over time,
divergence between the two blocks is a signal worth reading.

### Template

```yaml
llm_assessment:
  model: claude-opus-4-7        # which model made this call; required if block is non-null
  date: YYYY-MM-DD
  llm_capability: medium        # low | medium | high
  human_capability: high        # low | medium | high
  confidence: medium            # low | medium | high — how sure the assessor is
  reasoning: |
    Short prose. What about this direction makes it land where it
    does on each axis. Surface assumptions; flag if the framing
    feels brittle.

human_assessment: null          # fill same shape as llm_assessment when reviewed

divergence_notes: null          # short prose, only when human and llm disagree
```

Conventions:

- LLM assessment is filled at capture time when the model proposes or
  records a direction. Required when capturing via an AI-assisted
  workflow; optional otherwise.
- Human assessment is filled when the researcher reviews the entry.
  No deadline — entries can sit with only an LLM assessment for a
  long time.
- `divergence_notes` is null when blocks agree (or only one is
  filled). When they disagree, write one or two sentences on what's
  driving the gap.
- The same shape may eventually appear in per-study `study.md`
  Forward-looking sections; this file is just the orphan-direction
  home, but the convention transfers.

## Open ideas

### Literature-grounded research agents (search → relevance → implement)

When we move from *diagnosing* a small research agent (study 004) to
*improving* one, a core capability to test is whether the agent can use
the published literature: search for work relevant to its problem, judge
whether what it finds is actually relevant (not just keyword-matched),
extract the usable idea, and implement it correctly in its own
experiment. The literature on long-horizon agents and context
engineering turned out to be unexpectedly rich (ACE, ACON,
Context-Folding, the "lost in multi-turn" line, Anthropic's harness-design
work) — exactly the kind of material a self-improving researcher should
be mining. Each sub-skill is separately testable (retrieval quality,
relevance judgement, faithful implementation) and each is a distinct
point on the capability map. Likely its own study once study 004's
diagnostic framework is mature enough to plug a "read the literature"
tool into the loop.

```yaml
llm_assessment:
  model: claude-opus-4-8
  date: 2026-06-04
  llm_capability: medium
  human_capability: high
  confidence: low
  reasoning: |
    Retrieval and summarization are tractable for current LLMs; the hard,
    under-tested parts are relevance judgement (does this paper actually
    bear on my problem?) and faithful implementation of a method from a
    paper into running code. Splitting medium because the easy half is
    solved and the hard half is largely unmeasured for small models.
    Framing may be brittle: "implement an idea from a paper" bundles
    several capabilities that should probably be separated before scoring.

human_assessment: null

divergence_notes: null
```
