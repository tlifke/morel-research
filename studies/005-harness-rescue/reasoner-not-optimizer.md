# Reasoner, not optimizer — the thesis for the researcher agent

_Captured 2026-06-08 from a working conversation between Tyler and Claude. This
is the north star for how we approach the researcher-agent work (studies 003–005
and onward), and the lens that should shape every harness and metric decision.
It may graduate to a higher-level doc; for now it lives with the active work._

## The core distinction

A grid search, Bayesian optimization, or a closed-form scaling law (e.g. StepLaw
itself) will beat a 4B model at minimizing loss on a 2-D lr/bs grid — cheaper,
faster, lower regret. If the goal were "minimize this objective on this grid,"
an LLM is the *wrong tool*.

> **Gradient descent moves us in the right direction for a better solution; an
> LLM can reason about WHY that direction improved the solution — or didn't.**
> — Tyler

That "why" is the whole point. An optimizer takes a step because the math says
so; it has no model of the problem. An LLM can:

- understand a problem space (bring knowledge of *this class* of problem),
- act within it according to **hypotheses**,
- observe a result, **analyze** the data, and infer *why*,
- iterate intelligently on what it has learned,
- lean on outside help or its own internalized knowledge to make progress.

It can be wrong at any of these. **Refining precisely that ability — to do
hypothesis-driven science in a space — is what we are building.** We are not
building a dressed-up search algorithm.

## What an LLM provides that an optimizer cannot

- **Prior knowledge.** It can walk into a space it has never seen and draw on
  analogous problems, theory, and practice to form an informed starting point.
- **Reasoning about mechanism.** It can explain why a move helped, form a causal
  story, and test it — not just follow a gradient.
- **Operating where you can't search.** Expensive evaluations, high/unbounded
  dimensions, novel or ill-specified objectives — the regime where grid search
  and BO are infeasible. This is the weak-to-strong researcher's world.
- **Tool selection / meta-reasoning.** A competent researcher *recognizes the
  problem class* and reaches for the right instrument — including offloading a
  grid-search problem to a grid-search algorithm. (That nemotron has **not** done
  this on StepLaw is a sharp signal our harness isn't right yet: a good researcher
  would notice "this is a small smooth 2-D optimization, I should just sweep it
  systematically or hand it to an optimizer," instead of fumbling it by hand.)
- **Transfer.** It can carry a principle learned in one environment into a
  harder, different one.

## The process a good researcher follows (in any space)

Hypothesis-driven, knowledge-grounded — **science, not exhaustive search**:

1. **Orient** with prior knowledge — what do I know about this class of problem?
   What do theory/literature/analogous spaces say about structure, where good
   solutions live, and which variables interact? Form an explicit prior + hypotheses
   *before* sampling.
2. **Hypothesize** — make falsifiable claims about the space.
3. **Design experiments to reduce uncertainty** — choose each experiment to test
   a hypothesis / maximize information, not to tile the grid.
4. **Observe + analyze** — interpret results in domain terms; update beliefs.
5. **Iterate** — revise hypotheses, exploit discovered structure, recognize when
   a different method (or tool, or partner) is the efficient move.
6. **Know when to stop** — when marginal information is low.
7. **Generalize** — extract the principle, not the point.

For StepLaw specifically: a competent researcher should solve Env A — not
necessarily quickly — by reasoning, choosing experiments, and making testable
inferences, **discovering the lr×bs relationship** (from its own knowledge or by
experiment) and using that to guide its work.

## Why StepLaw's three environments are the right testbed

A → B → C is a **generalization ladder**, and the fast lookup substrate lets us
iterate cheaply on the researcher *and its partner agents* (critic, research
partner, reflector):

- **Env A** (215M/100B, over-trained): the simple env. Any competent reasoner
  should solve it. It is where we *develop and instrument* the process.
- **Env B, Env C**: progressively different regimes (optimal lr falls with N; Env
  C only swept low lr). The **win we are looking for** is a researcher that
  *learns the structure in a simple env and applies those learnings to be
  competent in a harder, different one* — without starting from scratch.
- **W2S** (real task): the destination — a space where you genuinely cannot grid
  search, so the reasoning is the only path.

A harness tuned to make the LLM a better grid-searcher on Env A will **overfit to
a task an algorithm should own and fail to transfer.** Generalization across the
ladder is the success criterion, not Env-A regret.

## The harness's job — the shift

The harness must stop trying to *supply the missing search competence* (algorithms
own that) and start *eliciting and sustaining the missing research reasoning*.
Every component reframes. **Each row must be testable or at least interpretable on
its own** — that is non-negotiable.

| Function | FROM (search-assistant) | TO (reasoning scaffold) | How we measure it | Success | Failure |
|---|---|---|---|---|---|
| **Orientation** | (none — start sampling) | Elicit the model's prior on the problem *class* before acting | Is the stated knowledge correct, relevant, and *used* in the first experiments? Compare elicited prior to known structure | States a correct, relevant prior (e.g. "lr & bs co-scale; larger batch tolerates higher lr; optimal lr falls with N") and its opening experiments follow it | Vacuous/wrong/irrelevant knowledge, or correct knowledge it then ignores |
| **Hypotheses** | (implicit) | Reflection = explicit, falsifiable hypotheses about the space | Are hypotheses testable and informative? Tag each as falsifiable/not; does an experiment follow that could refute it? | "Optimum is high-lr + large-bs; loss should drop as I raise both" — falsifiable, then tested | No hypothesis; vague/untestable ones; hypotheses untethered to experiments |
| **Experiment design** | Cover the grid | Choose experiments that *reduce uncertainty / discriminate hypotheses* | Does each experiment test the current hypothesis? Is it information-bearing (vs redundant/random)? | Experiments chosen to confirm/refute a named hypothesis; few, pointed | Tiling, repeats, or random probes unconnected to any hypothesis |
| **Analysis** | "loss went down" | Domain-grounded interpretation + belief update | Does it correctly read the result and update? Is the inference directionally right? | "This refutes H1 (bs didn't matter at low lr); revise to H2" | Misreads results; no update; confabulates a result/explanation |
| **Method/tool selection** | (none) | Recognize problem class; use the right instrument (incl. offloading to an optimizer) | Does it identify structure and pick an appropriate method? | "This is smooth low-dim optimization — coarse-sweep then refine, or hand to BO" | Manual fumbling with no recognition of the problem's shape |
| **Outside help** (critic / partner / reflector) | Advisor suggests configs | A partner that *challenges hypotheses and brings knowledge* | Does the help improve the *reasoning* (not just the next config)? Measure outcome with/without, and whether advice is on-grid/valid | Critique catches a flawed hypothesis or a frozen axis; net-positive | Noise, off-grid/invalid suggestions, steering into dead zones |
| **Termination** | Force a finish (C4) | Stop when marginal information is low / hypotheses converge | Does it stop for the *right reason*? Distinguish converged-stop vs satisfice-early vs wander | Stops once confident and evidence has converged | Satisfices early (under-informed) or never commits (wanders) |
| **Generalization** | (none) | Carry principles A→B→C→W2S | Does a principle learned in A speed up / improve B & C? | Applies the discovered lr×bs relationship to solve B faster than from scratch | Re-derives everything per env; no transfer |

## Metrics (the combined set)

Regret alone is the optimizer's game — but it still tells us things, and several
reasoning-native metrics matter more as we scale:

- **Reaches the optimum consistently** — valuable; a competent reasoner should hit
  it in the *majority* of runs on a simple env.
- **Cumulative regret across trials** (sum over the trajectory) — rewards a good
  *path*, not just a lucky endpoint; a BO-style quality measure of the whole search.
- **Sample efficiency** — experiments-to-good-answer; matters little here, decisively
  in larger problems, and we can measure it cheaply on StepLaw.
- **Hypothesis correctness** — is it inferring directionally well? Tells us whether
  the *reasoning* is sound independent of the outcome.
- **Generalizability** — the headline win: competent in A, *and* carries that to
  B, then C, then W2S. Measured by transfer across the ladder.

## Design constraints (hold the line on these)

- **Testable/interpretable at every step.** If we add a step (orient, hypothesize,
  design, analyze), we must be able to *check that step on its own* — was the prior
  applicable, did the experiment test the hypothesis, was the hypothesis informative.
  An un-inspectable step doesn't go in.
- **Do not overdesign.** An overly prescriptive harness wins on Env A and *breaks
  on generalization*. We want to scaffold the *process*, not script the *answer*.
- **Do not bias the priming.** When we ask the model what it knows / how it would
  approach the problem, we must not feed it a curated/answer-leaking set of facts.
  We seed it with the *question*, then measure how well *it* runs the scientific
  process at each step. The point is to observe the model's own reasoning, not to
  puppet it.

## What this is NOT

We are **not** building a better grid-searcher. If coverage is what we want, we
use a coverage algorithm. We are building — and trying to *rescue with harness
engineering* — a weak model's ability to do **knowledge-grounded, hypothesis-driven
research** that an optimizer cannot do and that *transfers* to problems where
search is impossible.
