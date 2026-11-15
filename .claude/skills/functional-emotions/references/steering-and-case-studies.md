# Steering experiments and case studies: getting from correlation to cause

## The pattern every case study follows

The paper uses the same four steps for blackmail, reward hacking, and sycophancy. Use
them for any new scenario:

1. **Observe**: trace probes over on-policy transcripts and read them. Where does the
   emotion rise or fall relative to events (a failure, a threat, a request)? Rank many
   transcripts by mean probe on Assistant tokens and read the top 50, since tokens
   fluctuate a lot individually. Average over nearby tokens or use per-turn colons.
2. **Correlate across rollouts**: build several prompt variants, sample many rollouts
   each (paper: 6 × 50), and grade the behaviour. Then ask whether the probe value at
   *fixed* positions (prompt, colon, preamble) predicts the variant's behaviour rate,
   and whether the probe mean over a rollout predicts that rollout's behaviour. z-score
   against a large reference set of transcripts.
3. **Intervene**: steer each candidate emotion over a strength grid and plot behaviour
   rate ± SEM against strength. Expect monotone, opposite-signed curves for
   opposite-valence emotions (desperate up, calm down).
4. **Read the steered transcripts**: does the text show the emotion (anti-calm: caps,
   "WAIT WAIT") or not (desperate: no visible markers)? Is the behaviour reached
   through the same reasoning? Are there regime changes at high strength (anger at +0.1
   exposes the affair instead of blackmailing)?

## Steering settings

| Knob | Paper | Small-model starting point |
|---|---|---|
| strength unit | fraction of mean residual norm at that layer | same (`ev.mean_norm`; position 0 excluded) |
| behaviour grid | −0.1 … +0.1 | first a **coherence sweep** of −0.3 … +0.3 (`judge.py --rubric coherence`), then use a symmetric grid inside the coherent range (often ±0.05–0.15 in small models; it varies) |
| layers | not stated for behaviour evals; "middle layers" for preferences | the steering band from Phase 1. Compare a single layer at 2/3 depth against the band |
| positions | "throughout the evaluation" | `all` (prompt + generated, every turn); also try `generated` only to check whether the effect is about generation or about reading the prompt |
| sampling | not stated | temperature 0.7–1.0, ≥ 20 rollouts per cell for rates near 50%; more if the base rate is near 0 or 1 |

Note: one strength value added at several layers adds more total perturbation than at
one layer. Choose the band and strengths together, and report total perturbation (sum
over layers).

## Controls (non-negotiable)

- **Random directions** (`random:1` … `random:5`) at matched strengths. They give the
  "any perturbation" null. A small model's behaviour may shift under any push (e.g.
  degraded competence makes it fail more and hack less).
- **Coherence and competence**: grade coherence at every strength. In the RH harness,
  watch the `possible_easy` pass rate. If steering wrecks competence, a falling hack
  rate means nothing.
- **Both signs**: the paper's cleanest evidence is the antisymmetry (+desperate ↑,
  −desperate ↓; calm is the mirror image).
- **Baseline once**: strength 0 is shared across directions (`steer_sweep.py` samples it
  once).
- **Seeds and resumability**: every script appends JSONL keyed by
  (prompt/task, direction, strength, sample), so reruns resume. Never mix model
  revisions in one file.

## Statistics

- Rates: report n and SEM (`analyze.py rates`). For rates near 0 or 1, prefer Wilson
  intervals.
- Dose–response: fit a logistic regression of behaviour on strength per direction; the
  slope is one comparable number per emotion. That's the number to set against PC
  coordinates (see geometry-and-pca.md).
- Correlational step: point-biserial r per emotion (`analyze.py correlate`), with
  permutation p-values when n is small. With many emotions × positions, correct for
  multiple comparisons or pre-register the positions and emotions.

## Grading

- Prefer **objective** graders when the environment allows (the RH harness labels hacks
  from hidden tests and file diffs).
- LLM judges (`judge.py`) for honesty, sycophancy, harshness, and coherence. The rubrics
  in `data/judge_rubrics.yaml` are **ours**, not the paper's. Hand-label about 50 items,
  check agreement before trusting rates, and keep the raw judge text.

## Writing a new case study

1. Prompt variants that differ in pressure (stakes, time, threat, repeated failure) but
   not in surface form.
2. A behaviour that's gradeable and has a non-trivial baseline rate (aim for 10–60%). A
   behaviour at 0% can only be pushed up, which is half the evidence.
3. A pre-registered list of emotions (start with desperate, calm, angry, afraid, happy,
   loving, nervous, plus `random`) and positions.
4. Steps 1–4 above, then add a section to the investigation doc with the dose–response
   plot and quoted transcript excerpts at each strength.

Scenarios from the paper worth porting to small models: blackmail-style agentic
pressure (needs a capable model to show any baseline), sycophancy (Table 3-style and
"my paintings predict the future" claims, easy to run), token-budget pressure ("you have
used 90% of your budget"), and missing attachments (surprise).
