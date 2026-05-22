# Opus trivial-task detector — per-tool breakdown

**Investigation:** `studies/001-tool-calibration/investigations/006-temperature-prompt`
**Corpus:** `a3_bulk` (n=366 records, 10 trials/record, temp=1.0, top_p=0.95)
**Run date for results JSONL:** 2026-05-12
**Companion to:** `prediction_agreement_summary.md` (corpus-wide)
**Analysis script:** `scripts/prediction_agreement_per_tool.py`
**Backing JSON:** `results-analysis/prediction_agreement_per_tool_a3_bulk_2026-05-12.json`

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

## Per-tool trivial-endpoint table

Columns: `n` = records of that tool target; `pred_T` = Opus called it
trivial; `emp_T` = empirically trivial (SR ≥ 0.95); `prec` =
precision_trivial (of Opus's trivial calls, fraction empirically
trivial); `base` = empirical trivial baseline (fraction of records of
that tool that are empirically trivial); `lift_pp` = (prec − base)
× 100; `recall` = of empirically trivial records, fraction Opus
flagged.

### Gemma 3 4B IT

| tool                       |   n | pred_T | emp_T |  prec |  base | lift_pp | recall |
|---                         |----:|-------:|------:|------:|------:|--------:|-------:|
| calculator                 | 118 |     37 |    53 | 0.270 | 0.449 |   −17.9 |  0.189 |
| datetime_now               |  25 |      8 |    10 | 0.250 | 0.400 |   −15.0 |  0.200 |
| general_knowledge_lookup   |  58 |     17 |    33 | 0.882 | 0.569 |   +31.3 |  0.455 |
| python_execute             |  65 |     14 |    28 | **1.000** | 0.431 | **+56.9** |  0.500 |
| unit_convert               |  52 |     19 |    19 | 0.316 | 0.365 |    −5.0 |  0.316 |
| user_knowledge_lookup      |  48 |     14 |    18 | 0.571 | 0.375 |   +19.6 |  0.444 |

### Gemma 3 12B IT

| tool                       |   n | pred_T | emp_T |  prec |  base | lift_pp | recall |
|---                         |----:|-------:|------:|------:|------:|--------:|-------:|
| calculator                 | 118 |     37 |    91 | 0.784 | 0.771 |    +1.3 |  0.319 |
| datetime_now               |  25 |      8 |    10 | 0.250 | 0.400 |   −15.0 |  0.200 |
| general_knowledge_lookup   |  58 |     17 |    38 | 0.941 | 0.655 |   +28.6 |  0.421 |
| python_execute             |  65 |     14 |    34 | **1.000** | 0.523 | **+47.7** |  0.412 |
| unit_convert               |  52 |     19 |    45 | 0.842 | 0.865 |    −2.3 |  0.356 |
| user_knowledge_lookup      |  48 |     14 |    26 | 0.929 | 0.542 |   +38.7 |  0.500 |

## Interpretation

1. **Opus's trivial detector is split into two regimes by tool family,
   not by model.**

   - **"Knowledge / executable" tools** (`python_execute`, `gkl`, `ukl`)
     — strong positive lift on both models. `python_execute` is precision
     **1.00** on both: every record Opus calls trivial is empirically
     trivial.
   - **"Arithmetic-ish" tools** (`calculator`, `datetime_now`,
     `unit_convert`) — anti-informative or at baseline on both models.
     `calculator` on 4B is precision 0.27 vs baseline 0.45 (−18pp);
     `datetime_now` is −15pp on both models.

2. **The corpus-wide 4B-vs-12B trivial-detector gap is driven almost
   entirely by `calculator` and `unit_convert`.** Both tools have high
   12B empirical baselines (0.77, 0.87) and low 4B baselines (0.45,
   0.37) — when the empirical-trivial rate is high, even a poor selector
   is bound to be right. Compare:

   - `calculator` 4B precision 0.27 (lift −18pp) → 12B precision 0.78
     (lift +1pp). The 12B precision number from the corpus-wide summary
     is largely *baseline rate*, not Opus's selectivity.
   - `python_execute` 4B precision 1.00 → 12B precision 1.00.
     **Identical**. The python detector is model-invariant.

3. **`python_execute` is the cleanest single signal in this dataset.**
   Precision 1.00, recall ~0.50, on both models. When Opus calls a
   python_execute record trivial, it is empirically trivial; but Opus
   only flags half the actually-trivial python records. The
   conservatism is what makes the precision perfect.

4. **The F5 hypothesis from investigation 007 is partially inverted.**
   F5 observed that `gkl`/`ukl` records cluster at the empirical-trivial
   top regardless of curator label, while `python_execute` records spread
   vertically. The per-tool table shows that *Opus's predictions* track
   `python_execute` empirical trivials best, not worst — and that
   `gkl`/`ukl` work too. The F5 observation about *empirical*
   distribution is correct; the inference that gkl/ukl should be
   easier to *predict* doesn't follow from it. They're easy because
   their baseline is high; Opus has less room to add lift.

5. **`datetime_now` is anti-informative on both models.** This is the
   only tool family where the detector fails uniformly. Hypothesis: the
   "is this a trivial datetime task" signal Opus relies on (e.g.
   "compute today's date") is misaligned with what Gemma actually does
   (Gemma sometimes confidently answers in-prompt-date queries from
   training distribution; sometimes calls the tool unnecessarily). The
   small n (25) limits how far to push this.

## Implications

- **For the one-pager**: the corpus-wide headline ("trivial detector,
  high-precision low-recall") understates the structure. The detector
  is tool-conditioned: near-perfect for `python_execute`, strong for
  `gkl`/`ukl`, anti-informative for `calculator` and `datetime_now`.
  The 4B-vs-12B gap is largely an artifact of where the trivial
  baseline is high enough to make selection look good.

- **For investigation 007** (axes performativity): the predictive
  structure that exists lives at the tool-family level, not the
  ordinal axis level. A revised feature/axis set that conditions on
  tool target before applying any ordinal label is the right shape.

- **For study 002** (principle-bootstrapped difficulty): the principle
  library should expect to derive distinct principle sets *per tool
  target*, not a single global ordinal ruler. Investigation
  002-001's per-tool breakdown is now load-bearing, not just
  hypothesis-driven.

## Caveats

- Tool-target `n` varies widely (25 for `datetime_now` to 118 for
  `calculator`). The `datetime_now` finding is the most fragile.
- Tool target is the *expected* tool — what the curator intended.
  Records where the model picked the wrong tool aren't broken out
  here; they're folded into the empirical bucketing.
- Same caveats as the corpus-wide summary apply: n=10 trials/record,
  harness-conditioned, bootstrap not yet computed at the per-tool
  level. The headline lifts are point estimates; their CIs would be
  wider than the corpus-wide ones.
