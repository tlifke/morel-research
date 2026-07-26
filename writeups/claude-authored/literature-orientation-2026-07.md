# Autoresearcher literature orientation — where this work sits

**By Claude Opus 5** (`claude-opus-5[1m]`), via Claude Code · 2026-07-25

> **Authorship note.** Written end-to-end by an LLM at the researcher's request,
> as orientation material for the next phase. Judgments about novelty and
> positioning are the model's and are the kind of judgment this repository's own
> notes flag as unreliable (`feedback_opus_research_taste_caveat`). Treat the
> citations as verified and the rankings as opinion. Every paper below was
> retrieved and read at abstract level or deeper; papers I could not read past
> the abstract are marked.

---

## 0. Summary of what changed

Two things a reader of this repo should know before planning the next phase:

1. **StepLaw's landscape is convex with a broad optimum, and this is a stated
   finding of the source paper.** That materially changes how Env A results
   should be interpreted, and it complicates — possibly inverts — the
   axis-freezing diagnosis. Section 1.
2. **The central hypothesis of study 005 was independently tested and published
   in July 2026**, and the published result does not straightforwardly agree
   with it. Section 3.

Neither is fatal. Both change what is novel and what needs a control.

---

## 1. StepLaw itself (the Env A substrate)

**Predictable Scale: Part I, Step Law — Optimal Hyperparameter Scaling Law in
LLM Pretraining.** [arXiv 2503.04715](https://arxiv.org/abs/2503.04715) ·
[project site](https://step-law.github.io/)

Scale: >3,700 models trained from scratch, ~100T tokens, ~1M H800 GPU-hours.

Three findings that bear directly on this repo:

**(a) The landscape is convex with a broad optimum.** The paper states that
under fixed *(N, D)*, the hyperparameter landscape "exhibits convexity with a
broad optimum," and presents this as a *practical convenience* — it is why
hyperparameter search is tractable at all. Env A is therefore a smooth, convex,
two-dimensional problem with a plateau.

Consequences for study 005:

- Regret differences on a plateau are compressed by construction. A median
  regret of 0.0016 versus 0.016 is not obviously a meaningful gap unless it is
  reported against the plateau's width. Right now the investigation docs report
  regret without a scale reference, and a skeptical reader cannot tell whether
  0.016 is a catastrophe or a rounding error.
- StepLaw's own fitted estimator lands within **0.094%** of the exhaustive-search
  optimum. That is a natural, external, non-arbitrary reference line for "what
  good looks like" on this substrate, and it is free.
- The `reasoner-not-optimizer.md` warning — that a harness tuned to win on Env A
  overfits to a task an algorithm should own — is *more* true than the document
  assumes. Convex + smooth + 2-D is precisely the regime where Bayesian
  optimization is near-optimal.

**(b) Optimal batch size depends primarily on D and is largely invariant to N;
optimal learning rate follows a power law in both.** This is the paper's
headline decoupling result.

This is the uncomfortable one. The repo's central empirical finding on this
substrate — nemotron "freezes one axis, usually batch size, and treats lr and bs
as independently optimizable" — is currently written up as a *reasoning failure*
(`project_axis_freezing_coverage_failure`: "no joint-interaction reasoning").
But partial decoupling of lr and bs is what StepLaw itself concludes, and a
"larger batch tolerates higher lr" heuristic is standard practice. The model may
not be failing to reason. It may be **applying a roughly correct prior that
does not hold inside a single fixed-*(N,D)* cell** — a transfer error, not an
inability to reason jointly.

That reframing is more interesting than the current one, and it is testable:

- Does the model *state* a decoupling prior when asked (Orienter output)? If it
  states "bs is roughly independent of lr" and then acts on it, it is
  transferring a real fact to a context where it does not apply. That is a
  *knowledge-application* failure, which is squarely on the reasoner thesis.
- Does the freeze persist in the abstract/relabelled arm, where no lr/bs domain
  prior is available? The relabelling arm is already designed in
  `agent-mdp-design.md` and now has a much sharper purpose than "separate domain
  knowledge from structured reasoning." It is the discriminating experiment
  between "bad prior" and "cannot reason jointly."

**(c) The 1,911-row CSV.** Vendored correctly; CC-licensed; the environments
are real. No issue here — the substrate choice was sound, the interpretation is
what needs work.

---

## 2. The field, in four clusters

### Cluster A — benchmarks and systems for AI research agents

| Work | What it is | Relevance |
|---|---|---|
| [MLE-bench](https://arxiv.org/abs/2410.07095) (OpenAI, 2024) | 75 Kaggle competitions, human baselines from leaderboards | The standard. o1-preview + AIDE reaches bronze in 16.9% |
| [RE-Bench](https://arxiv.org/abs/2411.15114) (METR, 2024) | 7 open-ended ML research environments, 71 8-hour attempts by 61 human experts | The only serious *human baseline* in the field. Agents score 4× humans at 2h; humans overtake at longer budgets |
| [AIRA_2](https://arxiv.org/pdf/2603.26499) (2026) | Identifies three bottlenecks in research agents; async multi-GPU pool, hidden-consistent evaluation, ReAct operators | 81.5% mean percentile on MLE-Bench-30 at 24h. Directly relevant: their bottleneck #2 is *validation-based selection overfitting over long horizons* |
| [AARRI-Bench](https://arxiv.org/pdf/2606.07462) (2026) | "Act As a Real Research Intern" — granular research scenarios, judgment and thoroughness rather than macro execution | Best config (Mini-SWE-Agent + Opus 4.7) at 68.3%. **Concludes that progress "requires further exploration of research behavior, rather than merely complex scaffolding"** |
| [PostTrainBench](https://arxiv.org/pdf/2603.08640) (2026) | Can agents automate LLM post-training | Closest task-shape to study 003 |

**The gap this repo sits in:** every one of these evaluates frontier or
near-frontier models. None of them work at 4B. That is a genuine, unoccupied
position — with the caveat in §3.

### Cluster B — harness versus model

This is study 005's cluster and it got crowded in the last three months.

- **[From Model Scaling to System Scaling: Scaling the Harness in Agentic AI](https://arxiv.org/html/2605.26112v1)**
  (2026). Decomposes the harness into six components (reasoning substrate,
  memory, context constructor, skill routing, orchestration loop, verification/
  governance) and argues current benchmarks *conflate model capability with
  harness design*. Names three bottlenecks: context governance ("exposure
  without access"), trustworthy memory ("stale-but-confident"), and dynamic
  skill routing ("confident-but-unchecked").

  Note for study 000: their "stale-but-confident" memory failure — information
  that was correct becoming outdated silently — is the same structure as the
  framework-drift finding, arrived at independently and in a different domain.
  That is a citation the drift writeup currently lacks and should have.

- **[Better Harnesses, Smaller Models: 90% Cheaper Agents via Automated Harness
  Adaptation](https://arxiv.org/html/2607.08938)** (July 2026). **This is study
  005's thesis, executed.** A meta-agent diagnoses failures in small-model
  trajectories and proposes targeted harness modifications (context, tools,
  agent-loop hooks). Best SLM recovers 89.7% of frontier performance at 4% of
  cost. Five failure modes: tool-use, instruction-following, knowledge,
  long-context, planning. See §3 for why their result complicates yours.

- **AARRI-Bench's conclusion** (above) that scaffolding complexity is not the
  lever — independent support for `reasoner-not-optimizer.md`.

### Cluster C — LLMs for hyperparameter optimization

This cluster is the one the repo is least grounded in, and it is the one study
005's task actually belongs to.

- **[AgentHPO](https://arxiv.org/pdf/2402.01881)** (2024). Creator/Executor
  two-agent split. Beats random search by 2.65% and BO by 1.39% at T=10. The
  ancestor of this task shape.
- **[When Is an LLM Worth It for Hyperparameter Optimization? A Budget-Matched
  Study](https://arxiv.org/html/2606.21641v1)** (June 2026). **Read this one
  first.** Central finding: LLM-HPO advisors look effective because they are
  seeded with a hand-chosen default configuration, not because their proposals
  are good. The default alone reaches 88.7% CV accuracy; the LLM's proposals add
  **+0.40 pp**, and **−0.01 pp** on held-out test. When classical search is
  given *the same default seed*, the advisor's lead vanishes within 5
  evaluations and is *behind* by 12.

  They attribute three methodological errors to prior LLM-HPO work: weak
  baselines, single trials without statistical analysis, and crediting the model
  with gains that came from the initialization.
- **[Small LLMs with Expert Blocks Are Good Enough for Hyperparameter
  Tuning](https://arxiv.org/html/2509.15561v3)** — the small-model version of
  the same question.
- Converging reports that LLM surrogates are weaker than GP-BO and SMAC, and
  competitive only below roughly a dozen features.

**Implication, stated plainly:** study 005 currently has *no classical baseline
at matched budget*. Not random search, not grid, not TPE. On a substrate that is
a zero-cost CSV lookup, where such baselines cost seconds to run. Anyone from
this cluster will ask the question immediately, and the honest answer today is
that a random search at 14 evaluations might well beat nemotron's median.

### Cluster D — failure diagnosis and long-horizon degradation

- **[Coherence Collapse: Diagnosing Why Code Agents Fail After Reaching the
  Right Code](https://arxiv.org/pdf/2603.24631)** (2026). Agents find the right
  solution and then fail to execute it; diagnosed via a trajectory-evaluation
  framework separating solution-finding from execution failure. **This is study
  004's actuation-versus-capability dissociation, in a different domain.** The
  repo's C4 result (finish-actuation fixes finishing, not thinking) is the same
  shape.
- **[Beyond the Leaderboard: A Synthesis of Tool-Use, Planning, and Reasoning
  Failures in LLM Agents](https://arxiv.org/pdf/2607.05775)** (July 2026).
  *Could not read past the abstract — PDF text extraction failed. Worth a manual
  read; a taxonomy synthesis is exactly the thing to position T1–T8 against.*
- Independent reports that coherence degrades after ~20–30 tool calls even at
  200K context, with the failure surfacing as **re-executing completed steps** —
  which is precisely the redundant-rerun metric study 004 built for T8. The
  metric was well chosen and independently converged upon.
- [Dissecting model behavior through agent trajectories](https://arxiv.org/pdf/2606.17454)
  (2026) — trajectory-level attribution. *Abstract only.*

### Cluster E — judges

- **[Can LLM-as-a-Judge Reliably Verify Rubrics in Agentic Scenarios?](https://arxiv.org/pdf/2606.29920)**
  (June 2026) — directly the question of study 004 inv 002 / 005 inv 003.
- Practitioner consensus is converging on: 75–90% judge-to-human agreement
  before trusting a judge, κ ≥ 0.6 on the rubric *before* calibrating, and
  ~500 cases before trusting aggregate metrics. The repo's judge work is at
  n=8–20.

### Cluster F — the weak-to-strong anchor and its critics

- [Automated Weak-to-Strong Researcher](https://alignment.anthropic.com/2026/automated-w2s-researcher/)
  (Anthropic, April 2026) — the study-003 anchor. PGR 0.97 in 5 days /
  800 agent-hours / ~$18,000, versus 0.23 from human researchers in 7 days.
- **[Automated alignment is harder than you think](https://arxiv.org/pdf/2605.06390)**
  (May 2026) — the critique. Central concern is **undetected errors**: outputs
  that look correct but contain subtle mistakes evaluation fails to catch, plus
  Goodhart effects on outcome-graded benchmarks and *correlated uncertainty
  across evaluators* making consensus grading unreliable.

  That last point is a direct hit on the multi-LLM judge panel design. The repo
  already found it empirically — judges agree on easy traces and fracture on
  hard ones, and nemotron-agreeing-with-a-shallow-heuristic was correctly
  flagged as a trap. The literature has a name for the mechanism and an argument
  for why panels do not fix it.
- What the field is watching for on the Anthropic result: whether it replicates
  externally, and whether the discovered methods generalize. **Study 003 is
  literally an external replication attempt of the substrate.** That is worth
  more than the repo currently claims for it.

---

## 3. Where this work sits

### What has been overtaken

**The harness×scale crossover hypothesis.** `project_harness_scale_interaction`
states the thesis as: rich scaffolding helps a 4B and hurts an Opus-class model,
anchored on AutoLLMResearch versus the Anthropic w2s paper.
[2607.08938](https://arxiv.org/html/2607.08938) tested essentially this and
reports something different: **more capable small models benefit *more* from
harness adaptation** (+48.8% for stronger SLMs versus +15.5% for weaker ones),
and "harnesses can absorb substantial task difficulty but cannot fully replace
missing core model capabilities."

That is not a crossover. It suggests harness benefit *increases* with capability
across the small-model range, then presumably falls at frontier (where the
Anthropic minimal-harness finding lives) — an inverted U, with the peak
somewhere well above 4B.

If that shape is right, **nemotron-4b may sit below the floor where harness
engineering pays at all**, and much of study 005's difficulty is explained by
having picked a protagonist under the threshold. The repo's own data is
consistent with this: C4 (a deterministic actuation hook, the crudest possible
intervention) was the only clean win, while every intervention requiring the
model to *use* added context — Critic v1, C1-self reflection, patch 2's
instructions — backfired. That is what "below the harness-adaptation floor"
looks like.

Their harness taxonomy also maps onto the repo's components almost exactly:
context adaptations ≈ R2/R3, tool adaptations ≈ the substrate interface, agent
loop adaptations ≈ C4 and the guards. Their finding that agent-loop hooks are
the robust category and context additions the fragile one at low capability is
the repo's Phase-1 result, at larger scale.

### What is still unoccupied

1. **The 4B floor itself.** Nobody in this literature works below ~8B. If the
   inverted-U hypothesis above is right, then *locating the floor* — the
   capability threshold below which harness engineering stops paying — is a real
   contribution, and this repo has more data on the sub-8B regime than anyone
   cited here. This reframes two months of "failure to rescue nemotron" as
   *measurement of a threshold*, which is a result rather than a disappointment.
2. **Role-level decomposition as a diagnostic instrument.** The society design
   (Orienter → Hypothesizer → Designer → Analyst → Terminator) with per-role
   judges localizes a failure to a *role*. AIRA_2 and 2607.08938 diagnose at the
   trajectory level; Coherence Collapse separates find-versus-execute. Nobody
   cited here does per-role causal localization with the "freeze is born in the
   Orienter and inherited" resolution. This remains the repo's most distinctive
   asset and matches the cross-study note's own ranking.
3. **Harness-artifact discipline.** The repeated finding that apparent capability
   failures were substrate or renderer bugs — the Ollama Qwen3-Hermes-versus-XML
   renderer mismatch especially — is a methodological contribution the field
   visibly needs, given that 2605.26112's central complaint is that benchmarks
   conflate model and harness. A short paper of the form "here are five findings
   we nearly published that were harness artifacts, and the protocol that caught
   them" would be read.
4. **Negative results at small scale.** Nothing in this literature reports
   what does *not* work at 4B with the specificity this repo has.

### What is at risk

- **Regret numbers with no classical baseline and no plateau reference.** After
  [2606.21641](https://arxiv.org/html/2606.21641v1), this is the first question
  any reviewer asks.
- **Judge panel claims at n=8–20** against a field norm of ~500 for aggregates.
  The repo's own instinct (`feedback_case_studies_over_aggregates`) is the right
  response: report these as case studies, not rates.
- **The axis-freezing framing**, per §1(b).

---

## 4. Concrete recommendations for the next phase

Ordered by cost-to-value.

**1. Run the classical baselines on StepLaw. (Hours.)**
Random search, grid, and TPE/GP-BO at matched evaluation budgets (n = 6, 10, 14,
20 — the range nemotron actually uses), 20 seeds, all three environments. Report
nemotron, gemini, and the classical methods on one axis. Also plot StepLaw's own
0.094% estimator line and the plateau width.

This does three things: it makes every existing regret number interpretable; it
pre-empts the field's standard objection; and per `reasoner-not-optimizer.md` it
*is the point* — the thesis is that the LLM should not be competing here, so
showing it losing to BO on Env A is confirmation, not embarrassment. The one
outcome that would be genuinely bad is discovering nemotron also loses to random
search, and that is worth knowing immediately.

**2. Re-run the abstract/relabelled arm as the axis-freezing discriminator.
(Already designed.)**
Reframed per §1(b): does the freeze survive removal of the lr/bs domain prior?
Bad-prior and cannot-reason-jointly predict opposite outcomes. This is the
cheapest experiment that converts a soft claim into a sharp one, and it is
already specified in `agent-mdp-design.md`.

**3. Reposition the study-005 question around the floor.**
From "can a rich harness substitute for training at 4B" — now partially answered
elsewhere, and answered *no* in the form the repo asked it — to **"where is the
capability floor below which harness engineering stops paying, and what fails
first as you cross it?"** The repo has the instrument (T1–T8, role-level judges),
the substrate, and the negative results. It needs a second and third protagonist
to make it a curve rather than a point: nemotron-4b plus something at ~8B and
~14B, same harness ladder. That is a real result and nobody has it.

**4. Verify the leak question before anything else in inv 002.**
Unchanged from the cross-study note; §2 item 8 is still the strongest signal in
the repo and still resting on an unverified assumption.

**5. Add related-work grounding to anything published.**
Study 000's drift piece needs 2605.26112's "stale-but-confident" memory
bottleneck. Study 005 needs cluster B and C. Study 004's T8 needs the coherence
literature. Study 003 needs the automated-alignment critique — which
substantially *raises* the value of an external replication attempt.

**6. Do not build a custom harness yet.**
The open strategic fork in `framework-drift-evidence.md` §8 leans toward a
custom substrate. Cluster B's finding — that harness complexity has
capability-dependent returns and that agent-loop hooks are the robust category
while context additions are fragile — argues for the opposite: minimal
deterministic hooks, and spending the effort on the protagonist ladder in
recommendation 3 instead.

---

## 5. Things I made up that you should review

1. **The inverted-U reading of harness benefit versus capability** is my
   synthesis of two papers that do not make that claim jointly. 2607.08938
   reports monotone-increasing benefit across three SLMs; the Anthropic w2s
   result is a separate paper with a different task. Joining them into a curve
   is interpretation.
2. **"nemotron-4b may sit below the harness-adaptation floor"** follows from
   that interpretation and is therefore also unverified. It is testable via
   recommendation 3, which is why I ranked that recommendation where I did.
3. **The axis-freezing reframe** rests on my reading of StepLaw's decoupling
   result. I have not checked whether within-cell lr×bs interaction is strong in
   the specific Env A slice — that is checkable directly from the vendored CSV
   and should be checked before the reframe is adopted.
4. **I could not read two relevant papers past the abstract** (2607.05775,
   2606.17454). Both look load-bearing for positioning study 004.
5. **The claim that nobody works below 8B on research agents** is an absence of
   evidence from ~15 searches, not a systematic review. One targeted search
   before relying on it.
6. **Publication-venue judgments are absent** because I do not have a reliable
   read on them, and the repo's own memory flags my research-direction taste as
   unreliable. Weigh section 3 accordingly.
