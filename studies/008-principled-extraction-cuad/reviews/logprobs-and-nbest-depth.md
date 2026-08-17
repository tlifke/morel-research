# Tinker logprobs and CUAD n-best depth — two empirical answers

Run date 2026-08-17. Answers task 0 of `plans/comparability-plan.md` and sizes
the "what k do we emit" decision. Nothing was committed.

AI Assistant Used: Claude Code

---

## Headline

**1. Teacher-forced candidate scoring: YES.** Verified live against
`Qwen/Qwen3.5-9B`. `SamplingClient.compute_logprobs(prompt)` in the native
`tinker` SDK returns per-token logprobs for an arbitrary token sequence we did
not generate. It works, it is deterministic, it discriminates correctly, and
prefix caching makes per-candidate scoring against a shared contract cheap
(~1.5 s/candidate, 98% of the prefill cached after the first call).

**It is NOT reachable through the OpenAI-compatible endpoint we currently use.**
The shim returns logprobs for *generated* tokens only, and refuses top-k
alternatives outright. Teacher forcing requires a second backend path on the
native SDK. That is a real but small cost — the native path is a different
client object, not a different auth story or a different account.

**2. Recommended k: 10 deduplicated candidate spans per question.** Not 20.

Ten near-duplicate-free candidates **match or beat** their full 20 on AUPR for
all three checkpoints. Eight is the floor (99% of full AUPR, and the minimum
that reaches 80% span recall for the RoBERTas, without which Precision@80%Recall
is undefined). Past 10 the returns are under 1 pp of AUPR.

**3. A model-emitted within-question rank is NOT enough.** Their threshold is
swept globally, so we need a cross-question-comparable score. Teacher-forced
candidate likelihood is the best available construct for it — but see §1.5, the
length bias is real and must be handled before it is used as a ranking key.

---

# Part 1 — Tinker logprobs

## 1.1 What `TopkPromptLogprobs` is

**Read in docs**, at
`https://tinker-docs.thinkingmachines.ai/tinker/api-reference/types/topkpromptlogprobs/`,
verbatim (identical to `tinker/types/topk_prompt_logprobs.py` in the PyPI wheel,
`tinker==0.25.0`):

```python
@dataclass(frozen=True, slots=True)
class TopkPromptLogprobs:
    """Top-k most likely tokens at each prompt position, as dense numpy matrices.

    Both matrices have shape ``(prompt_length, k)`` where ``k`` is the number
    of top tokens requested. Empty positions are filled with sentinel values
    (``token_id=0``, ``logprob=-99999.0``).
    """
    token_ids: np.ndarray   # int32, shape (prompt_length, k)
    logprobs: np.ndarray    # float32, shape (prompt_length, k)
```

So: **top-k over the vocabulary at each *prompt* position.** Not sampled tokens,
not the actual token's logprob.

The actual-token logprob is a **separate sibling field** on the same response.
From `SampleResponse` (`tinker/types/sample_response.py`; field list confirmed
live by introspection):

```
sequences               : Sequence[SampledSequence]     # sampled-side
prompt_logprobs_np      : Optional[np.ndarray]          # shape (prompt_length,)
topk_prompt_logprobs_np : Optional[TopkPromptLogprobs]
prompt_cache_hit_tokens : int
```

with the docstring for `prompt_logprobs_np`:

> "Per-token log probabilities for the prompt as a 1-D float32 numpy array,
> shape `(prompt_length,)`. `NaN` at positions where logprobs were not computed
> (e.g. the first prompt token). None if prompt logprobs were not requested."

**Both are available, independently toggled.** `prompt_logprobs` is the one we
want; `topk_prompt_logprobs` is a bonus (distillation-shaped) we do not need.

The naming in the plan is slightly off, worth fixing where it appears: the class
is `TopkPromptLogprobs` (lowercase k), and it is not the field that answers the
teacher-forcing question — `prompt_logprobs` is.

## 1.2 The decisive question, verified live

`SamplingClient.compute_logprobs(prompt: ModelInput) -> list[float | None]`.

Live, `Qwen/Qwen3.5-9B`, three prompts differing in one token:

| text | logprob of the differing token |
|---|---|
| The capital of France is **Paris**. | **−0.540** |
| The capital of France is **Berlin**. | **−6.602** |
| The capital of France is **banana**. | **−15.618** |

Every other position is **bit-identical across the three requests**
(` capital` = −9.27897834777832 in all three, etc.), which is the proof that
this is a real teacher-forced prefill over supplied tokens and not a
re-generation. `logprobs[0]` is `None` (no preceding context), as documented.

Candidate scoring in the shape we would actually use — one shared context, four
candidate spans, `ModelInput.from_ints(ctx_ids + cand_ids)`, take the tail:

```
Contract excerpt: This Agreement shall be governed by the laws of the State of New York.
Question: What is the governing law?
Answer:
```

| candidate | tokens | sum logprob | mean logprob |
|---|---|---|---|
| the laws of the State of New York | 8 | **−14.11** | −1.76 |
| This Agreement shall be governed by the laws of the State of New York | 14 | −14.56 | **−1.04** |
| the laws of the State of Delaware | 7 | −23.67 | −3.38 |
| the Parties hereto | 4 | −32.04 | −8.01 |

Correct and wrong candidates separate cleanly. **None of this text was
generated by the model.** This is exactly the mechanism the plan hypothesised,
and it is available today.

Independently, the docs describe the same construction and literally call it
teacher forcing (`tinker/losses/cross-entropy/`):

> ```python
> # 2. Teacher-force the completion to recover top-K logprobs at each position.
> teacher_forced = tinker.ModelInput.from_ints(prompt_tokens + sampled_tokens)
> ```

and the `true-thinking-score` cookbook recipe scores text it did not generate
via `compute_logprobs_async`, computing `exp(sum(logprobs))` over answer tokens.

## 1.3 Reachability: native SDK only — verified live

**Measured against `https://tinker.thinkingmachines.dev/services/tinker-prod/oai/api/v1`,
the base URL `harness/backends/tinker_backend.py` already uses:**

| request | result |
|---|---|
| `/chat/completions` + `logprobs:true, top_logprobs:3` | **HTTP 400** — `"top_logprobs=3 requested but top-k alternatives are not yet supported. Set top_logprobs=0 or omit it to get chosen token logprobs."` |
| `/chat/completions` + `logprobs:true, top_logprobs:0` | **200** — per-token logprobs for **generated** tokens, `top_logprobs: []` at every position |
| `/chat/completions` + `prompt_logprobs:0` | **200, silently dropped** — `logprobs: null`, no prompt logprobs anywhere in the response |
| `/completions` + `echo:true, max_tokens:0, logprobs:0` | **HTTP 400** — `"logprobs is not yet supported for /v1/completions. Use /v1/chat/completions instead."` |

The classic OpenAI `echo` + `max_tokens=0` teacher-forcing trick is therefore
**closed** on the shim, and so is every other route to prompt-side logprobs.
The shim gives sampled-token logprobs and nothing else.

**What a second backend path costs us.** Same `TINKER_API_KEY`, same models
(`Qwen/Qwen3.5-9B` resolves as a `base_model` on both surfaces). What differs:

- **Different client object.** `tinker.ServiceClient().create_sampling_client(base_model=...)`,
  not an HTTP POST. New dependency (`tinker`, 42 packages) and a tokenizer
  dependency (`transformers`) — `compute_logprobs` takes token ids, not text, so
  we must tokenize locally with `client.get_tokenizer()`.
- **No chat template applied for us.** `ModelInput.from_ints` is raw tokens. To
  score inside a chat-formatted prompt we render the template ourselves.
- **`separate_reasoning` and `reasoning_effort` do not exist in the native SDK.**
  Grepped the whole package: zero hits. They are shim-only concepts. So the
  scoring path and the generation path are genuinely two different surfaces, and
  our token-budget/context facts in `TINKER_MODEL_FACTS` were measured on the
  shim, not on this one.

This is a **new backend, not a new capability tier**. Nothing in the harness's
existing generation path has to change; scoring is a separate pass.

## 1.4 Constraints — measured, not read

**Max top-k (undocumented; the docs state no cap at all).** Measured live:

| `topk_prompt_logprobs` | result |
|---|---|
| 0 | ok, `topk_prompt_logprobs is None` |
| 1, 5, 20 | ok, width exactly k |
| 100 | ok (with `max_tokens=4`) |
| 1000 | **HTTP 400** — `"topk_prompt_logprobs=1000 exceeds limits: must be <= 20 or max_tokens * topk_prompt_logprobs must be <= 1000 (got 4000)"` |

So the real rule is `k <= 20` **or** `max_tokens * k <= 1000`. Irrelevant to us
(we want `prompt_logprobs`, not top-k), but it is the only hard numeric limit
anywhere in this area and the docs do not have it.

**Prefix caching works and is the operational headline.** Scoring 5 candidates
against a shared 6,013-token context:

```
   1557ms cache_hit=     0   the laws of the State of New York
   1680ms cache_hit=  6016   the laws of the State of Delaware
   1670ms cache_hit=  5888   Acme Corp and Beta LLC
   1244ms cache_hit=  5888   the Uniform Commercial Code
   1922ms cache_hit=  5888   this Agreement
```

`SampleResponse.prompt_cache_hit_tokens` confirms ~98% of the prefill is reused
across candidates. Scoring k candidates for one question is roughly **one
prefill plus k short suffix passes**, not k full prefills. At k=10 and ~1.5 s
per call that is ~15 s/question serially, and the calls are independent so they
parallelise.

**`compute_logprobs` always burns one generated token.** From the SDK source it
is sugar over `sample(..., max_tokens=1, include_prompt_logprobs=True)`. It also
returns *only* the flat list — for top-k you must call `sample()` directly.
Sampling params (`temperature`, `top_p`, `top_k`) do **not** affect prompt
logprobs; they are a prefill quantity. Verified: identical values at
`temperature=0.0` across repeated calls, and `ctx_prefix_stable` was `True`.

**Requires a sampling client**, not a training client. Works on base models
(`base_model=`) and LoRA checkpoints (`model_path=`) alike. A third route exists
via `TrainingClient.forward(data, loss_fn="cross_entropy")` which returns
`logprobs` for supplied `target_tokens` — heavier (needs a training client), but
it is the only route that gives logprobs for *specified* candidate tokens per
position rather than the model's own top-k.

## 1.5 The one caveat that matters for ranking

Sum-logprob is **length-biased**, and the live numbers show it is not a small
effect. In the governing-law probe the 14-token superset span scored −14.56 sum
/ −1.04 mean against the 8-token correct span's −14.11 / −1.76: **sum and mean
rank these two candidates in opposite orders.** Their start+end logit score has
no such bias.

This does not block the route — AUPR is invariant to monotone transforms, but
length bias is not monotone in the score, it is a confound. It means the
normalisation (sum vs mean vs length-penalised) is a **design decision that must
be made and justified before any AUPR is computed**, not a detail. It is
cheaply settleable: score the gold spans and a matched set of distractors on a
dev split and pick the normalisation that ranks best. Recommend doing that
before task 2.

Separately, one shim finding that closes out the plan's "sequence logprob is the
worst option" claim with evidence: with `separate_reasoning: true`, the shim's
`logprobs.content` array covers the **reasoning** tokens, not the `content`
field. Live, a request whose `content` was `''` and whose `reasoning_content`
was 40 tokens of thinking returned 40 logprob entries — all reasoning. There is
no field alignment between `logprobs` and `content`. Extracting "the logprob of
the emitted span" from the shim is not merely biased, it is **not implementable**
under our current `separate_reasoning=True` setting.

---

# Part 2 — how deep the n-best signal lives

Computed on the authors' shipped `nbest_predictions_.json` for all three
checkpoints against their own `repo/test.json`, 4,182 questions, via their
unmodified `evaluate.py` (`get_jaccard`, `get_preds`, `get_precisions_recalls`,
`get_aupr`, IOU 0.5, including the `substr_ok` special case for `Parties`).
`get_jaccard` was wrapped in an `lru_cache` for speed — same function, same
values. Our `test` split contracts were never loaded.

**Validation:** depth-20 AUPR recovers 0.4259 / 0.4825 / 0.4779, matching the
published 42.6 / 48.2 / 47.8 exactly. The harness is right.

Scripts: `scripts/cuad-baseline/nbest_depth.py`,
`scripts/cuad-baseline/nbest_dedup_depth.py`.
Data: `data/cuad-baseline/table2/nbest_depth.json`, `nbest_dedup_depth.json`.

## 2.1 Rank of first correct candidate — the misleading answer

Of 4,182 questions, 1,244 have gold. Fraction of *recoverable* questions
(those with a correct candidate anywhere in the 20) satisfied by depth d:

| depth | RoBERTa-base | RoBERTa-large | DeBERTa |
|---|---|---|---|
| 1 | 85.9% | 88.0% | **88.4%** |
| 3 | 94.7% | 96.0% | 97.1% |
| 5 | 97.5% | 97.5% | 98.6% |
| 10 | 98.9% | 98.9% | 99.6% |
| 20 | 100% | 100% | 100% |

Read alone this says "rank 1 is nearly everything, emit k=1". **That reading is
wrong**, and it is the trap this question was worth asking to avoid.

## 2.2 Gold-span recall — the answer that drives AUPR

Their recall denominator is **gold spans (2,643), not questions (1,244)** — an
average of 2.12 gold spans per answerable question, and up to 5.32 for `Parties`.
Their metric asks "did you find *each* gold span", so a shortlist of one can
never exceed one span per question.

Fraction of all 2,643 gold spans recovered by depth d:

| depth | RoBERTa-base | RoBERTa-large | DeBERTa |
|---|---|---|---|
| 1 | 45.8% | 46.5% | **47.3%** |
| 3 | 67.6% | 69.0% | 70.2% |
| 5 | 76.0% | 77.1% | 79.0% |
| 10 | 84.9% | 85.9% | 87.3% |
| 20 | 89.9% | 90.5% | **91.7%** |

**Depth 1 caps span recall at 47%.** This, not per-question hit rate, is what
their n-best depth is for. Their 20 candidates are not 20 hedges on one answer;
they are coverage of multi-span questions.

## 2.3 AUPR lost to truncation (raw n-best, no dedup)

| depth | RoBERTa-base | RoBERTa-large | DeBERTa | DeBERTa Δ vs 20 |
|---|---|---|---|---|
| 1 | 0.2755 | 0.3046 | 0.2943 | **−18.4 pp (−38%)** |
| 2 | 0.3276 | 0.3628 | 0.3534 | −12.4 pp |
| 3 | 0.3572 | 0.4047 | 0.3935 | −8.4 pp |
| 5 | 0.3872 | 0.4383 | 0.4321 | −4.6 pp (−9.6%) |
| 10 | 0.4152 | 0.4713 | 0.4644 | −1.3 pp (−2.8%) |
| 20 | 0.4259 | 0.4825 | 0.4779 | — |

So on the raw list, **depth 5 is not close to depth 20** — a 20-candidate output
is *not* mostly wasted tokens, contrary to the hypothesis in the brief. Depth 10
is close (within 3%).

**Precision@80%Recall is undefined below depth 10** on the raw list for every
model: max recall at depth 5 is 0.76–0.79, under the 0.8 threshold, so
`get_prec_at_recall` returns 0. If we want to report their headline operating
point at all, our shortlist must reach 80% span recall.

## 2.4 Near-duplicates — how much of the depth is a windowing artifact

Per question, fraction of the ~19.2 non-empty candidates that sit within
Jaccard ≥ 0.8 of at least one other candidate in the same question:

| model | near-dup fraction | exact-dup fraction | mean **distinct** candidates/question |
|---|---|---|---|
| RoBERTa-base | **59.5%** | 0.0% | **11.75** |
| RoBERTa-large | **61.5%** | 0.0% | **11.42** |
| DeBERTa | **60.7%** | 0.0% | **11.56** |

Exact duplicates are 0% — their n-best writer already collapses identical text.
So the ~60% is entirely *near*-duplication, which is the overlapping-window
signature. Collapsing near-dup clusters greedily in rank order leaves
**~11.5 genuinely distinct hypotheses per question, not 20.** Tyler's read is
confirmed: roughly **40% of their depth is an artifact of the 512-token
encoder**, not alternative hypotheses.

## 2.5 The decisive result — dedup then truncate

If we do not window, our k candidates are all distinct. So the right comparison
is *deduplicated* depth against their raw 20.

| depth | RoBERTa-base | RoBERTa-large | DeBERTa | DeBERTa span recall | DeBERTa P@80%R |
|---|---|---|---|---|---|
| 1 | 0.2755 | 0.3046 | 0.2943 | 47.3% | undefined |
| 3 | 0.3657 | 0.4136 | 0.4032 | 71.4% | undefined |
| 5 | 0.4011 | 0.4544 | 0.4484 | 81.4% | 0.380 |
| **8** | **0.4231** | **0.4788** | **0.4729** | **87.4%** | **0.450** |
| **10** | **0.4290** | **0.4862** | **0.4798** | **89.2%** | **0.465** |
| 20 (= full dedup list) | 0.4354 | 0.4930 | 0.4877 | 91.6% | 0.465 |
| *their raw 20* | *0.4259* | *0.4825* | *0.4779* | *91.7%* | *0.440* |

Three things fall out:

1. **Dedup at depth 10 matches or beats their raw depth 20 for all three
   models** (0.4290 > 0.4259; 0.4862 > 0.4825; 0.4798 > 0.4779). Ten distinct
   candidates are worth more than twenty windowed ones.
2. **Depth 8 reaches ~99% of full AUPR** (0.4231/0.4354, 0.4788/0.4930,
   0.4729/0.4877) and is the minimum depth at which all three models clear 80%
   span recall, i.e. the minimum at which P@80%R exists.
3. **Deduplication is net-positive, not merely neutral.** The full deduplicated
   list beats the raw list by +0.95 to +1.05 pp AUPR while losing only
   0.08 pp of span recall (2,423 → 2,421 spans of 2,643 for DeBERTa). Near-dups
   generate false positives above threshold without adding true positives.
   Their published AUPR is, in a small way, *depressed* by their own windowing.

## 2.6 Does it differ by model or category?

**By model: no, the shape is identical.** All three peak at ~11.5 distinct
candidates, ~60% near-dup, rank-1 question hit rate 86–88%, and the same
knee at depth 8–10. DeBERTa is uniformly a little better at every depth; the
*curve shape* is the same. This is architecture-independent and consistent with
it being a property of the windowing scheme, which all three share.

**By category: rank depth matters more for rare categories, but k=5 closes it.**
DeBERTa, fraction of recoverable questions found at rank 1 / top-5:

| group | n categories | mean gold spans/question | rank-1 | top-5 |
|---|---|---|---|---|
| frequent (≥40 answerable questions) | 9 | 2.00 | **0.921** | 0.994 |
| rare (<40) | 31 | 2.24 | **0.816** | 0.970 |

Worst rank-1 cases are rare *and* structurally ambiguous: `Most Favored Nation`
0.50, `Volume Restriction` 0.53, `Competitive Restriction Exception` 0.56,
`Non-Disparagement` 0.57, `Ip Ownership Assignment` 0.61, `Change Of Control`
0.67. All except `Most Favored Nation` and `Volume Restriction` reach ≥0.88 by
top-3.

The bigger category effect is **spans per question**, which is what k has to
cover: `Parties` 5.32, `Source Code Escrow` 5.00, `Rofr/Rofo/Rofn` 4.00,
`Insurance` 3.66, `Affiliate License-Licensor` 3.33 versus 1.00 for
`Document Name`, `Agreement Date`, `Most Favored Nation`. A fixed k is
wasteful on single-span categories and binding on `Parties`. A **variable k**
(model emits as many distinct spans as it believes exist, capped at 10) is
strictly better than a fixed one and costs nothing to specify — their format
already tolerates variable-length lists.

---

# What this means for the design

**Emit k = 10 distinct candidate spans per question, capped not padded.** k=8 is
the defensible floor; k=20 buys under 1 pp of AUPR for double the output tokens.
Do not emit near-duplicates — the whole point of having 65k context and no
windowing is that our 10 are 10 real hypotheses, and the dedup experiment shows
that is worth roughly the same as their 20.

**Do not emit k=1.** It looks defensible from the per-question hit rate (88%)
and is indefensible from the metric (span recall 47%, AUPR −38%, P@80%R
undefined). A committed single decision cannot be scored on their axes at all.
This is a genuine tension with D-14 and needs resolving explicitly: our
committed decision and our ranked shortlist are two different outputs and
should be two different fields, not one field asked to do both.

**A model-emitted within-question rank is not sufficient.** Their threshold is
swept globally across all 4,182 questions, so AUPR measures cross-question
ranking quality. A within-question rank of 1–10 gives us at most 10 discrete
global levels, which coarsens the PR curve badly and — per the plan's own
table — biases AUPR **low**. We need a continuous, cross-question-comparable
score. Teacher-forced candidate likelihood is now confirmed available and is
the best construct we have for it.

**Before computing any AUPR, settle the length normalisation** (§1.5). Sum and
mean logprob disagree on ranking in the very first realistic probe. That is a
one-afternoon dev-split experiment and it gates the whole route.

**Their windowing is a cost to them, not just a constraint.** §2.5 shows their
own AUPR would be ~1 pp higher with a deduplicated n-best. Worth a sentence in
the writeup: it is a clean, quantified example of an architectural artifact
showing up in a published number, which is the kind of thing this study exists
to notice.

---

## Things I made up that you should review

1. **"k=10" is a recommendation, not a measurement of our system.** It is
   derived from *their* models' candidate distributions. Our model's candidates
   may have a different rank-quality profile — plausibly better at rank 1
   (no window fragmentation) or worse (no trained span head). The k=10 figure
   says "10 distinct candidates is enough headroom to match their ceiling", not
   "our k=10 will score 0.48".
2. **The Jaccard ≥ 0.8 near-duplicate threshold is my choice.** 0.8 is a round
   number chosen to sit clearly above their 0.5 correctness threshold. The
   ~60% figure and the ~11.5 distinct-candidate count both move with it; I did
   not sweep it. The *direction* (a large minority of depth is duplication) is
   robust to the choice; the exact 40% is not.
3. **Greedy rank-order dedup** (keep a candidate if it is <0.8 Jaccard to every
   already-kept one) is one of several reasonable clusterings. It favours
   high-probability candidates by construction, which is the behaviour we want,
   but it is not connected-components and would give slightly different counts.
4. **"Variable k is strictly better than fixed k"** is an argument from the
   spans-per-question spread, not something I measured. I did not test whether a
   model asked for "as many as you think exist" produces a usefully calibrated
   count — that is plausibly a harder ask than producing a fixed 10.
5. **The `topk_prompt_logprobs` cap** (`k <= 20 or max_tokens*k <= 1000`) is
   from a single 400 response. I did not binary-search the boundary; k=100 with
   max_tokens=4 passed and k=1000 failed, consistent with the stated rule but
   not an independent confirmation of it.
6. **Latency and cache figures are one run of five calls** on a 6k-token
   synthetic context, not a benchmark. The ~1.5 s/candidate should be treated as
   an order of magnitude. I did not measure at our real ~30–60k contract lengths,
   where the first (uncached) prefill will be substantially more expensive.
7. **"Same auth story" for the native SDK** — `ServiceClient()` picked up
   `TINKER_API_KEY` from the environment and worked with no extra setup, but I
   only exercised sampling clients on base models. I did not check quota,
   rate-limit, or billing behaviour of the scoring path versus the shim, and
   `compute_logprobs` billing (it does generate 1 token per call) is unverified.
8. **I did not verify that our harness's chat template can be reproduced
   token-exactly** on the native path. If the scoring prompt must match the
   generation prompt exactly, that is an unvalidated assumption and a plausible
   source of silent skew.
