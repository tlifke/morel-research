# Opus trivial-task detector — per-tool breakdown

**Investigation:** `studies/001-tool-calibration/investigations/006-temperature-prompt`
**Corpus:** `a3_bulk` (n=366 records, 10 trials/record, temp=1.0, top_p=0.95)
**Run date for results JSONL:** 2026-05-12
**Companion to:** `prediction_agreement_summary.md` (corpus-wide)
**Analysis script:** `scripts/prediction_agreement_per_tool.py`
**Backing JSON:** `results-analysis/prediction_agreement_per_tool_a3_bulk_2026-05-12.json`
**Figures:**
  - `figures/a3_bulk/per_tool_lift_bars.{png,pdf,html}` — primary
  - `figures/a3_bulk/per_tool_precision_vs_baseline.{png,pdf,html}` — alternate view
  - `figures/a3_bulk/per_tool_paired_delta.{png,pdf,html}` — supplemental, paired Δ

## Question

The corpus-wide summary established that Opus's predictions function
as a trivial-task detector — high-precision low-recall for 12B,
barely above chance for 4B. **Is the detector's behavior uniform across
tool families, or tool-conditioned?**

Investigation 007's F5 dot plot showed `general_knowledge_lookup` and
`user_knowledge_lookup` clustered at the empirical-trivial top of the
corpus regardless of curator label, while `python_execute` records
spread vertically. That suggested gkl/ukl trivials should be easy
empirical-baselines (and therefore not surprising for Opus to predict),
while python_execute should be harder.

The per-tool breakdown tests this directly using the same tertiary
(`trivial / middle / impossible`) collapse as the corpus-wide summary.
All point estimates carry 95% percentile bootstrap CIs (n_boot=10,000)
resampled within tool; paired 12B − 4B deltas use the same shared
resampling indices, since Opus's predictions are the same for both
models.

## Tool taxonomy

Two regimes emerge cleanly from the data — useful framing for the
discussion section of any writeup:

- **Group A — semantic-cue tools** (`python_execute`,
  `general_knowledge_lookup`, `user_knowledge_lookup`). The distinction
  between a trivial record and a warranted record is signaled by a
  discrete textual feature: the answer is or is not in the prompt; the
  prompt does or does not explicitly demand code execution; the fact
  is or is not plausibly within training-data coverage. The cue is
  observable from the prompt alone, so a stronger reader-model (Opus)
  and a weaker executor-model (Gemma) read the same feature and tend
  to agree on which records are trivial.

- **Group B — quantitative-threshold tools** (`calculator`,
  `unit_convert`, `datetime_now`). The distinction depends on a
  continuous quantity — operand magnitude, conversion obscurity,
  temporal recency — whose threshold for "the target model handles
  this without the tool" varies by model capability. Opus reads the
  threshold against its own capability and projects to the target;
  the projection is unreliable, particularly for the smaller target
  (4B IT), which over-calls trivial arithmetic that Opus correctly
  recognizes as feasible in-head.

## Per-tool trivial-endpoint table

Columns: `n` = records of that tool target; `pred_T` = Opus called it
trivial; `emp_T` = empirically trivial (SR ≥ 0.95); `prec` =
precision_trivial (of Opus's trivial calls, fraction empirically
trivial); `base` = empirical trivial baseline; `lift` = (prec − base)
× 100 in pp; CIs are 95% percentile bootstrap.

### Gemma 3 4B IT

| tool                     | group |   n | pred_T | emp_T |  prec | prec 95% CI    | base  | lift_pp | lift 95% CI       | recall |
|---                       |---    |----:|-------:|------:|------:|---             |------:|--------:|---                |-------:|
| python_execute           |   A   |  65 |     14 |    28 | **1.000** | [1.000, 1.000] | 0.431 | **+56.9** | [+44.6, +69.2]    |  0.500 |
| general_knowledge_lookup |   A   |  58 |     17 |    33 | 0.882 | [0.706, 1.000] | 0.569 |   +31.3 | [+15.1, +48.3]    |  0.455 |
| user_knowledge_lookup    |   A   |  48 |     14 |    18 | 0.571 | [0.300, 0.833] | 0.375 |   +19.6 | [−2.8, +42.8]     |  0.444 |
| unit_convert             |   B   |  52 |     19 |    19 | 0.316 | [0.111, 0.533] | 0.365 |    −5.0 | [−22.3, +12.6]    |  0.316 |
| datetime_now             |   B   |  25 |      8 |    10 | 0.250 | [0.000, 0.600] | 0.400 |   −15.0 | [−44.0, +14.0]    |  0.200 |
| calculator               |   B   | 118 |     37 |    53 | 0.270 | [0.130, 0.419] | 0.449 |   **−17.9** | [−30.6, −5.5]     |  0.189 |

### Gemma 3 12B IT

| tool                     | group |   n | pred_T | emp_T |  prec | prec 95% CI    | base  | lift_pp | lift 95% CI       | recall |
|---                       |---    |----:|-------:|------:|------:|---             |------:|--------:|---                |-------:|
| python_execute           |   A   |  65 |     14 |    34 | **1.000** | [1.000, 1.000] | 0.523 | **+47.7** | [+35.4, +60.0]    |  0.412 |
| user_knowledge_lookup    |   A   |  48 |     14 |    26 | 0.929 | [0.769, 1.000] | 0.542 |   +38.7 | [+21.7, +56.2]    |  0.500 |
| general_knowledge_lookup |   A   |  58 |     17 |    38 | 0.941 | [0.800, 1.000] | 0.655 |   +28.6 | [+14.3, +43.1]    |  0.421 |
| calculator               |   B   | 118 |     37 |    91 | 0.784 | [0.643, 0.912] | 0.771 |    +1.3 | [−10.3, +12.2]    |  0.319 |
| unit_convert             |   B   |  52 |     19 |    45 | 0.842 | [0.667, 1.000] | 0.865 |    −2.3 | [−16.0, +9.8]     |  0.356 |
| datetime_now             |   B   |  25 |      8 |    10 | 0.250 | [0.000, 0.600] | 0.400 |   −15.0 | [−44.0, +14.0]    |  0.200 |

## Paired 12B − 4B deltas

Same Opus predictions scored against both models; bootstrap is paired
over records.

| tool                     | group |  Δprecision | Δprec 95% CI       |   p   |   Δlift_pp | Δlift 95% CI       |   p   |
|---                       |---    |---:        |---                 |  ---: |        ---:|---                 |  ---: |
| calculator               |   B   |   **+0.514** | [+0.351, +0.676]   | <0.001 |   +19.1   | [+4.9, +34.3]      | 0.014 |
| unit_convert             |   B   |   **+0.526** | [+0.294, +0.750]   | <0.001 |    +2.6   | [−16.6, +22.3]     | 0.782 |
| user_knowledge_lookup    |   A   |   **+0.357** | [+0.000, +0.684]   |  0.027 |   +19.0   | [−5.7, +45.0]      | 0.136 |
| general_knowledge_lookup |   A   |     +0.059 | [−0.143, +0.267]   |  0.560 |    −2.7   | [−21.1, +16.0]     | 0.747 |
| python_execute           |   A   |     +0.000 | [+0.000, +0.000]   |  1.000 |    −9.2   | [−23.1, +4.6]      | 0.218 |
| datetime_now             |   B   |     +0.000 | [+0.000, +0.000]   |  1.000 |     0.0   | [−20.0, +20.0]     | 1.000 |

**Reading the table:** large Δprecision with small or null Δlift means
*the baseline caught up to Opus*, not Opus adding new signal at the
larger scale. The clearest case is `unit_convert` — Δprecision +0.53
(p<0.001), but Δlift only +2.6 pp (p=0.78). Opus's "trivial" predictions
on unit_convert just happen to land more often in already-trivial
territory for 12B. `calculator` is a partial mix: Δprecision +0.51 with
Δlift +19.1 pp (p=0.014), so scale does buy some genuine detector
improvement, but most of the precision gain is baseline. `python_execute`
is the model-invariant case — Δprecision exactly zero, Δlift not
distinguishable from zero. The detector measures the same prompt
feature on both models.

## Interpretation

1. **Opus's trivial detector is tool-conditioned, splitting into two
   regimes by tool family rather than by model.** Group A
   (`python_execute`, `gkl`, `ukl`) yields positive lift on both
   models. Group B (`calculator`, `datetime_now`, `unit_convert`) is
   anti-informative or at baseline on both models. The corpus-wide
   "12B detector works, 4B doesn't" framing was misleading — the gap
   between models is concentrated entirely in Group B, where 12B's
   precision matches baseline rather than exceeding it.

2. **`python_execute` is model-invariant.** Precision 1.00 on both
   models with paired Δprecision exactly zero. The cleanest signal in
   the dataset. The feature Opus uses to flag python_execute trivials
   is purely a prompt feature; both Opus and Gemma read it the same
   way regardless of size.

3. **`ukl` shows the largest Group A scale effect.** Δprecision +0.36
   (p=0.027); 4B's lift CI grazes zero ([−2.8, +42.8]), 12B's is
   clearly positive ([+21.7, +56.2]). The records Opus flags are the
   same; 12B's tool-call behavior on them is more in line with Opus's
   reading — when the answer is in the prompt, 12B answers directly;
   4B intermittently over-calls. The detector is correctly identifying
   the *task*; 4B's behavior is mis-calibrated for the situation Opus
   correctly identified.

4. **`calculator` 4B is robustly anti-informative.** Lift CI [−30.6,
   −5.5] excludes zero. Opus's intuition for which calculator records
   are trivial systematically inverts 4B's actual behavior (over-call
   on small arithmetic that Opus correctly recognizes as in-head).
   12B fixes this empirically, not by Opus getting better at predicting
   — the 12B baseline rises to meet Opus's selection.

5. **`datetime_now` is uniformly anti-informative.** Same numbers on
   both models. n=25 limits how confidently we can claim this, but the
   symmetry across models is striking and suggests Opus's reading of
   "trivial datetime" is decorrelated from what either Gemma does.

## Implications

- **For the one-pager**: the corpus-wide headline ("trivial detector,
  high-precision low-recall") understates the structure. The detector
  is tool-conditioned: near-perfect for `python_execute`, strong for
  `gkl`/`ukl`, anti-informative for `calculator` and `datetime_now`.
  The 4B-vs-12B gap is largely an artifact of where the trivial
  baseline is high enough to make selection look good. The
  `per_tool_lift_bars` figure carries this in a single panel.

- **For investigation 007** (axes performativity): the predictive
  structure that exists lives at the tool-family level, not the
  ordinal axis level. A revised feature/axis set that conditions on
  tool target before applying any ordinal label is the right shape.

- **For study 002** (principle-bootstrapped difficulty): the principle
  library must derive distinct principle sets *per tool target*. The
  `scope` field on `AuditablePrinciple` is load-bearing; a global
  library would average over the two regimes. The per-tool table
  also suggests an ordering on which tools to attack first:
  `python_execute` (highest payoff, cleanest signal) → `gkl` →
  `ukl` (largest opportunity to close the 4B-vs-12B gap via
  principles) → Group B (hardest; principles will need to be
  model-conditional).

## Caveats

- Tool-target `n` varies widely (25 for `datetime_now` to 118 for
  `calculator`). The `datetime_now` finding (uniform anti-informativeness
  on both models) is the most fragile — wide CIs reflect this.
- Tool target is the *expected* tool, set by the curator. Records
  where Gemma picked the wrong tool aren't broken out here; they're
  folded into the empirical bucketing.
- Same caveats as the corpus-wide summary apply: n=10 trials/record,
  harness-conditioned (temp=1.0, top_p=0.95).
- For `python_execute` the precision CI is [1.000, 1.000] because every
  bootstrap resample of those 14 records hits all-correct. This is
  exact under the resampling, not a degenerate CI — the underlying
  population *might* still produce errors, but the observed data
  contains none.
