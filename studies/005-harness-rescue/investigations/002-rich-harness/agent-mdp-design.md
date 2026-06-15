# The researcher as a society of MDP agents + judges

_Design doc, 2026-06-08. Operationalizes [[reasoner-not-optimizer]] into a
buildable, inspectable architecture, and specifies the first reasoning-native
experiment. Decisions are joint; Claude proposes, Tyler approves before runs._

## Why this structure

The research *process* decomposes into steps (orient, hypothesize, design,
analyze, decide, generalize). We model **each step as an agent in a Markov
Decision Process** — it observes part of a shared state, takes a structured
action, and earns a reward — and **each process-agent is paired with a judging
agent** that scores how well it did *its specific job*. This buys exactly what
the thesis demands:

- **Inspectability per step.** We can ask of each step alone: was the prior
  applicable? did the experiment test the hypothesis? was the analysis correct?
- **Per-step reward** so we can see *where* reasoning succeeds or fails, not just
  whether the final answer was good.
- **Tunable judges.** The judges are themselves agents we validate and improve
  (study-004 judge-comparison methodology) — never naive metrics.

**Hard rule:** every step is judged **qualitatively, always, by an LLM judge**,
and **quantitatively where a ground-truth anchor exists** (real regret, or the
known landscape structure). We **never** use string-matching / keyword-presence
/ phrase-matching as a proxy for quality. A judge reads the agent's reasoning and
assesses it semantically.

**Overdesign guard (the tension we hold):** the decomposition is for *observation
and scoring*, not a rigid script the agent must march through. We elicit the
process with **Socratic, neutral prompts** and instrument the outputs so each is
separable and judgeable — we do **not** hard-code the answer or force a lockstep
pipeline. An over-prescriptive harness wins Env A and breaks transfer; we scaffold
the *process*, score each part, and let the reasoning stay the model's own.

## Shared state — the research record (blackboard)

All agents read/write a structured shared record:

```
record = {
  task_framing,                 # neutral statement of the problem + budget
  prior,                        # Orienter's output (knowledge, expected structure, approach, uncertainties)
  hypotheses[],                 # {claim, test, status: open|confirmed|refuted}
  trajectory[],                 # {config, result, hypothesis_tested, prediction, observation, belief_update}
  budget_remaining,
  decision,                     # continue | finish(answer)
}
```

Each agent sees the slice relevant to its job (state space), emits its
contribution (action space), and is scored (reward).

## The agents (MDP spec) and their judges

| Agent | State (observes) | Action (emits) | Reward = its Judge scores… (qualitative always; quantitative anchor noted) |
|---|---|---|---|
| **Orienter** | neutral task framing only | `{knowledge, expected_structure, approach, uncertainties}` | relevance to the *actual* problem · correctness (judge holds ground truth) · specificity vs boilerplate · **anticipates key structure unprompted** (e.g. that the controls interact) · actionability. *Anchor:* does the prior identify the real structure? |
| **Hypothesizer** | prior + record | `[{claim, how_to_test, what_would_confirm/refute}]` | falsifiability · informativeness (would discriminate regions) · grounding in prior/evidence · directional correctness. *Anchor:* do hypotheses align with the true landscape? |
| **Experiment designer** | open hypotheses + record + budget | `{next_config, hypothesis_targeted, predicted_result}` | does the experiment actually test a stated hypothesis? · information-bearing vs redundant? *Anchor:* did it reduce uncertainty / regret this step? |
| **Analyst** | result + prior beliefs | `{observation, which_hyp_confirmed/refuted, revised_hypotheses}` | correct interpretation given the data · appropriate update (no over/under-update, no confabulation). *Anchor:* matches the true result/structure? |
| **Method selector** _(future-live)_ | record + problem shape | `{method_choice}` incl. *[future: offload to an algorithm / write code]* | appropriateness to recognized structure (e.g. "recognize this is a small smooth optimization"). |
| **Critic / partner** _(C1-fresh, reframed)_ | current hypotheses/plan | `{challenge or knowledge injection}` | does it improve the reasoning (catch a flaw / a frozen axis)? validity / on-grid? |
| **Terminator** _(C4, reframed)_ | record + convergence signal | `continue \| finish(answer)` | stopped for the *right reason* (converged vs satisfice vs wander). *Anchor:* reported answer correct? |
| **Generalizer** _(cross-episode)_ | record across env(s) | `{extracted_principles}` | do principles transfer? *Anchor:* validated on **held-out** env (A→B→C→W2S). |

## The reward philosophy — two sources, kept separate

1. **Process reward** — each judge's score of how well *that agent* did its job
   (the reasoning quality), independent of luck.
2. **Outcome reward** — the task signal: reached-optimum, final + **cumulative**
   regret, sample-efficiency, generalization.

Keeping them separate is the entire point: a run can have a *good outcome from
bad reasoning* (lucky) or *good reasoning with a bad outcome* (unlucky). The
headline scientific question becomes measurable — **does process quality predict
outcome?** If yes, the reasoning is real and worth scaffolding; if not, we're
fooling ourselves with an optimizer-in-disguise.

**Decompose for credit, optimize for the global outcome** (MHGPO [2506.02718];
HiPER [2602.16165]). The per-step decomposition is a *credit-routing and diagnostic*
structure — **not** a set of local objectives to optimize in isolation. Each step's
credit must **anchor to whether it advanced the global outcome** (regret reduction),
HiPER-style boundary-bootstrapping: an analyze-step isn't "good" in a vacuum, it's
good if the hypothesis/design phase it served actually moved regret. MHGPO's lesson:
per-agent isolated optimization chases local proxies that don't compose into global
success — so we judge per step but **select/optimize on the whole-trajectory result**.
And boundaries stay **reasoning-driven, not rigidly imposed** (HiPER's SWITCH/KEEP):
a fixed five-stage pipeline graded by five independent judges is precisely what this
literature warns against — it reintroduces the over-prescription we're avoiding.

## The judging layer (how we keep it honest)

Design grounded in the 2026 credit-assignment literature (refs below); the
prescriptions below are not free choices — three of four papers converge on them.

- **Panel: Opus 4.8 + Haiku 4.5 + gemini-3.1-flash-lite + nemotron-3-nano:4b** — a
  spread of capability/cost (study-004 inv-002 method). 4B = cheapest cross-check
  (can a weak model peer-judge?); Opus = reference ceiling; Haiku/Gemini = the
  cheap-capable middle.
- **Retrospective + privileged** (CriticSearch [2511.12159]; survey [2604.09459]).
  Judges run **after** a trajectory completes, with **privileged access the actor
  never had** — the *full* trajectory **and the final outcome** (regret, distance
  to the known optimum). Grading a step in hindsight is the survey's recommended
  way to handle a sparse terminal signal; do **not** judge online/forward-only.
- **Coarse, hard-to-game labels — not rich summed scores** (survey reward-hacking
  warning; PURE min-form; CriticSearch binary). Each step gets a **coarse verdict**
  (e.g. `strong | adequate | weak`, or binary `helped | didn't`), **not** a 1–5
  score per dimension. We **aggregate bottleneck/min-form, never sum/average** —
  summed per-step scores invite "safe filler steps that inflate the total."
- **Separate decision-errors from information-gaps** (survey's named open problem —
  the biggest risk for an orient/hypothesize judge). The rubric **must** ask: *given
  what was knowable at this step, is this a genuine reasoning error, or reasonable-
  but-unlucky given the information then available?* A judge that punishes
  information-gaps will mis-assign credit and push us to over-prescribe.
- **Concentrate on bifurcation points** (survey). Most steps are routine; a few
  decisions drive outcome variance (e.g. *the* decision to freeze batch size). The
  judge identifies and weights the pivotal decisions rather than grading every step
  uniformly.
- **Frozen, not co-trained** (CriticSearch). Off-the-shelf judges; no judge↔actor
  co-optimization (avoids instability and is sufficient).
- **Validation bar before trusting scores** (CriticSearch protocol): hand-score a
  **~20-trajectory** reference sample; require **~80% judge↔reference agreement**;
  audit divergences; iterate the rubric. Below the bar = provisional only. This is
  the home of inv 003.
- **Never a naive proxy.** No keyword/string matching. We ask a judge "does this
  prior show the model understands the controls must be set jointly?" — semantically.

---

## The first reasoning-native experiment

**Goal:** test whether eliciting the model's *own* prior and hypotheses — without
leaking the problem's answer — produces better *reasoning* and better *outcomes*
than the Phase-1 harnesses, and whether reasoning quality predicts outcome.

**Live agents this round:** Orienter, Hypothesizer (real separate calls), plus
the existing experiment loop **instrumented** so design + analysis are observable
(the agent tags each experiment with the hypothesis it tests and a one-line
analysis). Terminator = C4 (kept in *all* arms so finishing never confounds the
outcome metric). Design/Analyst become full separate agents in a later round —
this round instruments them rather than scripting them (overdesign guard).

### The Socratic, non-biasing Orienter prompt (fixed, audited for leakage)

> *You're about to take on a tuning problem. You can set two values — a learning
> rate and a batch size — and for each setting you'll be told the resulting
> validation loss, which you want as low as possible, within a budget of 50 trials.*
>
> *Before running anything, think as a researcher would:*
> - *What do you know about problems of this kind? Have you seen this type of
>   problem before — what tends to be true of them?*
> - *How would a careful, knowledgeable person approach a problem like this?*
> - *What do you already expect about how each control affects the outcome, and
>   how confident are you?*
> - *What are the main things you're uncertain about that experiments could resolve?*
>
> *Be concrete and specific to what you actually know; say when you're unsure.*

**Why this is non-biasing:** it names the real domain (so the model's *domain
knowledge* is in play — that knowledge is the whole point), but it does **not**
state the answer or lead toward it. It never says the controls *interact*, never
hints where the optimum is, never says "co-vary them." If the model volunteers
"learning rate and batch size interact, so I should vary them together," that is
**its own knowledge**, and the Orienter-judge scores it as such. We seed the
*question*, not the *answer* — the way Tyler guides Claude.

### Hypothesizer prompt

> *Given what you just said, state specific predictions about this space you could
> confirm or refute by experiment — for each, what you'd run and what result would
> support or contradict it.*

### Design/analysis instrumentation (light, not scripted)

The main loop runs as in Phase 1, but each experiment carries two annotations:
before — `hypothesis_targeted`, `predicted_result`; after — `observation`,
`belief_update`. These are *requested*, not gated, so the agent isn't forced into
lockstep; they make the design/analysis steps judgeable.

### Arms — reasoning front-end × domain framing (C4 in all)

Two crossed factors:

- **Front-end:** **M** (minimal+C4) · **O** (+Orienter) · **OH** (+Orienter+Hypothesizer)
- **Domain framing:** **real** (named lr/bs/val-loss, real grid values — the
  model's domain knowledge is in play) · **abstract** (relabeled: "control A ∈
  {a1…a12}, control B ∈ {b1…b10}", a score to minimize; the substrate maps labels
  back to the real grid, so the *problem* is identical but the *semantics* are
  hidden). Implemented by a `DOMAIN=real|abstract` flag that rewrites the framing
  + a label↔value map; the substrate and optimum are unchanged.

= **6 arms** (M/O/OH × real/abstract). The contrast isolates **domain knowledge**
(real − abstract) from **structured reasoning** (front-end effect): does the
Orienter help because the model *recalls ML knowledge*, or because *being asked to
reason first* helps even with no domain to recall? A competent abstract-O run can
only win by general search reasoning; a real-O win that abstract-O doesn't get is
the value of the model's knowledge.

### Methodology — small-scale first (don't burn GPU on dead ends)

**Probe at <5 seeds per arm first**; only scale an arm to 20+ once it *shows
promise* (judge scores or outcomes clearly moving). Insights fast, cheap, and
GPU-frugal (nemotron is free but the one desktop GPU is serial). The full
6-arm × 20-seed grid is the *confirmation* run, not the *exploration* run.
Env A, reasoning=low throughout. Self-vs-fresh critic and the full design/analyst
agents layer on the winner in later rounds.

### What we measure

- **Process (judged):** Orientation quality, Hypothesis quality, per-experiment
  Design + Analysis quality — qualitative + rubric scores, validated judges.
- **Outcome:** reached-optimum, final + cumulative regret, sample-efficiency,
  finish-kind.
- **The linkage:** does higher process-quality predict better outcome (within and
  across arms)? Run the judges on the **Phase-1 traces too** (free retro-scoring)
  so we have reasoning quality for ~all runs, not just the new arms.

### Non-biasing safeguards (audit before running)

- Orienter prompt reviewed line-by-line for any leak of structure/optimum.
- Agents never see ground truth; **judges** hold it.
- No keyword/string proxies anywhere — all quality is LLM-judged semantically.
- Judges validated against a hand-scored reference sample before their scores
  are treated as load-bearing.

## Future hook — meta-agents that modify the action space

A competent researcher would recognize "this is a grid-search problem" and reach
for the right instrument — including **writing code to run a search algorithm**
or **offloading to an optimizer**. Today the action space is fixed (`run_config`,
`finish`, + the reasoning steps), so the agent *cannot* take that action even if
it proposes it. We accept that limitation for now. The key future capability is a
**meta-agent that expands a subagent's action space** (grants it a new tool /
the ability to author and run code) when the subagent's reasoning calls for it.
That is the path to the "recognize-and-offload" behavior whose *absence* is our
cleanest signal that the harness isn't finished — and it is the natural Phase-3+
extension of the Method-selector agent above.

## References (credit assignment & multi-agent)

- **From Reasoning to Agentic: Credit Assignment in RL for LLMs** — Zhang, 2026 —
  [2604.09459](https://arxiv.org/abs/2604.09459). Survey of 47 CA methods; anchor for
  hindsight credit, reward-hacking of sum-form scores (→ min-form/coarse), the
  decision-error-vs-information-gap open problem, and bifurcation-point focus.
- **CriticSearch: Fine-Grained Credit Assignment for Search Agents via a
  Retrospective Critic** — Zhang et al., CAS, 2025 —
  [2511.12159](https://arxiv.org/abs/2511.12159). The judge blueprint: frozen,
  privileged (full trajectory + gold/outcome), retrospective, coarse Good/Bad,
  human-validated (~80% on ~20 trajectories).
- **HiPER: Hierarchical RL with Explicit Credit Assignment for LLM Agents** —
  Peng et al., 2026 — [2602.16165](https://arxiv.org/abs/2602.16165). Two-level
  plan/execute with *reasoning-driven* SWITCH/KEEP boundaries; HAE boundary-
  bootstrapping; variance-reduction only when the hierarchy is informative.
- **End-to-End Optimization of LLM-Driven Multi-Agent *Search* Systems (MHGPO)** —
  Chen et al., 2025 — [2506.02718](https://arxiv.org/abs/2506.02718). Whole-system
  group comparison beats per-agent isolated optimization; decompose-for-credit,
  optimize-for-global. (Search-specific — transfer with care.)

_Venues for [2506.02718] (ACL 2026) and [2602.16165] (ICML) are arXiv-reported,
not independently confirmed. [2604.09459] is a single-author preprint._
