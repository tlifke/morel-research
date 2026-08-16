# C2 vs C3 on answer metrics — does requiring citation change what the model extracts?

**Run:** `data/traces/2026-08-16-c2c3-harness-val/` (240 trials) plus
`data/traces/2026-08-16-c2c3-budget-probe/` (12 trials, budget check only).
**Split:** `harness_val` (40 contracts). `test`, `principle_train`,
`principle_val` and `model_train` were not touched.
**Model:** `Qwen/Qwen3.5-9B` via Tinker. **Conditions:** C2, C3 only.
**Principle set:** `principles/working_set.yaml`, w01–w10, version
`working-set-2026-08-16`. **Schema variant:** `field_present` — **provisional,
P0 has not run.** **Seeds:** 0/1/2, three per contract per condition.
**Repair:** off (D-16, `max_repair_attempts = 0`).

**Contamination note travels with this table.** CUAD is public and in
pretraining corpora. The C3−C2 *comparison* is valid because both arms carry
the same contamination; the absolute numbers are not leaderboard-comparable.

---

## 1. The contrast, and its uncertainty

Paired by contract over the **38-contract intersection** where both conditions
produced at least one scored trial. Per-contract value is the mean over that
contract's scored seeds; CIs are 10,000-sample bootstraps over contracts.

| metric | C3 − C2 | 95% CI | t | contracts up/down |
|---|---|---|---|---|
| presence-class F1 (macro, per-trial) | +0.0029 | [−0.0048, +0.0121] | 0.68 | 5/5 |
| absent-class F1 (macro, per-trial) | +0.0037 | [−0.0037, +0.0113] | 0.94 | 10/6 |
| decision-kind accuracy | +0.0066 | [−0.0037, +0.0175] | 1.20 | 13/8 |
| false-present count per trial | −0.044 | [−0.136, +0.044] | −0.94 | 6/10 |
| false-absent count per trial | −0.035 | [−0.145, +0.057] | −0.68 | 5/5 |
| span F1 (TP cell) | −0.0075 | [−0.0406, +0.0252] | −0.44 | 17/16 |
| span precision | −0.0060 | [−0.0377, +0.0263] | −0.36 | 16/17 |
| span recall | −0.0075 | [−0.0429, +0.0269] | −0.42 | 18/15 |
| exact-match rate | −0.0027 | [−0.0584, +0.0521] | −0.09 | 16/15 |
| **verbatim exact rate** | **−0.0250** | **[−0.0462, −0.0050]** | **−2.35** | **6/17** |
| verbatim normalised-only rate | +0.0125 | [−0.0039, +0.0302] | 1.42 | 7/4 |
| verbatim not-found rate | +0.0126 | [−0.0111, +0.0378] | 0.99 | 10/8 |
| completion tokens | **+627** | **[+219, +1039]** | 2.96 | 25/13 |
| prompt tokens | **+48** | **[+48, +48]** | — | 38/0 |

**The answer-quality result is null.** Every accuracy metric's interval
contains zero. Nothing in the presence/absence call, the span overlap, or the
exact-match rate moves when the model is required to cite the principles it
used.

**Two things do move, and neither is an accuracy gain:**

1. **Byte-exactness of spans drops by 2.5 points** (17 of 23 contracts that
   moved went down). The mass shifts into `normalized_only` (+1.25) and
   `not_found` (+1.26), neither individually distinguishable from zero. The
   spans stay about as *correct* — span F1 is flat — but slightly fewer of them
   are literal substrings of the contract. This is the one signal worth
   following, and it is small.
2. **C3 reasons ~627 tokens longer per trial** for a prompt that is only 48
   tokens larger. The citation requirement costs roughly **13× its prompt cost
   in generated reasoning.**

### The one result that looked significant, and why it is not

Pooling decisions across the intersection rather than averaging per trial,
presence-class F1 comes out **+0.0169, CI [+0.0004, +0.0340]** — an interval
that excludes zero by four ten-thousandths, with both of its components
(precision +0.0163 [−0.0099, +0.0447], recall +0.0170 [−0.0028, +0.0370])
straddling zero.

It is a **survivorship artifact.** C3 lost more trials to parse failure than
C2, and the trials it lost were not a random subset. Restricting to the **18
contracts with a full 3/3 scored seeds in both conditions** — a seed-balanced
comparison with no survivorship asymmetry — the sign reverses:

| seed-balanced (18 contracts, 3/3 both arms) | C2 | C3 | delta | CI |
|---|---|---|---|---|
| presence-class F1 (pooled) | 0.7978 | 0.7956 | **−0.0022** | [−0.0172, +0.0117] |
| absent-class F1 (pooled) | 0.9219 | 0.9208 | **−0.0012** | [−0.0082, +0.0052] |

Read the null, not the +0.0169. Across ~14 comparisons, one interval clearing
zero by 0.0004 and vanishing under a cleaner design is what noise looks like.

---

## 2. What this run does and does not test

**The principle set is unselected.** It is `working_set.yaml`, not a locked or
curated set, and its own records say so:

- **9 of 10 principles carry `checker_status: needs_rebuild` or
  `not_yet_specified`.** Only **w03** is marked `usable`.
- **w10 has no measured footprint at all** — no applicability rate, no
  separability verdict, no phi. It was never built or footprinted.
- Several records fail D-21 separability outright (w01, w02, w04, w06 gate
  applicability on gold), and w06 fires on 1 of 480 harness_val decisions.

**Therefore this run tests whether *requiring citation of a principle set*
changes extraction. It does not test whether these principles are good.** A
null here is not evidence that principles do not help; it is evidence that
*adding a citation obligation on top of an already-present principle block*
does not change what the model extracts. C2 already contains all ten
principles — C3−C2 is the addition of the citation instruction alone, which
D-25 measured at 48 prompt tokens and this run confirms at exactly +48 on all
38 paired contracts.

**A null result is the finding.** It says the citation half of the study can be
built without fear that the requirement degrades extraction, and it says the
selection budget in inv 006 should not be spent hedging against that risk.

**Citation correctness remains unmeasured.** No applicability source is loaded,
so the runner correctly reports `citation: {available: false}` on all 100
scored C3 trials, and the environment logged the `APPLICABILITY_UNAVAILABLE`
warning. Nothing in this document is a citation-accuracy claim.

---

## 3. The manipulation worked

| | C2 | C3 |
|---|---|---|
| decisions scored | 1,260 | 1,200 |
| decisions with a non-empty `principles_cited` | **0 (0.0%)** | **1,077 (89.8%)** |
| principle references leaked into free-text fields | 0 | 0 |

C2 obeyed "leave `principles_cited` empty" perfectly and leaked nothing. C3
cited on ~90% of decisions. Citation distribution (C3, 1,077 cited decisions):

`w01` 619 · `w06` 368 · `w04` 99 · `w03` 98 · `w10` 91 · `w09` 48 · `w07` 22 ·
`w08` 19 · `w02` 14 · `w05` 5

Two observations, both to be read as description rather than result. **w01
(span granularity) and w06 dominate**, together taking 92% of citations — and
**w06 is the record whose checker fires on 1 of 480 decisions and whose
applicability gate is `gold_absence`.** The model cites it 368 times. **w10,
which has no measured footprint whatsoever, draws 91 citations.** Models cite
readily; citation frequency is not evidence a principle is doing work. This
echoes the smoke-run curiosity where the two most-cited principles were
fabricated calibration controls.

---

## 4. Feasibility — the assembled prompt, not the contract

**One contract is infeasible, identically in both conditions.**

| contract | contract tokens | condition | prompt estimate | + budget | limit | outcome |
|---|---|---|---|---|---|---|
| `INNOVIVA,INC_08_07_2014-EX-10.1-COLLABORATION AGREEMENT` | 41,703 | C2 (×3 seeds) | 50,843 | 67,227 | 64,512 | `infeasible_at_length` |
| same | 41,703 | C3 (×3 seeds) | 50,902 | 67,286 | 64,512 | `infeasible_at_length` |

**C2 and C3 have the same infeasible set** (`{INNOVIVA}` in both), so
infeasibility introduces no asymmetry into the contrast. The earlier finding of
zero infeasible contracts was about contract text alone; feasibility is decided
on the **assembled** prompt, and the principle block pushes this one over. The
gate fires 6 trials, 3 per condition.

**But it is very likely an estimator artifact, not real infeasibility.** The
gate uses `token_count_method: "heuristic"` — 4 chars/token — while CUAD text
runs at ~4.7. Regressing backend-measured prompt tokens on contract tokens over
the 38 contracts that did run gives

```
measured C2 prompt tokens ≈ 2,596 + 1.0079 × n_contract_tokens
```

which predicts **44,630** measured prompt tokens for INNOVIVA against the
heuristic's 50,843 — a **13.9% overstatement**. Predicted assembled cost is
44,630 + 16,384 = **61,014**, comfortably inside the 64,512 effective limit.
**This contract would almost certainly have run.** Reported, not fixed: the
brief forbids modifying `harness/`, and changing the token counter changes a
recorded parameter. Recommend an explicit decision before the grid — supplying
a real tokenizer to the backend would close it.

**The feasible sets are nonetheless not identical, for a different reason.**

| | C2 | C3 |
|---|---|---|
| contracts with ≥1 scored trial | 39 | 38 |
| paired intersection | **38** | **38** |
| in C2 only | `PharmagenInc_20120803_8-KA_EX-10.1_7693204_EX-10.1_Endorsement Agreement` | — |

Pharmagen drops out of C3 because **all three of its C3 trials failed
`json_decode`** (one of them truncated), while C2 scored 2 of 3. **Every paired
statistic in §1 is computed over the 38-contract intersection**, so the contrast
is over the same contracts on both sides. Pharmagen's C2 trials are excluded
from the paired comparison and reported here instead.

---

## 5. Output budget — unchanged, but truncation is not zero

**`max_output_tokens = 16384`, unchanged, as a single recorded value per
D-16.** `temperature = 0.7`, `max_repair_attempts = 0`. No per-model tuning.

The pre-run budget probe (12 trials spanning all four length buckets, including
the two longest contracts) saw **0 truncations**, with completions running
2,936–9,586 tokens against the 16,384 budget — a 58% peak. That justified
proceeding without raising the budget, and the budget was not raised.

**The full grid contradicts the probe's zero.** 4 of 240 trials truncated:

| condition | seed | bucket | contract | outcome |
|---|---|---|---|---|
| C3 | 1 | 0-4k | `LIGHTBRIDGECORP_11_23_2015-EX-10.26-STRA…` | `parse_failure` / `json_decode` |
| C3 | 0 | 0-4k | `GOCALLINC_03_30_2000-EX-10.7-Promotion A…` | `parse_failure` / `json_decode` |
| C3 | 0 | 0-4k | `CHINARECYCLINGENERGYCORP_11_14_2013-EX-1…` | `parse_failure` / `json_decode` |
| C3 | 0 | 4k-8k | `PharmagenInc_20120803_8-KA_EX-10.1_76932…` | `parse_failure` / `json_decode` |

**All four are C3. Three of four are on the shortest contracts.** C2 truncated
zero times. This is the same pathology the smoke run hit — runaway reasoning on
a *short* document — and it now has a condition asymmetry attached: the
citation requirement is what tips reasoning past the budget, and it does so
where the document gives least to reason about. Truncation rate is 3.3% in C3
and 0.0% in C2; overall 1.7%.

This does not invalidate the null. It does mean the probe under-sampled the
tail, and it is the mechanism behind C3's lower conformance.

---

## 6. Outcome rates

| | C2 | C3 |
|---|---|---|
| trials | 120 | 120 |
| `ok` | 105 | 100 |
| `parse_failure` | 9 (7.5%) | 12 (10.0%) |
| `api_error` | 3 (2.5%) | 5 (4.2%) |
| `infeasible_at_length` | 3 (2.5%) | 3 (2.5%) |
| truncated | 0 (0.0%) | 4 (3.3%) |
| **conformance** (ok / reached-model) | **105/114 = 92.1%** | **100/112 = 89.3%** |

Parse failure by stage, over trials that reached the model:

| stage | C2 | C3 |
|---|---|---|
| `json_decode` | 3 (2.6%) | 6 (5.4%) |
| `schema_validation` | 6 (5.3%) | 5 (4.5%) |
| `coverage` | 0 (0.0%) | 1 (0.9%) |

With repair disabled this **is** the clean unassisted conformance measurement.
C3 conformance is 2.8 points lower, driven by `json_decode` — which is where
truncation lands.

**The 8 `api_error` trials are infrastructure, not model behaviour.** All eight
are `tinker unreachable: [Errno 54] Connection reset by peer`, all in the
4k-8k bucket, and all occurred during the 8-way parallel burst. They are
recorded as a terminal outcome and excluded from scoring. They were *not*
retried, because retrying requires deleting rows from a store whose uniqueness
invariant is what makes the run resumable; silently re-rolling failed trials is
also the kind of thing that biases a result. Flagged for a decision.

---

## 7. Level A — presence and absence, with baselines

Pooled over all scored trials in each condition. **C2 has 1,260 decisions from
105 trials; C3 has 1,200 from 100** — the denominators differ, which is exactly
the survivorship asymmetry §1 warns about, so read these as per-condition
descriptions and take the contrast from §1.

| | C2 | C3 | always-absent | always-present |
|---|---|---|---|---|
| TP / FP / FN / TN | 381 / 39 / 142 / 698 | 371 / 31 / 129 / 669 | 0 / 0 / 523 / 737 | 523 / 737 / 0 / 0 |
| presence P | 0.907 | 0.923 | 0.000 | 0.415 |
| presence R | 0.728 | 0.742 | 0.000 | 1.000 |
| **presence F1** | **0.808** | **0.823** | **0.000** | **0.587** |
| absent P | 0.831 | 0.838 | 0.585 | 0.000 |
| absent R | 0.947 | 0.956 | 1.000 | 0.000 |
| **absent F1** | **0.885** | **0.893** | **0.738** | **0.000** |
| false-present | 39 | 31 | 0 | 737 |
| false-absent | 142 | 129 | 523 | 0 |
| decision-kind accuracy | 0.856 | 0.867 | 0.585 | 0.415 |
| macro presence F1 | 0.707 | 0.702 | — | — |
| macro absent F1 | 0.862 | 0.878 | — | — |

Both conditions beat both trivial baselines on both classes at the micro level.
The base rate is 41.5% present / 58.5% absent, so decision-kind accuracy of
~0.86 against an 0.585 always-absent floor is a real but unspectacular margin —
and it is base-rate-dominated, never a headline.

**The dominant error is false-absent by roughly 4:1** (142 vs 39 in C2, 129 vs
31 in C3). The model under-claims presence. That is a property of the task
setup shared by both arms, not something citation touches.

---

## 8. Level A by length bucket

Trivial baselines shift with bucket because the presence base rate does.

**0-4k** (17 contracts)

| | trials | ok | conf. | trunc. | TP/FP/FN/TN | presence F1 | absent F1 | always-present presF1 | always-absent absF1 |
|---|---|---|---|---|---|---|---|---|---|
| C2 | 51 | 49 | 0.961 | 0.000 | 116/10/48/414 | 0.800 | 0.935 | 0.436 | 0.838 |
| C3 | 51 | 48 | 0.941 | 0.059 | 115/10/45/406 | 0.807 | 0.937 | 0.435 | 0.839 |

**4k-8k** (9 contracts)

| | trials | ok | conf. | trunc. | TP/FP/FN/TN | presence F1 | absent F1 | always-present presF1 | always-absent absF1 |
|---|---|---|---|---|---|---|---|---|---|
| C2 | 27 | 23 | 0.958 | 0.000 | 95/16/31/134 | 0.802 | 0.851 | 0.627 | 0.704 |
| C3 | 27 | 16 | **0.727** | 0.037 | 63/8/19/102 | 0.824 | 0.883 | 0.599 | 0.729 |

**8k-16k** (7 contracts)

| | trials | ok | conf. | trunc. | TP/FP/FN/TN | presence F1 | absent F1 | always-present presF1 | always-absent absF1 |
|---|---|---|---|---|---|---|---|---|---|
| C2 | 21 | 17 | 0.810 | 0.000 | 91/8/30/75 | 0.827 | 0.798 | 0.745 | 0.578 |
| C3 | 21 | 18 | 0.857 | 0.000 | 100/9/29/78 | 0.840 | 0.804 | 0.748 | 0.574 |

**>16k** (7 contracts)

| | trials | ok | conf. | trunc. | TP/FP/FN/TN | presence F1 | absent F1 | always-present presF1 | always-absent absF1 |
|---|---|---|---|---|---|---|---|---|---|
| C2 | 21 | 16 | 0.889 | 0.000 | 79/5/33/75 | 0.806 | 0.798 | 0.737 | 0.588 |
| C3 | 21 | 18 | 1.000 | 0.000 | 93/4/36/83 | 0.823 | 0.806 | 0.748 | 0.574 |

Accuracy is remarkably flat across a 100× length range — presence F1 sits in
0.80–0.84 in every bucket in both conditions. **The C3 4k-8k conformance of
0.727 is the Pharmagen cluster plus the connection resets, not a length
effect**: n = 16 scored trials there, and its accuracy numbers rest on the
smallest denominator in the table.

---

## 9. Level B — spans, on the TP cell

**Denominator stated: Level B is computed on TP decisions only. C2 n = 381 TP
decisions (425 predicted spans); C3 n = 371 TP decisions (401 spans).**

| | C2 | C3 |
|---|---|---|
| TP denominator (decisions) | 381 | 371 |
| soft span precision | 0.810 | 0.814 |
| soft span recall | 0.744 | 0.742 |
| **soft span F1** | **0.768** | **0.767** |
| exact-match rate | 0.495 | 0.521 |
| spans classified | 425 | 401 |
| **verbatim exact** | **363 (85.4%)** | **338 (84.3%)** |
| **verbatim normalised-only** | **38 (8.9%)** | **39 (9.7%)** |
| **verbatim not-found** | **24 (5.6%)** | **24 (6.0%)** |
| multi-span ratio (pred/gold) | 0.893 | 0.872 |

Three-way verbatim classification is near-identical in the pooled view; the
paired test in §1 is the more sensitive read and finds the −2.5 point exact-rate
shift.

**The false-present cell, reported separately** (these are spans offered for
categories gold marks absent, so span F1 is undefined but verbatim fidelity is
not):

| | C2 | C3 |
|---|---|---|
| FP decisions | 39 | 31 |
| spans | 43 | 32 |
| verbatim exact | 25 (58.1%) | 23 (71.9%) |
| verbatim not-found | 6 (14.0%) | 3 (9.4%) |

**Invented language concentrates in the false-present cell** — 14.0% not-found
in C2's FP cell against 5.6% overall. When the model wrongly claims a category
is present, it is markedly more likely to have made up the supporting text. Both
conditions show it; C3's FP cell is smaller and cleaner, but on 31 decisions
that is not a claim.

---

## 10. Token and time cost

Per scored trial, means with bootstrap CIs:

| | C2 (n=105) | C3 (n=100) |
|---|---|---|
| prompt tokens | 10,789 [9,338, 12,366] | 11,531 [9,901, 13,292] |
| completion tokens | 8,293 [7,895, 8,669] | 8,939 [8,585, 9,277] |
| latency | 88.4 s [80.8, 96.9] | 105.3 s [96.7, 114.7] |

The unpaired prompt means differ by ~740 tokens, but that is a composition
artifact of which contracts scored. **Paired, the citation requirement's prompt
cost is exactly +48 tokens on every one of the 38 contracts** — confirming
D-25's backend-measured figure — while its completion cost is **+627 tokens
[+219, +1,039]** and latency runs ~17 s longer per trial.

**Totals across both runs (252 trial rows):** 3,193,056 prompt tokens +
2,066,898 completion tokens = **5,259,954 tokens**, and **6.55 model-hours** of
summed request latency.

**Wall clock:** roughly 5 hours end to end, across a session interruption.
Throughput was endpoint-limited, not local: eight parallel shards delivered
about the same aggregate rate as serial execution (~1.4 trials/min), with
per-request latency rising under concurrency. Each shard also paid ~15 minutes
of CUAD dataset parsing at startup, twice (initial launch and resume). The
resume relied on the store's uniqueness invariant via `skip_existing` and
re-ran none of the 204 completed trials.

---

## 11. Anomalies, in order of how much they should worry us

1. **C3-only truncation on short contracts** (§5). Four trials, all C3, three in
   the 0-4k bucket. The citation requirement inflates reasoning most where the
   document is smallest. Directly causes C3's conformance deficit. **This is the
   most actionable defect found.**
2. **The infeasibility gate is ~14% pessimistic** (§4). One contract excluded
   from a 40-contract split on an estimate that a fitted model says would have
   fit with 3.5k tokens to spare. On `test` (max 64,640 contract tokens) this
   will bite harder.
3. **Survivorship asymmetry between conditions** (§1). C3 lost more trials, and
   pooled statistics that ignore this produce a spurious significant result. Any
   future condition comparison should report the seed-balanced subset alongside
   the pooled one.
4. **8 transient connection resets** (§6), unretried, all in one bucket during
   the parallel burst. Needs a policy decision: retry-on-transport-error is
   defensible and is not the same as re-rolling a model failure.
5. **Citation frequency is uncorrelated with principle quality** (§3). The two
   most-cited principles include one whose applicability checker fires on 1 of
   480 decisions, and a principle with no measured footprint at all pulls 91
   citations. Do not let citation counts stand in for evidence in inv 006.
6. **Expiration Date and Volume Restriction are below their trivial baselines**
   (§12). Not a citation finding, but it is sitting in the data.

---

## 12. Per-category detail

Counts pooled per condition; baselines are per-category and identical in
structure across arms.

| category | C2 TP/FP/FN/TN | C3 TP/FP/FN/TN | C2 presF1 | C3 presF1 | always-present presF1 | always-absent absF1 |
|---|---|---|---|---|---|---|
| Agreement Date | 94/0/5/6 | 91/0/3/6 | 0.974 | 0.984 | 0.971 | 0.108 |
| Anti-Assignment | 57/0/2/46 | 55/1/0/44 | 0.983 | 0.991 | 0.720 | 0.609 |
| Cap On Liability | 39/0/12/54 | 37/0/13/50 | 0.867 | 0.851 | 0.654 | 0.679 |
| Exclusivity | 25/13/6/61 | 23/9/5/63 | 0.725 | 0.767 | 0.456 | 0.827 |
| **Expiration Date** | 16/0/69/20 | 16/0/63/21 | **0.317** | **0.337** | **0.895** | 0.320 |
| Governing Law | 78/0/3/24 | 75/0/2/23 | 0.981 | 0.987 | 0.871 | 0.372 |
| License Grant | 36/0/0/69 | 36/1/0/63 | 1.000 | 0.986 | 0.511 | 0.793 |
| Minimum Commitment | 10/7/19/69 | 9/6/18/67 | 0.435 | 0.429 | 0.433 | 0.840 |
| Most Favored Nation | 3/1/7/94 | 2/0/9/89 | 0.429 | 0.308 | 0.174 | 0.950 |
| Revenue/Profit Sharing | 20/8/11/66 | 24/4/9/63 | 0.678 | 0.787 | 0.456 | 0.827 |
| Source Code Escrow | 2/0/0/103 | 3/0/0/97 | 1.000 | 1.000 | 0.037 | 0.990 |
| **Volume Restriction** | 1/10/8/86 | 0/10/7/83 | **0.100** | **0.000** | **0.158** | 0.955 |

**Two categories lose to a trivial baseline, in both conditions:**

- **Expiration Date** scores 0.317 / 0.337 presence F1 against an
  **always-present baseline of 0.895.** Gold marks it present on 85 of 105
  decisions; the model claims absent on 69 of them. A constant "present" would
  nearly triple the score. This is the single worst cell in the study and it is
  a task-definition problem, not a citation problem.
- **Volume Restriction** scores 0.100 / 0.000 against an always-present 0.158,
  with 10 false-presents and at most 1 true-present in either arm.
- **Minimum Commitment** sits at parity with its baseline (0.435 vs 0.433).

Minimum Commitment and Volume Restriction are two thirds of the Savelka
confusable trio the study set out to probe, and both are at or below trivial.
Revenue/Profit Sharing, the third, is the only per-category cell where C3 shows
a visible gain (0.678 → 0.787) — on 31 present decisions, uncorrected for twelve
comparisons, so it is a hypothesis and not a result.

---

## 13. What this licenses next

- **Proceed with the citation half of the study.** The requirement does not
  degrade extraction. That was the open risk this run was scheduled to retire,
  and it is retired.
- **Fix the C3 truncation pathology before the grid**, or record it as a known
  condition-asymmetric conformance cost. It is currently a 2.8-point conformance
  penalty attributable to the manipulation itself.
- **Decide the tokenizer question** before `test` opens; the heuristic gate will
  exclude contracts that fit.
- **Do not read the principle-citation distribution as evidence about
  principles.** Build applicability (D-24) first; until then citation is
  frequency, not correctness.
- **Expiration Date's task definition needs looking at** independently of
  anything about principles.

*Written by Claude Code. Numbers are from
`data/traces/2026-08-16-c2c3-harness-val/` and are reproducible from the stored
trial and decision rows; individual trials are not re-runnable because Tinker
does not honour seeds, so the trace store is the only record of what was
sampled.*
