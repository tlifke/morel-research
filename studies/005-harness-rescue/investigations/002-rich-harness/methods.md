# Inv 002 — Rich-harness methods, components, and hypotheses

Companion to `investigation.md`. This is the running registry of **every
harness component we may test**, **how** we test it, **which phase** it falls
in, and **both Tyler's and Claude's hypotheses** (recorded *before* results, so
we can score our priors). Decisions here are made jointly; Claude proposes,
Tyler approves.

Last updated: 2026-06-08.

## Settled premises (from inv 001)

- **Protagonist is nemotron-3-nano:4b.** The core question is **minimal vs.
  rich harness on the *same weak model*** — can harness engineering lift the 4B?
  Gemini-3.1-flash-lite is used selectively (when nemotron is too slow, and as
  the Phase-4 transfer check), not as a "control model." We already know gemini
  is stronger; that is not the question.
- **Two confirmed, orthogonal failures:** *exploration discipline* (axis-locking;
  ~half of runs never reach the optimum region) and *actuation* (the ~45%
  "stall" — knows its answer, never calls `finish`). Reasoning level fixes the
  first and does nothing for the second.
- **Reasoning fixed at `low`** (captures the benefit cheaply; not a confound).
- **Env A first** (215M/100B, the failure-rich flat env). Strategies that
  explore well graduate to Envs B/C, then the real W2S task.
- **20 seeds/arm.** Metrics: median regret **and tail (max)**, stall rate,
  finished-rate, claim-fidelity, cost/time.
- **Timing:** ~30–60s per nemotron run at reasoning=low (~4s/experiment ×
  ~14 experiments); self-reflection ~+50%, fresh-agent reflection ~2×.

## Three-axis design space

Every experiment is a point in a cube, not a list:

- **Axis A — what context we inject** (components C1–C7 below).
- **Axis B — who owns each injected piece**: `self` (agent, inline) ·
  `fresh/meta-agent` (separate agent, clean window) · `harness-curated`
  (deterministic code) · `human` (ceiling control).
- **Axis C — cadence/scale**: per-step vs every-N; handoff `num_iterations`;
  self-consistency `k`; (reasoning level — settled at low).

We test a **slice**, never the full cube. The full binary factorial of C1–C7
is 128 conditions (~2–4 days GPU at 20 seeds); we reject it as wasteful.

## Component registry

Stable numbering C1–C7 (Tyler's message used a few overlapping labels; mapping
noted). For each: what it is · targets · grounding · **Tyler's hypothesis** ·
**Claude's hypothesis** (deltas called out) · how tested · phase.

### C1 — Verbal reflection
- **What:** after each experiment, a short natural-language "what did that
  result teach me / what next" that conditions the next proposal.
- **Targets:** exploration discipline (axis-locking, basin escape).
- **Grounding:** Reflexion ([2303.11366](https://arxiv.org/abs/2303.11366)) —
  the training-free analog of AutoLLMResearch's GRPO credit assignment.
- **Tyler:** Well-grounded; likely works well. Biggest lever besides C4.
- **Claude:** Agree it's the biggest *search* lever — **with one delta:** a 4B's
  self-reflections may be shallow or wrong, so the *self* variant may
  underdeliver and the **fresh-agent variant may be required** to get usable
  reflections. The open question is reflection *quality*, not whether reflection
  helps in principle. Predict: C1ₛₑₗf gives a real but noisy improvement;
  C1fᵣₑₛₕ tightens it.
- **How tested:** Phase 1. Self-reflection first (inline), then fresh-agent
  reflection (separate agent reads trajectory, writes reflection back). Ablated
  on top of C4.
- **Phase:** 1.

### C2 — Results table (structured state)
- **What:** an externalized, curated `config → loss → note` table re-injected
  each step instead of (or alongside) the raw transcript.
- **Targets:** stamina / context rot; consistency for a weak model.
- **Grounding:** MemGPT ([2310.08560](https://arxiv.org/abs/2310.08560)),
  Generative Agents ([2304.03442](https://arxiv.org/abs/2304.03442)), Anthropic
  context-engineering (structured note-taking).
- **Tyler:** Useful but **not always the decider** — a solidified format helps a
  weak model (consistency) more than it would help Opus; expect *somewhat*
  positive but nuanced, and **the format itself may matter** as much as having one.
- **Claude:** Agree. **Delta/caveat:** on StepLaw the context never gets large
  (≤50 experiments fits trivially in 256k), so C2's *compaction* value can't
  show here — any benefit will be from **format/consistency**, not from beating
  context rot. So StepLaw measures the format effect; the rot effect waits for
  the long-horizon real task.
- **How tested:** Phase 2 — format variants (terse table vs prose vs
  ranked-best-K), and ownership (harness-curated vs agent-maintained).
- **Phase:** 2.

### C3 — Strategy playbook (explicit prior)
- **What:** in-context heuristics ("vary both axes early", "probe the
  high-lr/large-bs corner before settling", "don't stop while improving").
- **Targets:** the exact early errors the strategy analysis found.
- **Grounding:** Plan-and-Solve ([2305.04091](https://arxiv.org/abs/2305.04091));
  branch/backtrack framing from ToT; **our own inv-001 strategy analysis**.
- **Tyler:** **Hold off.** Should be *empirically derived*, and we don't have
  strong enough results yet; it will also be problem-specific. Revisit after
  round 1. Innately linked to C6 (principles).
- **Claude:** Agree — and it risks Anthropic's "rigid script underperforms"
  finding, so if/when we add it, it must be a *revisable prior*, not a script.
  Deferring is correct; round 1 should not bake in answers we haven't earned.
- **How tested:** Phase 2+, *after* the first round tells us which strategies
  actually help (so the playbook is data-derived, not guessed).
- **Phase:** 2+.

### C4 — Finish-actuation + recovery
- **What:** make the terminal action go through the tool — reject prose
  conclusions, re-prompt "state it by calling `finish()`"; harden malformed-call
  handling; off-grid recovery (already partly in inv 001's guards).
- **Targets:** the ~45% stall; the s16 malformed-call give-up.
- **Grounding:** AutoLLMResearch Most-Similar Matching
  ([2605.11518](https://arxiv.org/abs/2605.11518)); MAST failure taxonomy
  ([2503.13657](https://arxiv.org/abs/2503.13657)) — premature termination,
  failure-to-commit, missing termination cues.
- **Tyler:** Expect a big improvement when we get it right, but implementation
  may be **finickier than our first try indicates**. Positive; maybe not
  helpful on a stronger model, not necessarily transferable. **Distinguish
  problem-space (off-grid recovery) from generalizable mechanisms (how to
  recover, how to report conclusions, forcing the finish tool).**
- **Claude:** Strongly agree on the problem-space vs. generalizable split — we
  should tag each C4 sub-mechanism accordingly. **Delta on the metric:** C4's
  effect on *regret-of-finished-runs* is ~zero (it doesn't improve search); its
  effect is on **finished-rate and claim-capture** — it rescues runs that
  *already found good answers but stalled* (e.g. inv-001 s19 found the exact
  optimum and stalled). So "big improvement" shows up in outcome/finished-rate
  and in *aggregate* regret (by converting stalls into reported wins), not in
  the search quality of runs that already finished. Near-certain mechanical win;
  good Phase-1 plumbing validation.
- **How tested:** Phase 1. Sub-mechanisms tagged generalizable vs problem-specific.
- **Phase:** 1.

### C5 — Compaction / bounded episodes / handoff
- **What:** summarize + reset the context window every N steps (or on a
  plateau/meltdown trigger); hand off state to a fresh window.
- **Targets:** stamina / meltdown over long horizons.
- **Grounding:** Anthropic compaction; meltdown
  ([2603.29231](https://arxiv.org/abs/2603.29231)); agent drift
  ([2601.04170](https://arxiv.org/abs/2601.04170)).
- **Tyler:** Lots of literature/approaches, **many specific to larger/stronger
  models.** Worth testing after round 1; **deep enough it will almost certainly
  demand its own investigation.** Overlaps with C2 (a results table *is* a form
  of compaction/handoff).
- **Claude:** Agree, and **delta:** on StepLaw at 50 experiments the context
  never grows enough to rot, so C5 likely shows **no effect here** — it is the
  wrong env to evaluate compaction. Its real test is the long-horizon W2S task.
  Recommend C5 graduates to its **own investigation** tied to the real task, not
  the StepLaw sim. C2 (format) is the StepLaw-appropriate slice of this idea.
- **Phase:** 3 / own investigation.

### C6 — Principle self-tagging
- **What:** give the agent a list of research principles; have it **name which
  principle it is applying** at each step (the tag becomes observable trace, and
  itself a piece of context that could be self/meta/curated).
- **Targets:** exploration + **observability** (we'd see the invoked strategy).
- **Grounding:** hybrid of C1 (reflection) and C3 (playbook).
- **Tyler:** **Innately linked to C3** — the strategies *are* the principles;
  when the agent employs one it should cite it. Reflection (C1) can be seen as
  one such principle but we test it separately first. Rich area; **hold until
  after round 1.**
- **Claude:** Agree they're one family (C3 = the principles, C6 = citing them
  in-flight). Note C6 is heavier on a 4B (extra structured output each step);
  expect observability value to exceed its direct performance value at first.
  Round 2, as a variant of whichever reflection wins.
- **Phase:** 2+.

### C7 — Self-consistency (k-sample voting)
- **What:** sample k candidate next-configs (or k reflections), pick by
  majority/agreement.
- **Targets:** noisy-proposal variance on a weak model.
- **Grounding:** Self-Consistency ([2203.11171](https://arxiv.org/abs/2203.11171)).
  (Tyler's message labeled this "C6"; it is C7 here.)
- **Tyler:** Hadn't considered it; random-forest-like intuition (aggregate of
  many small models can be meaningful). But sampling is expensive in time
  (cost-free for us, but slow). **Not optimistic** as a realistic solution;
  worth testing after the rest. Open question: **viable in a real,
  non-lookup-table setup?**
- **Claude:** Agree on low priority, and **a sharper delta on transfer:** on the
  lookup substrate k-sampling is "free" (only time), but in the **real W2S task
  each sample is a real training run** — so self-consistency is *prohibitively
  expensive there and will not transfer*. It is a sim-only luxury. Recommend
  lowest priority / possibly skip, precisely because it answers a question that
  doesn't carry to the target task.
- **Phase:** 3 (low priority / candidate skip).

## Axis B — "training the harness" (the meta-goal)

Tyler's framing: the end state is a harness that is **curated toward the
problem** — a self-model or a fresh/meta-agent that **observes which strategies
are effective and tunes the harness** accordingly. In effect, *training the
harness instead of the model*. This requires a **holdout** discipline:

1. derive/curate on a set of seeds,
2. validate the curated harness on **fresh held-out seeds** (does it generalize,
   or did we overfit the harness to specific runs?),
3. then transfer to **Env B / Env C**,
4. then to the **real W2S researcher** (inv 003).

This is the synthesis the whole study builds toward; Phase 1–3 produce the
ingredients (which components help, owned by whom), and the meta-curation is the
capstone.

## Phase plan

| Phase | Contents | Env / model / seeds |
|---|---|---|
| **1 (now)** | **C4** (actuation) + **C1** (reflection: self, then fresh-agent), ablated. Recommended as a clean **C1×C4 factorial** (6 arms) for main-effects + interaction; minimum is the focused 3 new arms. | Env A · nemotron · 20 |
| **2** | Axis-B ownership deep-dive on the winning component; **C2** results-table (format + owner); **C3/C6** principles + self-tagging (now data-derived). | Env A · nemotron · 20 |
| **3** | **C7** self-consistency (low priority / candidate skip); kick off **C5** compaction as its own investigation tied to the long-horizon task. | Env A + real task |
| **4** | Best harness → **gemini** transfer check (does it help the strong model, or is it weak-model-specific?); generalize to **Env B/C**; meta-curation with holdout → toward **inv 003 (real W2S)**. | Envs A/B/C · both models |

## Phase-1 experimental design (proposed; pending Tyler's go)

- **Arms** (C1×C4 factorial; ✓ = already have):
  - A0 `minimal` (C1 off, C4 off) — ✓ (inv-001 baseline, re-run under identical config for cleanliness)
  - A1 `+C4`
  - A2 `+C1self`
  - A3 `+C1self +C4`
  - A4 `+C1fresh`
  - A5 `+C1fresh +C4`
  - (focused-minimum = {A0, A1, A3, A5}; full-factorial adds A2, A4 for clean main effects)
- **Fixed:** Env A, nemotron, reasoning=low, BUDGET=50, 20 seeds.
- **Read-outs:** main effect of C4 (Δ finished-rate, Δ stall), main effect of C1
  (Δ regret median + tail, Δ reach-optimum), C1×C4 interaction, and
  self-vs-fresh for C1.
- **Decision rule:** carry the winning (C1-owner, C4) config to Phase 2; report
  problem-specific vs generalizable C4 mechanisms separately.
