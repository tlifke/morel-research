# Study 005 — Handoff to a fresh agent

_Written 2026-06-15 by the outgoing agent, whose context got large. This is the
single entry point. It orients you, states where things stand, and — because
Tyler explicitly wants fresh eyes on **direction** — ends with the open questions
you should genuinely reconsider, not just execute._

Branch: `005/harness-rescue` (pushed to origin; latest commit ~`0ea8fae`).
Everything is committed. `runs/` is gitignored; tracked data lives in
`investigations/001-.../data/` and `investigations/003-.../data/`.

---

## 1. Read these first, in this order

1. **`reasoner-not-optimizer.md`** — THE north star. If you read one thing, this.
   The whole study pivots on it: we are building a *reasoner that brings
   knowledge*, NOT a dressed-up search algorithm. Includes the harness-job-shift
   table and the **three-tier evaluation model** (objective outcome / intermediate
   problem-specific computable metrics / judge qualitative).
2. **`study.md`** — the question (harness vs training), the three-corner framing,
   the standing rule to report all three evaluation tiers.
3. **`investigations/001-steplaw-substrate/investigation.md`** — the substrate +
   the minimal-harness baseline (DONE). Read the Status/log entries; they're the
   narrative of what we learned.
4. **`investigations/002-rich-harness/`** — `investigation.md`, `methods.md`
   (component registry C1–C7 with pre-registered + scored hypotheses), and
   `agent-mdp-design.md` (the society-of-MDP-agents + judges design and the
   first reasoning-native experiment). DESIGNED, not yet built/run.
5. **`investigations/003-process-judges/investigation.md`** — the LLM judge panel
   (VALIDATED, tooling in place).
6. **Memories** (auto-loaded via `MEMORY.md`). The load-bearing ones:
   `feedback_reasoner_not_optimizer` (north star), `project_harness_scale_interaction`
   (thesis), `project_axis_freezing_coverage_failure` (the key empirical finding),
   `feedback_multi_llm_judge_panel`, `feedback_small_scale_first`,
   `project_pi_internal_loop` (harness gotcha), `feedback_case_studies_over_aggregates`,
   `feedback_check_before_fixing_failures`.

## 2. The thesis in one paragraph

Can a **rich harness** (context engineering) substitute for **training** to make a
small prompted model (nemotron-3-nano:4b) a competent long-horizon *research*
agent? This stakes a third corner between the automated-w2s paper (strong model +
minimal harness) and AutoLLMResearch (weak model + *training*). The deeper reframe
that emerged: the LLM's value over an optimizer is **knowledge-grounded,
hypothesis-driven reasoning that transfers** — so the harness must *elicit and
scaffold reasoning*, not engineer coverage an algorithm would do better. We develop
cheaply on the **StepLaw** lr/bs loss landscape (Env A→B→C), then aim to transfer to
the real weak-to-strong task (no objective optimum there — which is why the
intermediate metrics matter).

## 3. Where things stand

- **inv 001 (substrate + minimal baseline): DONE.**
  - Substrate: `harness/scripts/steplaw_query.py` (real-grid lookup, off-grid
    rejected). Harness: `harness/src/researcher.ts` (Pi single-conversation loop,
    `run_config` + `finish` tools, guards, reasoning-level control, and the Phase-1
    knobs `REFLECT=off|self|fresh` and `ACTUATE`).
  - Minimal-harness baseline + a C1×C4 factorial (120 runs) + a reasoning-level
    sweep (105 runs). **Headline findings below.**
- **inv 002 (rich harness): DESIGNED, NOT BUILT.** The first reasoning-native
  experiment is fully specified in `agent-mdp-design.md` but the Orienter/
  Hypothesizer agents + the abstract-relabel layer are **not implemented yet**.
  This is the obvious next build — *if* it survives the fresh-eyes questions (§6).
- **inv 003 (judges): VALIDATED, ready to use.** A 4-model panel (Opus + Haiku as
  Agent subagents; gemini-3.1-flash-lite + nemotron-4b via API/SSH) scores each run
  retrospectively with a coarse, hard-to-game rubric (`harness/judges/process_judge.md`).
  Tooling: `judge_casefile.py`, `run_api_judge.py`, `run_ssh_judge.py`,
  subagent judges, `persist_judgments.py` (tracked dataset), `judge_compare.py`
  (the three-tier per-trace artifact; also a **skill**: `three-tier-evaluation`).

## 4. Load-bearing findings (don't re-derive these)

- **Study-004's dramatic failures were harness artifacts.** Pi's `agent.prompt()`
  is itself a loop; don't wrap an external re-prompt loop around it
  (`project_pi_internal_loop`).
- **nemotron's real failure on StepLaw is axis-freezing** — it treats lr and bs as
  independently optimizable, freezes one (usually bs) off a misleading early slice,
  and sweeps the other → a confident-WRONG minimum. It's a *coverage/reasoning* gap
  (no joint-interaction reasoning), NOT stamina or perception
  (`project_axis_freezing_coverage_failure`).
- **C4 (force the `finish` tool / reject prose conclusions) is a clean win**:
  stall 0% across all conditions; it fixes *finishing*, not search.
- **C1 reflection** doesn't move the median but tightens the tail; **fresh-agent
  reflection > self**, and the fresh advisor is the *only* intervention that
  actually breaks axis-freezing — but it's noisy (can steer wrong). Self-reflection
  does NOT break the freeze.
- **Reasoning is load-bearing for exploration** (off → ~16× worse regret) and the
  weak model is far more sensitive than gemini — but reasoning does NOT fix the
  stall (orthogonal). `low ≈ medium ≈ high` on the median (`low` is the efficient
  setting; fixed at `low`).
- **The coverage "fix" I proposed was WRONG** — it encoded Env A's answer
  (high-lr/large-bs) and would mislead on Env C (low-lr optimum). The generalizable
  move is to elicit the model's reasoning, not script coverage. This is what
  triggered the reasoner-not-optimizer reframe.
- **Judges: panel validated** (6/8 unanimous on the tightened rubric; the splits
  are genuine credit-attribution edges). **nemotron-4b as a judge: partial** —
  tracks the panel on clear cases, blanks on the hardest. Keep as a cheap
  cross-check, don't trust alone.

## 5. What's decided for the next experiment (if you proceed as planned)

First reasoning-native round (`agent-mdp-design.md`): **arms M / O / OH × {real,
abstract domain} = 6 arms**, C4 in all, reasoning=`low`, Env A, **small-scale
(<5 seeds) first, then scale on promise** (`feedback_small_scale_first`).
- **O** = + an Orienter agent (Socratic, NON-leading: "what do you know about this
  *type* of problem and how would you approach it?" — never naming the lr/bs
  interaction). **OH** = + a Hypothesizer.
- **abstract** = relabel the lr/bs grid to opaque "control A/B" (the build piece
  not yet written) to separate domain-knowledge from structured-reasoning.
- Score every run with the judge panel + the three-tier artifact; the headline
  question is **does process quality predict outcome?**
- Build pieces still missing: the Orienter/Hypothesizer agents in `researcher.ts`,
  the relabeling layer, and (optionally) promoting Designer/Analyst to real agents.

## 6. Open questions for FRESH EYES (Tyler wants you to reconsider, not just execute)

These are genuinely open. Anchor to the north star (`reasoner-not-optimizer.md`)
and to sharp, judgeable targets (`feedback_opus_research_taste_caveat`).

1. **Is StepLaw still the right proxy?** The reasoner-thesis warns we must not
   overfit the harness to a grid-search task an algorithm should own. We've learned
   a lot here cheaply, but is it time to move toward a substrate where the LLM's
   knowledge is *necessary* (search infeasible)? Or is Env B→C→W2S transfer enough?
2. **Is the Orienter/Hypothesizer arm the right next step — or is the
   "recognize-and-offload" probe sharper?** Tyler's cleanest diagnostic: a good
   researcher would notice "this is a grid-search problem" and *offload it to an
   algorithm*. nemotron never does. Testing whether the harness can elicit that
   (and the future meta-agent that *expands a subagent's action space*) may be more
   decisive than the elicitation arm.
3. **Do the C1–C7 components still frame it right,** or has the reasoner reframe
   superseded the literature-component list? Consider re-deriving the harness from
   the reasoner-thesis (orient→hypothesize→design→analyze) rather than the
   component catalog.
4. **Intermediate metrics** are defined for lr/bs (corner-reached, axis-frozen,
   coverage). What are they for the next substrate / W2S? They must be identified at
   problem-framing outset — that's a design task, not an afterthought.
5. **Judges**: is a frozen LLM panel the right instrument, and is nemotron-4b worth
   keeping in it? The credit-assignment literature (`agent-mdp-design.md` refs)
   cautions that judge scores are advisory heuristics, not ground truth.

## 7. Operational notes

- **Harness**: TypeScript subtree under `investigations/001-.../harness`. Run a
  researcher with env vars (PROVIDER, OLLAMA_URL, THINK, REFLECT, ACTUATE, BUDGET,
  N, D). `scripts/sweep.sh` drives multi-seed/arm sweeps; `scripts/*report.py` +
  `fig_*.py` aggregate/plot (Plotly, per repo convention; see `morel-branding`).
- **Models**: nemotron-3-nano:4b on the desktop GPU (free, slow, single serial
  resource); gemini-3.1-flash-lite via API (cost in `.env` GEMINI_API_KEY). Opus/
  Haiku via Agent subagents (`model:` override).
- **Desktop GPU**: RTX 3080, WSL2-on-Windows, over Tailscale SSH
  (`desktop-gpu-access` skill). Currently the **tailnet:11434 path is flaky after a
  reboot** (WSL Hyper-V firewall sets DefaultInboundAction=Block; SSH/22 is fine).
  Reliable workaround for ollama: **SSH → WSL-localhost**, body via SSH stdin
  (`run_ssh_judge.py` shows the pattern; cmd.exe has an ~8191-char arg limit).
- **Judges**: see `feedback_multi_llm_judge_panel`. Rubric is retrospective +
  privileged + coarse; persist with `persist_judgments.py`; visualize with
  `judge_compare.py` / the `three-tier-evaluation` skill.
- **Conventions**: `CLAUDE.md` (no comments in code, `uv run`, no traces left,
  Plotly figures, one-pagers are human-prose-only, run `update_lineage.py` after
  frontmatter edits). Small-scale-first. Diagnose-and-report before fixing
  run/desktop failures.
