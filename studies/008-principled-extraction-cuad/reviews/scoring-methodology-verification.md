# Task 0 — scoring methodology verification

Recorded 2026-08-17. Three independent verification passes, dispatched blind:
upstream CUAD `evaluate.py`, the ContractEval paper + repo, and our own eval
code. This is the "report discrepancies before changing anything" step of the
CUAD eval harness plan. **Nothing has been changed yet.**

## The three regimes are genuinely different

| | unit | match rule | topology | TN cell |
|---|---|---|---|---|
| CUAD `evaluate.py` | gold span | set-Jaccard ≥ 0.5, + `Parties` substring escape | many-to-many | none |
| ContractEval | (contract, question) | `all(gold_span in pred)`, exact substring | n/a (binary per pair) | yes |
| our `harness/metrics.py` | (contract, category) decision | multiset token-F1 ≥ 0.5 | soft best-match | yes |

The plan's proposed **one-to-one greedy matching is a fourth regime**, matching
none of the above. See D-A below.

## Verified against source

### Upstream CUAD `evaluate.py`

- `get_jaccard` (`evaluate.py:58-74`): deletes `. , ; :`, lowercases, maps `/`
  to space, then `set(s.split(" "))`. **Splits on the literal space character,
  not whitespace** — newlines and tabs stay glued inside tokens, and runs of
  spaces emit an empty-string token that enters the union. Set Jaccard, so
  token multiplicity is discarded. No stemming, no stopwords, no Unicode
  normalization.
- Threshold `IOU_THRESH = 0.5`, compared with `>=` (`evaluate.py:7,102`).
- **Parties exception** (`evaluate.py:84,99-102`): `substr_ok = "Parties" in key`
  — a substring test on the whole question id, not an equality test on the
  category. Relaxes matching to `jaccard >= 0.5 or ans in pred`, tested on the
  **raw unnormalized strings**, gold-in-prediction only. Verified 0 spurious
  collisions on the test key set.
- **Topology is many-to-many** (`evaluate.py:90-128`), with no assignment and no
  consumption. Two independent passes: TPs counted in gold-space (a gold scores
  TP if *any* prediction matches), FPs counted in prediction-space (a prediction
  escapes FP if it matches *any* gold). Consequences:
  - ten near-duplicate predictions matching one gold → **TP=1, FP=0**;
  - one long prediction matching three golds → **TP=3, FP=0**;
  - `tp + fn == len(answers)` exactly, so recall's denominator is the gold-span
    count while precision's denominator mixes gold-space TPs with
    prediction-space FPs.
- Gold-empty questions: `fp += len(preds)`. Gold-empty **and** pred-empty
  contributes nothing — there is no true-negative term anywhere in the file.
- `get_preds` (`evaluate.py:27-39`): **exact-string dedup, last-wins** on
  probability (so duplicates retain the *lowest* probability in a
  descending-sorted n-best); drops the empty-string candidate without
  renormalizing the remaining probabilities; threshold is strict `>`.
- Aggregation is micro/pooled only. The shipped script never computes
  per-category numbers. AUPR sweeps 101 confidence values with a PR-envelope
  step and trapezoidal integration.

### ContractEval (arXiv 2508.03080, github.com/olivialiu121/ContractEval)

- Unit is the (contract, question) pair — confirmed in §III-A and in the code,
  one confusion increment per row.
- **"Fully cover" is exact substring containment of every gold span**:
  `all(substr.strip(" \n`") in output.strip(" \n`") for substr in label)`.
  Case-sensitive, whitespace-sensitive, no threshold, no partial credit. A model
  that reformats or re-wraps scores FN while being semantically correct.
- **FP arises only from gold-empty rows**, decided by whether
  `'no related clause'` appears in the output. `Evaluation.py` uses
  substring-anywhere; the two inference scripts disagree (`startswith` for
  proprietary, `in` for open-source), so their model families were scored by
  different predicates. Since ~70% of rows are gold-empty, their precision is
  substantially a string test.
- Jaccard is **byte-identical to upstream CUAD's**, including the `split(" ")`
  behaviour. Reported as a mean over *all* gold-positive rows including ones
  where the model declined outright, so it is contaminated by the laziness
  signal rather than being quality-given-hit.
- **F2 is in their Table III**: `(5·P·R)/(4·P+R)`, justified by CUAD's
  positive/negative imbalance. Aggregation micro/pooled; per-category numbers
  exist only for their Figure 4 and are never macro-averaged.
- False-declination denominator is a hardcoded `1244`. That matches the
  gold-positive question count established in our own depth analysis, so the
  constant is right for the full test split but silently deflates the rate for
  models that dropped rows on OOM.
- Their stated **4,128 test points is almost certainly a typo for 4,182**
  (102 × 41), which is what our reproduction holds.

### Our own code

- `score_split_runs.py:69-75` and `score_c2c3_with_cuad_evaluator.py:69-75` both
  implement upstream's many-to-many topology and import `get_jaccard`
  unmodified. `score_c2c3` asserts agreement with upstream to 1e-12.
- **Both scoring scripts drop the `Parties` substring exception**, which the
  analysis scripts (`nbest_depth.py`, `nbest_dedup_depth.py`) preserve. Dead
  code at 12 categories because `Parties` is excluded from the subset; **live
  and large at 41** — see D-C.
- `harness/metrics.py` shares no code with the CUAD evaluator and never computes
  Jaccard. `token_f1` (`metrics.py:101`) is **multiset** token-F1 over
  `re.findall(r"[a-z0-9]+")` — whitespace-agnostic, strips all non-alphanumerics,
  harmonic mean rather than |∩|/|∪|. Both it and upstream threshold at 0.5, but
  **they are thresholds on different functions**.
- `metrics.normalize_for_matching` (NFKC, quote/dash folding, whitespace
  collapse) is used **only** by the verbatim locator, never by `token_f1`. Two
  incompatible normalizations in one file, serving two metrics.
- **F2 exists nowhere in the study.** Every F-measure in the repo is β=1.
  `point_pr` and `pr()` compute no F-measure at all — precision and recall only.
- `nbest_dedup_depth.py:48-52` has greedy near-duplicate collapse at Jaccard
  ≥ 0.8, keep-first. Note 0.8 (duplicate) and 0.5 (match) are two distinct
  thresholds on the same function.
- Name collisions worth knowing: "recall" denotes three different quantities
  across the codebase (span-level IoU recall, question-level presence-detection
  recall, and soft mean best-token-F1); `presence_recall` is used with a
  gold-span denominator in `score_split_runs.py:216` and a decision denominator
  in `c2c3_absence_profile.py:86`.

## Decisions this forces

**D-A — one-to-one greedy vs many-to-many.** The plan specifies one-to-one
greedy. Upstream CUAD, ContractEval, and every scoring path we have are
many-to-many. Our Table 2 reproduction matched published values to four decimals
*because* of that topology; adopting one-to-one breaks the anchor that makes the
DeBERTa baseline credible, and penalizes DeBERTa for near-duplicate candidates
that are an artifact of its 512-token encoder. **Recommendation: many-to-many as
the headline, one-to-one computed as a sensitivity check only.**

**D-B — deduplication interacts with topology.** Under many-to-many, redundant
predictions on gold-*present* questions are already free, so near-dup dedup
barely moves those. Its real effect is on gold-*empty* questions, where
`fp += len(preds)` counts every surviving candidate — and those are ~70% of
questions. **Dedup is therefore mostly a precision intervention on the negative
majority**, which is exactly where DeBERTa's windowing artifact concentrates.
Threshold and ordering (dedup-then-truncate vs truncate-then-dedup) both need
fixing explicitly; the two existing analysis scripts do it in opposite orders.

**D-C — the Parties exception must be restored before any 41-category run.**
On `harness_val`, `Parties` is 216 of 951 gold spans (22.7%) — the single
largest category, and its golds are short entity names that models return inside
longer "by and between X and Y" spans. Without the exception those fail
set-Jaccard on length grounds. Scoring 41 categories with the current
`point_pr` would understate every system on roughly a quarter of all gold mass.

**D-D — whitespace normalization for the ContractEval arm.** 24 of 951
`harness_val` gold spans (2.5%) contain a newline or tab. Negligible under
Jaccard ≥ 0.5. Potentially decisive under ContractEval's exact-substring rule,
where any whitespace mismatch in any span flips the row to FN.

**D-E — pair-level rollup is not ContractEval's metric.** A "did any span match"
rollup over Jaccard-based MatchRecords is a third thing. Comparing to their
published Table III requires implementing their containment rule as a separate
arm.

**D-F — F2 and F1 are new code.** Not a port; nothing in the study computes
them.

## The scoring surface at 41 categories (`harness_val`)

Measured, not inferred:

- 1,640 questions (40 contracts × 41), **480 gold-positive (29.3%)** — closely
  matching ContractEval's ~30% positive rate on test.
- 951 gold spans, **1.98 per positive question**; 36.2% of positive questions
  are multi-span.
- Severe concentration: `Parties` is 216 spans (22.7%); 11 categories have fewer
  than 8. Micro-pooled metrics at 41 categories will be substantially a
  `Parties` measurement — an argument for reporting macro alongside micro even
  though neither external methodology does.

## Things the verification could not establish

- Whether our vendored `data/raw/evaluate.py` is byte-identical to upstream
  (not fetched and diffed).
- Whether ContractEval's published Table III numbers were regenerated after the
  `startswith`/`in` predicate divergence; their result CSVs are not in the repo
  and `Evaluation.py` references an undefined variable, so their pipeline is not
  runnable end-to-end from the repo alone.
- The empirical divergence between `metrics.token_f1` and upstream `get_jaccard`
  on our actual decision rows — no script currently joins the two.
