# Platform notes — carried forward for a future body of work

Running record of things the file+CLI era has proven (or demanded) that
the eventual platform — the morel-primordia frontend over this repo's
contracts — should absorb. Not a build plan; a memory the platform work
starts from. Append as discoveries happen; date entries.

## Interaction patterns proven in review artifacts (2026-07-27)

- **Progressive disclosure**: title + one-sentence summary + human_needed
  visible; everything else behind a dropdown. Detail-on-demand engages
  the reviewer instead of dissuading them (Tyler, round-2 review).
- **Reviewer layer separate from proposal**, toggleable, off by default —
  one artifact was trying to be two vehicles (agent's proposal + reviewer
  commentary); splitting them fixed it.
- **Clickable dependency graph**: wave-layout DAG at top of a
  decomposition, nodes jump to the ticket detail (added round 3).
- **Per-ticket HTML card as complexity limiter** — if it doesn't fit one
  simple card, decompose further (human-understanding constraint).
- **Phone-first gate approval**: reviewer is often on a phone,
  asynchronously; gates capture rationale + would-change-mind verbatim.
- **Downloadable self-contained HTML checked into the repo**; no external
  hosting. Charset meta is mandatory (Android Latin-1 mojibake incident).

## Mechanisms to absorb (2026-07-27)

- Gates as data; cost ceilings enforced at dispatch; no hidden retries.
- **human_needed wrongness marking**: reviewer can mark any declaration
  or agent choice wrong-with-reason; accumulated approve/reject
  rationales become a principles corpus that later powers a reviewer
  (trained classifier or LLM prompted with the principles). Choices like
  round-3's meta-agent selection are review-layer territory — don't
  overtune drafting prompts to force them.
- **Handoff resolver (K/Q/V shape, v1.2 proposal)**: producers declare
  keys (produces), consumers declare queries (consumes), the artifact is
  the value; edges are derived by matching, orphaned keys and unmatched
  queries are surfaced. See ticket-system.md v1.2.
- **LLM-selection as recorded prediction**: every ticket carries
  `agent_explanation` — the drafter's own reasoning for its
  assignee-class and any in-task model choices. Joined with provenance
  outcomes this becomes empirical model-selection data (which
  explanations predicted success); until then it makes the choice
  reviewable instead of implicit.
- Idea backlog as a first-class store — agent memory (including
  non-Anthropic and weaker models) is not durable.
- Resource elicitation as a structured flow (Skill first, platform form
  later); resources.md is the contract it fills.
- Decomposition rounds as comparable experiments: contracts versioned
  verbatim, outputs archived per round, review pages generated from
  records.

## Tech-stack notes (2026-07-27)

- Current: pure static HTML generated deterministically by Python
  scripts from YAML records. Right for artifacts-in-repo: zero build
  step, opens anywhere including phones, diffs in git. Vanilla JS covers
  toggles and anchors comfortably.
- The line where HTML stops being enough: inline editing, wrongness
  marking, live drain status, filtering across many tickets, auth. At
  that point a typed frontend (TypeScript; the existing Vercel/Next.js
  setup in morel-primordia) pays for itself. Until then TS would add a
  build step with no user-visible gain.
- Portability rule either way: all state stays in YAML/JSON records in
  this repo; renderers (Python now, app later) are views. If the app
  needs a field, the schema here grows first.
