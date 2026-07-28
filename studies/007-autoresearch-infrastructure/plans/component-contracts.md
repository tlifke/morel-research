# Component contracts (v0)

Contract-level plans for the components the walkthrough demands but does
not yet demand deeply. Each states its boundary: inputs, outputs, minimal
local form, and what is explicitly deferred. Depth is added only when a
live investigation hits the boundary and finds it insufficient.

Author: claude-fable-5, 2026-07-26. Human-unreviewed draft.

## 1. Literature system (paper cards)

- **In:** a paper (URL/PDF) + the standing constraints doc.
- **Out:** a paper card (`literature/<arxiv-id>-<slug>.md`) with claims,
  methods, reproducibility assessment, relevance links, citation edges,
  and an assumptions list; signed by author model, `human_reviewed` flag.
- **Minimal form:** the schema instantiated by the Better Harnesses card;
  cards at study level, promoted to a repo-level `literature/` when two
  studies want the same card.
- **Deferred:** graph database, automatic citation crawling, researcher
  entities. Citation edges stay as text in cards until ~10 cards exist
  and a real retrieval need appears.

## 2. Constraints doc (new, small, load-bearing)

- A single `constraints.md` at study level: hardware (3080 12GB, desktop
  via Tailscale), standing budget policy, available model fleet, judge
  panel availability. Paper cards and replication plans read from it so
  reproducibility assessments never hardcode stale facts.
- **Deferred:** anything fancier than one markdown file.

## 3. Reproducibility assessment (replication plans)

- **In:** a paper card + constraints doc.
- **Out:** a replication plan: testable claims, substitutions, PoC slice,
  risks, **fidelity contract** (pre-registered success criteria per
  claim), deviation log (append-only, written at decision time).
- **Minimal form:** one markdown file with a YAML fidelity block per
  claim; lives in the investigation.
- **Deferred:** scoring papers for reproducibility in the abstract (we
  assess only papers we intend to replicate).

## 4. Gated phasing

- Absorbed into the ticket system: gates are data in `plan.yaml`
  (approver, date, rationale, would-change-mind), phases are
  Derisk → Pilot → Scale → Report with per-phase budgets.
- **Deferred:** a standalone phasing component. If gates outgrow
  plan.yaml, that's the signal.

## 5. Artifact layer (agent-facing + human-facing)

- **In:** provenance records + raw run outputs (trajectories, logs).
- **Out:** (a) agent-facing: untouched JSONL + machine-readable results
  records; (b) human-facing: comparison artifacts and gate summaries
  rendered *from* the records by checked-in scripts — same source, two
  views, so they cannot drift.
- **Minimal form:** a results-record schema (YAML) defined when ticket
  004 (first baseline run) produces the first real results; renderers
  reuse existing conventions (compare_runs-style grids, agent-trace-report
  skill, morel branding).
- **Measured empirically:** downstream-agent success for (a); Tyler's
  comprehension checks for (b). A failed check is a recorded result that
  triggers artifact revision.
- **Deferred:** artifact templates beyond what the derisk needs; any
  hosted gallery.

## 6. Comprehension check

- **In:** a closing phase + its results records.
- **Out:** a short structured file: Tyler's answers (what was tested /
  found / surprising / would-tell-someone), written without reading raw
  traces, plus a score against the records and a list of artifact fixes
  if it failed.
- **Minimal form:** a markdown template, ~5 minutes to fill; scored by an
  agent, sampled-checked by Tyler (mirrors curator convention).
- **Deferred:** anything statistical until there are ≥5 checks.

## 7. Frontend (morel-primordia)

- **Contract only:** the frontend is a remote view/editor of ticket files
  and gate records, communicating exclusively through git commits to this
  repo. Any logic it wants must exist here as schema or script first.
- **Deferred entirely** until the derisk shows the file+CLI loop working
  and identifies which interaction actually needs the phone (most likely:
  reading a gate summary and approving with rationale).

## 8. Harness surface (skills, CLAUDE.md, memory)

- Not a module but a convention: skills, CLAUDE.md rules, and memory
  entries used by working agents are infrastructure under study. Edits to
  them on behalf of this study are interventions — recorded in the
  relevant investigation's Decisions log with what failure motivated them.
  Existing repo rules are revisable through the same door.

## Things I made up that you should review

1. The constraints doc as its own component (it kept appearing as a
   dependency, so I named it).
2. Fidelity contracts as pre-registered YAML per claim — the strongest
   process commitment in here; it's the anti-tinkering mechanism, but it
   adds friction to plan-writing.
3. Comprehension checks scored by an agent with sampled human review.
4. The promotion rules (cards to repo level at 2 studies; graph at ~10
   cards; standalone phasing when plan.yaml groans) — thresholds are
   guesses, the trigger-on-demand principle is the point.
