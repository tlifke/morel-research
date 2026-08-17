# Plan — making our results directly comparable to the CUAD paper

Recorded 2026-08-17 for a **future investigation**. Not started. Tyler's
instruction: understand the interpretation before running anything.

## Why this exists

Two claims I made were wrong and this plan exists because of them:

1. **"AUPR is unavailable to us by construction"** — false. AUPR needs a
   *ranking with scores*; our current output contract emits one committed
   decision with no score. That is a **design choice**, not a property of
   prompting.
2. **"Tinker exposes no logprobs"** — false. `TopKPromptLogprobs` exists
   (`tinker-docs.thinkingmachines.ai/tinker/api-reference/types/topkpromptlogprobs/`).

The 12-category subset is a third instance of the same pattern: chosen at
INV1-D4 for **principle-derivation** reasons, before the external comparison
became load-bearing, and never revisited.

## How their ranking actually works

Established from their code and the reproduction, not inferred:

- A `(contract, category)` pair is one **question**. 102 × 41 = 4,182 on test.
- The contract is chunked into 512-token windows advancing by a 256 stride
  (`max_seq_length 512 / doc_stride 256`).
- An extractive-QA head scores candidate `(start, end)` spans in each window.
  The top **20** are kept per question (`n_best_size 20`), softmaxed to
  probabilities, and an **empty-string candidate carries probability mass**
  alongside them.
- A **prediction** is the set of non-empty n-best candidates above a probability
  threshold. `get_preds` discards the empty prediction entirely; for a
  zero-gold question, `fp += len(preds)`.
- Absence has its own signal: `null_odds_.json`, the SQuAD-2 threshold
  statistic their training genuinely optimised.
- The PR curve comes from sweeping that probability threshold **globally across
  all questions**. AUPR integrates it.

**The consequence that matters:** because the threshold is global, AUPR measures
the quality of a **cross-question ranking** — can the system rank "this span, in
contract A, category X" above "that span, in contract B, category Y"? It is a
shortlist-quality metric, which matches the paper's stated purpose (a lawyer
reviews a ranked list; recall matters more than precision).

## What a score of ours would and would not be

**AUPR is invariant to monotone transformations of the score.** It needs the
*ranking* to be informative; it does not need the scores calibrated. So a
differently-constructed score is legitimate — but what it *means* differs, and
that must be stated wherever the number appears.

| | their score | sampling frequency | sequence logprob | teacher-forced candidate likelihood |
|---|---|---|---|---|
| construct | trained head's span probability | behavioural consistency under sampling | likelihood of the emitted tokens | likelihood of a candidate span given the contract |
| cross-question comparable? | yes, by training | roughly — "how often does it commit" | **poorly** | plausibly |
| granularity | continuous | coarse, k+1 levels | continuous | continuous |
| known biases | — | coarse ranking biases AUPR **low** | **length-biased**, and conditioned on that sample's reasoning trace | needs verification |
| cost | — | k× sampling | free with generation | one extra scoring pass per candidate |

**Sequence logprob is the worst option despite feeling closest.** With
`separate_reasoning`, span tokens are emitted after a long reasoning trace, so
their logprob is heavily conditioned on that particular trace — two samples
producing the same span get different logprobs. It is also length-biased in a
way their start+end logit score is not.

**`TopKPromptLogprobs` may be the best option and needs investigating first.**
It scores *prompt* tokens, which implies a teacher-forcing path: generate
candidate spans, then score each candidate's likelihood by placing it in a
prompt and reading the logprobs back. That yields a per-candidate score
independent of any one reasoning trace — structurally much closer to their
mechanism than sequence logprob. **Whether the API supports this shape is
unverified and is task 0.**

**Verdict on comparability.** The metric would be computed identically, on the
same gold, by the same scorer. What differs is what the score *is*: their
trained head's confidence versus our sampling consistency (or candidate
likelihood). That makes it a fair **system-level** comparison — "can a prompted
LLM produce a usefully ranked shortlist?" — and **not** a like-for-like
measurement of the same construct. Arguably the more interesting comparison,
but it must be described that way and never as "our AUPR versus theirs" without
the qualifier.

## Separate their artifact from their design (Tyler, 2026-08-17)

The sharpest framing available, and it changes what we should copy.

**Their windowing is an architectural artifact.** A 2021 bidirectional encoder
has a 512-token limit, so a 25k-token contract *must* be chunked into
overlapping windows and the pieces reassembled. Much of their 20-deep n-best is
consequently the same span rediscovered in adjacent windows, not twenty
genuine alternative hypotheses. **We have 65k+ context and no such constraint.
Mimicking the windowing would be copying a workaround for a problem we do not
have.**

**Their ranking is a genuine design choice.** A lawyer reviews a ranked
shortlist; the paper says outright that recall matters more than precision.
That is what AUPR measures and it is the thing worth adopting, because it is
what makes the comparison meaningful rather than a coincidence of metrics.

**So the candidate design is: emit a ranked top-k of candidate spans per
category as structured output, each carrying its own `principles_cited`.**
That is a direct analogue of their n-best, obtained in **one generation instead
of k samples**, and it preserves the study's core — citation stays attached to
each candidate rather than being bolted on afterwards. Rank 1 remains the
committed decision, so our own Level A/B/C metrics are unaffected and both
metric families come from a single run.

**Three things that must be settled before adopting it:**

1. **Within-question rank is not a cross-question score.** Their threshold is
   swept **globally across all questions**, so a PR curve needs candidates from
   different questions to be comparable. A model emitting ranks 1–20 per
   question gives no such ordering. Either we obtain a score that compares
   across questions (teacher-forced likelihood being the most promising), or we
   accept that our curve is constructed differently and say so.
2. **Self-reported confidence is poorly calibrated** and should not be the
   primary route. AUPR needs only ranking, not calibration — but it does need
   the ranking to hold *across* questions, which is exactly where self-report
   is weakest.
3. **k costs output tokens.** 20 candidates × 41 categories is ~820 spans per
   contract, which is not viable. The right k is an empirical question about
   where their n-best's signal actually lives, not a number to copy from their
   config — hence the depth analysis in
   `reviews/logprobs-and-nbest-depth.md`.

**On the subset question**: Tyler's position is that the easy-subset finding
(D-34) is not a concern in itself, since expanding is planned regardless and
the current numbers were never meant to be directly comparable. It stays
recorded as a caveat on absolute figures rather than as a blocker.

## Answered 2026-08-17 (`reviews/logprobs-and-nbest-depth.md`)

**Task 0 is resolved: teacher-forced candidate scoring WORKS.**
`SamplingClient.compute_logprobs(prompt)` in the **native** `tinker` SDK scores
arbitrary supplied tokens. Verified live on Qwen3.5-9B — "The capital of France
is X" gave Paris −0.540, Berlin −6.602, banana −15.618, with every other
position **bit-identical across the three calls**, proving it is a real prefill
over supplied tokens rather than regeneration.

- **Not reachable through our OAI shim.** All four routes measured closed:
  `top_logprobs` → 400 "not yet supported"; `logprobs:true` → 200 but
  **generated tokens only**; `prompt_logprobs` → silently dropped;
  `/completions` + `echo` → 400. **We need a second backend path**, and the two
  surfaces are genuinely disjoint — `separate_reasoning` does not exist in the
  native SDK at all.
- **Prefix caching makes it cheap**: 5 candidates against a shared 6,013-token
  context ran ~1.5 s each with ~5,888/6,016 tokens served from cache. One
  prefill plus k short suffix passes.
- **Length normalisation must be settled before any AUPR is computed.** In a
  realistic probe, *sum* and *mean* logprob ranked a correct 8-token span and a
  14-token superset in **opposite orders**. This is not a footnote.
- **Sequence-logprob-of-the-span is not merely biased, it is unimplementable**
  on the shim: under `separate_reasoning: true` the returned `logprobs` cover
  the *reasoning* tokens, not `content`. Option closed.
- Undocumented cap, measured: `topk_prompt_logprobs` ≤ 20, or
  `max_tokens × k ≤ 1000`.

**Task 2 is resolved: k = 10 deduplicated spans, not 20.**

The intuition that rank 1 is nearly enough is **half right, and the wrong half
matters**. Rank 1 satisfies 88% of recoverable *questions* — but their recall
denominator is **gold spans (2,643), not questions (1,244)**: 2.12 spans per
answerable question, 5.32 for `Parties`. So depth 1 caps span recall at **47%**
and costs **38% of AUPR**, and P@80%R is *undefined* below depth 10 because max
recall never reaches 0.8.

- **Near-duplication confirmed and large**: ~60% of candidates sit within
  Jaccard ≥ 0.8 of another in the same question, leaving **~11.5 genuinely
  distinct hypotheses, not 20**. Roughly **40% of their depth is the 512-token
  encoder** — the artifact, quantified.
- **Deduplicated depth 10 matches or beats their raw 20 on all three models**
  (0.4290 > 0.4259, 0.4862 > 0.4825, 0.4798 > 0.4779).
- **Their published AUPR is slightly depressed by their own windowing** — the
  full deduplicated list beats the raw list by ~+1 pp while losing 0.08 pp of
  span recall. A clean, quantified instance of an architectural artifact
  landing in a published number.
- Shape is identical across all three models. Rare categories are worse at rank
  1 (0.82 vs 0.92) but top-5 closes the gap; the larger effect is
  spans-per-question spread, which argues for **variable k capped at 10** rather
  than a fixed k.

**Rank is not enough.** A within-question rank gives at most 10 discrete global
levels against a threshold swept globally, which coarsens the curve and biases
AUPR low. The continuous cross-question score is needed, and teacher-forced
likelihood is now confirmed available for it.

**A design tension that needs an explicit ruling against D-14.** k = 1 is
indefensible on their axes, so the **committed decision and the ranked
shortlist should be two fields, not one field doing both**. D-14 fixes exactly
one decision per target; a shortlist is not that. Settle it deliberately rather
than letting the schema drift.

## The plan

**Task 0 — determine what the API actually gives.** Read the Tinker logprobs
API properly. Can we score arbitrary candidate text against a prompt
(teacher-forcing), or only read logprobs of tokens we generated? That answer
picks the scoring route. Do not assume; the last two assumptions here were both
wrong.

**Task 1 — move to all 41 categories.** No data work: INV1-D3 deliberately kept
all 41 in the manifest, so this is a config edit
(`scripts/config/category_subset.yaml`). Two things to measure rather than
assume:
- **Truncation.** The task definition grows ~615 → ~2,100 prompt tokens, and
  output grows with 41 decisions instead of 12. C3 already truncated on *short*
  contracts at 12 categories (D-28). Probe before committing to a budget, and
  consider sharding by category group.
- **Dilution.** Our nine principles cover a handful of categories, so at 41 the
  aggregate is dominated by 36 uncovered ones. **Report both** — all-41 for
  comparability, principle-covered subset for effect size. This is not an
  argument for staying at 12.

**Task 2 — produce a score per decision**, by whichever route task 0 selects.
Default if teacher-forcing is unavailable: **sampling frequency**, k = 10–20.
It requires no prompt change, no output-contract change, and composes cleanly —
the model still emits one committed decision plus its citations (D-14 intact),
with the ranking layered on top. State the coarse-ranking bias.

**Task 3 — emit in their shape and score with their tooling.** `(span, score)`
pairs per question, so `evaluate.py` yields **AUPR and Precision@80%Recall**
directly. Keep our own Level A/B/C reporting alongside: their metric has **no
TN cell and cannot see hallucination**, so it hides the absence behaviour this
study most cares about. Both, never either.

**Task 4 — run on `test` at G4.** Then we appear in their Table 2 as a fourth
row and in their Figure 4 as a fourth bar, on identical axes, same gold, same
scorer. Carry the contamination asymmetry with the number, per D-26 as amended.

## Cost

Roughly $12–18 for a 41-category repeat of the C2/C3 grid at 3 seeds
(2–3× the $5.49 that grid cost), and roughly $30–60 with k=10–20 sampling for
the ranking. Inference cost is not the constraint on this plan; interpretation
is.

## Open questions to settle before running

- Does `TopKPromptLogprobs` support teacher-forced candidate scoring?
- Do we emit **multiple candidate spans per decision** to mirror their n-best,
  and if so how does that interact with D-14's one-decision-per-target?
- Do we produce an absence score analogous to their `null_odds`, or accept that
  our absence behaviour is only visible in our own metrics?
- Their models emit ≤1 span per question at any single threshold, so their
  recall is structurally capped on multi-span categories (License Grant
  averages 3.81 gold spans per question). Does our shortlist inherit that cap
  or beat it — and if it beats it, is that a real advantage or an artifact of
  emitting more?
