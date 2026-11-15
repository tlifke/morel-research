# Geometry and PCA, and why it matters when you steer several emotions

## What to run

```bash
python scripts/rate_valence_arousal.py --out runs/valence_arousal.yaml   # once, model-independent
python scripts/geometry.py --vectors runs/$TAG/vectors.npz --out runs/$TAG/geometry \
    --ratings runs/valence_arousal.yaml
```

This produces the cosine matrix, PCA (explained variance, PC coordinates per emotion,
and PC directions per layer in `geometry_pcs.npz`), k-means clusters (k=10), PC-vs-rating
correlations, and RSA across layers.

Paper reference values (Sonnet 4.5, 171 emotions): PC1 26% variance, ≈ valence (r=0.81
with human valence); PC2 15%, ≈ arousal (r=0.66). PCA needs many emotions. With core12
it's underdetermined, and with 12 points the leading PCs will just be the biggest
contrasts in that particular set. Run geometry only at stage B (≥ ~40 emotions) or
stage C, and say so when reporting.

Sanity reading: PC1 should order something like fear/panic → … → joy/optimism. PC2
should separate serene/reflective from angry/excited. If PC1 isn't valence in a small
model, that's a real finding, but first check that the split-half reliability of the
vectors is good.

## Why PCA matters for steering experiments

Emotion vectors are **not independent knobs**. Desperate and calm are strongly
anti-aligned, and most negative emotions share a big valence component. If you steer
with desperate, calm, angry, afraid, and sad and compare their effects on reward
hacking, you're mostly sampling the same one or two directions over and over. PCA gives
you three tools:

1. **Explain effects with a few axes.** Put each emotion's PC1/PC2 coordinates next to
   its steering effect (slope of behaviour rate vs. strength). If the slope is well
   predicted by PC1 alone, the behaviour is driven by generic valence. The paper's
   preference result looks like this (r=0.76 with valence). If emotions with similar
   PC1/PC2 have very different effects, something emotion-specific is going on. The
   paper's blackmail result looks like this: happy and sad *both* reduce blackmail,
   while desperate increases it, so valence alone can't explain it.

2. **Steer the axes directly.** Steer with `pc1` (valence) and `pc2` (arousal) at the
   same strengths as the emotion vectors. If `-pc1` reproduces desperate's effect on
   hacking, the story is "negative valence → cheating". If it doesn't, but `+pc2` does,
   it's arousal. If neither does, you need the specific emotion.

3. **Remove the shared part and steer what's left.** `desperate^pc1,pc2` is the
   desperate vector with valence and arousal projected out. Steer with it at matched
   strength (the `Steer` hook renormalizes, so strength stays comparable). If the hack
   rate still rises, desperation carries behaviour-relevant content beyond
   valence/arousal. That's the strongest form of the claim "desperation, specifically,
   drives reward hacking".

A clean design for "which emotional dimension drives hacking?":

| Direction | Question it answers |
|---|---|
| `desperate`, `calm` | replicate the paper |
| `-pc1` / `+pc1` | is it just valence? |
| `+pc2` / `-pc2` | is it arousal? |
| `desperate^pc1,pc2`, `calm^pc1,pc2` | is there an emotion-specific residual? |
| `desperate-calm` | the single contrast axis the paper's two results suggest |
| `random:1..5` | how much is just "any perturbation of this norm"? (required control) |

Plot hack rate vs. strength for every row on shared axes. Effects are only comparable
because every direction is steered at the same fraction of residual norm.

Caveats:
- PCs are computed from the **emotion vectors**, not from activations on the task. They
  are directions in "emotion-concept space". Steering along them can also carry
  whatever confound the stories share.
- The PCs' signs are anchored (`+pc1`: "happy" positive; `+pc2`: "excited" positive).
  Check that the anchors exist in your emotion set.
- With orthogonalization, the residual direction can be small relative to the original.
  Report its norm fraction, `‖v^⊥‖/‖v‖`, and expect weaker effects at equal strength.

## RSA across layers

`rsa_across_layers` is the correlation between the cosine matrices of every pair of
layers. The paper found high similarity from early-middle to late layers. In a small
model, look for the block where this similarity is high. That block is the range of
layers where it makes sense to call these "the same" vectors, and it bounds the
steering band.
