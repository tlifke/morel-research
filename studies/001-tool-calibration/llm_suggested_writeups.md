# LLM-suggested one-pager writeups

Compiled by Claude (claude-opus-4-7) on 2026-05-12 from the study's
work to date. Each entry is a candidate one-page LaTeX writeup
following the repo's `one-pagers/template/` structure: title,
research question, methods, results, forward-looking statement,
one figure, 3–5 takeaway bullets.

These are *recommendations*. The human writes the prose; this doc
is a menu of plausible publishing directions ordered by my read of
novelty × concreteness × likely audience interest.

Provenance for the underlying data:
- A1 corpus: `studies/001-tool-calibration/seeds.jsonl` (18 pairs).
- 006 4B / 12B 2×2 results: `results/<model>/006_*_2026-05-12.jsonl`.
- 005 A/B experiments: `results/tool_variant_experiment/*.jsonl`.
- Bulk corpus + A4 grading: `bulk_seeds.jsonl`, run 007.

---

## Tier 1 — strongest candidates

### (A) "An LLM's hypothesized task difficulties don't predict another LLM's empirical difficulty"

**Source investigations**: 002, 004, 006 (F3/F4/F5), 007.

**Figure**: `investigations/006-temperature-prompt/figures/curator_vs_empirical_heatmap.png`
— curator-assigned `difficulty_label.value` rows × empirical bucket
columns, 4B and 12B side by side. The diagonal (perfect Opus →
Gemma prediction) is mostly empty; mass concentrates in the lower-
left where curator-`hard` predictions empirically came out
`trivial`.

**Research question**: when one LLM (Claude Opus 4.7) is asked to
hypothesize per-prompt difficulty for tool-use tasks, do those
hypotheses validate against the empirical difficulty measured on
smaller / different models (Gemma 3 4B IT, 12B IT)?

**Hook (opening paragraph candidate)**:
Claude Opus 4.7 served as the curator for our matched-pair tool-
calibration corpus. As part of curation, it assigned each prompt a
`difficulty_label.value` — its prediction of how hard the task
would be for an LLM. We then ran the corpus against Gemma 3 4B IT
and 12B IT and measured empirical difficulty per record per model.
Opus's predictions don't validate. For both 4B and 12B IT at
neutral baseline, prompts Opus labeled `hard` overwhelmingly land
in the empirical `trivial` bucket. The curator's introspective
model of "this is hard for an LLM" doesn't correspond to how
specific LLMs actually fail.

**Why this matters**:
LLMs increasingly serve as judges, evaluators, and curators in
their own evaluation pipelines. This study has a concrete instance
of one LLM (Opus 4.7) making structured predictions about another
LLM (Gemma 3 IT family) and missing systematically. The specific
mechanism: Opus's difficulty axes (operand digits, algorithmic
complexity, fact obscurity) target *task difficulty* — could the
model solve this problem in principle? The empirical score
captures *tool-call decision quality* — does the model recognize
when to invoke the tool? Opus implicitly assumed the two are
correlated; the data says they aren't.

**Candidate takeaways (≥1 figure-linked, ≥1 limitation)**:
- Opus-`hard` records empirically cluster in `trivial` for both
  Gemma scales at neutral baseline. The figure shows 9 of 15
  Opus-`hard` records land in 12B's empirical `trivial` bucket.
- The diagonal of the curator×empirical matrix is mostly empty —
  Opus's per-record predictions and Gemma's per-record behavior
  are not strongly correlated.
- One concrete failure-mode of LLM-as-curator: predictions are
  calibrated to an internal model of "LLM difficulty" that does
  not match the target model's actual behavior.
- Implication for evaluation-data curation: if an LLM is doing
  the labeling, validate its labels against the target model
  empirically before treating them as ground truth. Don't
  outsource the predicate of the experiment to the curator.
- Limitation: small corpus (18 pairs / 36 records) and single
  curator (Opus 4.7) on a single target-model family (Gemma 3 IT).
  Phase A4 grading of the 366-record bulk corpus is the next-step
  validation; 007 is the dedicated investigation.

**Caveats / open questions**:
- Does this generalize? Other curators (smaller LLMs; different
  families) labeling the same corpus would tell us whether the
  miscalibration is curator-specific or general to LLM-as-judge.
- Does Opus's prediction calibrate against Opus's own behavior?
  We haven't run the corpus against Opus 4.7 as a target. Would
  illuminate whether Opus's "this is hard" tracks its own
  difficulty or an abstract notional model.
- The empirical difficulty is itself model-relative; the same
  record is "trivial" for 12B and "medium" for 4B. Calibration
  citations must name the target model.

---

### (B) "Prescriptive prompt engineering interacts with model scale"

**Source investigations**: 005, 006.

**Figure**: `investigations/006-temperature-prompt/figures/per_record_scatter_banded.png`
— per-record 4B IT vs 12B IT success at temp=1.0 under directive
prompts. Highlight the "Scale Hurts" / "Scale Breaks" regions
where 12B underperforms 4B.

**Research question**: how does prescriptive tool-description
language ("REQUIRED whenever...") interact with model scale?

**Hook (opening paragraph candidate)**:
On Gemma 3 4B IT, adding the directive clause "REQUIRED whenever
the user asks about themselves" to a tool description moved
success from 0% to 87% on records the model had previously
refused. On Gemma 3 12B IT — same clause, same records — the model
started failing in *new* ways: invoking the wrong tool, deflecting
with clarifying questions, applying the directive too literally
(calling `calculator` on "5 × 9"), or answering from training
distribution despite anti-refusal framing. Prescriptive prompts
are a stronger handle on the larger model, and 12B grips them
harder — sometimes to bad places.

**Specific failure modes observed at 12B under directive that 4B
did not exhibit**:
1. Literal over-application: "use calc for arithmetic" → calc on
   trivial cases despite "skip trivial" clause.
2. New escape routes: Socratic deflection, wrong-tool selection,
   training-distribution confidence bypassing the tool path.
3. Each prescriptive clause closes one failure mode; 12B invents
   a new one to take its place.

**Candidate takeaways**:
- 4B IT directive Cell D: 73.9%. 12B IT directive Cell D: 86.9%.
  But the *per-record* breakdown shows specific records
  regressing at 12B — figure highlights the Scale Hurts/Breaks
  region.
- Directive cuts under_calls ~60% in both models; over_calls and
  wrong_tool fail differently across scale.
- Style-guide implication: pair "REQUIRED whenever..." with
  explicit "Do NOT call when {trivial}" — directives with only the
  positive case break the matched-pair design at 4B and propagate
  to 12B in different ways.
- Limitation: 2 model sizes, one family (Gemma 3 IT). Cross-family
  transfer untested. The morel-research style guide is
  explicitly calibrated to 4B-class IT only.
- Forward: test on 27B / non-Gemma IT to characterize the scaling
  function for prescriptive interaction.

**Caveats / open questions**:
- We don't have a mechanistic explanation for *why* 12B reads
  directives more literally. Likely related to instruction-tuning
  strength scaling with size, but unverified.

---

## Tier 2 — solid candidates

### (C) "Tool-blind deferral: the model knows it doesn't know but doesn't know it has a tool"

**Source investigation**: 005 ukl A/B variants.

**Figure**: bar chart of variant success rates (would need to be
built — not yet rendered).
Candidate spec: 5 bars, one per variant (v0_baseline → v4_combined),
y = mean success rate across 3 ukl hard records at n=10. Show the
0% → 87% climb from v0 to v1a.

**Research question**: what tool-description language change is
necessary to get an instruction-tuned model to invoke a tool it
has been given for a question it can't otherwise answer?

**Hook**:
Asked "what's my wedding anniversary date?", Gemma 3 4B IT
correctly responded "I don't have access to your personal profile"
20 trials in a row — while the `user_knowledge_lookup` tool was
listed in its available palette the whole time. This is *tool-
blind deferral*: the model knew it didn't know, but didn't map
"I don't know" to "use the tool that would tell me."

**Sweep**:
- v0 (baseline "search the user's profile..."): 0%
- v1 ("REQUIRED whenever the user asks about themselves..."): 73%
- v1a (v1 + "do NOT respond with 'I don't have access...'"): 87%
- v2 (rename to `lookup_user_info`, baseline description): 0%
- v3 (epistemic framing "the tool DOES give you access"): 7%
- v4 (rename + directive + epistemic combined): 27%

**Candidate takeaways**:
- Strict imperative ("REQUIRED") is the load-bearing lever. Softer
  language ("Use whenever") collapses the effect (73% → 27%).
- Naming alone doesn't move calibration (v2: 0%).
- Over-cueing hurts (v4 < v1a). Each clause is a constraint the
  model must reconcile; the wrong combination creates conflict.
- Anti-refusal clause stacks: explicitly suppressing "I don't have
  access" picks up another 14 pp on top of the bare REQUIRED.
- Failure shifts rather than vanishing: v1a's 13% remaining
  failure is Socratic deflection ("Could you tell me who Aunt
  Nina is?") — the model invents new escape routes when one is
  closed.

**Caveats / open questions**:
- One model, one tool (ukl) on 3 records. Generality to other
  tools / models / refusal modes is unclear.
- The 87% ceiling under v1a may itself be a model limit. v1a+
  with "do NOT ask the user for clarifying info" is untested.

---

### (D) "Curator confabulation: when an LLM curates a knowledge base it makes things up"

**Source**: Decision 16 in 001-foundations + the parallel
fabricated/verified KBs.

**Figure**: side-by-side table comparing 6–8 entries from
`kb/general_knowledge.json` (fabricated) vs `kb/general_knowledge_real.json`
(WebSearch-verified). Highlight specific divergences (wrong dates,
wrong publication titles, invented events).

**Research question**: when an LLM is asked to populate a research
knowledge-base, what fraction of its specific factual claims are
wrong?

**Hook**:
Building a tool-calibration study, I asked Claude (Opus 4.7) to
populate a small knowledge base with post-training-cutoff facts:
recent Premier League scores, market prices, AI-paper publication
dates. Claude wrote 21 entries fluently. When the human reviewer
spot-checked via WebSearch, almost every specific value was wrong
— wrong scores, wrong dates, wrong paper titles, sometimes
events that hadn't happened. The user kept the fabricated KB as
a counterfactual and asked Claude to build a parallel verified
version. The two KBs are now both checked into the repo as a
research artifact — fabricated × real × model behavior on each is
the dataset.

**Candidate takeaways**:
- LLM curator confabulation rate (Claude Opus 4.7 on a small
  general-knowledge KB): ~95% of specific factual claims diverged
  from ground truth on WebSearch check. Confabulation was fluent,
  internally consistent, and undetectable without external
  verification.
- The model had WebSearch available the whole time but didn't
  invoke it spontaneously. The user's correction made it visible.
- The parallel fabricated/real KB pair lets future calibration
  research probe whether models behave differently when the
  lookup tool returns real vs. plausible-but-false snippets.
- Generalization: if the model is curating its own evaluation
  data, the data may be confabulated. Verify with external
  ground truth before treating LLM-generated "facts" as facts.
- Implication for AI-assisted research workflow: build the
  external-verification step into the curation loop, not the
  review loop. By review time, the confabulation has already
  contaminated downstream artifacts.

**Caveats / open questions**:
- One model (Claude Opus 4.7) on one KB topic (sports / finance /
  AI papers). Confabulation rate may differ across topic domains
  and model versions.
- "95% wrong" is a rough estimate from spot-checking; not a
  rigorous accuracy measurement.

---

## Tier 3 — supplementary / less novel

### (E) "Scaling 4B → 12B beats prompt-engineering at neutral baseline"

**Source**: 006 2×2.

**Figure**: F1 cell means
(`investigations/006-temperature-prompt/figures/cell_means.png`).

**Status**: confirmatory rather than novel. Useful as a supporting
baseline for (A) and (B); weaker as a standalone one-pager.

**Headline**: 4B neutral 63.1% → 12B neutral 79.7% (+16.6 pp from
scale at neutral). 4B neutral → 4B directive: +10.8 pp from
prompt-engineering. Effects roughly stack: 4B-neutral → 12B-
directive = +23.8 pp.

---

### (G) "The matched-pair tool-calibration corpus: design, scope, limits, and what to ask next"
*(reviewer-proposed 2026-05-12)*

**Source**: 001 (substrate), 002 (axes), 003 (bulk corpus), 005
(tool-spec optimization), 006 (methodology lock). Cross-cutting.

**Figure**: corpus structure diagram. Six tools at the top; two
KBs (real + fabricated for gkl, persona for ukl); pair structure
beneath (Type A difficulty manipulation, Type B affordance
manipulation); the directive vs. neutral prompt-set layer; the
empirical-grading layer (per model). The diagram doesn't yet
exist — would need to be drafted.

**Research question (meta)**: what is this corpus actually
*for*? What can a calibration researcher ask of it? Where does
it stop working? How would one extend it?

**Hook (opening paragraph candidate)**:
Most LLM evaluation discusses "what models can do." This study
takes a different cut: it asks "when do models correctly *decide
whether to use a tool*?" — and builds a small but tightly-designed
dataset to probe that decision. The matched-pair design isolates
specific cognitive moments. The two parallel KBs make
counterfactual grading possible. The bulk corpus extends the
substrate to ~200 pairs. This piece walks through the design
choices, what they enable, and what they don't.

**Content sketch (per-section)**:
- *What the corpus measures.* Tool-call decision quality, not
  task-solving ability. Specifically: does the model correctly
  invoke its tool palette under matched-pair conditions where
  only one variable changes per pair?
- *Design choices and their consequences.*
  - Matched pairs (Type A difficulty manipulation; Type B
    affordance manipulation). Each pair isolates one cognitive
    moment.
  - Six-tool palette covering compute, time, units, world-
    knowledge, and personal-knowledge cognitive moments.
  - Two KBs (real + fabricated) for general_knowledge_lookup so
    counterfactual KB experiments are first-class.
  - A persona-based user_knowledge_lookup KB (Maya Patel) for
    private-context probing.
  - Strict schema with per-record provenance, including LLM-
    assessment signatures (every label signed by the LLM that
    produced it).
- *Questions this corpus enables.*
  - Cross-model comparison at the per-record level (4B vs 12B
    figures from 006).
  - Prompt-engineering A/B with controlled variation (005 → style
    guide).
  - Methodology lockdown via factorial design (006 2×2).
  - LLM-as-curator validation against empirical reality (007).
- *Where the corpus is insufficient.*
  - Single-turn only. Multi-turn dialogue calibration is a
    fundamentally different question.
  - No long-context probes (all prompts are short).
  - No tool-output interpretation probes (planned: 004
    tool-failure-recognition).
  - Limited to deterministic verifiable answers. Open-ended
    reasoning isn't tested.
  - Tool palette is fixed at six; real agent palettes are larger
    and more dynamic.
- *Expansion directions.*
  - More models — non-Gemma families to test generalization.
  - Older / smaller models for capability-frontier probing.
  - Multi-turn extension where tool-call decisions accrete over
    a conversation.
  - Larger seed pool for the trivial halves of GKL (current
    cycle is 8 facts).
  - A complementary axis system that *does* predict tool-call
    calibration (the 007 outcome).

**Candidate takeaways**:
- This corpus is calibration-of-tool-use, not capability-of-
  reasoning. The two should not be confused.
- Matched-pair design is necessary for clean attribution but
  costly: ~2 records per cognitive moment. Bulk generation
  scales the substrate without sacrificing matched-pair structure.
- LLM-curator artifacts (Opus's `difficulty_label`, generated
  prompts) carry provenance signatures so future analysts can
  trace any specific decision back to the curator.
- Limitation: single-turn, single-language, fixed palette.
  Generality to broader agent regimes is open.

**Why include**: this is the "dataset paper" of the study. Useful
both as a standalone publication and as a citable substrate for
the other writeups (A/B/C/D all reference subsets of the corpus
this piece describes).

---

### (H) "Case studies in scale-driven behavior change"
*(reviewer-proposed 2026-05-12)*

**Source**: 006 4B-vs-12B comparison, output samples.

**Figure**: per-case mini-tables of model outputs at temp=1.0
neutral and directive cells for the 4–6 records of interest.
Could also be a 3×N small-multiples grid: each row is a record,
columns are 4B Cell C / 4B Cell D / 12B Cell C / 12B Cell D, with
representative output snippets. Format depends on case selection.

**Research question**: what specifically changes between Gemma 3
4B IT and Gemma 3 12B IT on the same tool-calibration prompts?
Not as aggregate success rates but as concrete behavioral shifts
on individual records.

**Hook**:
Aggregate statistics summarize but obscure. Looking at specific
records where 4B and 12B behave differently surfaces *why* the
scale gap exists — which is more illuminating than just measuring
how big the gap is.

**Candidate cases (each ~1 paragraph of the writeup)**:

1. **NLA paper, hard half** — "When did Anthropic publish the
   Natural Language Autoencoders (NLA) paper?"
   - 4B neutral, temp=0: 0/20 confabulate "published in 2020...
     learning representations from noisy text" (same wrong answer
     20/20 trials).
   - 12B neutral, temp=1.0: 100% target invocation. Correctly
     recognizes "this is post-cutoff, look it up."
   - **Mechanism**: capability for recognizing the limits of
     training knowledge scales meaningfully between 4B and 12B
     for this specific case.

2. **SHA-256 hash, hard half** — "Compute the SHA-256 hash of
   'open-source research collaboration'"
   - 4B neutral: 0% target. Invokes `calculator(expression=
     "hash('...', algorithm='sha256')")` — picks the wrong tool.
   - 12B neutral: 100% target. Correctly invokes
     `python_execute`.
   - **Mechanism**: tool-selection accuracy scales. The
     calc-vs-python boundary that confused 4B is resolved at 12B.

3. **Aunt Nina** — "Is Aunt Nina left-handed?"
   - 4B neutral: 0% — model refuses ("I don't have access to
     personal information about Aunt Nina").
   - 12B neutral: 10% — model mostly refuses too, but partial
     improvement.
   - 4B directive (v1a): 87% — anti-refusal clause overrides.
   - 12B directive: 50% — wider failure-mode diversity (Socratic
     deflection, wrong-tool selection, intermittent no-call).
   - **Mechanism**: the refusal prior is similar across scales;
     the directive lifts both but introduces *new* failure modes
     in 12B that 4B doesn't exhibit. Scale + directive is a real
     interaction, not just an additive lift.

4. **mult_isolated trivial half** — "Compute 5 × 9" (calc-only env)
   - 4B directive: 100% correct (skips trivial mental arithmetic).
   - 12B directive: 0% — invokes calc on 5 × 9 every trial.
   - **Mechanism**: 12B reads the calc description's "use for
     arithmetic" clause more literally. The accompanying "skip
     for trivial cases" clause is operative for 4B but ignored
     by 12B.

5. **Fibonacci 1000 mod 1M, hard half** — under py_only directive.
   - 4B directive, temp=0: 0/20 invocations. Model reasons out
     the Pisano period theoretically instead of calling python.
   - 12B directive, temp=0: 0/20 invocations. Same Pisano-period
     reasoning path.
   - **Mechanism**: this regression is *scale-invariant*. The
     directive's "REQUIRED for any computation calculator cannot
     do" invites a "this is hard, let me think harder" response
     in both models. Mechanism is the same; outcome is the same.

6. **Anniversary trivial half (in-prompt answer)** — "My wedding
   anniversary is June 12, 2021. What's my wedding anniversary?"
   - 4B directive: 100% — correctly extracts from prompt.
   - 12B directive: 70% — over-eager invocation of
     `user_knowledge_lookup` despite the answer being in-prompt.
   - **Mechanism**: 12B's directive-compliance prior partially
     overrides contextual cues that 4B respects.

**Candidate takeaways**:
- Aggregate success-rate deltas hide the mechanistic story.
  Per-record analysis reveals different *kinds* of behavioral
  change at scale.
- Three failure modes that scale-fixes-cleanly: confabulation on
  post-cutoff facts (NLA), wrong-tool selection (SHA-256),
  partial refusal (Aunt Nina under directive lift).
- Three failure modes that scale doesn't fix or makes worse:
  literal over-application of directives (5 × 9), Pisano-period
  evasion (fibonacci), directive over-compliance ignoring
  context (anniversary trivial).
- Implication: scale and prompt-engineering both move calibration
  but along different dimensions. A model trained at larger scale
  has stronger instruction-following and stronger introspection;
  these can fight each other under prescriptive prompts.

**Caveats / open questions**:
- 6 cases out of 36 records. Selection bias is real; these are
  the ones where the scale × prompt interaction was loudest.
- We don't have mechanistic interpretability evidence — only
  output-content evidence. Real circuit-level analysis would
  ground the "mechanism" claims more rigorously.
- Each case study is a small-n probe. Replicating across the
  bulk corpus once A4 is graded would strengthen the patterns.

---

### (F) "Building research infrastructure with Claude: a 1-day desktop calibration rig"

**Source**: existing draft at `drafts/desktop-setup-blogpost.md`.

**Status**: closer to a blog post than a one-pager. Already
drafted by a subagent; needs human prose pass. Meta-narrative
about human-AI collaboration on infrastructure (vs. the prior
solo-attempt timeline the user mentioned).

**Why include here**: it's the closest existing prose artifact;
worth flagging that the writeup exists if the human wants a
faster-to-publish piece.

---

## Recommendations

**Tier 1 standalones** (publishable findings): (A), (B).
- **(A)** Opus's hypothesized difficulties don't predict empirical
  difficulty on Gemma 3 IT — concrete instance of LLM-as-curator
  miscalibration. Strengthened substantially by A4-on-bulk
  results (currently in progress).
- **(B)** Prescriptive prompts × model scale interaction — surprising,
  concrete, lands directly in applied-ML / prompt-engineering
  discourse.

**Tier 2 standalones** (smaller-scope but cleaner): (C) tool-blind
deferral A/B, (D) curator confabulation parallel KBs.

**Methodology / substrate writeup**: (G) describes the corpus
itself — design choices, what it enables, where it stops working,
how to extend it. Useful as a citable foundation for the other
pieces and as a standalone dataset paper. Reviewer-proposed
2026-05-12.

**Case studies**: (H) is a cluster of per-record deep-dives at
the 4B/12B scale gap. Doesn't rest on aggregate statistics; uses
concrete behavioral differences to surface mechanism. Could be
its own writeup or supplemental sections within (A) or (B).
Reviewer-proposed 2026-05-12.

**Infrastructure / blog**: (F) is the closest-to-ready prose
artifact. Draft already exists at `drafts/desktop-setup-blogpost.md`.

**Confirmatory / supporting**: (E) is weakest as a standalone
but useful as supporting material in any of the above.

For "review what's worth writing up myself": (B), (D), (F) are the
human-flagged interesting set. (A) reframed in agent-centered
terms also worth the human's eye. (G) is a substantial piece worth
considering for the dataset-paper slot. (H) is the most fun if the
human enjoys concrete mechanism-hunting.
