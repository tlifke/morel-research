# Round 1 drafting contract (schema v0)

Verbatim prompt given to the drafting subagent (claude-haiku-4-5-20251001)
on 2026-07-27. The subagent had no other project context. Preserved as the
experimental condition for the round-1 vs round-2 decomposition comparison.

Outcome notes: 7 tickets, all schema-valid except two acceptance items with
unquoted colons that parsed as YAML dicts (caught by `drain.py check` after
a rule was added); 5/7 tickets assigned to human; fully linear dependency
chain.

---

You are drafting work tickets for a research replication project. Write YAML ticket files to this directory (create it):

/Users/tylerlifke/Projects/morel-research/studies/007-autoresearch-infrastructure/investigations/001-better-harnesses-derisk/tickets/

CONTEXT. We are derisking a replication of the paper "Better Harnesses, Smaller Models" (arXiv 2607.08938). The paper shows a meta-agent can automatically adapt an agent harness so small language models (SLMs) recover ~90% of frontier-LLM performance at ~4% cost on routine business tasks. Their code: https://github.com/malusamayo/migration-analysis, built on the OpenHands software-agent-sdk. Our constraints: one RTX 3080 12GB GPU (reached via the desktop/ollama), ~$20 total budget, frontier-agent work done via Claude subscription. The PoC slice: ONE low-diversity task (budget-approval) x ONE SLM that fits the 3080, single harness-optimization run, reduced instance counts. Key risks from the paper card: (a) unverified whether their repo includes task-instance pipelines or only the optimizer; (b) paper's claim 3 says weak models benefit least, so a small model may sit below the capability floor where adaptation pays off; (c) local inference has no API price so the cost metric needs a documented substitute.

DERISK WORK TO DECOMPOSE (from the approved walkthrough, adapt as you see fit into 6-8 tickets):
1. Author the replication plan with a pre-registered fidelity contract (what "replicated" means per claim, decided before running anything) — frontier-agent work.
2. Clone and audit the migration-analysis repo: does it contain task pipelines or only the optimizer?
3. Stand up software-agent-sdk locally; run one budget-approval instance with a generic harness and a frontier model to verify the environment works.
4. Measure which SLMs actually load and run on the 3080 (don't estimate — measure load success and tokens/sec).
5. Run the generic-harness baseline for the chosen SLM on a reduced instance set.
6. One harness-optimization run under budget; log all trajectories raw.
7. Compare results against the fidelity contract; produce the comparison artifact.

PINNED SCHEMA — every ticket file must have exactly these fields (filename NNN-slug.yaml, ids zero-padded from 001):

id: NNN-slug
title: short imperative title
claim: which paper-card claim (1-7) or risk (a-c) this serves, as free text like "paper-card claim 1 / risk a"
description: >
  2-6 sentences. What to do, concretely. Include commands/URLs where known.
acceptance:
  - list of criteria verifiable by inspecting artifacts (files that must exist and what they must contain). Never vague ("understand X" is invalid; "inventory.md lists each paper task with yes/no on regenerability" is valid).
assignee_class: human | frontier-agent | small-agent   (your hypothesis of the weakest class that can do it)
depends_on: [list of ticket ids, may be empty]
gate: derisk-approval
cost_ceiling_usd: your proposed number (the human finalizes at gate time)
status: draft
provenance:
  executed_by: null
  started: null
  finished: null
  cost_spent_usd: null
  artifacts: []
  verdict: null
related: []
created: 2026-07-27
created_by: claude-haiku-4-5-20251001

RULES:
- All tickets status: draft (the gate is not yet approved).
- Dependency graph must be acyclic and only reference tickets you create.
- Each ticket should be small enough that its full contract fits on one simple HTML card — if a ticket needs subsections, split it.
- Sum of proposed cost ceilings must stay under $10 (the derisk phase budget is $5 for compute; ceilings for frontier-agent tickets done under subscription may be 0 with a note in description; small-agent/local tickets cost ~0 but reserve real dollars only where API/optimization spend happens).
- No comments in the YAML files.
- Write ONLY the ticket files, nothing else (no plan.yaml, no README).

Your final message: list the filenames you created, one line each with the ticket title and assignee_class — raw data, no prose.
