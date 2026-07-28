# Round 3 drafting contract (schema v1.1)

Verbatim prompt given to a fresh drafting subagent (claude-haiku-4-5-20251001)
on 2026-07-27, blind to rounds 1-2 and their reviews. Changes from round-2
contract: ships primary sources verbatim (paper-card claims +
reproducibility assessment, full resources.md) instead of paraphrased
context; `human_touchpoints` renamed to `human_needed` (mandatory, may be
empty, rendered even when empty); explicit note that assignee choices and
model/task choices must be grounded in the shipped sources.

---

You are drafting work tickets for a research replication project. Write YAML ticket files to this directory (create it if needed):

/Users/tylerlifke/Projects/morel-research/studies/007-autoresearch-infrastructure/investigations/001-better-harnesses-derisk/tickets/rounds/round-3/

TASK. We are derisking a replication of the paper "Better Harnesses, Smaller Models" (arXiv 2607.08938; code https://github.com/malusamayo/migration-analysis, built on the OpenHands software-agent-sdk). The PoC slice: ONE low-diversity task (budget-approval) x ONE SLM that fits our hardware, single harness-optimization run, reduced instance counts. Two primary sources follow — ground every choice (models, tasks, budgets, assignees) in them rather than in your own recollections; your knowledge of our hardware and of current models is assumed stale.

PRIMARY SOURCE 1 — paper card (claims and reproducibility assessment, drafted by the study's frontier agent from the full paper):

Claims:
1. Adaptation closes most of the gap. Optimized harnesses significantly improve 16/21 task-SLM pairs; 7 pairs close the SLM-LLM gap entirely. Best SLM (gemma-4-26b-a4b) goes 31.4% -> 80.2% average accuracy vs LLM 89.7%, at $0.071 vs $1.735 per instance (4% of cost). Per-task exemplar: budget-approval 75.0% -> 98.3% vs LLM 97.3% at 8% cost.
2. Task diversity predicts adaptation effectiveness. Spearman rho = -0.96 across tasks; controlled experiment drops 89.1% -> 68.0% as workflow templates go 3 -> 20.
3. Base capability predicts adaptation effectiveness. More capable SLMs gain more (+48.8% vs +15.5%); harnesses cannot replace missing core capability (ministral-3-8b stays at 0% on two tasks even optimized).
4. Adaptations are explainable by a failure-mode framework. Most-addressed failure modes: instruction-following (81%), knowledge (81%), tool-use (62%), long-context (33%); dominant strategies: adding contexts (86%), creating tools (43%), managing tools (29%).
5. Optimization cost amortizes: $20 one-time optimization per run recovered after ~13 deployment runs.
6. Negative result: no successful sub-agent adaptations were discovered.
7. Harnesses don't transfer across SLMs; re-optimize per model.

Reproducibility assessment (under our resources):
- Code is public; task data derives from public benchmarks (budget-approval comes from TheAgentCompany-derived templates). UNVERIFIED whether the released repo includes task-instance generation pipelines or only the optimizer — auditing it is early derisk work.
- Their per-optimization-run budget was $20 with a frontier meta-agent (gemini-3.1-pro); the meta-agent quality matters (a cheaper meta-agent gave worse harnesses — their Lesson 1). Raw JSON trajectories beat summarized markdown as meta-agent input.
- Their SLMs (gemma-4-26b-a4b ~16GB Q4, qwen3-coder-30b-a3b ~18GB Q4) exceed our 12GB VRAM; ministral3-8b-class dense models (~5GB Q4) fit, as does our 4B-class fleet. Substitution tests the directional claim, not their exact numbers.
- Claim 3 is the key derisk risk: a 4B-class model may sit below the capability floor where adaptation pays off.
- Local inference has no API price; cost claims need a documented proxy metric.
- Authors report high run-to-run stochasticity; single-run results need wide error bars.

PRIMARY SOURCE 2 — resources.md (verbatim):

Resources first; constraints derive from resources.

Compute:
- RTX 3080 12GB in the Windows desktop (WSL2), reached from the Mac via Tailscale SSH; ollama serves local models. PRIMARY resource — its 12GB VRAM is the binding hardware constraint on local model size.
- Modal, $30/month serverless GPU budget. SECONDARY — an escalation path when the 3080 cannot do the job, not a default; using it is a gate-worthy decision.
- A MacBook (Apple Silicon): orchestration, CPU-scale work.

Model access:
- Claude Code subscription: frontier-agent work and Haiku subagents; no marginal dollar cost, bounded by usage limits.
- Gemini API key: flash-lite-class models for judge roles (small real API cost).
- Local ollama fleet on the 3080: 4B-class models (nemotron-4b, qwen3.5:4b family) verified in past studies; the current installed list must be measured at execution time, not assumed.

Money:
- Study replication budget: ~$20 total; derisk phase compute ceiling $5.
- Modal $30/month (above), separate pool.

Human attention (scarcest resource):
- One researcher. Review bandwidth at gates is title + one-sentence summary per unit, detail on demand. Often reviewing from a phone, asynchronously.

Agent streams:
- Typically one interactive Claude session plus background subagents; local-model experiments serialize on the single GPU, so parallelism must come from non-GPU work.

Derived constraints:
- Max local model = what measurably fits 12GB VRAM quantized (roughly: 8B dense at Q4 fits; ~30B MoE does not fit comfortably — measure per model, never estimate).
- Local inference has no API price -> cost metrics need a documented proxy.
- Escalation ladder: 3080 -> Modal ($30/mo) -> anything beyond requires the human, explicitly.

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
claim: which paper-card claim (1-7) or reproducibility risk this serves, as free text
description: >
  2-6 sentences. What to do, concretely. Include commands/URLs where known.
acceptance:
  - criteria verifiable by inspecting artifacts (files that must exist and what they must contain). Never vague.
assignee_class: human | frontier-agent | small-agent
depends_on: [ticket ids, may be empty]
produces: [named artifact files this ticket hands off, e.g. repo-audit.md]
consumes: [artifact names it needs from other tickets; each must appear in the produces of a ticket listed in depends_on]
human_needed: [every moment in this ticket genuinely requiring the human — judgment calls, credentials/admin passwords, purchases, new resources; empty list if none. This field is mandatory and rendered even when empty: an empty list is an assertion, not an omission.]
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
- AI-FIRST ASSIGNMENT: minimize human work. assignee_class human ONLY when the work itself is judgment/approval or physically requires a human. Agents drive the GPU desktop over the SSH route, clone repos, run experiments. Genuine human moments inside agent tickets go in human_needed, and the ticket stays agent-assigned.
- THE PLAN IS A GRAPH, NOT A CHAIN: a depends_on edge exists ONLY when this ticket consumes an artifact the other produces. No ordering edges for tidiness. Maximize what can run in parallel.
- GROUND EVERY CHOICE in the two primary sources above: model names, VRAM feasibility, budgets, who runs the meta-agent, cost proxies. If a needed fact is absent from the sources, say so in the ticket description rather than inventing it.
- All tickets status: draft (the gate is not yet approved).
- Dependency graph must be acyclic and only reference tickets you create.
- Each ticket must be small enough that title + summary alone let a reviewer approve it, and its full contract fits one simple HTML card — if it needs subsections, split it.
- QUOTE any YAML string value that contains a colon.
- Ceilings: tickets spending real compute/API dollars must sum to <= $5; work under the Claude subscription carries 0 with a note in the description.
- No comments in the YAML files.
- Write ONLY the ticket files, nothing else (no plan.yaml, no README).
- SELF-VALIDATE before finishing: run
  cd /Users/tylerlifke/Projects/morel-research/studies/007-autoresearch-infrastructure && uv run scripts/drain.py --dir investigations/001-better-harnesses-derisk/tickets/rounds/round-3 check
  and fix every ERROR and WARN it reports, then run it again until clean.

Your final message: the final clean check output, then one line per file: filename | title | assignee_class. Raw data, no prose.
