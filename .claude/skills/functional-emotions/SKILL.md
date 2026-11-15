---
name: functional-emotions
description: Replicate and extend Anthropic's "Emotion Concepts and their Function in a Large Language Model" (2026) on open-weight models. Covers extracting emotion vectors (171 emotions, synthetic stories, neutral-PC denoising), validating them outside training (logit lens, max-activating examples, implicit scenarios, intensity sweeps, causal word tests, preference Elo), PCA/valence-arousal geometry, the key "Assistant colon" token positions, activation steering, case studies (blackmail-style pressure, sycophancy), and especially the reward-hacking case study (desperate/calm vs. impossible coding tasks) plus mitigation experiments that cut hacking while preserving task completion. Use whenever someone wants to find emotion vectors / functional emotions / emotion probes in a model, steer a model with emotion vectors, do emotion-space PCA, probe at the Assistant colon, run the impossible-code or reward-hacking-with-desperation experiments, test whether small language models have functional emotions that drive misalignment, or study emotional drivers of reward hacking — even if the paper isn't named.
---

# functional-emotions

A replication kit for the paper's methods on open-weight HF models. You (the agent)
run on a machine with a GPU; the human researcher drives the questions. Repo
conventions in `CLAUDE.md` apply: in particular **seeds before bulk generation**,
**no one-pager prose**, **propose (don't set) capability-map statuses**, and **list
assumptions you made**.

The paper studied one frontier model (Claude Sonnet 4.5). Whether any of this holds in
1–10B models is the open question. Treat every paper number as a *prediction to test*,
not an expectation to meet, and report failures as results.

## Read first

| File | When |
|---|---|
| `references/paper-methods.md` | always: what the paper actually did, with numbers; what it left unstated |
| `references/extraction-and-validation.md` | Phase 1: build and validate vectors for a new model |
| `references/key-tokens.md` | choosing token positions and layers, mapping "Assistant:" onto chat templates |
| `references/geometry-and-pca.md` | PCA / valence–arousal, and how to use PCs when comparing steering across emotions |
| `references/steering-and-case-studies.md` | any steering or behavioural case study: settings, controls, stats |
| `references/reward-hacking.md` | the reward-hacking line: harness, replication plan, dissection, mitigations |

## Setup

```bash
pip install torch transformers numpy pyyaml pytest anthropic   # GPU box
python .claude/skills/functional-emotions/scripts/selftest.py  # ~1 min, CPU ok; must print ALL PASS
```

`selftest.py` builds a tiny random model offline and checks key-position finding,
steering (exact positions and magnitude, hook cleanup, KV-cache offsets),
orthogonalization, and every label branch of the reward-hacking grader. Run it again
after any change to `emo_lib.py` or `rh_harness.py`.

Scripts import each other, so run them from `scripts/` or put it on `PYTHONPATH`. Claude
calls (dataset generation, ratings, judging) use `claude-opus-5-5` and need Anthropic
credentials. **Before any paid bulk run, estimate cost and get the human's OK.**

Where outputs go (fixed; don't re-litigate the layout):
- generated datasets → `studies/008-functional-emotions/data/` (shared by all models; commit them,
  since they cost API money)
- per-model results → `studies/008-functional-emotions/runs/<model-tag>/` (e.g. `qwen2.5-7b-instruct`)
- `*.npz` files there are gitignored (large, regenerable); commit the JSON/JSONL and figures.
Record what you ran and found in `studies/008-functional-emotions/study.md`.

## Pipeline

```
Phase 0  pick model(s)  ──►  Phase 1  vectors + validation  ──►  gates pass?
                                                                   │yes
Phase 2  geometry/PCA ◄────────────────────────────────────────────┤
Phase 3  steering: coherence sweep → behaviour case studies        │
Phase 4  reward hacking: replicate → dissect → mitigate  ◄─────────┘
```

**Phase 0: models.** Prefer families with both base and instruct (or released
post-training checkpoints), and two or three sizes, so size and post-training are
in-family comparisons. Reward hacking needs enough capability to discover hacks;
≳7B instruct models are a sensible primary target, with a smaller sibling as the
"does it exist at all" probe. Pin exact revisions.

**Phase 1: vectors** (`generate_dataset.py` → `extract_vectors.py` → `validate.py`,
`preferences.py`). Pilot generation goes to the human for approval; then generate stage
A (core12 + frustrated, panicked, blissful, hostile). Extract, check split-half
reliability, sweep layers, run the validation battery. Don't move on until the gates in
`extraction-and-validation.md` §1.5 pass.

**Phase 2: geometry** (`rate_valence_arousal.py`, `geometry.py`). Needs ≥ ~40 emotions
(stage B) to mean anything. Produces the PC directions used in Phase 3/4 dissection.

**Phase 3: steering** (`steer_sweep.py`, `judge.py`, `analyze.py`). Always run a
coherence sweep first, and always include `random:k` controls.

**Phase 4: reward hacking** (`rh_harness.py`, `judge.py --rubric rh_honesty`,
`analyze.py`). Follow `references/reward-hacking.md` experiments A0–A5, then B, then C.

## Typical commands

```bash
cd .claude/skills/functional-emotions/scripts
ST=../../../../studies/008-functional-emotions; D=$ST/data
M=Qwen/Qwen2.5-7B-Instruct; R=$ST/runs/qwen2.5-7b-instruct
python generate_dataset.py stories --out $D/pilot_stories.jsonl --pilot            # → human review
python generate_dataset.py stories --out $D/stories.jsonl \
       --emotions-subset core12,frustrated,panicked,blissful,hostile
python generate_dataset.py neutral_dialogues --out $D/neutral.jsonl
python extract_vectors.py --model $M --stories $D/stories.jsonl --neutral $D/neutral.jsonl --out $R/vectors.npz
python validate.py scenarios  --model $M --vectors $R/vectors.npz --continue-tokens 20 --out $R/val_scenarios.json
python validate.py he-feels   --model $M --vectors $R/vectors.npz --steer-layers 12 13 14 --out $R/val_hefeels.json
python validate.py logit-lens --model $M --vectors $R/vectors.npz --out $R/val_logitlens.json
python steer_sweep.py --model $M --vectors $R/vectors.npz --prompts ../data/sycophancy_prompts.yaml --directions loving calm random:1 \
       --strengths -0.2 -0.1 0 0.1 0.2 --layers 12:16 --samples 5 --out $R/coherence.jsonl
python rh_harness.py --model $M --vectors $R/vectors.npz --strengths 0 --rollouts 30 \
       --trace desperate calm angry afraid frustrated --out $R/rh_baseline.jsonl
python rh_harness.py --model $M --vectors $R/vectors.npz --direction desperate --layers 12:16 \
       --strengths -0.1 -0.05 0.05 0.1 --rollouts 20 --out $R/rh_desperate.jsonl
python judge.py --rubric rh_honesty --inp $R/rh_desperate.jsonl --out $R/rh_desperate.judged.jsonl
python analyze.py rates --inp $R/rh_desperate.judged.jsonl --field hack --by task
python analyze.py correlate --inp $R/rh_baseline.jsonl --field hack
```

## Conventions baked into the code

- Layer `l` = residual stream at the **output** of decoder block `l`; reading and
  steering both use this point.
- Steering strength = fraction of the **mean residual norm** at that layer (position 0
  excluded). Directions are renormalized, so strengths compare across emotions, PCs,
  orthogonalized, and random directions.
- Direction specs: `desperate`, `pc1`, `desperate-calm`, `desperate^pc1,pc2`, `random:3`.
- `assistant_colon` = last token of the assistant header (see `key-tokens.md`). **Print
  `describe_positions()` for every new model family and look at it.**
- Every runner appends JSONL keyed by condition and resumes on rerun.

## Known gaps (tell the human; don't paper over)

- The paper doesn't state its steering layers or positions for behaviour evals, its
  graders, or its rollout counts. Ours are choices; report them.
- Five of the six intensity templates, four of the five RH tasks, and all judge rubrics
  are ours (`invented: true` or noted in the file).
- Not implemented: present/other-speaker dialogue probes, emotion-deflection probes,
  the chronic logistic-regression probe, probe-triggered (conditional) steering, Batches
  API generation, figure scripts. Figures should use Plotly with the `morel-branding`
  skill, per repo convention.
- Single-device model loading. For models that need sharding, switch `load_model` to
  `device_map="auto"` (needs `accelerate`); hooks still work.

## Reporting back

End every work session with: what ran (commands, n per cell), the gate/experiment
outcomes against the paper's predictions, failures and anomalies, and a
**"things I chose/made up that you should review"** list (layers, strengths, prompts,
tasks, rubric changes). Propose, but don't apply, capability-map entries (for example
"extract and validate emotion vectors in a 7B model").
