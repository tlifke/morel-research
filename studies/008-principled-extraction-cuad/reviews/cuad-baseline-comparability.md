# CUAD baseline comparability — can study 008 anchor against the paper's own models?

Assessment only. No models were run; the desktop is offline and this is a paper
feasibility study. Every claim about the CUAD pipeline below is quoted from the
paper (arXiv:2103.06268, v-of-record PDF) or from the repo at
`github.com/TheAtticusProject/cuad` (default branch `main`, last pushed
2023-07-13). Nothing is reconstructed from memory.

AI Assistant Used: Claude Code

---

## Verdict

**Yes — but only in one direction, and it is not the direction the study has
been assuming.**

The blocking assumption in `plans/component-contracts.md` ("Not computed, and
why") is that CUAD's metrics require a ranking we do not produce, and therefore
no comparison exists. That is half right. It is true that **we cannot produce
AUPR or Precision@80%Recall** — those summarise a curve, and we emit one
committed decision per target (D-14), which is a point. But a point on someone
else's curve is a perfectly legitimate comparison, and producing it requires
**no invented parameters on our side at all**.

The defensible artifact is:

> Their published precision–recall curve, recomputed on our 12-category subset
> from their released checkpoints, with our system plotted on it as a single
> (precision, recall) point — scored by **their** `evaluate.py`, on **their**
> gold, on **their** test split, with **their** Jaccard ≥ 0.5 matcher.

What that compares, precisely: *at the recall our system achieves, is our
precision above or below the precision a CUAD-finetuned extractive-QA model
achieves at that same recall, under an identical span-matching rule?* Nothing
more. It is not a claim about AUPR, not a claim about who has the better model,
and — because of the contamination asymmetry in §5 — it can support "we are
worse than / comparable to" far more strongly than "we are better than."

The reverse mapping (their spans → our Level A/B metrics) is **not** defensible
as a headline. It requires inventing a presence/absence decision rule their
system never specified, and every choice of that rule is attackable. It is
worth computing as a secondary, caveated exhibit — with a *swept* threshold so
we report their best case, not an arbitrary point — but it must not be the
anchor.

Feasibility and cost are **not** the constraint. All three released checkpoints
fit on a 12 GB RTX 3080 with room to spare, and the full 41-category test-split
inference for all three is ~3–7 GPU-hours locally or **~$2–5 of Modal GPU time**
(~$10–30 all-in once dependency-pinning iterations are priced). The real costs
are a 2021-era dependency stack and a governance problem (§3, §6): **every one
of our non-`test` splits is inside CUAD's official train set, i.e. inside their
fine-tuning data**, so there is no split on which their models are honest except
the sealed one. The baseline run is inherently G4-gated.

Recommendation: **do it, once, at G4, as a curve-plus-point figure** (§6).

---

## 1. Why their setup is framed as retrieval with ranking

### 1.1 The task shape

The paper structures CUAD as SQuAD-2.0-style extractive QA:

> "We finetune several pretrained language models using the HuggingFace
> Transformers library (Wolf et al., 2020) on CUAD. Because we structure the
> prediction task similarly to an extractive question answering tasks, we use
> the QuestionAnswering models in the Transformers library, which are suited
> for this task. Each 'question' identifies the label category under
> consideration, along with a short (one or two sentence) description of that
> label category, and asks which parts of the context relate to that label
> category. To account for the long document lengths, we use a sliding window
> over each contract."
> — paper, §"Experiments"

So the unit of prediction is the **(contract, category) pair**, exactly as ours
is under D-14. The 102-contract test set × 41 categories = 4,182 questions.
Encouragingly, *the decision granularity already matches.*

### 1.2 Chunking

`run.sh` (repo root) is the canonical invocation:

```
--max_seq_length 512 --max_answer_length 512 --doc_stride 256 --n_best_size 20
```

`train.py` calls `squad_convert_examples_to_features(..., max_seq_length,
doc_stride, max_query_length, ...)` with `--max_query_length` defaulting to 64.
So the doc window is ≈ 512 − 64 − specials ≈ **445 tokens, advancing 256 tokens
per window**. A 65k-token contract becomes ~250 windows *per category*.

Training had to be rebalanced because of this:

> "More than 99% of the features generated from applying a sliding window to
> each contract do not contain any of the 41 relevant labels. If one trains
> normally on this data, models typically learn to always output the empty
> span, since this is usually the correct answer. To mitigate this imbalance,
> we downweight features that do not contain any relevant labels..."

### 1.3 What a "prediction" actually is

`train.py` → `utils.compute_predictions_logits(...)` (a CUAD-modified copy of
HF's SQuAD post-processing) emits, per question id, an **n-best list of up to 20
candidate spans, each with a softmax `probability`** over the candidates'
start+end logit sums (`utils.py: _compute_softmax`, `output["probability"] =
probs[i]`). A null/empty candidate participates in that softmax
(`version_2_with_negative`), so absence is expressed as probability mass sitting
on the empty string, and `null_odds_.json` is written separately.

`evaluate.py` then does the thing that makes it a retrieval metric:

```python
def get_preds(nbest_preds_dict, conf=None):
    ...
        for pred_dict in list_of_pred_dicts:
            text = pred_dict["text"]; prob = pred_dict["probability"]
            if not text == "":
                preds[text] = prob
        preds_list = [pred for pred in preds.keys() if preds[pred] > conf]
```

**The empty prediction is discarded outright.** A "prediction" at threshold
`conf` is the *set* of non-empty candidates whose probability exceeds `conf` —
size 0 to 20, varying with `conf`. There is no committed answer; there is a
shortlist whose depth is a dial.

### 1.4 How the metrics are computed

`compute_precision_recall(gt_dict, preds_dict, category=None)` counts
**span-level** TP/FP/FN, micro-pooled over all questions:

- for each gold answer, TP if any predicted span matches, else FN;
- for each predicted span, FP if it matches no gold answer;
- for a question with zero gold answers, `fp += len(preds)` — up to 20 FPs from
  one question.

There is **no true-negative cell anywhere in their framework.** Correctly
saying "this category is absent" earns nothing.

Matching is Jaccard bag-of-words at 0.5:

> "We determine whether a highlighted text span matches the ground truth with
> the Jaccard similarity coefficient... A is the set of words in an annotation,
> and B is the set of words in an extracted prediction. To get the set of words
> in a string, we first remove punctuation and make the string lower case, then
> we separate the string by spaces... We use the threshold 0.5 ≤ J(A,B) for
> determining matches."

`evaluate.py` adds one undocumented exception: `substr_ok = "Parties" in key`,
which also accepts `ans in pred` for the Parties category. **"Parties" is not in
our 12-category subset**, so this exception never fires for us.

The curve is traced by sweeping the threshold:

```python
for conf in list(np.arange(0.99, 0, -0.01)) + [0.001, 0]:
```

then `process_precisions` takes the running max from the high-recall end
(interpolated precision: best precision achievable at this recall or higher),
`get_aupr` takes `sklearn.metrics.auc(recalls, processed_precisions)`, and
`get_prec_at_recall` walks the sweep and returns the first precision at
`recall >= 0.8` (or 0.9). Matching the paper:

> "Each prediction comes with a confidence probability. With the confidences,
> we can smoothly vary the minimum confidence threshold we use for determining
> what to count as prediction (while always ignoring the empty prediction). We
> can then compute the best precision that can be achieved at the recall level
> attained at each confidence threshold. This yields a precision-recall curve...
> The area under this curve is then the Area Under the Precision Recall curve
> (AUPR)."

Two code-reading notes for anyone reusing `evaluate.py`: `precisions`/`recalls`
are seeded with `[1]`/`[0]` but `confs` is not, so the `conf` *returned* by
`get_prec_at_recall` is off by one index (the precision value itself is
unaffected); and `preds[text] = prob` dedupes by text keeping the last
probability rather than the max.

### 1.5 Why this framing — and whether it is the same task as ours

It is a deliberate product decision, stated outright:

> "recall is more important than precision since CUAD is about finding needles
> in haystacks. Moreover, 80% recall may already be reasonable for some
> lawyers. The performance of DeBERTa may therefore already be enough to save a
> lawyer substantial time compared to reading an entire contract."

> "Note having a precision of about 30% at this recall level means that a
> lawyer would need to read through about 2 irrelevant clauses for every 1
> relevant clause selected as important by the model."

The deployed object is a **highlighter feeding a human reviewer**. Its output is
a shortlist whose length the reviewer implicitly controls, and its failure mode
of record is a missed clause, not a wasted glance. Under that framing a
committed presence/absence decision is not merely unnecessary, it is the wrong
product: it takes the recall/precision trade-off out of the lawyer's hands.

**Study 008's framing is a different task.** We ask for one adjudicated decision
per (contract, category) — present with these spans, or absent — because the
object of study is whether *principles* change how a decision gets made and
whether the agent can say *which* principle it followed. Absence is a
first-class ruling for us (D-14) and worth zero to them. Deliberation is the
dependent variable for us and is absent from their system entirely.

So the honest framing of any comparison: **same corpus, same gold, same
granularity of question, different output contract, different intended user.**
That is a real caveat but not a disqualifying one, because §2 shows the output
contracts are inter-convertible in one direction losslessly.

### 1.6 Their published numbers (Table 2)

| Model | AUPR | P@80% Recall | P@90% Recall |
|---|---|---|---|
| BERT-base | 32.4 | 8.2 | 0.0 |
| BERT-large | 32.3 | 7.6 | 0.0 |
| ALBERT-base | 35.3 | 11.1 | 0.0 |
| ALBERT-large | 34.9 | 20.9 | 0.0 |
| ALBERT-xlarge | 37.8 | 20.5 | 0.0 |
| ALBERT-xxlarge | 38.4 | 31.0 | 0.0 |
| RoBERTa-base | 42.6 | 31.1 | 0.0 |
| RoBERTa-base + Contracts Pretraining | 45.2 | 34.1 | 0.0 |
| RoBERTa-large | 48.2 | 38.1 | 0.0 |
| DeBERTa-xlarge | 47.8 | 44.0 | 17.8 |

These are **pooled micro over all 41 categories**. A recomputation restricted to
our 12 is a different number and must never be printed next to these as if it
were the same quantity.

---

## 2. Is a matched metric constructible?

### 2.1 Direction B (us → their `evaluate.py`) — the defensible one

This is the recommended anchor and it is close to free.

Our `TaskOutput` already contains everything their scorer consumes. The mapping
is total and involves no free parameters:

| ours | theirs |
|---|---|
| `Extraction(category, spans=[s1..sk])` | `preds_list = [s1..sk]` for that question id |
| `AbsenceClaim(category)` | `preds_list = []` |
| our decision, one per target | their question id, one per (contract, category) |

Then call `compute_precision_recall(gt_dict, our_preds_dict, category=...)`
unmodified. We get **one (precision, recall) point per (model, condition, seed)**
— three seeds give three points, reportable as a cloud or mean ± range.

Why this is defensible where the reverse is not:

1. **No parameter is invented on our side.** We do not choose a threshold; we
   have no threshold. The decision was already committed by the system under
   study, for reasons that are the study's subject.
2. **No parameter is invented on their side either.** Their curve is *all*
   thresholds. We compare against the whole curve, so we cannot be accused of
   picking a flattering or unflattering operating point for them.
3. **The matcher, gold, split, and pooling rule are all theirs.** The only thing
   that differs between the two systems on that plot is the system.
4. **The gold noise floor (D-15) cancels.** Both are scored against the same
   corrupted gold with the same matcher, so the ceiling is shared.

The claim it licenses: *"At R = x, a zero-shot prompted [model] under condition
C3 achieves P = y. DeBERTa-xlarge, fine-tuned on CUAD's 408 training contracts,
achieves P = z at the same recall on the same 12 categories."* That is a clean
sentence and it is the one worth having.

Caveats that must ship with it:

- **We are a point, not a curve; we never report AUPR or P@80%R for ourselves.**
  If our recall lands far from 0.8, the comparison must be read off the curve at
  *our* recall, and the paper's headline 44.0% is not the relevant number.
- **If our recall is very low (< ~0.2), the comparison is weak**, because their
  interpolated curve is near-vertical there and small recall differences swing
  precision wildly. This is a foreseeable outcome worth pre-registering: if our
  recall comes in under 0.2, report the point and say the comparison is
  uninformative rather than reading a precision gap off a cliff.
- **Their matcher is blind to the failure mode we care most about.**
  `get_jaccard` is bag-of-words over lowercased, punctuation-stripped tokens. A
  paraphrase, a reordering, or a normalised quotation can clear 0.5. Their
  system extracts spans by construction and *cannot* hallucinate; ours can. So
  their scorer **systematically flatters us** relative to our own Level-B
  verbatim-fidelity metric. Say so, and report our not-found rate alongside as
  the correction.
- **Multi-span outputs are punished span-wise.** Every unmatched predicted span
  is an FP. Their model at low `conf` emits up to 20 and eats the same penalty,
  so this is symmetric — but it means our Level-A-friendly habit of emitting
  several spans per decision costs precision under their rule in a way it does
  not under ours.
- **`evaluate.py`'s category filter is a substring test on the question id**
  (`if category and category not in key`). Question ids embed the contract
  title, so a title containing e.g. "Exclusivity" would silently pull in the
  wrong questions. Verify the 12-way partition is exact before trusting any
  per-category number.

### 2.2 Direction A (their models → our Level A/B) — secondary, caveated

The proposal in the brief was: take their top-1 span above their operating
threshold, call it a presence decision, score with Level A/B. **Do not do it in
that form.** Two independent problems:

1. **"Their operating threshold" is not a property of their model.** It is the
   `conf` value that `evaluate.py` discovers, *on the test set*, to make recall
   hit 0.8. At that point `conf` is low and the top-1 non-empty candidate is
   almost always present, so their system would be recorded as claiming presence
   nearly everywhere and would post a catastrophic Level-A presence precision.
   That measures our thresholding choice, not their model. This is exactly the
   handicap the brief warned about, and it is worse than "not tuned for top-1" —
   it is a rule they never wrote.
2. **They do have a genuine presence/absence signal and it is not the one
   proposed.** Their models were trained `--version_2_with_negative` and emit
   `null_odds_.json`; `compute_predictions_logits` already implements
   `score_diff = score_null − best_non_null_start − best_non_null_end;
   predict null iff score_diff > null_score_diff_threshold`. That IS an
   absence ruling, and it is the one their architecture was trained to make.

So if Direction A is computed at all, the honest form is:

- decide presence via the **null-score-diff rule**, not top-1-above-`conf`;
- **sweep τ** and report their *best achievable* Level-A F1 over the sweep,
  rather than one point — this removes the "you picked a bad operating point"
  objection completely;
- tune nothing on `test`; if a single τ is quoted, it must come from a split
  their models never saw — and §3/§6 shows **no such split exists in our
  arrangement**, which is itself a reason to prefer the swept, best-case form.

Even done that way, Direction A has an irreducible unit mismatch: their TP/FP/FN
are over **spans**, ours (Level A) over **(contract, category) decisions**, and
their framework has no TN cell at all, so our absent-class precision/recall and
our trivial always-absent baselines have no counterpart on their side.
Direction A is therefore an illustrative exhibit — "here is roughly what a
CUAD-finetuned model looks like under our metrics if you force it to commit" —
and never a headline.

### 2.3 The direction that does not work: eliciting confidence to get AUPR

Rejected. Reasons, in descending order of force:

1. **It would require abandoning D-14.** AUPR needs a ranked candidate list deep
   enough to trace recall from 0 to 1 — their n-best is 20 deep. Emitting 20
   ranked candidates per target is a *different task* from committing to one
   decision, and the committed decision is the object study 008 exists to
   measure. It would also destroy the citation denominator (D-14's second
   rejection ground) and make C3 non-comparable across models.
2. **A single self-reported confidence is far too coarse.** Prompted confidences
   pile up at a handful of round values; AUPR is dominated by ranking resolution
   across the pooled 1,224 decisions (102 × 12).
3. **Token logprobs are not available where we need them.** Per
   `plans/component-contracts.md`, all current arms run through Tinker in
   prompt-plus-parse mode; there is no scored-candidate surface.
4. **Self-consistency over 3 seeds gives 4 confidence levels.** Not a curve.

If the study ever wanted a genuine curve it would need a deliberate
candidate-generation arm, which is a separate investigation and arguably a
different study.

---

## 3. Can we run their checkpoints locally on the 12 GB RTX 3080?

**Yes, comfortably — with two real caveats that are about CPU/RAM and software
age, not VRAM.**

### 3.1 The checkpoints

The repo README:

> "We [provide checkpoints](https://zenodo.org/record/4599830) for three of the
> best models fine-tuned on CUAD: RoBERTa-base (~100M parameters),
> RoBERTa-large (~300M parameters), and DeBERTa-xlarge (~900M parameters)."

Zenodo record 4599830 ("Models finetuned on the Contract Understanding Atticus
Dataset (CUAD)") holds exactly three files: `roberta-base.zip` (447.4 MB),
`roberta-large.zip` (1.3 GB), `deberta-v2-xlarge.zip` (3.1 GB) — 4.9 GB total.

These are the *paper's own* checkpoints and are the ones to use. Third-party
HuggingFace re-finetunes exist (e.g. `akdeniz27/deberta-v2-xlarge-cuad`,
`akdeniz27/roberta-large-cuad`) but they are independent training runs, not the
released artifacts, and using them would forfeit the ability to check
reproduction against Table 2.

Precision: the checkpoints are 2021-era fp32 `pytorch_model.bin`. Inference in
fp16 is safe for all three (encoder-only, no known fp16 instability); note
`train.py`'s `--fp16` path goes through **apex**, which is a 2021 dependency
nobody should install today — use `torch.autocast` instead, or just run fp32.

### 3.2 VRAM

| model | params | fp32 weights | fp16 weights | verdict on 12 GB |
|---|---|---|---|---|
| RoBERTa-base | ~125M | 0.50 GB | 0.25 GB | trivial |
| RoBERTa-large | ~355M | 1.42 GB | 0.71 GB | trivial |
| DeBERTa-v2-xlarge | ~900M | ~3.6 GB | ~1.8 GB | fits with wide margin |

Sequences are fixed at 512 tokens, so activation memory does not grow with
contract length — **the sliding window removes long-document VRAM pressure
entirely**, which is the opposite of our generative arms' situation. DeBERTa-v2's
disentangled attention allocates extra `[B, heads, L, L]` score matrices
(24 heads × 512² × 4 B ≈ 25 MB per matrix per batch item, a few per layer under
`no_grad`); at batch 8 that is a few hundred MB transient. Batch 8–16 at fp32 is
safe on 12 GB; fp16 leaves room for batch 32.

**VRAM is not the constraint.** WSL2 costs ~5–10% throughput and some host RAM
headroom; it does not change the verdict.

### 3.3 Compute — what the run actually costs

Measured from our manifest (`data/processed/instances.jsonl`, aggregate token
counts only; no test-split text was read):

- `test`: 102 contracts, **1,016,885 Qwen3-8B reference tokens**, 4,778,515
  characters, mean 9,969 tok, median 5,440, max 64,640.
- Converting to their tokenizers at ~4.0 chars/token (RoBERTa BPE) and ~4.3
  (DeBERTa-v2 SentencePiece) on this legalese: **~1.19 M / ~1.11 M subword
  tokens**.
- Windows at `span=445, stride=256`: **4,646 (RoBERTa) / 4,319 (DeBERTa) per
  category**.

| | 41 categories | 12 categories |
|---|---|---|
| RoBERTa sequences | 190,486 | 55,752 |
| DeBERTa sequences | 177,079 | 51,828 |

FLOPs per 512-token sequence (2·params·tokens for the encoder, plus attention;
DeBERTa allowed a 2.5× attention multiplier for disentangled attention):
RoBERTa-base **97 GFLOP**, RoBERTa-large **335 GFLOP**, DeBERTa-v2-xlarge
**792 GFLOP**. Full 41-category test-split totals: **18 / 64 / 140 PFLOP**.

Wall-clock, assuming an effective **18 TFLOPS** on the 3080 in fp16 (≈30% of its
59.5 TFLOPS fp16-with-fp32-accumulate tensor peak, which is a normal MFU for HF
encoder inference at seq 512):

| model | 41 cats | 12 cats |
|---|---|---|
| RoBERTa-base | 0.28 h | 0.08 h |
| RoBERTa-large | 0.98 h | 0.29 h |
| DeBERTa-v2-xlarge | 2.17 h | 0.63 h |
| **all three** | **~3.4 h** | **~1.0 h** |

At fp32/TF32 (~9 TFLOPS effective) double these: ~6.9 h for all three at 41
categories. Either way this is an overnight job at worst.

### 3.4 The two real caveats

**(a) Feature conversion, not the GPU, is the bottleneck.**
`train.py --threads` defaults to **1**, and
`squad_convert_examples_to_features` is notoriously slow single-threaded.
190,486 features on one core is plausibly hours — potentially longer than the
GPU work. Fix: `--threads 8`–`16`, and shard the run per category.

**(b) RAM will bite before VRAM does.** `load_and_cache_examples` builds the
entire feature list in memory and then `torch.save({"features", "dataset",
"examples"}, cached_features_file)`. A `SquadFeatures` object holds several
512-element Python lists plus a `token_to_orig_map` dict and a token string
list — on the order of tens of KB each. At 190k features that is **~10 GB+ of
host RAM and a multi-GB cache file**, per model. Fix: run one category at a time
(41 shards of ~4.6k features each), which also makes the job resumable and caps
peak RAM at a few hundred MB.

Neither is a blocker; both are reasons the job should be scripted as a sharded
loop rather than one `run.sh` invocation.

### 3.5 The software stack is the actual difficulty

README: *"This repository requires the HuggingFace Transformers library. It was
tested with Python 3.8, PyTorch 1.7, and Transformers 4.3/4.4."*

`train.py` imports, all of which are fragile against modern versions:

```python
from transformers import (MODEL_FOR_QUESTION_ANSWERING_MAPPING, WEIGHTS_NAME,
                          AdamW, ..., squad_convert_examples_to_features)
from transformers.data.processors.squad import SquadResult, SquadV1Processor, SquadV2Processor
from transformers.trainer_utils import is_main_process
```
and `utils.py` does `from transformers.models.bert import BasicTokenizer`.

`AdamW`, `WEIGHTS_NAME`, `is_main_process`, the top-level
`squad_convert_examples_to_features` export, and `BasicTokenizer`'s location have
all moved or been removed across the 4.x → 5.x line. Two viable stacks:

- **Pin old (recommended).** Python 3.9/3.10, `torch==1.13.1+cu117`,
  `transformers==4.12.x`, `datasets` not needed, `scikit-learn` + `pandas` for
  `evaluate.py`. Torch 1.13/cu117 supports **sm_80 (A100) and sm_86 (A10G, RTX
  3080)**. This runs `train.py --do_eval` essentially unmodified. Note PyTorch
  1.7 as shipped will *not* work on the 3080 — Ampere GA102 is sm_86 and needs
  cu111+, i.e. torch ≥ 1.8.
- **Modernise.** Modern torch 2.x + transformers, with ~5 import patches and a
  `torch.load(..., weights_only=False)` accommodation for the 2021
  `pytorch_model.bin` (torch ≥ 2.6 flipped that default). More work, but it is
  the only option on newer GPUs (see §4).

---

## 4. If not local: Modal cost

Local is fine, so this is a convenience/parallelism option rather than a
necessity. It is cheap enough that it may be worth it anyway to avoid a 2021
stack on the desktop.

### 4.1 GPU class

**Choose an Ampere GPU: A10G (sm_86) or A100-40GB (sm_80).** This is not a
performance choice, it is a *dependency* choice — the pinned-old stack
(`torch 1.13.1+cu117`) supports sm_80/sm_86 and nothing newer. L40S (sm_89) and
H100 (sm_90) would force torch 2.x and therefore the modernisation path with its
import patches. Do not pick a faster GPU and then discover the stack does not
build on it.

A10G's 24 GB is ample; even T4 (16 GB, sm_75) would fit but is slow and fp16
tensor-limited.

### 4.2 Cost

At Modal's listed rates (A10 ≈ **$1.10/h**, A100-40GB ≈ **$2.10/h**, physical
core ≈ $0.047/h, memory ≈ $0.008/GiB-h), and assuming an effective 37 TFLOPS on
A10G / 94 TFLOPS on A100-40GB (same ~30% MFU assumption as §3.3):

| | A10G GPU-h | A10G $ | A100-40 GPU-h | A100-40 $ |
|---|---|---|---|---|
| RoBERTa-base, 41 cats | 0.14 | $0.15 | 0.05 | $0.11 |
| RoBERTa-large, 41 cats | 0.48 | $0.53 | 0.19 | $0.40 |
| DeBERTa-xlarge, 41 cats | 1.05 | $1.16 | 0.41 | $0.86 |
| **all three, 41 cats** | **1.67** | **$1.84** | **0.65** | **$1.37** |
| all three, 12 cats | 0.49 | $0.54 | 0.19 | $0.40 |

**Realistic all-in: $10–30.** The GPU seconds are $2–5. What actually costs
money is (a) feature conversion and model loading pinned to a GPU-attached
container — mitigate by doing feature conversion on a CPU-only Modal function
and caching features to a Volume, which drops the GPU-attached time to close to
the compute numbers above; (b) 3–6 image-build/debug iterations on a 2021 stack,
each mostly CPU-time but each burning wall-clock; (c) re-runs after any
`evaluate.py` wiring mistake.

### 4.3 Assumptions behind the numbers, stated

1. **~30% MFU** for HF encoder inference at seq 512, batch 8–16. If real
   throughput is half that, double every time and dollar figure; the conclusion
   ("cheap") survives a 4× miss.
2. **chars/token of 4.0 (RoBERTa) / 4.3 (DeBERTa-v2)** on CUAD text, extrapolated
   from the measured 4.699 for Qwen3-8B. A 15% error here moves everything 15%.
3. **Window count ≈ N/256 + 1**, from `max_seq_length 512`, `max_query_length
   64`, `doc_stride 256` per `run.sh` and `train.py` defaults. Exact per-window
   packing in `squad_convert_examples_to_features` may differ by a few percent.
4. **DeBERTa disentangled attention costs 2.5× standard attention.** Attention is
   a minority of total FLOPs at seq 512, so even a 2× error here moves the
   DeBERTa total by <15%.
5. **Feature conversion moved off the GPU container.** If it is not, add 1–4 h of
   GPU-attached wall-clock per model and roughly 3–5× the dollar figure.
6. Modal prices as listed on `modal.com/pricing` at time of writing.

---

## 5. Is the comparison meaningful even if computable?

Two asymmetries. They point in **opposite** directions, which is what makes the
resulting claim one-sided rather than useless.

### 5.1 Training asymmetry — favours them

They fine-tuned on 408 CUAD contracts × 41 categories, with a deliberate
class-rebalancing scheme, selecting the checkpoint by grid search on a held-out
validation set:

> "We chose a random split of the contracts into train and test sets. We have
> 80% of the contracts make up the train set and 20% make up the test set. In
> preliminary experiments we set aside a small validation set, with which we
> performed hyperparameter grid search... We select the model with the highest
> AUPR found using grid search and report the performance of that model...
> Models are trained using 8 A100 GPUs."

We prompt a general model with no task-specific training at all. The comparison
is therefore **zero-shot prompted general LLM vs. task-specific fine-tuned
encoder** — a well-precedented and interesting framing, but it cannot support a
claim about model quality. It can support a claim about *what the task costs to
reach a given quality*: "prompting with an explicit principle set reaches
precision P at recall R with no labelled training data, against a model that
consumed 408 expert-annotated contracts to reach P' at the same R."

Phase 2 changes this: fine-tuning on `model_train` (264 contracts) would put us
in the same regime, on a **subset of their own training pool** (264 of their
408). That is a *much* better-matched comparison and is worth flagging now as a
reason to keep the baseline infrastructure once built.

### 5.2 Contamination asymmetry — favours us, and is unfixable

Their encoders' pretraining corpora all predate CUAD's March 2021 release, and
their fine-tuning saw only the official train split. **Their test exposure is
genuinely zero — the annotations could not have been seen.** (The underlying
contracts are public SEC/EDGAR filings and could appear in a web crawl; the
*labels* could not.)

Our arms are modern models. CUAD v1 has been public since 2021 on GitHub,
Zenodo, the Atticus site, and HuggingFace (`theatticusproject/cuad-qa`,
CC-BY-4.0), which is exactly the shape of thing that lands in a pretraining
corpus. Our models may have seen the test contracts *and their gold
annotations*.

Consequence, and it should be stated in the writeup rather than buried:

> **This comparison is directionally asymmetric.** A result showing our system
> at or below the CUAD-finetuned baseline is strong evidence, because
> contamination could only have helped us. A result showing our system above
> the baseline is confounded and cannot be read as a modelling claim.

This is *also* the argument for why the study's real load-bearing results are
the **condition contrasts** (C1 vs C2 vs C3), which share the contamination
exactly and therefore cancel it. The CUAD baseline is context, not the finding.

### 5.3 Smaller mismatches worth listing in limitations

- **12 categories, not 41.** Their published numbers are 41-pooled. Anything we
  compute on 12 is our recomputation and must be labelled as such.
- **Point vs curve.** Restated because it is the one a reviewer will press on.
- **Their matcher cannot see hallucination** (§2.1); our verbatim-fidelity rates
  are the correction and must be printed adjacent.
- **Gold noise (D-15) is shared and therefore cancels** — a rare place where the
  comparison is cleaner than either system's absolute numbers.
- **Prior prompted-LLM work on CUAD does not solve this for us.** Savelka et al.
  (arXiv:2305.04417) and later prompt-engineering papers report CUAD numbers,
  but each reformulates the task (typically classification over pre-segmented
  candidate clauses) and reports its own metric, so their numbers are no more
  drop-in comparable than the paper's. Worth one afternoon to confirm before
  citing — **flagged as unverified secondary reading, not established here.**

---

## 6. Recommendation, alternatives ranked

### The governance point that changes the sequencing

**Every one of our non-`test` splits sits inside CUAD's official *train* set,
which is these models' fine-tuning data.** `harness_val` was drawn from the 408
official-train contracts (INV1-D5); `model_train`, `principle_train`,
`principle_val` were carved from the same pool; `scratch` duplicates other
splits' content. There is therefore **no split on which the CUAD baselines are
honest except `test`**, which `plans/splits.md` rule 1 seals until G4.

Two consequences:
1. The baseline run cannot be rehearsed for real numbers before G4. Pipeline
   shakedown on `harness_val` is fine and useful — it will validate the wiring,
   the id mapping, and the RAM/threads fixes — but any *score* it produces is
   meaningless (their models memorised those contracts) and must not be recorded
   as a result.
2. Reproduction of Table 2 (§ below) requires the test split, so it too is
   G4-gated. Plan for it there.

### Ranked options

**1. (Recommended) Direction B, at G4, as one figure.** Run all three released
checkpoints over the `test` split, all 41 categories, via the pinned-old stack.
Then:
- **Reproduction gate first:** run `evaluate.py` unmodified on all 41 categories
  and check we recover AUPR 42.6 / 48.2 / 47.8 and P@80%R 31.1 / 38.1 / 44.0. If
  the released checkpoints do not reproduce Table 2, everything downstream is
  void and we should say so and stop. This is why the 41-category run is not
  optional overhead — it *is* the sanity check.
- Recompute their PR curves restricted to our 12 categories (`evaluate.py`
  already takes a `category` argument; verify the substring filter partitions
  cleanly).
- Plot our per-(model, condition, seed) points on those axes.
- Report our Level A/B/C numbers *separately and unchanged* as the study's own
  metrics; the CUAD plot is one external-anchor figure, not a replacement.
Cost: ~$10–30 on Modal, or an overnight run on the 3080 once it is back. Effort:
1–2 days, most of it dependency pinning and the sharded-inference wrapper.

**2. Direction A as a secondary exhibit, same run, no extra inference.** Once
`nbest_predictions_.json` and `null_odds_.json` exist, deriving a presence/
absence decision via the null-score-diff rule with a **swept** τ costs only CPU.
Report their best achievable Level-A F1 over the sweep, explicitly as a best
case. Marginal cost ≈ 0; marginal risk = a reader mistaking it for the anchor,
so it belongs in an appendix.

**3. Cite Table 2 as context, run nothing.** Zero cost, zero risk, and honest if
worded as "for scale, the CUAD paper's best fine-tuned model reaches 44.0%
Precision@80%Recall over 41 categories under a ranked-shortlist protocol we do
not share." This is a genuinely acceptable fallback and should be the plan if
G4 slips or the reproduction gate fails. It gives the reader a sense of the
task's difficulty without pretending to a comparison.

**4. Elicit confidences to compute our own AUPR.** Rejected — §2.3. It would
require abandoning D-14, which is the study's decision model.

**5. Adopt a different external anchor entirely.** The prompted-LLM CUAD
literature (§5.3) is the obvious candidate but each paper reformulates the task,
so this trades one comparability problem for a less-documented one. Only worth
pursuing if the reproduction gate fails.

### Bottom line for the study

The `plans/component-contracts.md` line — *"CUAD's own benchmark metrics are
AUPR and Precision@80%Recall, which assume a retrieval-ranking setup. This is
generative extraction with no candidate ranking, so they are not computable
here"* — is **correct as written and should stay**. But the conclusion drawn
from it ("therefore no comparison") should be replaced. We cannot compute their
*summary statistics*; we can put ourselves on their *axes*, exactly and
cheaply, and that is the comparison worth having.

---

## Things I made up that you should review

1. **~30% MFU** on the 3080/A10G/A100 for HF encoder inference at seq 512. A
   plausible engineering assumption, not measured. Every time and cost figure in
   §3–§4 scales inversely with it.
2. **chars/token = 4.0 (RoBERTa) / 4.3 (DeBERTa-v2)** on CUAD text. Extrapolated
   from our measured 4.699 for Qwen3-8B; not tokenized.
3. **DeBERTa disentangled attention = 2.5× standard attention FLOPs.** A guess,
   low-impact.
4. **~10 GB host RAM for 190k `SquadFeatures`.** Order-of-magnitude reasoning
   about Python object sizes, not profiled. The *direction* (RAM binds before
   VRAM) I am confident about; the number I am not.
5. **`transformers==4.12.x` + `torch==1.13.1+cu117` as the pin.** Chosen for
   sm_80/86 support and 4.x API surface; not build-tested. The specific minor
   version may need adjusting.
6. **The claim that `--fp16` in `train.py` requires apex.** Read off the import
   guard in the source; I did not test whether the eval path ever touches it
   (it may only matter for training, in which case fp32 eval is the default
   regardless).
7. **The "if our recall < 0.2 the comparison is uninformative" threshold.** My
   judgement call about where their interpolated curve gets too steep to read;
   pick your own number, but pre-register something.
8. **Modal price list** as fetched; verify before committing budget.
9. **The prior-art paragraph (§5.3)** rests on search-result summaries of
   arXiv:2305.04417 and a ScienceDirect abstract, not on reading those papers.
   Treat as a lead.
10. **That the released Zenodo checkpoints reproduce Table 2.** Untested and
    genuinely uncertain — hence its promotion to a hard gate in option 1.
11. **Governance reading**: I have treated "running their baseline on `test`" as
    a G4-gated action under `splits.md` rule 1. Arguably a third-party model
    reading the sealed split leaks nothing to our system; but it would produce
    test-split numbers early and create anchoring pressure, so I recommend the
    conservative reading. Your call.
