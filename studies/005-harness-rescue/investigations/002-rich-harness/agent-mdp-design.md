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

## The judging layer (how we keep it honest)

- Judges are **LLM agents** (panel: Opus + Haiku + the local 4B, per study-004
  inv-002 judge-comparison), each with a rubric *per process-agent*.
- Output: a **qualitative assessment + justification** (always) and a **rubric
  score per dimension** (1–5), plus the quantitative anchor where one exists.
- **Validation (tuning the judges):** before trusting judge scores at scale, we
  hand-score a small held-out sample of each step type as the reference, measure
  judge↔reference agreement, audit divergences, and iterate the rubric — exactly
  the methodology from study 004's judge investigation. A judge we haven't
  validated produces *provisional* scores only.
- **Never** a naive proxy. We do not score "mentioned the word interaction"; we
  ask a judge "does this prior demonstrate understanding that the two controls
  must be set jointly?" and let it reason.

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

### Arms (C4 in all; reasoning front-end varies)

| arm | front-end | tests |
|---|---|---|
| **M** (= Phase-1 A1) | none (minimal + C4) | baseline; judges score its *implicit* reasoning from the trace |
| **O** | + Orienter | does eliciting a neutral prior alone help? |
| **OH** | + Orienter + Hypothesizer | does the full reason-first front-end help? |

20 seeds, Env A, reasoning=low. (Self vs fresh-critic and the full design/analyst
agents are the *next* round, layered on the winner.)

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
