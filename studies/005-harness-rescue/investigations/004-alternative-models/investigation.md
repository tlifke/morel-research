---
id: studies/005-harness-rescue/investigations/004-alternative-models
title: Alternative models for reasoning roles (VibeThinker-3B)
status: in-progress
parents:
  - studies/005-harness-rescue
children: []
related:
  - studies/005-harness-rescue/investigations/002-rich-harness
  - studies/005-harness-rescue/investigations/001-steplaw-substrate
  - studies/005-harness-rescue/investigations/003-process-judges
axes:
  llm_capability: medium
  human_capability: high
tags:
  - harness
  - model-selection
  - reasoning
  - reasoner-not-optimizer
  - heterogeneous-agents
created: 2026-06-25
updated: 2026-06-25
---

# Inv 004 — Alternative models for reasoning roles (VibeThinker-3B)

## Scope

Test whether swapping a **reasoning-trained, non-tool-trained** small model into the
**reasoning roles** of the inv-002 society — specifically the **Orienter** and
**Hypothesizer** — improves process and/or outcome over the homogeneous
nemotron-3-nano:4b society. First candidate: **VibeThinker-3B**
([WeiboAI](https://huggingface.co/WeiboAI/VibeThinker-3B)). The society already
routes per-role to a stronger model (`STRONG_ROLES` → gemini); this investigation
generalizes that seam into **heterogeneous, capability-matched role assignment** and
asks where a reasoner's *lack of knowledge* (a 3B trained for verifiable reasoning,
not breadth) becomes the binding constraint.

## Why VibeThinker for these roles (the fit)

The reasoner-not-optimizer thesis (`reasoner-not-optimizer.md`) says the harness's
job is to **elicit and sustain research reasoning**, not supply search competence.
The society decomposes that into agents; the front-end roles are the *purely
reasoning* ones:

- **Orienter** — recall prior knowledge of the problem *class*, state expected
  structure, approach, uncertainties. No tools, no actuation. Pure reason + recall.
- **Hypothesizer** — turn the prior into a falsifiable, prioritized hypothesis
  hierarchy. No tools. Pure reason.

These are exactly the roles VibeThinker was trained for (multi-step reasoning,
constraint satisfaction, self-correction) and exactly the roles where the
inv-002 failure lives: **axis-freezing is born in the Orienter/Hypothesizer**
(`project_axis_freezing_coverage_failure`, `project_society_critic_state`) — the
front-end never reasons about the lr×bs *interaction*, so the search inherits a
single-axis frame. The mechanical Executor needs no model; the Analyst/Terminator
are light. So the high-leverage place to upgrade reasoning is precisely the
no-tool front-end — which is also the only place a non-tool-trained model can go.

**The knowledge question (Tyler's framing).** VibeThinker is 3B and explicitly *not*
trained for breadth — the model card warns it is weaker on general knowledge than
on verifiable reasoning. The Orienter's value, though, is partly *domain recall*
(that lr and bs co-scale; that optimal lr falls with N). So this investigation is
also a **probe of where knowledge becomes the binding constraint**: does a strong
reasoner with thin knowledge orient well by *reasoning* about the problem class, or
does it miss structure a more knowledge-rich model would recall? The real/abstract
framing from `agent-mdp-design.md` is the clean way to separate these (below).

## Background — VibeThinker-3B (from the model card + smoke test)

- **Base:** Qwen2.5-Coder-3B, 3B dense params. **License:** MIT.
- **Trained for:** verifiable reasoning (math, competitive code, STEM) via the
  Spectrum-to-Signal Principle (curriculum SFT → MaxEnt-guided policy optimization).
  Reported: AIME-2026 94.3, GPQA-Diamond 70.2, IMO-AnswerBench 76.4, LeetCode 96.1%.
- **Explicitly NOT trained for** tool-calling / agentic / function-calling. Model
  card recommends against function calling and autonomous coding agents — which is
  why it can only occupy the **no-tool** roles here.
- **Recommended sampling:** temperature=1.0, top_p=0.95, top_k=-1 (the society
  already runs temp=1; top_p/top_k to be set per the card). Context up to ~102K.
- **Deployed here:** `hf.co/bms22/VibeThinker-3B-Q8_0-GGUF:Q8_0` (Q8_0, 3.3 GB) on
  the desktop RTX-3080 ollama (pulled 2026-06-25). Q8_0 over the Q4_K_M used for the
  other local models — a 3B reasoner is more quantization-sensitive and VRAM is ample.

## Initial observations (2026-06-25, smoke test) — the integration problem

Two single-call probes against the Orienter prompt (see `data/` once captured):

1. **Under the society's hard JSON-grammar constraint** (ollama `format: schema`,
   the `elicit()` path in `society.ts`), VibeThinker degenerated: it emitted
   schema-valid JSON with **placeholder values** (`"..."`) in ~27 tokens. A
   reasoning-trained model wants to *think first*; a strict output grammar forces it
   straight into the object and starves the reasoning.
2. **Unconstrained** (no `format`), the same prompt produced a long, explicit
   `<think>…</think>` block followed by a thorough, knowledgeable orientation — it
   recalled the lr/bs trade-off, the U-shaped batch-size effect, and even gestured at
   the **interaction** and at replication/controls. It hit the 3072-token cap without
   finishing (~18 s).

**Implications (the live design question for this inv):**
- VibeThinker reasons **inline via `<think>` tags in `content`**, not via ollama's
  native `think` field (the `thinking` field was empty). The harness's current
  assumption — *grammar-constrained JSON emission* — is tuned for instruct/tool
  models (nemotron, qwen3) and **fights a pure reasoner**. We need a
  **reason-then-extract** elicitation path for this role class: let it reason
  unconstrained, then extract the structured fields (parse the post-`<think>` text,
  or a cheap second extraction pass — possibly with the instruct model).
- **Verbosity/latency:** orientation alone wanted >3072 tokens. Cost/stamina budget
  per role matters; cap and prompt for concision, or accept slower front-end.
- **Knowledge looked better than feared** on *this* domain (Qwen2.5-Coder base
  retains substantial ML knowledge) — which sharpens the real/abstract contrast as
  the place to actually measure the knowledge gap, rather than assuming it.

## Methods (draft — for review; Tyler owns the final call)

_Anchored to `feedback_small_scale_first` and `feedback_reasoner_not_optimizer`._

1. **Build the heterogeneous routing + reason-then-extract path.** Generalize
   `STRONG_ROLES` into per-role `MODEL_<ROLE>` assignment in `society.ts`, and add a
   `REASON_THEN_EXTRACT` elicitation mode that (a) calls the role model with **no
   format constraint**, capturing `<think>` + answer, then (b) extracts the role's
   JSON (regex/post-think parse, falling back to a cheap instruct-model extraction
   call). Keep the captured raw reasoning in the trace for the judges.
2. **Arms (small-scale first, <5 seeds, Env A, reasoning=low elsewhere):**
   - **B** baseline — homogeneous nemotron society (inv-002 FULL config), the control.
   - **V-OH** — VibeThinker in **Orienter + Hypothesizer**, nemotron elsewhere.
   - **V-O** / **V-H** — single-role swaps, to attribute any effect to one role.
   - (stretch) **V-A** — VibeThinker also on the Analyst (still no tools).
3. **Domain framing crossed in (real / abstract)** per `agent-mdp-design.md`, to
   separate *domain knowledge* (real − abstract) from *structured reasoning*. The
   knowledge-gap probe lives here: if VibeThinker's win is real-only, it's recall;
   if it wins abstract too, it's reasoning.
4. **Score with the inv-003 judge panel + three-tier artifact.** Headline questions:
   (i) does the reasoner front-end **break axis-freezing** at the source (joint
   lr×bs reasoning in the Orienter/Hypothesizer)? (ii) does process quality predict
   outcome? (iii) **where does thin knowledge bite** (abstract-arm orientation
   quality; any confidently-wrong domain claims)? Retro-score the inv-002 traces
   with the same rubric for comparison.
5. **Cost discipline:** local/free but serial on the one GPU; VibeThinker is verbose
   (≥1 long generation per front-end step). Cap `num_predict`, prompt for concision,
   and only scale an arm to 20+ seeds on shown promise.

## Decisions

> **Decision 1 — Q8_0 quant** (2026-06-25)
> Pulled `VibeThinker-3B-Q8_0` rather than Q4_K_M (the other local models' quant).
> A 3B reasoner is more quantization-sensitive and VRAM is ample (12 GB, idle);
> reasoning fidelity > footprint here.

> **Decision 2 — reason-then-extract, with nemotron as the extractor** (2026-06-25)
> Reasoner roles run the role model with **no output grammar** (the grammar starves a
> reasoner — see smoke test), capturing its full `<think>`+answer; then **nemotron**
> (the base model) extracts the role's JSON schema from that text. Chosen over
> relax-grammar-and-parse because it (a) keeps the role-specific schema enforced on the
> extractor and (b) preserves the raw reasoning in the trace for the judges. Built into
> `society.ts` behind `REASONER_ROLES` / `REASONER_MODEL` (generalizing the `STRONG_ROLES`
> seam); `roleIsReasoner()` excludes the Critic, so only the named primary roles use it.

## Results

### Build + first end-to-end run (2026-06-25)

`society.ts` now supports heterogeneous per-role routing + reason-then-extract.
Run it with:

```
REASONER_ROLES=orienter,hypothesizer \
REASONER_MODEL=hf.co/bms22/VibeThinker-3B-Q8_0-GGUF:Q8_0 \
node src/society.ts
```

First validated run (`runs/vibe_smoke_s901/`, Env A, BUDGET=2, CRITIC=off, seed 901):
**finished**, 2 experiments, final regret 0.040, 17 model calls, **218 s** (≈2× the
homogeneous society — VibeThinker is verbose and each reasoner role costs a long
generation + an extraction call). VibeThinker drove the Orienter (×1) and the
Hypothesizer (×3 across the loop); the rest stayed on nemotron.

**What works:** the reasoner produces rich, on-topic content — the Orienter prior
recalled the lr/bs trade-off and U-shaped batch effect; the Hypothesizer reasoning
contained concrete, config-bearing hypotheses (h1–h5 with grid values). Extraction is
content-faithful: 12/12 hypotheses well-formed (id + claim) after the array-coercion fix.

**Open issue — nested-schema extraction is lossy (the live problem for this inv).**
nemotron reliably extracts the *flat* Orienter schema, but on the Hypothesizer's
**nested** schema it (i) intermittently emits `hypotheses` as an object keyed by id
instead of an array (now coerced back, + a prompt rule), and (ii) drops the
**structural fields** — `level`/`parent`/`config` came back null, with the config
values stranded *inside the claim text* ("lr=3.453e-4, bs=1024 yields…") rather than the
`config` field. Consequence: no high/narrow tiering and no machine-usable configs, so
`mechanicalExec` finds nothing to run and the **nemotron LLM-Executor takes over** — i.e.
in this first build VibeThinker shapes the *prose* of orientation/hypotheses but nemotron
still owns all *structural* search decisions. This is the first concrete finding, not a
blocker: it pinpoints where a reasoning model + a 4B extractor lose information.

**Two latent harness bugs found & fixed along the way** (benefit all arms): array-typed
schema fields crashed the run when the model returned a non-array (`uncertainties` as a
string → `.join` TypeError); now coerced (string→`[string]`, id-keyed-object→array).

### A vs B vs executor + the extractor matrix (2026-06-25)

Added knobs to `society.ts`: `HYP_EXTRACT=single|simple|per_item`, `MECH_EXEC=on|off`
(force the LLM Executor), `EXTRACT_MODEL` (which model does the structuring step).

**Executor on VibeThinker works (surprise).** `REASONER_ROLES=executor MECH_EXEC=off`:
all 3 steps produced **valid on-grid configs** and moved *both* axes up together toward
the high corner (the joint move nemotron freezes on). Reason: the Executor's output
schema is **flat + numeric**, which extracts reliably — unlike the nested Hypothesizer.
**Schema shape, not role, governs extraction reliability.**

**A (per_item) vs B (simple):** B wins. B = one extraction call with a flattened numeric
schema; A = claim-list then per-hypothesis calls. A costs ~2× the calls (34 vs 18), still
emits some null configs, and is no better on outcome. B is the mechanism to keep.

**The `think:false` bug.** My extraction calls forced `think:false`; nemotron then
abandoned the JSON grammar (returned markdown / LaTeX `\boxed{…}` / bare arrays) and
degraded as context grew. Switching extraction to `think:"low"` (the proven baseline
setting) restored reliable structured emission (B: 6/6, 3/3, 3/3, 6/6 configs).

**Extractor matrix — the key result** (B/simple, Env A, budget 3, seed 950, 1 seed each;
on-grid measured *pre-`snap()`*; outcome numbers noisy, on-grid rates (n=12–24) robust):

| extractor | on-grid pre-snap | cfg present | regret | reached corner |
|---|---|---|---|---|
| nemotron | 8/24 (33%) | 24/24 | 0.0174 | no |
| VibeThinker self-format | 10/22 (45%) | 22/22 | 0.0001 | yes |
| gemini | **12/12 (100%)** | 12/14 | 0.0018 | yes |

**Caveat on `reached_corner`** (Tyler, 2026-06-25): it is `bs ≥ 736 AND lr ≥ 0.005524` —
an **Env-A-specific diagnostic of axis-freezing** (did the run break the freeze and probe
the joint-high extreme), NOT a generalizable headline metric. It *encodes Env A's answer*
(Env C's optimum is low-lr), so tuning to it would overfit and mislead on the ladder — the
`reasoner-not-optimizer.md` trap. It is outcome/coverage, not reasoning quality (an
optimizer reaches it with zero reasoning). Headline metrics stay: regret / cumulative
regret, the reasoning-quality judgments, and A→B→C generalization.

**The off-grid values are faithful transcription, not extractor noise** (verified): nearly
every off-grid config nemotron emitted has its number appearing verbatim in VibeThinker's
prose (round decades `lr=0.1/0.01/0.001`, even `bs=0.5/0.25` from a ratio it discussed).
nemotron *generates* on-grid (selects from the grid in its context) but *transcribes*
off-grid (we told it to be faithful, and VibeThinker reasons in approximate/round terms).
gemini hits 100% because it *maps* approximate values to the nearest valid grid point — a
snap-to-grid competence the 4Bs lack. So the shift traded a hypothesis-**reasoning**
bottleneck for a hypothesis-**grounding** one; grounding is the easier to engineer away
(`snap()` already rescues the outcome; gemini fixes fidelity), but only worth it if
VibeThinker's reasoning gain holds across seeds. Fidelity still matters for the science:
if `snap()` moves a config to a different grid point, the experiment no longer tests the
stated hypothesis.

**Answer to "can VibeThinker do structured output?": yes.** Self-formatting its own
reasoning, it beat nemotron on on-grid fidelity and gave the best run (proposed
`lr=0.0055, bs=1024/2048` — the corner — and ran it). The first smoke test's placeholder
JSON was the grammar *starving its reasoning* (one-shot), not a formatting inability.

**Implications (architecture):**
- **Reasoner roles → VibeThinker self-formats** (`EXTRACT_MODEL=reasoner`): one model, no
  extraction hop, more faithful than nemotron-extract. nemotron-as-extractor is strictly
  dominated — drop it.
- **Grid fidelity is a small-model limit, not a VibeThinker limit:** both 4B-class models
  strand ~half their configs off-grid (`snap()` rescues outcome, not fidelity). **gemini
  is the only 100%-on-grid extractor** — route extraction there when fidelity matters.
- Needs seeds to confirm the outcome ordering; the on-grid ordering
  gemini > vibe-self > nemotron is the load-bearing finding.

### Knowledge-gap, early signal

The Orienter prior (faithfully extracted from VibeThinker) predicted the optimum sits at
**"moderate lr / moderate-large bs"** — the textbook prior, which is *wrong* for Env A
(optimum is the high-lr/large-bs corner). So on lr/bs, VibeThinker's knowledge is present
but conventionally-biased in the same direction nemotron's is — the real/abstract arms
are needed to tell whether being-asked-to-reason helps independent of (mis)recall.

## Forward-looking

_To be populated. Natural follow-ons: heterogeneous role-to-model assignment as a
first-class harness knob; reasoner front-end + a separate tool/actuation model is a
template for the W2S task; the "recognize-and-offload" probe (HANDOFF §6 Q2) may pair
well with a strong reasoner that can articulate "this is a grid search."_

## Things I made up that you should review

- **Slug/title/scope wording** — confirm "alternative models" is the right framing
  vs. e.g. "heterogeneous reasoning roles."
- **The arm set (B / V-OH / V-O / V-H / V-A)** and that Orienter+Hypothesizer is the
  right pair to start with — I inferred this from the axis-freezing-born-in-the-front-end
  finding; you may want a different cut.
- **Q8_0 over Q4_K_M** — a judgment call (above); reverse if you'd rather match the
  other models' quant for comparability.
- **reason-then-extract** as the integration fix — there are alternatives (relax the
  grammar and parse; a constrained-decoding model that still reasons; two models, one
  to reason + one to format). I picked the one that preserves the reasoner's `<think>`
  for the judges; flag if you'd rather test another.
- Treating the **real/abstract** framing as the knowledge-gap probe — borrowed from
  inv 002's `agent-mdp-design.md`; confirm it carries over cleanly.

## Limitations

_To be populated. Known up front: single GPU is serial and VibeThinker is verbose
(latency); one quant tested; knowledge-gap conclusions are domain-specific to lr/bs
unless the abstract arm + a second substrate corroborate them._
