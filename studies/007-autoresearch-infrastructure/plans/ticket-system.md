# Ticket system — deep spec (v0)

The mandatory component: file-based tickets tracking both human and agent
work, with a local drain runner. No app, no database. Designed so any
future frontend (morel-primordia) is a pure view over these files and any
logic lives here, in the open repo.

Author: claude-fable-5, 2026-07-26. Human-unreviewed draft.

## Design principles

1. **Files are the system.** Tickets are YAML files in git; git history is
   the audit log; a ticket's path is its id.
2. **Humans are first-class assignees.** Tyler's tickets look identical to
   agent tickets — assignee class differs, tracking doesn't. The
   (assignee-class, outcome) pairs are the delegation dataset that feeds
   the capability map.
3. **Gates are data.** A gate is a field a human must satisfy, with their
   rationale text stored — not a process convention someone remembers.
4. **Cost ceilings, not blank checks.** Every ticket carries a ceiling set
   at gate time; the runner refuses to dispatch a ticket whose ceiling is
   unset or exhausted.
5. **No hidden retries.** Failure is a terminal state that surfaces to a
   human; retry is a new ticket linking the failed one.
6. **HTML is the human ceiling.** YAML/markdown is the agent-facing source
   of truth; every ticket also renders to a single self-contained HTML
   card, and that render is a deliberate limiter: if a ticket is too
   complex to present as one simple card, the ticket is not decomposed
   enough. This is a human-understanding constraint, not an AI one —
   agents keep the full YAML. Same rule extends upward: plans and
   literature cards get generated HTML views for human review.

## Layout

```
studies/007-autoresearch-infrastructure/investigations/001-better-harnesses-derisk/
└── tickets/
    ├── plan.yaml          # tree metadata: phase, gate records, ceilings
    ├── 001-audit-repo.yaml
    ├── 002-sdk-smoke-test.yaml
    ├── 003-measure-slm-fit.yaml
    └── ...
```

Tickets live with their investigation (bounded work belongs to bounded
units). Cross-investigation work means a new ticket in the other
investigation, linked via `related`.

## Ticket schema (v0)

```yaml
id: 001-audit-repo
title: Clone migration-analysis and audit contents
claim: paper-card 2607.08938 / reproducibility risk 1
description: >
  Clone https://github.com/malusamayo/migration-analysis. Determine
  whether task-instance pipelines are included or only the optimizer.
  Produce an inventory listing what exists vs what the paper describes.
acceptance:
  - inventory.md exists listing repo contents vs paper section IV
  - explicit yes/no per task on regenerability of instances
assignee_class: small-agent   # human | frontier-agent | small-agent
depends_on: []
gate: derisk-approval          # named gate in plan.yaml; null if ungated
cost_ceiling_usd: 0.50
status: ready                  # draft | blocked | ready | in-progress |
                               # done | failed | abandoned
provenance:                    # written by the runner at completion
  executed_by: null            # model id or human name
  started: null
  finished: null
  cost_spent_usd: null
  artifacts: []                # paths produced
  verdict: null                # pass | fail per acceptance, with note
related: []
created: 2026-07-26
```

Field notes:
- `claim` ties every ticket to the paper-card claim or risk it serves —
  the no-orphan-work rule made checkable.
- `acceptance` must be verifiable by inspection of artifacts, not vibes;
  a ticket whose acceptance can't be written that way is not decomposed
  enough.
- `assignee_class` is a hypothesis. If a small-agent ticket fails and is
  reissued to a frontier agent (or Tyler), that pair of records is exactly
  the delegation measurement this study exists to collect.

## plan.yaml (tree metadata)

```yaml
phase: derisk                  # derisk | pilot | scale | report
phase_budget_usd: 5.00
gates:
  derisk-approval:
    approved_by: null
    date: null
    rationale: null            # Tyler's 1-3 sentences, verbatim
    would_change_mind: null
```

A ticket whose `gate` names an unapproved gate can never become `ready`.

## Status lifecycle

```
draft → blocked → ready → in-progress → done
                              ↓
                            failed → (new ticket supersedes)
any → abandoned
```

- `draft`: exists, not yet part of an approved plan.
- `blocked`: dependencies or gate unsatisfied. Derived, but stored
  explicitly so `git grep status:` answers questions without a tool.
- Transitions are edits to the file; the runner makes them for agent
  tickets, Tyler (or Claude on his word) for human tickets.

## Drain runner (v0 scope)

A small CLI (`scripts/drain.py`, run with uv) that:

1. `status` — renders the tree with states, gates, ceilings, spend.
2. `check` — validates schema, dependency acyclicity, gate references,
   ceiling presence; refuses drains on violation.
3. `next` — lists `ready` tickets per assignee class.
4. `run <ticket>` — dispatches one agent ticket: frontier-agent tickets
   via `claude -p` (headless) with the ticket file as the prompt contract;
   small-agent tickets via the desktop ollama route. Writes provenance,
   flips status. One ticket per invocation in v0 — no daemon, no
   parallelism, no auto-advance; a human watches the drain (matches
   check-before-fixing-failures).
5. Human tickets: `run` prints the contract and exits; completion is
   recorded with `done <ticket> --by tyler`.
6. `render` — generates the per-ticket HTML cards and an index
   (`tickets/html/`), the human-facing view per principle 6.

Explicitly deferred: parallel drain, retry policies, cron/background
draining, any web UI, cross-investigation queries.

## Contracts with other components

- **In:** an approved replication plan (Stage 1 artifact) is the only
  legitimate source of a ticket tree.
- **Out:** provenance records are the only legitimate source for the
  results/artifact layer and capability-map proposals.
- **Frontend (future):** reads/writes these files through git, nothing
  else. If the frontend needs a field that doesn't exist here, the schema
  changes here first.

## Things I made up that you should review

1. Tickets live under the investigation, not a top-level `tickets/` —
  chosen for locality; revisit if cross-study work becomes common.
2. The v0 schema fields, names, and the `claim` requirement.
3. Cost ceilings denominated in USD even for local inference (a synthetic
  price for 3080 time will be needed — flagged, not solved).
4. `claude -p` headless dispatch as the frontier-agent mechanism.
5. One-ticket-per-invocation drain (no autonomy) for v0.
6. Gate rationale + would-change-mind as required fields — my reading of
  your "small, scheduled writing obligations" goal; cut if it feels like
  ceremony.
