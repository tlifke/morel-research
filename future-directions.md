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

_None yet. Add new directions below using the format above._
