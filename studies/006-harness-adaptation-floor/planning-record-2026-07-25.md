# Planning record — 2026-07-25

_Assembled by Claude (`claude-opus-5[1m]`) via Claude Code from a working
conversation with Tyler on 2026-07-25, at his request, as the reference
document for scoping this study and for building the infrastructure that
follows it._

_**Provenance convention used throughout:** positions marked **(Tyler)** are
his, recorded as stated or as corrected by him in conversation. Everything
else is Claude's analysis and is subordinate to his judgment. Literature
claims were retrieved and read during the conversation; depth of reading is
flagged per source. Where Claude was wrong earlier in the conversation and
corrected, both the error and the correction are recorded, because the
correction is the useful part._

---

## 1. How this study came about

The precipitating event was a literature review that should have happened two
months earlier. Studies 001–005 were conducted with essentially no literature
grounding beyond two anchor papers. A survey run on 2026-07-25 (see
`writeups/claude-authored/literature-orientation-2026-07.md`) found that:

- the central hypothesis of study 005 had been independently tested and
  published in July 2026 while the work was paused;
- the substrate used in study 005 (StepLaw Env A) has properties the source
  paper states explicitly and that the investigation docs never accounted for;
- an entire literature cluster (LLM-driven hyperparameter optimization) sits
  directly under study 005's task shape and was never consulted, including a
  June 2026 paper whose central finding undercuts the standard experimental
  design in that cluster.

**(Tyler)** on the lesson:

> "We absolutely must must must ground ourselves in the literature before
> doing research. The research direction I'm going in wasn't wrong — the
> publishing of the smaller models, better harnesses paper is really
> interesting and confirms our hypothesis. […] But even if I read it in full
> and you do too and we plan on replicating the results, we'll end up here in
> another month because we aren't keeping up to date on the literature."

The conclusion drawn was **not** to build literature infrastructure first (see
§6), but to attach the next piece of work to a published baseline so that the
grounding is structural rather than a matter of discipline.

---

## 2. The anchor paper, read in detail

**Better Harnesses, Smaller Models: Building 90% Cheaper Agents via Automated
Harness Adaptation.** Chenyang Yang, Xinran Zhao, Tongshuang Wu, Christian
Kästner. [arXiv 2607.08938](https://arxiv.org/abs/2607.08938), submitted
2026-07-09.

_Read: full HTML rendering, two passes (methodology; results and limitations).
The PDF's text layer would not extract. No code or data availability link was
found on the abstract page — **verify before assuming a replication package
exists.**_

### 2.1 Headline claim

Small language models paired with an *automatically discovered, adapted*
harness match frontier-model performance on routine business tasks at ~90%
lower cost. Across 7 tasks × 3 SLM families = 21 pairs: significant
improvement on 16, the SLM–LLM gap closed entirely on 7, best case recovering
**89.7% of frontier performance at 4% of cost** with 25% lower latency.

The framing insight, in their words: much of the task difficulty is *shared
across instances* and can therefore be "lifted from the model into the
harness."

### 2.2 How the tasks were built — the part that matters most here

They authored almost nothing from scratch. All seven tasks are curated from
existing benchmarks, with instance variants generated from templates:

| Task | Source | Instances |
|---|---|---|
| attendance-auditing | TheAgentCompany templates + generated variants | 100 |
| budget-approval | TheAgentCompany templates + new instances | 100 |
| stock-alert | LOCA-Bench selection + pipeline-generated variants | 100 |
| anomaly-detection | LOCA-Bench selection + generated instances | 100 |
| playwright-testing | WebGenBench + frontier-LLM-generated HTML sites | 100 |
| website-management | WebArena CMS subset, filtered to solvable cases | 50 |
| code-refactoring | RefactorBench instances | 100 |

**Three properties of this design are the transferable lessons:**

1. **Grading is described as programmatic.** "Check against ground truth" for
   most; "run generated tests" for playwright-testing; "run tests to check the
   refactored code's AST" for code-refactoring.

   > **Correction, 2026-07-25, after reading the code.** The claim originally
   > recorded here — "no LLM judges anywhere in the pipeline" — **is wrong.**
   > `tasks/budget_approval_s2l/run.yaml` specifies
   > `eval_model: gemini-3-flash-preview` alongside a separate `eval_batch_size`.
   > There *is* a model in the evaluation path, at least for this task, which
   > is unsurprising given that its outputs include free-text manager replies
   > and CFO escalations. "Check against ground truth" in the paper apparently
   > describes the *comparison target*, not a claim that the comparison is
   > performed mechanically.
   >
   > This matters for two reasons. First, it means the verification problem is
   > **reduced** here, not dissolved — an LLM grader comparing against a known
   > answer is a far easier and more constrained job than judging process
   > quality with no ground truth (which is what studies 004/005 attempted),
   > but it is not free of judge-reliability concerns. Second, it is a worked
   > example of why reading the artifact is not optional: the paper's prose
   > implies mechanical checking, and the config says otherwise.
   >
   > **Open item:** read `tasks/budget_approval_s2l/eval.md` and the eval
   > module to determine exactly what the eval model does — full grading,
   > partial grading of free-text fields, or extraction feeding a
   > deterministic check. This bears directly on how much of their headline
   > accuracy numbers rest on a judge.

   The consequence, and the reason this is recorded first: *substrate choice
   and the verification problem are the same decision.* Studies 004 and 005
   spent substantial effort on judge validation because their substrate had no
   programmatic ground truth for process quality. Yang et al. did not build
   better judges; they chose tasks that do not need them. That decision is
   made once, at substrate-selection time, and it either removes an entire
   research direction from the critical path or installs it there permanently.

   **(Tyler)** independently reached the position that the study-004/005 judge
   panel, rubric, and three-tier evaluation artifact are **not** worth
   carrying forward. This paper's design is consistent with that call, and
   supplies the alternative: get ground truth from the task, not from a judge.

2. **A 20/20/60 train/validation/test split per task.** Harness adaptation is
   treated as a *learning problem*. Adaptations are fit on train, selected on
   validation, and reported on test. Any study that tunes harness components
   and reports on the same runs is doing something else.

   Study 005's C1/C4 factorial has no such split — components were selected
   and reported on the same 120 runs. This is the single cheapest methodological
   upgrade available and it is not optional in this study.

3. **100 instances per task.** Enough that per-task claims are about a
   distribution rather than a handful of runs.

### 2.3 The harness optimizer

- **Meta-agent model:** `gemini-3.1-pro-preview`. A *frontier* model designing
  harnesses for a *weak* model — note this is itself an instance of the
  delegation question, resolved affirmatively for this particular delegation.
- **Search:** a **GEPA-style genetic procedure**, sampling candidates from a
  Pareto front (a sampled harness is optimal on at least one training
  instance).
- **Meta-agent context:** four sources — task trajectories, the current
  harness, search-memory summaries of past proposals, and design-space
  documentation.
- **Validity:** candidates get a cheap sanity check before evaluation; invalid
  candidates are returned to the meta-agent for repair, up to a retry cap.
- **Budget:** **$20 per task-model pair**; **$1,260 total** for the main
  experiments. Each pair is optimized **three times**, keeping the harness
  with the best validation score.
- **Implementation:** built on the **OpenHands Software Agent SDK**
  ([arXiv 2511.03690](https://arxiv.org/html/2511.03690v1),
  [github.com/OpenHands/software-agent-sdk](https://github.com/OpenHands/software-agent-sdk)) —
  MIT-licensed, Python, model-agnostic, explicitly supports open-weight models.
  _Resolved 2026-07-25; the earlier open item is closed._
- **Optimizer lineage:** GEPA ([arXiv 2507.19457](https://arxiv.org/abs/2507.19457)),
  an existing published reflective-evolution optimizer, not a bespoke method.

### 2.4 The adaptation taxonomy

Five failure modes, mapped to three adaptation categories:

| Failure mode | → | Adaptation category |
|---|---|---|
| tool-use | | **Tool adaptations** — higher-level custom tools, filtering irrelevant tools, tailoring schemas |
| instruction-following | | **Context adaptations** — detailed instructions, examples, domain guidance in the system prompt |
| knowledge | | |
| long-context | | **Agent-loop adaptations** — deterministic checks/hooks, programmatic safeguards |
| planning/reasoning | | |

Observed frequencies: successful adaptations most often address
instruction-following (81%) and knowledge (81%) failures, via adding context
(86%), creating tools (43%), and managing tools (29%).

Worked example given in the paper (budget-approval): narrow the action space
from many MCP tools to a curated set; rewrite the system prompt into an
explicit step-by-step procedure; add an `anti_loop_hook.py` safeguard.

_Caveat: the paper does not state who labeled failure modes or report
inter-rater agreement. The taxonomy appears derived from surveying model cards
and agentic benchmarks rather than from annotated trajectories._

### 2.5 Their models, and the correction that matters

| Model | Total params | Active params |
|---|---|---|
| gemma-4-26b-a4b | 26B (MoE) | ~4B |
| qwen3-coder-30b-a3b | 30B (MoE) | ~3B |
| ministral-3-8b | 8B | 8B (dense) |
| gemini-3.1-pro-preview | frontier baseline | — |

Per-instance costs: $0.002–$5.785 depending on model and task; SLMs 4–96%
cheaper than the frontier model.

> **Recorded error and correction.** Earlier in the conversation Claude read
> these as 8B–30B models and concluded that nemotron-3-nano:4b "may sit below
> the harness-adaptation floor," offering that as an explanation for study
> 005's difficulty. **That reading was wrong.** In *active* parameters their
> models are 3–8B, and their best performer — `gemma-4-26b-a4b`, the +48.8%
> improver — activates ~4B per token, comparable to study 005's protagonist.
>
> The surviving difference is **total capacity (stored knowledge), not
> inference compute.** That is a different and sharper hypothesis, and it is
> directly testable with the Gemma 4 ladder below, which spans both axes.

### 2.6 Their key finding about capability

"Models with stronger capabilities perform better and improve more with
optimized harnesses": `gemma-4-26b` improved **+48.8%**, `ministral-3-8b`
**+15.5%**. Their framing: "harnesses can absorb substantial task difficulty
but cannot fully replace missing core model capabilities."

This is **monotone-increasing benefit with capability across their range**,
not the crossover that study 005's thesis
(`project_harness_scale_interaction`) predicted. Combined with the Anthropic
weak-to-strong finding that minimal harnesses beat structured ones at
frontier, Claude proposed an **inverted-U** reading — benefit rising with
capability through the small-model range and falling at frontier.

> **Flagged as interpretation, not result.** That curve joins two papers that
> do not make the claim jointly, on different tasks. It is a hypothesis this
> study can test, not a premise it should assume.

### 2.7 Their rigor, assessed honestly

Recorded because **(Tyler)** raised a concern that published work is "well
beyond anything we've done here," and the comparison is more mixed than that.

**Weaker than study 005's factorial:** three runs per configuration, averaged.
No significance test stated. Temperature not stated. The task-diversity finding
— a strong negative correlation (Spearman ρ = −0.96) between task diversity
and optimized-harness performance, with diversity measured as normalized
Levenshtein distance over tool-call sequences — rests on **n = 7 tasks**.

**Genuinely ahead of anything in this repo:** train/val/test discipline;
programmatic grading; task provenance from established benchmarks so nobody
argues about task validity; a deployment-relevant framing; related-work
grounding.

**The lesson:** the gap is in *setup*, not statistical sophistication. Setup is
fixable at planning time, which is what this document is for.

### 2.8 Their stated limitations

- *Internal validity:* runs and the optimization process are highly stochastic
  even with repeated runs.
- *External validity:* one set of tasks, models, and a single optimizer
  implementation; may not transfer to other tasks, future models, or other
  optimizers.
- Scope limited to tasks with clear metrics in clean environments, not complex
  deployment scenarios.
- **Reproducibility threatened by black-box API evolution** — `gemini-3.1-pro-preview`
  is a preview model that will move. *This is a direct argument against a pure
  replication and in favor of the downward extension: an extension retains
  value when the baseline drifts; a replication does not.*

---

## 3. The Gemma 4 ladder

Released 2026-04-02, Apache 2.0, open weights, pre-trained and instruction-tuned
variants. _Source: Gemma 4 technical report ([arXiv 2607.02770](https://arxiv.org/html/2607.02770v1))
and Google model documentation; read at overview level._

| Variant | Total | Active / effective | Notes |
|---|---|---|---|
| E2B | — | 2.3B effective | edge/mobile/browser tier |
| E4B | — | 4.5B effective | edge tier |
| 12B | 12B | dense | unified multimodal, encoder-free |
| **26B MoE** | **26B** | **3.8B active** | **the paper's model** |
| 31B | 31B | dense | server-grade |

**Why this ladder is the right instrument:**

- It is **single-family**, removing the cross-family confound that made study
  003's model comparisons hard to interpret.
- It **separates the two axes** that §2.5 identified as confounded: 26B-MoE
  (3.8B active, 26B total) versus 12B dense versus E4B (4.5B effective)
  spans total capacity at near-constant active compute, and vice versa.
- **It is open-weight and locally runnable.** This substantially changes the
  cost model: the SLM inference runs on the RTX 3080, not through an API.
  Only the meta-agent costs money. The $20/pair figure is therefore an
  *upper* bound for this replication, not a floor.

---

## 4. What a "harness" concretely is

**(Tyler)** asked whether the harness is a terminal interface to use
interactively, or something launched from a command line that runs by itself.

**It is the second.** In this literature a harness is a *program*, not a UI:

- a **control loop** (receive input → reason → optionally call tools → observe
  result → repeat until done),
- a set of **tool definitions** exposed to the model,
- a **system prompt** / context construction policy,
- **hooks** that intercept steps to log, validate, or redirect them,
- plus session state, compaction, and permission handling.

Claude Code, Codex, and Pi are harnesses in this sense — they are agent
runtimes that own capabilities larger than a model call. The study-005 harness
(`researcher.ts` on Pi) is one too.

So an "adapted harness" in Yang et al. is a **set of configuration artifacts**:
a rewritten system prompt, a curated tool list with tailored schemas, and hook
scripts such as their `anti_loop_hook.py`. The meta-agent's output is those
artifacts. Nothing about it is interactive; a run is a CLI invocation that
executes autonomously and emits a trajectory.

_Implication for build effort: the deliverable of the harness optimizer is
text and small scripts, which is why $20 of frontier tokens can produce one.
The expensive part is not generating candidates — it is **evaluating** them
across instances, which is where the local GPU does the work._

---

## 5. Scope of the first investigation

**(Tyler)**, defining it:

> "This should be defined as its own study with a clear, specific scope — test
> a smaller Gemma 4 model and see if we can apply the exact same process, with
> the same $20 budget for building the harness they utilize in the small
> models, better harness paper. And we apply it to one of the 7 tasks. This is
> feasibility testing."

Deliberately **feasibility, not result**. What it should produce:

1. A yes/no on whether the process runs end-to-end at a smaller scale.
2. A cost and wall-clock accounting (meta-agent spend; local GPU hours;
   human hours).
3. **A list of every place the published method is under-specified** — this is
   the durable output, and per study 003's experience it is where the real
   time goes.
4. A decision on whether the full ladder is worth running.

Success criteria are programmatic by construction (§2.2), so no judge
validation is on the critical path.

### 5.0 The replication package — verified to exist

_Checked 2026-07-25 after the scoping decision. This changes the shape of the
first investigation from reconstruction to reuse._

**[github.com/malusamayo/migration-analysis](https://github.com/malusamayo/migration-analysis)**
is the paper's replication package. The repository name does not mention the
paper, which is why the first pass missed it; it is confirmed by the README.

Contents:

- `data/*.json` — **task datasets committed to the repo**, including
  `budget_approval_s2l_{medium,high,extra_high}.json`, plus
  `attendance_payroll_audit_s2l_*`, `machine_operating_s2l`,
  `refactorbench`, `webarena_shopping_admin_easy`, `webtest`,
  `woocommerce_stock_alert_s2l`.

**What `low / medium / high / extra_high` actually are — resolved.** Not an
effort or reasoning-budget setting, despite the resemblance to LLM effort
terminology. They are **workflow-diversity tiers**, defined by how many
templates are drawn into the slice. From
`tasks/budget_approval_s2l/metadata.yaml`: a "compositional diversity sweep
over 20 template specs built from a shared atom library" of documents, contact
queries, computations, and actions.

| Tier | Templates included |
|---|---|
| low | 1 |
| medium | 3 |
| high | 8 |
| extra_high | 20 |

**All slices share identical MCP servers, setup modules, and evaluation
modules** — the *only* thing that varies is template composition in the data
file. Each tier has its own `run_*.yaml` and `gepa_optimize_*.yaml`.

This is the controlled experiment behind the paper's ρ = −0.96 diversity
finding (optimized-harness performance falling 89.1% → 68.0% as diversity
rises), and the paper describes exactly this construction for the budget and
attendance tasks — which is why only those two tasks carry the suffixes.

_Consequence: a clean second axis is available for free on the chosen task._
Where the model ladder asks "how small before the process fails," the diversity
ladder asks "how varied before it fails," on identical infrastructure. If a
floor exists, the interesting result is plausibly a **surface** over both —
and running `low` first is also the cheapest possible smoke test, since it is a
single template.
- `src/` — core implementation; `run.py` — experiment orchestrator, with
  `run.py run-baseline` and `run.py run` (GEPA optimization), configured by
  manifest.
- `tasks/<task_id>/run*.yaml` — task configurations referencing the data.
- `replication_package/` — scripts to re-render the paper's tables and figures.
- `included_task_model_seed_triplets.csv` — the exact triplets used for the
  paper-scale experiments.
- Large artifacts (raw runs, eval outputs) on figshare:
  `https://figshare.com/s/520e6259e3cc730c358d` — two archives, one sufficient
  for re-rendering, one needed to recompute from raw runs.

**The project uses `uv`**, which matches this repo's conventions directly.

**Stated prerequisites:** "The task server Docker image and model/API
credentials must be available before launching new experiments." Models
named include Gemma, Gemini 3.1 Pro Preview, and Claude variants.

### 5.0.1 The three risks, checked (2026-07-25)

**Risk 1 — task server Docker image: CLEARED.** `docker-compose.yml` defines
11 services including `budget_approval_s2l`, and **all images build locally**
from `tasks/Dockerfile` (or `tasks/Dockerfile.loca`) with `context: .`. Both
Dockerfiles are present in the repo. Nothing is pulled from a private registry.
`run.yaml` confirms `docker: true`, `server_image: budget_approval_s2l:latest`.
The only remaining question is whether the build succeeds, which is an
empirical matter of an afternoon.

**Risk 2 — local model substitution: LIKELY FINE, one known gotcha.**
`run.yaml` names models as bare aliases (`ministral-3-8b`,
`gemini-3-flash-preview`) with no `base_url` in the task config, so routing is
resolved elsewhere — almost certainly LiteLLM, which the OpenHands SDK uses and
which supports local Ollama/vLLM endpoints via provider prefixes and env vars.
Unverified but low-risk.

> **Gotcha:** `.gitmodules` declares the SDK submodule over **SSH**
> (`git@github.com:malusamayo/software-agent-sdk.git`). A plain
> `git clone --recursive` will fail without GitHub SSH keys configured. Fix
> with `git config --global url."https://github.com/".insteadOf git@github.com:`
> or by editing `.gitmodules` after cloning.

**Risk 3 — license: NOT CLEARED. See §5.0.2.**

**Submodules:** `software-agent-sdk` → a **public fork** of the OpenHands SDK
under the authors' account, carrying the upstream **MIT** license (clean).
`LOCA-bench` → `https://github.com/malusamayo/LOCA-bench.git`, public over
https. Budget-approval derives from TheAgentCompany rather than LOCA-bench, so
the latter may not be needed for the first investigation.

### 5.0.2 Licensing — the actual position

**The repository has no LICENSE file, and the GitHub "About" panel shows no
license.** The working assumption that "it's public, so we can use it" is
**not correct as a matter of copyright**, and the distinction matters here
because the intent is eventually to publish.

- Absent a license, the default is **all rights reserved**. Public
  availability grants nothing by itself.
- GitHub's Terms of Service grant other GitHub users only the right to **view
  and fork within GitHub**. They do not grant rights to use, run, modify, or
  redistribute the code outside that mechanism.
- Practically: running it privately to replicate is low-risk and routine, and
  the authors labelled it a *replication package*, which signals clear intent
  to permit exactly that. The exposure appears when **vendoring their code or
  data into a public repo, or publishing derived results.**

**Recommended action, cheap and high-yield: email the authors and ask them to
add a license.** Chenyang Yang (CMU, GitHub `malusamayo`). The repo has 2 stars
and 1 fork — a replication attempt is likely to be welcomed, and adding a
LICENSE file takes them two minutes. This also opens a correspondence with the
authors of the paper this study is built on, which is worth more than the
license.

**Independent of their license:** the task data derives from upstream
benchmarks that carry their own terms — **TheAgentCompany** (the source for
budget-approval), plus WebArena, RefactorBench, WebGenBench, and LOCA-bench for
other tasks. Those licenses govern the derived data regardless of what the
authors do with theirs. **Check TheAgentCompany's license specifically before
vendoring any budget-approval data.**

### 5.1 Task selection — decided

**(Tyler)**, deciding:

> "Let us start with budget approval. That's the simplest case and if it works,
> we can try other tasks. If the replication package or code exists, we can
> re-use their setup — otherwise, we'll go back to the source benchmarks and
> follow the methods of the paper as close as we can."

**Decision: `budget-approval`, reusing their package** (§5.0 confirms it
exists).

**What the task is** (from the paper): the agent must collect, review, and
communicate budget requests in a company — gather requests, retrieve prices and
budget policies, then reply to requesters. Graded by check-against-ground-truth.

**Their published numbers on it**, which become this study's reference line:

| Condition | Accuracy | Cost/query |
|---|---|---|
| Frontier (gemini-3.1-pro-preview) | 97.3% | $0.22 |
| SLM, unadapted harness | 75.0% | — |
| SLM, optimized harness | **98.3%** | — |

This is a good feasibility target: a wide, unambiguous gap (75.0 → 98.3) with
the optimized SLM *exceeding* the frontier model, so a partial reproduction is
still interpretable. Derived from TheAgentCompany templates with
researcher-generated variants; 100 instances; 20/20/60 split.

_Superseded — Claude's original selection criteria, retained because they
remain the reasoning to apply when choosing the second task:_

- **Local reproducibility.** Can the task's environment run on the desktop
  without a web stack or hosted services? `code-refactoring` (RefactorBench)
  and the LOCA-Bench-derived tasks look most tractable; `website-management`
  (WebArena) and `playwright-testing` carry heavy environment dependencies.
  Study 003's history is unambiguous that environment fragility, not model
  capability, is what consumes the calendar.
- **Checker strength.** AST-based and ground-truth checks are the least
  ambiguous. `code-refactoring` grades by running tests against the refactored
  code's AST — about as unambiguous as it gets.
- **Position on their diversity axis.** Their ρ = −0.96 result says repetitive
  workflows benefit most and diverse ones least, with `code-refactoring` named
  as the *least*-benefiting task. This cuts both ways and the choice should be
  deliberate: a **repetitive** task is the fairest first test of whether the
  process runs; the **diverse** task is where a floor would show up soonest.
  For a feasibility test, argue for the former.
- **Instance count.** 100 instances × multiple candidate harnesses × three
  optimization runs is real local compute. Budget it before committing.

_Open: whether to reconstruct their task variants or to go back to the source
benchmarks directly. Reconstruction fidelity is the main threat to comparing
against their numbers._

---

## 6. Gaps identified, and positions taken

Recorded because these shaped the scope and should shape the infrastructure.

### 6.1 Verification is a research direction, not a step

**(Tyler)**:

> "Without quality judging, without understanding of what success looks like
> and having high quality methods of understanding whether we've achieved that
> success, all the infrastructure in the world won't save us."

Supporting evidence from this repo's own history: at least five findings were
nearly written up before being caught as harness or substrate artifacts (the
Ollama Qwen3-Hermes-vs-XML renderer mismatch; the Pi internal-loop bug; the
Mac/desktop endpoint confound; study 004's pathologies; the coverage "fix" that
encoded Env A's answer). Every catch was ad hoc.

External support: *Automated alignment is harder than you think*
([arXiv 2605.06390](https://arxiv.org/pdf/2605.06390)) names **undetected
errors** as the core failure of automated alignment demonstrations, and warns
that **correlated uncertainty across evaluators** makes consensus grading
unreliable — the mechanism behind this repo's own finding that agreement
between two weak judges is not validation.

**Position for this study:** the verification problem is dissolved *by
substrate choice*, not solved by better judges. That is why programmatic
grading is a hard requirement here.

### 6.2 Reuse is two-way

**(Tyler)**, correcting an over-broad Claude suggestion that the repo's
instruments should be carried forward:

> "The re-usability of our instruments is key as well, but I'd like to be
> careful about what we re-use. I don't agree that the ladder, judge panel and
> rubric, and three tier evaluation artifact are useful. […] It's a two way
> road though — keeping what is not useful is actively destructive."

**Carried forward:** the separation of *tooling/infrastructure* from
*documentation/findings*, so the former can be versioned and reused and the
latter can be archived.

**Explicitly not carried forward:** T1–T8 ladder, judge panel, rubric,
three-tier evaluation artifact, StepLaw as a substrate.

### 6.3 The PI needs error-correction too

Claude raised that "human stays directive" assumes a reliable human, whereas
the study-000 audit found three material errors in Tyler's own recollection of
the work, and that a solo researcher has no peer check.

**(Tyler)**:

> "My goal is to become an expert in autoresearchers, so this is as much about
> training my judgement as it is designing the systems that can work. […] I
> have a handful of individuals that if my work is sufficiently high quality
> for my bar I would seek their opinion before actually publishing. But it is
> worth noting that that is part of the purpose of publishing — even an arXiv
> paper would provide me that sort of feedback."

Recorded as an open thread: an evaluative framework for "is this work good
enough to publish" is itself a task on the list, and publishing is partly *how*
the error-correction is obtained rather than something that waits for it.

### 6.4 Using autoresearchers vs. studying them

**(Tyler)**:

> "My primary goal is to develop autoresearchers that improve my own capacity
> — if I can delegate writing code, can I delegate research direction? I see
> it as an evolution of the usage of LLMs."

So the two are not in tension by his framing: studying autoresearchers is
instrumental to using them. Literature search is deferred but considered
necessary — "autoresearch is not technically about the literature, [but]
knowledge absolutely is."

### 6.5 The infrastructure trap

Claude's caution, recorded because it directly shaped the decision to scope
this study small: three of the four lessons Tyler drew were "build a system,"
and study 000's finding is that this repo already built an organizing framework
that became ceremonial while the mechanism meant to protect it was never built.

**The test proposed:** does the thing get consulted *during* the work, or only
around it? Bookkeeping that is optional goes stale; bookkeeping coupled to an
act already being performed stays true. Applied here: a literature agent
consulted when stuck will survive; a weekly digest will not.

**Decision taken:** do not build infrastructure first. Attach to a published
baseline so that grounding is structural.

### 6.6 Agent-authored artifacts as a Tier-1 output

**(Tyler)**:

> "Agent-authored artifacts like blog posts, one-pagers, HTML artifacts,
> visualizations, technical reports, and full publish-intended papers are
> extremely useful and need to be considered a Tier 1 result of autoresearch.
> […] We need to build clear principles around this however — what an LLM
> considers to be publishable is not the same as what actually is publishable."

Claude proposed measuring that calibration gap as an experiment. **(Tyler)**
declined for now:

> "The true test would be actually publishing. […] Actually running an
> experiment — does the LLM's work meet the standards — is a later problem.
> And not one I'm inclined to try solving before I have work worth publishing."

**Agreed action, deferred:** retrieve venue standards for reference and
possibly as a Skill. Not yet.

An unplanned data point exists already: on 2026-07-25 Claude produced a
technical report and a blog post from study 000's material and assessed them as
tier-3 publishable; Tyler assessed the underlying work as not worth publishing.
Those artifacts are preserved, labelled, in `writeups/claude-authored/`.

### 6.7 Delegation threshold

**(Tyler)**:

> "Think of the human as the PI and the LLM as the intelligent grad student.
> […] A grid search should be doable; a multi-dimensional grid might be more
> complicated; an architecture choice might be impossible; a harness design
> might be difficult."

Note from §2.3: **harness design is exactly what Yang et al. successfully
delegated**, to a frontier meta-agent, with a documented design space and
cheaply-checkable candidates. Those two conditions — a documented action space
and a cheap validity check — may be the general precondition for delegation,
and are worth treating as a hypothesis rather than an incidental detail.

Claude's open question to Tyler, unresolved at the close of the conversation:
**is "how small can we go" the real question, or a proxy for the delegation
threshold?** They want different experiments — a *protagonist* ladder on fixed
tasks versus a *task* ladder on a fixed protagonist. This study as scoped is
the former.

---

## 7. Immediate next actions

Items 2 and 3 as originally written were resolved on 2026-07-25 and are struck
through; the list below is current.

1. **(Tyler)** Write the study question in `study.md`.
2. ~~Resolve task selection~~ — **done: `budget-approval`** (§5.1).
3. ~~Confirm whether a replication package exists~~ — **done: it does**
   (§5.0), and `software-agent-sdk` is the OpenHands SDK (§2.3).
4. **Verify the three open risks in §5.0 before committing time** — Docker task
   server availability, local-endpoint substitution for the SLM, and license.
   These are cheap checks and they determine whether the first investigation is
   a day or a fortnight.
5. Scaffold `investigations/001-feasibility-single-task` once 4 is settled.
6. Pre-register: the stopping criterion, the train/val/test split, and what
   outcome would end the study. Study 003 inv 004's pre-registered patch budget
   is the model — it is the one piece of this repo's bookkeeping that
   demonstrably held under pressure.

**Proposed shape of the first run**, for review: reproduce their
`budget-approval` × `gemma-4-26b-a4b` cell first — *their* model, *their* task,
*their* $20 budget — before changing anything. That is the only configuration
where a published number exists to check against, so it is the only one that
can tell us whether the pipeline is working. Descending the ladder starts at
run two.

---

## 7a. Outstanding items — the fresh-agent entry point

_Written for whoever picks this up next, human or agent. Ordered so that the
cheap things that could invalidate the plan come first._

### A. Artifacts not yet read, ranked by value

Everything below is in the replication package and was identified but not
opened. **The first three are load-bearing for the study design, not just for
the build.**

1. **`docs/adaptation.md`** — almost certainly the "design-space documentation"
   fed to the meta-agent as one of its four context sources (§2.3). This is the
   encoded answer to *what harness modifications are possible*, which is the
   thing this study is ultimately trying to learn. Highest-value single read in
   the repository.
2. **`tasks/budget_approval_s2l/eval.md` + the eval module** — resolves the
   open question in §2.2: how much of the grading is the `eval_model` doing,
   and how much is deterministic. Determines how much of the paper's headline
   accuracy rests on a judge.
3. **`tasks/budget_approval_s2l/gepa_optimize.yaml`** — the actual optimizer
   configuration. What is mutable, how the $20 budget is expressed and
   enforced, generations/population, selection rule.
4. **`tasks/budget_approval_s2l/prompts/`** — the *baseline* harness being
   adapted. Reading the before-state is how the adaptations become legible.
5. **`included_task_model_seed_triplets.csv`** — the exact cells the paper ran,
   including seeds and replicate counts. This is the ground truth for "what
   would reproducing their cell actually mean."
6. **`run.py`** — the orchestrator's CLI surface.
7. **`docs/read_trajectory.md`** — the trajectory format, needed for any
   failure analysis.
8. **Their `AGENTS.md` / `CLAUDE.md`** — the authors' own agent instructions,
   which often reveal the real workflow and its sharp edges.

### B. Unresolved factual questions

- **Which config reproduces the paper?** `run.yaml` has `max_examples: 10`
  while the paper reports 100 instances with a 20/20/60 split. The checked-in
  `run.yaml` looks like a smoke/dev config, and the **split is not visible in
  it**. Find where the split is defined before trusting any comparison to
  published numbers.
- **What does "$20 budget" mean operationally?** Dollars of meta-agent tokens?
  Is it metered by the harness, or a reported post-hoc figure? Affects whether
  the constraint is reproducible at all.
- **Does the eval path cost money?** `eval_model: gemini-3-flash-preview` is an
  API model. Even with local SLM inference, **every evaluation run has a paid
  component.** Budget it explicitly; on 100 instances × many candidate
  harnesses × 3 optimization runs, eval spend may exceed the $20 optimization
  budget.
- **Local hardware ceiling — RESOLVED EMPIRICALLY (Tyler, 2026-07-25).**

  | Model | Runs on the RTX 3080 (12 GB)? |
  |---|---|
  | Gemma 4 12B dense | **Yes — confirmed** |
  | Gemma 4 E4B (4.5B eff) | Expected yes (untested) |
  | Gemma 4 E2B (2.3B eff) | Expected yes (untested) |
  | **Gemma 4 26B MoE (`gemma-4-26b-a4b`)** | **No — confirmed. Does not fit.** |

  MoE reduces *compute*, not *resident weights*: all 26B parameters must be
  held in memory even though only ~3.8B activate per token. The earlier
  estimate in this document (13–14 GB at 4-bit) is superseded by the
  measurement.

  **Consequences for the study design:**

  1. **The descent ladder is fully local.** 12B → E4B → E2B all run on the
     desktop, so the core question — how far down before the process fails —
     costs no inference spend.
  2. **The anchor cell is not.** `gemma-4-26b-a4b` is the paper's model and the
     only configuration with a published number to check against
     (§5.1). Reproducing it requires **Modal or a hosted API provider**, and
     therefore from *run one* under the sequencing proposed in §7 — not later
     in the study.
  3. **This forces a decision, not just a purchase.** Either (a) pay for the
     anchor cell on Modal to get a verified reproduction before descending, or
     (b) start at 12B, accept that no published number exists for that cell,
     and treat the whole ladder as relative-to-own-baseline. Option (a) buys
     the ability to say "our pipeline reproduces theirs"; option (b) is cheaper
     but leaves the pipeline unvalidated, which is precisely the failure mode
     this repo has hit before. **Recommend (a).**
  4. Note that Modal introduces a *second* execution environment alongside the
     desktop, and the task server is a Docker service the agent must reach
     (§7a.C). Running the anchor cell on Modal means the task server and the
     model server are on different hosts unless both move to Modal. Scope this
     before committing — it is exactly the split-host shape that has cost this
     repo time repeatedly.

### C. The risk most likely to eat weeks, given this repo's history

**Tool-call format compatibility for locally-served Gemma 4.** Study 003's
single most expensive confound was Ollama rendering Qwen3.5 tool prompts with
the wrong template — producing "tool calls" that were string matches inside
markdown fences rather than structured calls, which silently corrupted an
entire investigation's conclusions.

This study runs an agentic harness against a locally-served model over a tool
protocol. The identical failure mode is available, and it is silent.

**Mitigation to build before any measurement run:** a one-instance assertion
that the model emitted a *structurally parsed* tool call — not a substring
match — logged and checked. If study 006 produces one instrument worth
carrying forward, this is the candidate.

Related: the task server is a **Docker service the agent reaches over a network
path**. On a split-host setup (Mac driving the WSL2 desktop over Tailscale)
that path has bitten this repo repeatedly. Decide early whether everything runs
on one host.

### D. Decisions to pre-register before the first measurement run

Per §7 item 6, and following the one bookkeeping pattern that held under
pressure in this repo (study 003 inv 004's patch budget):

1. **What "the process ran" means, numerically.** A feasibility test needs a
   pass mark written down in advance. Candidate: the optimizer completes a full
   GEPA cycle, produces a harness artifact, and the adapted harness scores
   above the unadapted baseline on held-out test at the `low` diversity tier.
   Note this is deliberately *not* "matches 98.3%."
2. **The stopping rule.** How many days or dollars before the attempt is
   abandoned, with the either-way clause: *the failure is also the result, and
   the under-specification list is the deliverable.*
3. **The split.** Whatever their 20/20/60 turns out to be, restate it
   explicitly and never report a number selected on validation as a result.
4. **Whether the meta-agent model is held fixed.** `gemini-3.1-pro-preview` is
   a preview model the authors themselves flag as a reproducibility threat. If
   it is unavailable or has moved, substituting it is a *deviation to record*,
   not a detail.

### E. The missing artifact

This document is a **planning record** — it carries context and decisions but
is not an operational entry point. A fresh agent starting here still has to
derive the order of operations.

The repo already knows what works: `HANDOFF.md` in study 005 is the one
bookkeeping artifact that survived a five-week absence intact, because it was
written once, at a moment when it was load-bearing, as a single ordered entry
point (`framework-drift-evidence.md` §5).

**Recommendation:** once the first investigation is scaffolded and the §D
decisions are made, write the equivalent here — read-these-in-this-order, state
of play, and the open questions a fresh reader should genuinely reconsider
rather than execute. Do not write it now; it would be speculative. Write it at
the first natural handoff.

## 8. Things Claude made up that should be reviewed

1. **The inverted-U curve (§2.6)** joins two papers that do not make the claim
   jointly. Hypothesis, not premise.
2. **The total-capacity-not-active-compute reading (§2.5)** is a reinterpretation
   after an error, and has not been tested.
3. **Task-selection criteria (§5.1)** are Claude's, ranked by Claude. The
   local-reproducibility criterion is weighted heavily on the basis of study
   003's history, which is a judgment call about this researcher's constraints
   rather than a property of the tasks.
4. **The "documented action space + cheap validity check" delegation
   precondition (§6.7)** is generalized from a single worked example.
5. **`software-agent-sdk` was not identified.** Treated above as an open item;
   do not assume it is an off-the-shelf dependency.
6. **Gemma 4 variant details** are from a technical report read at overview
   level plus secondary sources. Verify parameter counts and licensing against
   the model cards before committing to the ladder.
7. Claude's judgment on research *direction* is flagged as unreliable by this
   repo's own memory (`feedback_opus_research_taste_caveat`). §5 and §7 are
   proposals.
8. ~~The 13–14 GB VRAM estimate for `gemma-4-26b-a4b`~~ — **superseded
   2026-07-25 by measurement:** 12B runs on the 3080, 26B does not. The
   direction of the estimate was right; the figure was arithmetic and is now
   moot. §7a.B carries the confirmed result and the decision it forces.
9. **§7a.A's claim that `docs/adaptation.md` is the meta-agent's design-space
   documentation** is inference from the filename and the paper's description
   of four context sources. Plausible, unconfirmed, and it is ranked first
   partly on that inference.
10. **The suggested pass mark in §7a.D.1** is Claude's invention. It is offered
    so that *something* is written down before running, not because this
    particular threshold is defensible. Replace it.
