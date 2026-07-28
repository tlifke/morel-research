# Walkthrough — the Better Harnesses replication through the system

This is the overarching plan for study 007. It traces one real user story —
replicating "Better Harnesses, Smaller Models" (arXiv 2607.08938) under a
3080 + $20 constraint — through the system we intend to build. Every data
structure or contract the story demands is marked **[DEMANDS: ...]**; a
component earns design depth only if something here demands it. Human gates
are marked **[GATE]**.

Author: claude-fable-5, 2026-07-26. Human-unreviewed draft.

## Actors

- **Tyler** — approves gates, owns publishable prose, is the ground truth
  for comprehension measurements.
- **Frontier agent (Claude)** — paper carding, reproducibility assessment,
  task decomposition, meta-agent roles, artifact generation.
- **Small agents (local fleet via ollama / 3080)** — the objects of study
  and, where they prove capable, executors of leaf tickets.
- **The repo** — the shared state. No databases; files are the system.

## Stage 0 — Intake

Tyler encounters the paper and sends it into the system (today: tells
Claude; later: shares a URL from the phone frontend).

An agent reads the paper and produces a **paper card**: claims with
evidence, methods, resources, reproducibility assessment under our standing
constraints, relevance links to existing studies, citation edges, and an
assumptions-to-review list. Cards are signed by their author model and
marked human-unreviewed until Tyler touches them.

**[DEMANDS: paper-card schema; a standing "our constraints" document the
assessment reads from (hardware, budget, model fleet) so cards don't
hardcode stale facts.]**

*Status: done for this story —
`literature/2607.08938-better-harnesses-smaller-models.md`.*

## Stage 1 — Reproducibility assessment → replication plan

From the card, an agent drafts a **replication plan**: which claims are
testable under constraints, what must be substituted (models, cost
metrics), the recommended PoC slice, risks, and an explicit
fidelity contract — what "successfully replicated" will mean, stated
before any experiment runs (e.g. "directional confirmation of claim 1 on
one task-SLM pair: optimized harness improves accuracy by ≥20 points over
generic harness, within one $20 optimization run").

**[DEMANDS: replication-plan schema with a machine-checkable fidelity
contract; deviation log format (every substitution recorded at decision
time, not reconstructed later).]**

**[GATE — Derisk approval.]** Tyler reads the plan (phone-sized artifact),
writes 1–3 sentences: why approved / what would change his mind. That text
is stored with the gate record. Nothing downstream exists until this gate.

## Stage 2 — Decomposition → ticket tree

An agent decomposes the approved plan into **tickets**: bounded units with
acceptance criteria, dependencies, an assignee class (human /
frontier-agent / small-agent), and a cost ceiling. For this story, the
derisk phase decomposes roughly as:

1. Clone and audit the migration-analysis repo — does it contain the task
   pipelines or only the optimizer? (small-agent candidate)
2. Stand up software-agent-sdk locally; run one budget-approval instance
   with a generic harness and a frontier model to verify the environment.
3. Verify which SLMs actually fit/run on the 3080 (measure, don't
   estimate). (small-agent candidate)
4. Run the generic-harness baseline for the chosen SLM on a reduced
   instance set.
5. One harness-optimization run under budget; log all trajectories.
6. Compare against the fidelity contract; produce the comparison artifact.

Each ticket names which claim of the paper card it serves. Tickets that no
claim demands don't get created.

**[DEMANDS: ticket schema + tree layout + status lifecycle — the deep spec,
see `ticket-system.md`.]**

**[GATE — plan-of-record.]** Tyler approves the tree (or edits it) before
any ticket is drainable. Approval sets each ticket's cost ceiling.

## Stage 3 — Drain

A local runner walks the tree: tickets whose dependencies are met and whose
gate is satisfied become `ready`; the runner dispatches each to its
assignee class and records the outcome. Human-assigned tickets just sit
visible until Tyler does them — the system tracks his work identically to
agent work (this is the delegation dataset accumulating).

Every completed ticket records provenance: who/what executed it, model id,
cost spent vs ceiling, artifacts produced, and a verdict against its
acceptance criteria. Failures don't auto-retry; they surface.

**[DEMANDS: drain semantics (CLI runner), provenance record, cost
metering. Also: the runner dispatching to agents is exactly where new
Skills get written — skills, CLAUDE.md rules, and memory are part of the
infrastructure surface under study here, versioned and revisable like any
other component; when a handoff fails, the fix may be a skill edit, and
that edit is an experimental intervention worth recording.]**

## Stage 4 — Artifacts

Two artifact families, deliberately separate because the paper's own
Lesson 1 says agents and humans want opposite things:

- **Agent-facing:** raw trajectories (JSON/JSONL), full logs, machine-
  readable results. Never summarized for storage; summarization is a view.
- **Human-facing:** small comparison artifacts (per feedback conventions:
  comparison grids, trace reports), phone-readable gate summaries.

Both are generated from the same underlying records so they can't drift
from each other.

**[DEMANDS: results record schema (the single source both views render
from); a place for standing, comparable artifacts rather than one-offs —
templates keyed to record schemas.]**

## Stage 5 — Comprehension check

Before the phase closes, Tyler answers a short structured check (what was
tested, what was found, what surprised us, what would he tell someone
else) *without looking at raw traces*. Scored against the record. If he
can't, the human-facing artifacts failed and get revised — that result is
data for study 007, not just process friction.

**[DEMANDS: comprehension-check format + scoring convention. Cheap: a
5-minute form, not a ceremony.]**

**[GATE — phase gate.]** Derisk → Pilot → Scale → Report, each gated the
same way: results vs fidelity contract, comprehension check passed, next
phase's cost ceiling set. Pilot = single full optimization run with clean
logging (echoes single-seed-transparency-first). Scale = only what the
Pilot's open questions justify. Report = Tyler writes the one-pager;
Claude scaffolds and gives feedback only.

## Component demand summary

| Component | What this story demands | Depth earned |
|---|---|---|
| Ticket system + drain | Stages 2–3 entirely | Deep spec now |
| Paper cards / literature | Stage 0; card schema + constraints doc | Schema from the built instance |
| Reproducibility assessment | Stage 1; plan schema + fidelity contract + deviation log | Contract-level doc |
| Gated phasing | Every [GATE]; gate record with Tyler's rationale text | Folded into ticket spec (gates are ticket attributes) |
| Artifacts (agent + human) | Stages 4–5; results record + templates + comprehension check | Contract-level doc |
| Frontend | Nothing yet — files + CLI suffice; phone approval is deferred to primordia | Contract sketch only |
| Knowledge graph | Nothing yet — citation edges live inside cards as text | None; revisit when ≥ ~10 cards exist |
| Harness surface (skills, CLAUDE.md, memory) | Stage 3; treated as versioned infrastructure, edits recorded as interventions | Convention, not a component doc |

## What the derisk investigation must answer

1. Does the released code actually support replication (or is the
   environment the real work)?
2. Can any 3080-feasible model clear the paper's RQ3 capability floor —
   i.e. does our study-006 floor finding predict this paper's curve at
   small scale?
3. Does the ticket system survive contact with real work, including human
   tickets Tyler actually has to do?
4. Do the human-facing artifacts pass the first comprehension check?
