# Round 2 drafting contract (schema v1)

Verbatim prompt given to a fresh drafting subagent (claude-haiku-4-5-20251001)
on 2026-07-27. The subagent had no knowledge of round 1 or its review.
Changes from round-1 contract: adds summary/why/produces/consumes/
human_touchpoints fields, AI-first assignment policy, graph-not-chain
parallelism rule with handoff-justified edges, colon-quoting rule, and a
self-validation loop via drain.py check.

---

You are drafting work tickets for a research replication project. Write YAML ticket files to this directory (create it if needed):

/Users/tylerlifke/Projects/morel-research/studies/007-autoresearch-infrastructure/investigations/001-better-harnesses-derisk/tickets/rounds/round-2/

CONTEXT. We are derisking a replication of the paper "Better Harnesses, Smaller Models" (arXiv 2607.08938). The paper shows a meta-agent can automatically adapt an agent harness so small language models (SLMs) recover ~90% of frontier-LLM performance at ~4% cost on routine business tasks. Their code: https://github.com/malusamayo/migration-analysis, built on the OpenHands software-agent-sdk. Our constraints: one RTX 3080 12GB GPU (reached via a scripted SSH route to a desktop running ollama — agents can drive it without a human), ~$20 total budget, frontier-agent work done via Claude subscription. The PoC slice: ONE low-diversity task (budget-approval) x ONE SLM that fits the 3080, single harness-optimization run, reduced instance counts. Key risks from the paper card: (a) unverified whether their repo includes task-instance pipelines or only the optimizer; (b) paper's claim 3 says weak models benefit least, so a small model may sit below the capability floor where adaptation pays off; (c) local inference has no API price so the cost metric needs a documented substitute.

DERISK WORK TO DECOMPOSE (adapt as you see fit into 6-9 tickets):
1. Author the replication plan with a pre-registered fidelity contract (what "replicated" means per claim, decided before running anything) — frontier-agent work.
2. Clone and audit the migration-analysis repo: does it contain task pipelines or only the optimizer?
3. Stand up software-agent-sdk locally; run one budget-approval instance with a generic harness and a frontier model to verify the environment works.
4. Measure which SLMs actually load and run on the 3080 (don't estimate — measure load success and tokens/sec).
5. Run the generic-harness baseline for the chosen SLM on a reduced instance set.
6. One harness-optimization run under budget; log all trajectories raw.
7. Compare results against the fidelity contract; produce the comparison artifact.

PINNED SCHEMA — every ticket file must have exactly these fields (filename NNN-slug.yaml, ids zero-padded from 001):

id: NNN-slug
title: short imperative title that alone tells a reviewer what this ticket is
summary: one sentence a reviewer can approve from; title + summary must stand alone
why: >
  1-2 sentences: why this ticket exists and what breaks without it, tied to the claim/risk it serves.
claim: which paper-card claim (1-7) or risk (a-c) this serves, as free text like "paper-card claim 1 / risk a"
description: >
  2-6 sentences. What to do, concretely. Include commands/URLs where known.
acceptance:
  - criteria verifiable by inspecting artifacts (files that must exist and what they must contain). Never vague.
assignee_class: human | frontier-agent | small-agent
depends_on: [ticket ids, may be empty]
produces: [named artifact files this ticket hands off, e.g. repo-audit.md]
consumes: [artifact names it needs from other tickets; each must appear in the produces of a ticket listed in depends_on]
human_touchpoints: [moments genuinely requiring a human inside this ticket, e.g. admin password, purchase approval; empty list if none]
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
- AI-FIRST ASSIGNMENT: minimize human work. assignee_class human ONLY when the work itself is judgment/approval or physically requires a human (credentials, purchases, new resources). Agents drive the GPU desktop, clone repos, run experiments. If an agent ticket contains one genuine human moment, keep the ticket agent-assigned and declare the moment in human_touchpoints.
- THE PLAN IS A GRAPH, NOT A CHAIN: a depends_on edge exists ONLY when this ticket consumes an artifact the other produces. No ordering edges for tidiness. Maximize what can run in parallel.
- All tickets status: draft (the gate is not yet approved).
- Dependency graph must be acyclic and only reference tickets you create.
- Each ticket must be small enough that title + summary alone let a reviewer approve it, and its full contract fits one simple HTML card — if it needs subsections, split it.
- QUOTE any YAML string value that contains a colon (unquoted colons corrupt the parse).
- Ceilings: tickets spending real compute/API dollars must sum to <= $5 (the derisk compute budget); work done under Claude subscription carries 0 with a note in the description.
- No comments in the YAML files.
- Write ONLY the ticket files, nothing else (no plan.yaml, no README).
- SELF-VALIDATE before finishing: run
  cd /Users/tylerlifke/Projects/morel-research/studies/007-autoresearch-infrastructure && uv run scripts/drain.py --dir investigations/001-better-harnesses-derisk/tickets/rounds/round-2 check
  and fix every ERROR and WARN it reports, then run it again until clean.

Your final message: the final clean check output, then one line per file: filename | title | assignee_class. Raw data, no prose.
