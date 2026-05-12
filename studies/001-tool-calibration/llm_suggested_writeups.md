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

### (A) "Task difficulty doesn't predict tool-call calibration"

**Source investigations**: 002, 004, 006 (F3/F4/F5), 007.

**Figure**: `investigations/006-temperature-prompt/figures/curator_vs_empirical_heatmap.png`
— curator-assigned `difficulty_label.value` rows × empirical bucket
columns, 4B and 12B side by side. Mass concentrates *off* the
diagonal; the rows expected to predict difficulty instead show the
opposite signal.

**Research question**: do task-difficulty axes (operand digits,
algorithmic complexity, fact obscurity) predict whether a model
correctly invokes a tool?

**Hook (opening paragraph candidate)**:
We curated a matched-pair seed corpus to study LLM tool-calibration
and labeled each prompt with a per-tool task-difficulty axis. The
prediction: hard prompts should drive tool calls; trivial prompts
should be answered directly. Empirically, that prediction doesn't
hold — for both Gemma 3 4B IT and 12B IT, prompts labeled `hard`
by the curator overwhelmingly land in the `trivial` empirical
bucket (98%+ success). The axes don't measure what the score
measures.

**Why this happens** (one-paragraph mechanism):
Task-difficulty axes describe how hard the underlying problem is to
solve. Our scoring measures whether the model's tool-call decision
matches expectation. These are different cognitive moments — the
model's tool-call decision turns out to be dominated by prompt
surface features ("Compute X × Y" triggers `calculator`; "today is..."
triggers `datetime_now`) and refusal priors, not by the model's
self-assessment of task difficulty.

**Candidate takeaways (≥1 figure-linked, ≥1 limitation)**:
- Curator-`hard` records empirically cluster in the `trivial`
  bucket for both 4B and 12B at neutral baseline — figure shows
  9/15 hard records in trivial for 12B.
- Calibration measurement targets tool-call decision-making, not
  task-solving ability. These are distinct properties that the
  literature sometimes conflates.
- The A1 corpus has no `easy` or `extreme` curator labels — the
  bulk corpus (A4 pending) will populate these and may shift the
  picture.
- Implication for calibration research: design axes that predict
  the metric you actually measure. Test predictiveness empirically
  before relying on a-priori difficulty taxonomies.
- Limitation: 18 pairs / 36 records is small for strong claims;
  Phase A4 grading of the 366-record bulk corpus is the
  next-step validation.

**Caveats / open questions**:
- Whether the curator-vs-empirical gap generalizes across model
  families or just within Gemma 3 IT is open. Investigation 007
  is the right home for the deeper work.

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

If forced to pick: **(A) or (B)**. Both are publishable directions
backed by data the repo already produced.

- **(A)** is the more methodologically interesting result — a
  framing critique that affects how calibration studies should
  design their predictor axes. Likely interest to
  evaluation / benchmark researchers.
- **(B)** is more empirically punchy — surprising, concrete,
  with a clear "test at target scale" recommendation. Likely
  interest to applied-ML practitioners doing prompt engineering at
  scale.

Both stand alone; both can land as one-pagers without further data
collection (007's A4-on-bulk would strengthen (A) substantially —
worth waiting if (A) is the pick).

For a quicker-to-publish piece: **(C)** or **(D)**. Both have
narrower scope but cleaner single-finding stories.

For a non-research-research piece: **(F)** is essentially ready
for a prose pass.
