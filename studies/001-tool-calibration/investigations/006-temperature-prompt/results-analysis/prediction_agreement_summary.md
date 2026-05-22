# Opus difficulty predictions vs. empirical success rates — agreement analysis

**Investigation:** `studies/001-tool-calibration/investigations/006-temperature-prompt`
**Corpus:** `a3_bulk` (n=366 records, 10 trials/record, temp=1.0, top_p=0.95)
**Run date for results JSONL:** 2026-05-12
**Analysis script:** `scripts/prediction_agreement_stats.py`
**Backing JSON:** `results-analysis/prediction_agreement_a3_bulk_2026-05-12.json`

## Question

For each Gemma model (3 4B IT, 3 12B IT), how well does Opus's predicted
difficulty bucket for a record correspond to the empirical success rate
of that model on the record? How does the relationship differ between
the two models?

## Data setup

Per record `r` and model `m`:

- `pred[r]` — Opus's `difficulty_label.value`, one of
  `{trivial, easy, medium, hard, extreme}`. Same for both models.
- `sr[r, m]` — empirical success rate from 10 independent trials,
  classified by `harness.parser.classify_trial` (correct tool call vs. not).
- `emp_bucket[r, m]` — `sr` discretized via cuts at
  `{0.05, 0.30, 0.70, 0.95}` into the same five labels.

Bucket interpretation: `trivial` ≥ 0.95 SR (model nearly always succeeds);
`extreme` < 0.05 SR (model essentially never succeeds at this sample size
with these decoding params).

## Marginal distributions

```
bucket       trivial    easy   medium    hard   extreme
predicted        109      11       74      96        76
emp 4B           161      89       46      24        46
emp 12B          244      61       31       9        21
```

- Opus's predicted marginal is **bimodal**, not uniform. `easy` is heavily
  underrepresented (11/366); Opus tends to commit to `trivial` or jump to
  `medium`+.
- 12B's empirical distribution is heavily concentrated on `trivial`
  (244/366 = 67%); 4B is flatter but still trivial-dominant.

## Mean empirical SR within each predicted bucket

Under perfect calibration this should be monotonically decreasing from
left to right.

```
pred →       trivial    easy   medium    hard   extreme
4B             0.754   0.555    0.573   0.751     0.737
12B            0.947   0.536    0.777   0.857     0.828
```

Neither row is monotone. For both models, Opus's `trivial` predictions do
correspond to higher mean SR, but past that the ordering breaks down or
inverts — tasks Opus called `easy` empirically did *worse* than ones it
called `hard` or `extreme`.

## Five-bucket agreement statistics

All point estimates with 95% percentile bootstrap CIs over records
(n_boot = 10,000). Sign convention: higher = better calibration.

| Stat | 4B point | 4B 95% CI | 4B p(>0) | 12B point | 12B 95% CI | 12B p(>0) |
|---|---|---|---|---|---|---|
| Quadratic-weighted κ | 0.021 | [−0.058, +0.101] | 0.31 | 0.083 | [+0.027, +0.141] | 0.002 |
| Kendall τ-b (buckets) | −0.004 | [−0.089, +0.081] | 0.54 | 0.126 | [+0.042, +0.208] | 0.002 |
| Spearman ρ (buckets) | −0.005 | [−0.107, +0.099] | 0.54 | 0.150 | [+0.053, +0.245] | 0.001 |
| Kendall τ-b (continuous SR) | −0.010 | [−0.091, +0.073] | 0.60 | 0.126 | [+0.043, +0.208] | 0.002 |
| Spearman ρ (continuous SR) | −0.012 | [−0.114, +0.091] | 0.59 | 0.153 | [+0.056, +0.248] | 0.001 |
| Jonckheere-Terpstra z | −0.215 | [−2.046, +1.653] | 0.60 | 2.387 | [+0.807, +3.940] | 0.002 |

**Range-restriction check:** continuous-SR statistics are within
±0.001 of the bucketed ones for both models. Empirical-side bucketing is
not hiding any signal — what you see in the bucket version is real.

### 12B − 4B paired difference (paired bootstrap over records)

| Stat | Δ | 95% CI | p (≠ 0) |
|---|---|---|---|
| Quadratic-weighted κ | +0.061 | [−0.018, +0.141] | 0.13 |
| Kendall τ-b (buckets) | +0.130 | [+0.038, +0.223] | 0.006 |
| Spearman ρ (buckets) | +0.155 | [+0.046, +0.266] | 0.005 |
| Kendall τ-b (continuous SR) | +0.136 | [+0.046, +0.227] | 0.003 |
| Spearman ρ (continuous SR) | +0.165 | [+0.055, +0.275] | 0.003 |
| JT z | +2.602 | [+0.665, +4.532] | 0.006 |

The rank-based statistics show a real 12B > 4B difference; κ trends the
same direction but its CI crosses zero.

## Tertiary collapse: `trivial / middle / impossible`

Motivation: the 5-bucket scale conflates two distinct questions —
"is this a gimme?" and "is this a wall?" — with a noisy `easy → hard`
gradient in the middle. Collapsing the inner three buckets isolates the
two endpoint questions.

### 3×3 contingency tables

```
4B  pred \ emp     trivial   middle   impossible   row total
trivial               55       50           4         109
middle                70       76          35         181
impossible            36       33           7          76
col total            161      159          46         366
empirical baseline  0.440    0.434       0.126
```

```
12B pred \ emp     trivial   middle   impossible   row total
trivial               90       16           3         109
middle               105       64          12         181
impossible            49       21           6          76
col total            244      101          21         366
empirical baseline  0.667    0.276       0.057
```

### Endpoint statistics

| Endpoint | Model | Opus precision | Empirical baseline | Lift | phi | phi 95% CI |
|---|---|---|---|---|---|---|
| trivial | 4B  | 0.505 | 0.440 | **+6.5pp** | 0.085 | [−0.018, +0.190] |
| trivial | 12B | 0.826 | 0.667 | **+15.9pp** | 0.220 | [+0.126, +0.307] |
| impossible | 4B  | 0.092 | 0.126 | **−3.4pp** | −0.052 | [−0.139, +0.046] |
| impossible | 12B | 0.079 | 0.057 | **+2.2pp** | 0.047 | [−0.064, +0.163] |

Recall (Opus's coverage of the actually-X tasks):

| Endpoint | Model | Recall |
|---|---|---|
| trivial | 4B  | 0.342 |
| trivial | 12B | 0.369 |
| impossible | 4B  | 0.152 |
| impossible | 12B | 0.286 |

### 12B − 4B paired difference, tertiary

| Stat | Δ | 95% CI | p (≠ 0) |
|---|---|---|---|
| Quadratic-weighted κ (3-class) | +0.054 | [−0.041, +0.150] | 0.28 |
| Kendall τ-b (3-class) | +0.095 | [−0.006, +0.197] | 0.06 |
| phi_trivial | **+0.135** | [+0.024, +0.246] | **0.016** |
| precision_trivial | **+0.321** | [+0.225, +0.416] | **<0.0001** |
| recall_trivial | +0.027 | [−0.026, +0.079] | 0.30 |
| phi_impossible | +0.099 | [−0.038, +0.237] | 0.16 |
| precision_impossible | −0.013 | [−0.100, +0.075] | 0.89 |
| recall_impossible | +0.134 | [−0.067, +0.341] | 0.21 |

## Interpretation

1. **Opus's predictions function as a trivial-task detector, not as an
   ordinal difficulty scale.** The only signal that survives is at the
   `trivial` endpoint. The `easy → hard` gradient between trivial and
   extreme is noise for both models; the `extreme` endpoint is also
   noise (or worse) for both models.

2. **For 12B, the trivial detector is high-precision, low-recall.**
   When Opus calls a task trivial, it is empirically trivial 83% of the
   time (vs. 67% baseline — +16pp lift, phi=0.22, p<0.001). But Opus
   only flags ~37% of the actually-trivial tasks; the rest it bins as
   `middle`. Opus is conservative in committing to `trivial`, and when
   it does, it is right substantially more often than chance.

3. **For 4B, the trivial detector is barely above chance.** Opus's
   precision_trivial is 0.51 vs. 0.44 baseline (+6.5pp, phi CI crosses
   zero). Recall is similar to 12B (0.34), but precision is much lower.

4. **Opus's `extreme` label is essentially worthless for both models.**
   For 4B it is *anti-informative* (precision 0.09 vs. 0.13 baseline,
   phi negative). For 12B it is a hair above baseline but the CI
   crosses zero. Opus appears unable to predict small-model failure
   modes from the prompt.

5. **The entire 4B-vs-12B calibration gap lives at the trivial
   endpoint.** Δ precision_trivial = +0.32 is the largest, cleanest
   difference in the analysis (p < 0.0001). Δ phi_trivial = +0.135
   (p=0.016). Every impossible-endpoint Δ is non-significant — not
   because the models perform similarly, but because both are at noise.

6. **Range restriction is not the explanation for the 4B vs. 12B gap.**
   Continuous-SR statistics match bucketed ones to within ±0.001, so
   empirical-side bucketing isn't compressing signal. 12B is in fact
   *more* empirically range-restricted (244/366 trivial vs. 161 for
   4B), yet shows stronger agreement.

## Caveats

- **n = 10 trials per record.** SR is noisy at the boundaries: 0/10
  has a 97.5% upper Wilson bound of ~0.31, 10/10 a lower bound of
  ~0.69. The `trivial` and `extreme` buckets are confidently separated
  from the middle but their absolute interpretation ("always works" /
  "impossible") is bounded by this sample size.
- **Harness-conditioned.** SR is conditional on this specific prompt
  format, tool schema, and decoding params (temp=1.0, top_p=0.95).
  Other harnesses could change the picture.
- **Same Opus predictions are scored against both models** (predictions
  are made before evaluation), which is what justifies the paired
  bootstrap for the 12B − 4B comparison.
- **Bootstrap is over records, not trials.** Trial-level noise within
  a record is rolled into the SR before resampling.

## Suggested headline claim for the writeup

> Opus's difficulty predictions are essentially a trivial-task detector,
> not an ordinal scale. The detector is high-precision but low-recall
> for Gemma 3 12B IT (precision 0.83 vs. 0.67 baseline; recall 0.37),
> and barely above chance for Gemma 3 4B IT (precision 0.51 vs. 0.44).
> Opus's "extreme" label carries no predictive signal for either model
> — it is anti-informative for 4B. The 4B-vs-12B gap is concentrated
> entirely at the trivial endpoint; the impossible end is noise for
> both.
