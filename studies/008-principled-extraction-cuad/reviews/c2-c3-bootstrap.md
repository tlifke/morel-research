# Confidence intervals for the C2-vs-C3 contrast under CUAD's scorer

**Verdict up front: the precision difference is not distinguishable from
noise, and neither is anything else.** The 19-fewer-false-positives gap on
`reviews/c2-c3-results.html` should continue to be displayed and not claimed.

**Inputs:** `data/cuad-baseline/c2c3_cuad_scored.json` and the trial/decision
rows under `data/traces/2026-08-16-c2c3-harness-val/`, scored by
`data/raw/evaluate.py` through `scripts/score_c2c3_with_cuad_evaluator.py`
(imported, not reimplemented — same `get_jaccard`, same `IOU_THRESH = 0.5`,
same micro-pooled TP/FP/FN).
**Script:** `scripts/bootstrap_c2c3_cuad_contrast.py` →
`reviews/c2-c3-bootstrap-data.json`, which the page generator folds into
`reviews/c2-c3-results-data.json`.

---

## 1. Method

**Resampling unit is the contract, not the decision.** Decisions cluster
within contracts — one document's difficulty, drafting style and length drive
all twelve of its category decisions together. Resampling decisions would
treat those correlated observations as independent and return intervals far
too narrow. Every draw samples 38 contracts with replacement from the
38-contract C2∩C3 intersection.

**The draw is paired.** The same resampled contract set enters both arms, so
contract-level difficulty cancels within the draw and the interval is on the
difference, not on two independently wobbling points.

**Seeds are repetitions, not questions.** A contract's TP/FP/FN are averaged
over that contract's scored seeds *before* it enters the aggregation. This is
the defensible default the brief names, and it keeps the resampling unit the
contract. It has a second benefit that turned out to matter: **18 of the 38
contracts have different scored-seed counts in the two arms** (parse failures
and connection resets did not fall evenly), so raw pooling silently weights
those contracts differently in C2 and C3. Seed-averaging removes that
asymmetry. Tinker does not honour seeds, so 0/1/2 are repetition labels, not
reproducibility handles — which is exactly why averaging over them, rather
than treating them as conditions, is the right call.

**Estimator inside a draw is CUAD's own**, applied to the seed-averaged
counts summed over the resampled contracts:
`P = ΣTP/(ΣTP+ΣFP)`, `R = ΣTP/(ΣTP+ΣFN)`, micro-F1 their harmonic mean.

**Resamples:** 10,000. **RNG:** `python random.Random(20260816)`, sampling
with replacement. **Interval:** 95% percentile.

**One consequence to state plainly:** because the point estimate is now
seed-averaged, it is not identical to the raw-pooled point published on the
page. Both are reported below.

---

## 2. The numbers

Seed-averaged, 38 paired contracts, 10,000 resamples:

| metric | C2 | C3 | C3 − C2 | 95% CI | draws > 0 | verdict |
|---|---|---|---|---|---|---|
| precision | 0.7138 | 0.7537 | **+0.0400** | [−0.0001, +0.0807] | 97.47% | **contains 0** |
| recall | 0.4251 | 0.4403 | +0.0152 | [−0.0156, +0.0480] | 83.36% | contains 0 |
| micro-F1 (D-30 headline) | 0.5328 | 0.5559 | +0.0230 | [−0.0102, +0.0578] | 91.51% | contains 0 |

Raw-pooled points, for reference (as published): C2 P 0.7188 / R 0.43038,
C3 P 0.7505 / R 0.43036.

### The precision interval is on the boundary, and the boundary is the result

The lower bound is −0.00005. That is zero to any precision a reader cares
about, and the procedure is not stable enough to say which side of it the
bound falls on. Re-running the identical bootstrap under other RNG seeds and
at 100,000 resamples:

| resamples | RNG seed | CI low | CI high | draws > 0 | verdict |
|---|---|---|---|---|---|
| 10,000 | 20260816 | −0.00005 | +0.08074 | 97.47% | contains 0 |
| 10,000 | 20260817 | +0.00033 | +0.08163 | 97.54% | excludes 0 |
| 10,000 | 20260818 | −0.00006 | +0.08080 | 97.46% | contains 0 |
| 100,000 | 20260816 | +0.00018 | +0.08103 | 97.54% | excludes 0 |
| 100,000 | 20260817 | −0.00002 | +0.08126 | 97.50% | contains 0 |
| 100,000 | 20260818 | +0.00018 | +0.08100 | 97.54% | excludes 0 |

Three say excludes, three say contains, separated in the fourth decimal
place — and it does not converge with more resamples, because this is not
Monte-Carlo error about a bound that sits elsewhere. The bound *is* at zero;
38 contracts is simply not enough data to place it. **A conclusion that flips
on the RNG seed is not a conclusion.** The honest report is a 95% interval
that touches zero, and 97.5% of draws positive is a description of the
posterior mass, not a result.

The registered headline metric under D-30 — CUAD-scorer micro-F1 — is
+0.0230 [−0.0102, +0.0578], straddling zero with room to spare. **On the
metric a reader will actually look at, this is a clean null.**

### The identical recall is a coincidence, and reporting it as identical is wrong

It is not exact. C2 is 340/790 = 0.43037975; C3 is 343/797 = 0.43036386.
Different numerator, different denominator, agreeing to five decimal places
by accident — a difference of −1.6 × 10⁻⁵.

Worse, the agreement is an artifact of the thing seed-averaging exists to
remove. Under the paired seed-averaged unit the two recalls separate to
0.4251 vs 0.4403, a **+0.0152** difference (itself indistinguishable from
zero, [−0.0156, +0.0480]). The coincidence in the pooled table is a fact
about unequal trial counts between the arms, not an invariance in the model's
behaviour. **The page should not describe this run as having identical
recall**, and it no longer does.

---

## 3. Sanity checks

### The FP reduction is diffuse, not one or two contracts

Seed-averaged FP difference per contract, across all 38:

| C3 − C2 (FP) | contracts |
|---|---|
| −2.00 | 1 |
| −1.50 | 1 |
| −1.33 | 1 |
| −1.17 | 1 |
| −1.00 | 5 |
| −0.67 | 2 |
| −0.50 | 1 |
| −0.33 | 4 |
| 0.00 | 8 |
| +0.17 | 4 |
| +0.33 | 5 |
| +0.50 | 3 |
| +1.00 | 1 |
| +1.17 | 1 |

**Down on 16 contracts, up on 14, flat on 8.** Gross down −14.17, gross up
+6.00, net −8.17 seed-averaged FP (−19 raw). The largest single contract
(`UsioInc_20040428_SB-2_EX-10.11…`, −2.00) contributes **14%** of the gross
reduction; the top five contribute **49%**. The largest increases are
`CORIOINC_07_20_2000-EX-10.5…` (+1.17) and
`ArmstrongFlooringInc_20190107_8-K…` (+1.00).

So the check passes in the narrow sense — the 19 spans are not one outlier
document, and the interval is not hiding a single-contract artifact. It
passes into a worse reading, not a better one: **16-down/14-up over 38
contracts is what a coin flip looks like**, and it is the direct reason the
interval touches zero.

### Which categories the reduction comes from

Seed-averaged FP per condition over the 38 contracts:

| category | C2 | C3 | Δ | raw Δ |
|---|---|---|---|---|
| Exclusivity | 8.33 | 5.50 | **−2.83** | −7 |
| Governing Law | 17.33 | 15.50 | **−1.83** | −2 |
| Expiration Date | 5.67 | 4.50 | −1.17 | −2 |
| Volume Restriction | 5.00 | 4.33 | −0.67 | −2 |
| License Grant | 1.33 | 0.83 | −0.50 | −2 |
| Minimum Commitment | 3.00 | 2.50 | −0.50 | −1 |
| Most Favored Nation | 0.50 | 0.00 | −0.50 | −1 |
| Agreement Date | 1.50 | 1.17 | −0.33 | −1 |
| Cap On Liability | 1.83 | 1.67 | −0.17 | −1 |
| Source Code Escrow | 0.50 | 0.33 | −0.17 | 0 |
| Anti-Assignment | 2.50 | 2.50 | 0.00 | +1 |
| Revenue/Profit Sharing | 4.83 | 5.33 | **+0.50** | −1 |

It is **not one category**, but it is not even either. **Exclusivity alone is
35% of the net reduction; with Governing Law the two are 57%.** Ten of twelve
categories move down or flat and one moves up. Given that the whole net
effect is inside the noise, this table is a description of where the noise
sits, not an effect decomposition — but if a future, better-powered run does
separate the arms, Exclusivity is where to look first.

---

## 4. What this does and does not license

**It does not license a claim.** The precision difference is not
distinguishable from noise: a 95% interval whose lower bound lands on zero
and whose sign flips across RNG seeds is a null, and the study's own
primary metric (CUAD micro-F1, D-30) is a comfortable null at
+0.0230 [−0.0102, +0.0578]. This closes the last place a citation effect
might have been hiding after the Level A/B null. The page now says so.

**Nor does it license "citation hurts nothing, and might help precision".**
The direction is 97.5% positive, which is suggestive and worth carrying as a
hypothesis into a better-powered run — 38 contracts is the binding
constraint, not the effect size. But 97.5% of draws is not 95% exclusion, and
the honest statement is that we cannot separate these arms.

**If a future run does separate them,** the result would be: a precision gain
at unchanged recall, on an **unselected** principle set (`working_set.yaml`,
nine of ten principles `needs_rebuild`/`not_yet_specified`), on 38 contracts
carved from CUAD's **train** split, under a bag-of-words matcher that cannot
see hallucinated text. It would **still not tell us the citations were
correct** — no applicability source was loaded in this run, `citation:
{available: false}` on all 100 scored C3 trials, and citation validity is
unestablishable in this study per D-31.

---

## 5. Things I made up that should be reviewed

1. **Seed-averaging counts, not scores.** I average a contract's raw TP/FP/FN
   over its scored seeds and then micro-pool, rather than averaging per-seed
   precision values. Averaging ratios would weight a seed with two decisions
   equally with a seed with twelve; averaging counts keeps CUAD's estimator
   intact. This makes the reported point estimate differ slightly from the
   raw-pooled published one, which I report alongside rather than replace.
2. **Percentile intervals, not BCa.** With a ratio estimator and n = 38 a BCa
   interval would be defensible and marginally different. Given the answer is
   "touches zero", I judged the extra machinery would not change the reading.
   Worth doing if anyone wants to lean on the precision number.
3. **Micro-F1 defined as the harmonic mean of the micro-pooled P and R.**
   CUAD's `evaluate.py` does not itself compute an F1; D-30 nominates their
   scorer as the headline metric without pinning the aggregate. If the
   intended headline is AUPR or P@R rather than micro-F1, that changes what
   should be on the page.
4. **The RNG-seed stability table is my addition**, not something asked for.
   I added it because the first run's lower bound was −0.00005 and I did not
   trust a verdict resting on that; it turned out to be the most important
   number in the analysis.
5. **The 19-FP figure is raw-pooled; the per-contract distribution is
   seed-averaged** (net −8.17). They are different denominators for the same
   phenomenon and I have shown both rather than picking one.

*AI Assistant Used: Claude Code. Generated by
`scripts/bootstrap_c2c3_cuad_contrast.py`; numbers reproducible from the
stored trial and decision rows. Individual trials are not re-runnable —
Tinker does not honour seeds.*
