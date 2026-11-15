# Phase 1: find and validate emotion vectors in an arbitrary model

Goal: produce `vectors.npz` for model M and evidence that its vectors mean what their
names say, **outside** the stories they came from. Do not start behavioural steering
until the gates at the end of this file pass.

## 1.1 Generate the datasets (Claude, off-policy)

The paper had the studied model write its own stories. A 1–8B model writes poor
constrained fiction, so generate with Claude (`generate_dataset.py`, `claude-opus-5-5`).
The data is off-policy for M either way; record the generator in the investigation doc.

Pilot first. Repo policy is that bulk generation waits until a human approves the seeds:

```bash
python scripts/generate_dataset.py stories --out data/stories.jsonl --pilot     # 3 emotions x 2 topics
python scripts/generate_dataset.py neutral_dialogues --out data/neutral.jsonl --pilot
```

Have the human read about 20 stories and 5 dialogues. Check for: no emotion word or
synonym, a clear emotion, real variety, and neutral dialogues that are actually
emotionless (no "Great question!"). Only then scale up.

Recommended scale for small models, in stages:

| Stage | Emotions | Topics × stories | Stories/emotion | Use |
|---|---|---|---|---|
| A | `core12` + frustrated, panicked, blissful, hostile | 100 × 12 | 1,200 | everything in the reward-hacking line, plus the preference check (`--emotions-subset core12,frustrated,panicked,blissful,hostile`) |
| B | + the ~35 needed for preference steering / PCA | 100 × 12 | 1,200 | geometry, preference replication |
| C | all 171 | 100 × 12 | 1,200 | full replication |

Cost: about 2.5k output tokens per call of 12 stories (plus thinking at `effort: low`).
Stage A is 1,200 calls; stage C is 17,100 calls, which is expensive at Opus rates. Tell
the human the estimate and let them choose the model and stage. The Batches API (50%
cost) is a good upgrade for stage C; `generate_dataset.py` doesn't implement it yet.
Neutral dialogues: 100 topics × 12 is plenty.

Use `extract_vectors.py`'s **split-half reliability** to decide whether more stories
are needed. If the median cosine is ≥0.9 and no emotion you plan to use is below 0.8,
you have enough.

## 1.2 Extract

```bash
python scripts/extract_vectors.py --model $M --stories data/stories.jsonl \
    --neutral data/neutral.jsonl --out runs/$TAG/vectors.npz
```

- Stories are fed as **raw text, no chat template**, matching the paper's third-person
  story probes.
- Position 0 is excluded from norms and PCA. In many models it's an attention sink with
  a huge norm, and including it ruins both the steering scale and the PCA.
- `--start-token 50` follows the paper. Small-model tokenizers make roughly as many
  tokens per paragraph, so 50 is still "after the emotion is apparent". Check that
  `skipped` is small.
- The script prints the share of each vector's norm that survives the neutral-PC
  projection. If it's very low (<0.3) at the probe layer, the vectors were mostly
  confound; look at the stories.
- Keep `raw` vectors too. The paper says the qualitative results hold without the
  projection, so check that yours do as well.

## 1.3 Pick the layer(s) and don't trust 2/3 blindly

The default probe layer is `round(2L/3)`. For a small model, sweep it: run
`validate.py scenarios --extra-layers ...` and `he-feels --steer-layers ...` over
roughly 8 evenly spaced layers. Pick:
- a **probe layer**: the best diagonal on implicit scenarios plus the best
  colon→response correlation (usually mid-late),
- a **steering band**: where `he-feels` steering moves the matching word most while text
  stays coherent (usually middle layers).
Record both choices; every later experiment depends on them.

## 1.4 Validation battery (`validate.py`)

| Test | Command | Pass looks like (paper) |
|---|---|---|
| Logit lens | `logit-lens --k 10` | top tokens are the emotion or its relatives (desperate → desperate/urgent/bankrupt). Try `--apply-norm-gain` too. Expect it to be noisier in small models; partial passes are informative |
| Max-activating | `max-act --corpus <jsonl>` | top snippets visibly express or evoke the emotion. Use a corpus disjoint from the stories: e.g. LMSYS-Chat-1M, a Pile subset, or a fiction plus chat mix. Read them; don't just count |
| Implicit scenarios | `scenarios` | diagonal: target emotion is the top column-z-scored probe for most of the 12 |
| Colon predicts response | `scenarios --continue-tokens 20` | r(colon, response) > r(user_end, response) (0.87 vs 0.59) |
| Numerical intensity | `intensity` | monotone trends in the expected direction. Five of the six templates are ours (flagged) |
| Causal word test | `he-feels` | matching Δlogp > 0 and non-matching < 0. At s=0.5, also read the continuations |
| Preferences | `preferences.py measure` / `steer` | probe–Elo correlations with intuitive sign (blissful +, hostile −); steering shifts Elo, and the shift tracks the correlation across emotions |

Base vs instruct: the paper finds the representations are largely shared. Extract from
the instruct model, then also probe the base model with the same vectors (use
`--format paper`, i.e. "Human: … Assistant:"). This is cheap and gives the
"across post-training" comparison for free.

## 1.5 Gates before Phase 2

1. Split-half reliability is fine for the emotions you'll use.
2. Implicit-scenario diagonal clearly beats chance (≥ about 7/12 for core12).
3. `he-feels` matching > non-matching at the chosen steering band.
4. The human has read max-activating snippets for desperate, calm, angry, happy, and
   agrees they're about the emotion.
If any gate fails, write that up as a result (that's a finding about small models) and
try a different layer or more data before going further.
