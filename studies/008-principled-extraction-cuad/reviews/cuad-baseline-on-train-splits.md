# The CUAD paper's three models on our development splits

All three released CUAD checkpoints — `roberta-base`, `roberta-large`,
`deberta-v2-xlarge` — run over `harness_val` (40 contracts) and
`principle_train` (60 contracts) on the 12-category subset, on the 3080, and
scored through their own `evaluate.py`.

Run date 2026-08-16. 18 shards, 1.49 GPU-hours, fp32, batch 16.
**`test` was never loaded.**

AI Assistant Used: Claude Code

---

## 0. Read this before any number below

**These 100 contracts are inside CUAD's official train split. They are inside
these three checkpoints' fine-tuning data. Every score in this document is
memorisation-inflated and none of it is evaluative.**

This is not a baseline. It is not "their performance on our data." It is not a
fair contest with our C2/C3 numbers, and nothing here may be quoted as one. The
smoke test already measured the size of the inflation on a 4-category slice
(AUPR 0.85–0.91 against a published test-split 0.43–0.48, with the model
ordering scrambled); the 12-category figures below show the same signature —
`harness_val` AUPR 0.688 / 0.744 / 0.718 against the reproduced Table 2 values
of 0.426 / 0.482 / 0.478, and again `roberta-large > deberta-v2-xlarge >
roberta-base` rather than the published order.

The value of the run is **diagnostic**: it tells us what a model that was
trained on these annotations has learned to treat as the right answer. Where
their models and ours diverge, the divergence is evidence about the *annotation
convention*, not about model quality — because on these contracts their models
have effectively been shown the key.

One further comparability caveat, which matters as much as the memorisation
one and is easy to miss: **at any single confidence threshold their models emit
at most one span per question** (measured 0.20–1.00 spans per gold-present
question at `conf = 0.5`), while our harness emits a set. On categories whose
gold carries several spans per contract — License Grant averages 3.81 gold
spans per gold-present question on `harness_val`, Source Code Escrow 7.0 — their
recall is structurally capped near `1 / spans-per-question` and their apparent
weakness there is an artifact of the comparison, not a finding. Per-category
numbers are therefore reported at two operating points (§3), and the
single-span categories — Agreement Date, Governing Law, Expiration Date, Most
Favored Nation — are the only ones where the point comparison is close to
clean.

---

## 1. The Expiration Date question — answered, and it favours `w11`

**Their models handle duration-expressed Expiration Dates. All three of them,
on both splits, at every threshold checked.**

`expiration-date-diagnosis.md` found our 9B scoring presence recall 1.00 where
the gold span names a calendar date and 0.00 where it states the term as a
duration, with 78% of gold-present contracts in the non-calendar classes. The
question this run was commissioned to settle is whether a model fine-tuned on
this corpus learned the convention. It did.

Gold spans classified by the same four-way taxonomy the diagnosis used
(`scripts/cuad-baseline/expiration_taxonomy.py`, deterministic rules plus five
recorded overrides). Two recall figures per cell, because they say different
things: **presence** (did the model return any span at all for this question)
and **span-IOU** (did a returned span match this gold span at the upstream
Jaccard ≥ 0.5).

### `harness_val` — 35 gold Expiration Date spans over 33 contracts

| gold span class | n | roberta-base | roberta-large | deberta-v2-xlarge | our C2 | our C3 |
|---|---|---|---|---|---|---|
| calendar date | 7 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 | **1.00 / 0.07** | **1.00 / 0.27** |
| **duration** | **18** | **0.89 / 0.89** | **1.00 / 0.94** | **1.00 / 0.94** | **0.00 / 0.00** | **0.02 / 0.02** |
| event / perpetual | 5 | 0.60 / 0.60 | 0.80 / 0.60 | 0.80 / 0.80 | 0.00 / 0.00 | 0.00 / 0.00 |
| other (multi-limb) | 5 | 1.00 / 0.80 | 1.00 / 0.80 | 1.00 / 1.00 | 0.00 / 0.00 | 0.00 / 0.00 |

*(presence / span-IOU. C2/C3 denominators are decisions — 3 seeds × contracts,
n = 47 duration decisions in C2 — rather than spans; the rates are comparable,
the counts are not.)*

### `principle_train` — 55 gold spans over 49 contracts, no C2/C3 counterpart yet

| gold span class | n | roberta-base | roberta-large | deberta-v2-xlarge |
|---|---|---|---|---|
| calendar date | 18 | 0.94 / 0.89 | 0.83 / 0.78 | 0.89 / 0.83 |
| — of which terminal date | 15 | 0.93 / 0.87 | 0.87 / 0.80 | 0.87 / 0.80 |
| — of which start date only | 3 | 1.00 / 1.00 | 0.67 / 0.67 | 1.00 / 1.00 |
| **duration** | **21** | **1.00 / 0.95** | **1.00 / 0.95** | **1.00 / 0.95** |
| event / perpetual | 7 | 1.00 / 1.00 | 1.00 / 1.00 | 1.00 / 1.00 |
| other (multi-limb) | 9 | 1.00 / 0.56 | 0.56 / 0.44 | 1.00 / 0.56 |

Expiration Date false positives are low for all three — 5 / 6 / 4 on
`harness_val`, 8 / 4 / 5 on `principle_train` — so the high duration recall is
not bought by blanket claiming.

### What the spans actually look like

The hits are verbatim reproductions of the gold sentence, on the exact contracts
the diagnosis named as our misses. RoBERTa-base at `conf = 0.5`:

```
TURNKEYCAPITAL   gold: 'The term of this Agreement is twenty-four (24) months.'
                 pred: 'The term of this Agreement is twenty-four (24) months.'
ULTRAGENYX       gold: '...shall remain in force for three years (the "Initial Term").'
                 pred: identical
MPLXLP           gold: '...for a period of fifteen (15) years after the project's in-service date'
                 pred: identical
HOLIDAYRVSUPER…  gold: '...shall be three years, commencing on the date of this Agreement...'
                 pred: identical
```

Our model, on these same four contracts, located and quoted the clause, computed
the expiry date in three of them, and then ruled **absent** — citing `w06`.

### The inference

1. **The convention is real and it is learnable.** Three architectures at three
   scales, trained on this corpus, all converge on "the clause that fixes the
   term answers the Expiration Date question, however it fixes it." That is not
   an artifact of one model's inductive bias.
2. **`w11` targets something genuine.** The diagnosis proposed it on gold
   statistics alone (`provenance_axis: data_only`). This run is independent
   corroboration from a different direction: a model that consumed these
   annotations learned exactly the rule `w11` states. **Strong prior in favour
   of spending ladder budget on it.**
3. **`w11` alone will not collect the win, and this run quantifies why.** Look
   at the calendar-date row for C2/C3: presence recall 1.00, span-IOU recall
   **0.07 / 0.27**. On the cases our model *does* claim, its span fails the
   scorer's IOU bar because `w01`'s date-category exception clips it to the bare
   value while the gold span is a whole sentence (median 199 characters). Their
   models score 1.00 on the same cells. This is the diagnosis's "`w01` will
   fight it" caveat, now measured rather than predicted: converting the
   duration false-absents into extractions without simultaneously narrowing
   `w01`'s exception buys presence and loses it again at the IOU gate. **Test
   `w11` and the `w01` narrowing as a pair, as §5.3 of the diagnosis said.**
4. **The event / perpetual class is the one place their models are also
   uneven** (0.60–0.80 presence on `harness_val`, though 1.00 on
   `principle_train`, n = 5 and 7). If `w11` is drafted to cover "fixes no
   point at all" cases it is on thinner ice there than on durations. The
   duration limb is the load-bearing one and it is solid.

---

## 2. Pooled scores, both splits

Through unmodified `evaluate.py`, 12 categories, question-id assertion passing
for all six model×split combinations.

| split | model | AUPR | P@80%R | P@90%R | max recall |
|---|---|---|---|---|---|
| harness_val | roberta-base | 0.688 | 0.536 | 0.486 | 0.952 |
| harness_val | roberta-large | 0.744 | 0.608 | 0.552 | 0.964 |
| harness_val | deberta-v2-xlarge | 0.718 | 0.590 | 0.550 | 0.979 |
| principle_train | roberta-base | 0.647 | 0.544 | 0.440 | 0.959 |
| principle_train | roberta-large | 0.721 | 0.646 | 0.536 | 0.967 |
| principle_train | deberta-v2-xlarge | 0.670 | 0.554 | 0.429 | 0.969 |

Single-threshold precision/recall, pooled over the 12 categories:

| split | model | conf 0.1 | conf 0.3 | conf 0.5 | conf 0.9 |
|---|---|---|---|---|---|
| harness_val | roberta-base | 0.55 / 0.78 | 0.67 / 0.57 | 0.71 / 0.46 | 0.78 / 0.34 |
| harness_val | roberta-large | 0.63 / 0.79 | 0.73 / 0.61 | 0.75 / 0.48 | 0.86 / 0.38 |
| harness_val | deberta-v2-xlarge | 0.59 / 0.80 | 0.69 / 0.61 | 0.73 / 0.46 | 0.79 / 0.36 |
| principle_train | roberta-base | 0.56 / 0.77 | 0.62 / 0.51 | 0.67 / 0.41 | 0.77 / 0.30 |
| principle_train | roberta-large | 0.65 / 0.81 | 0.70 / 0.53 | 0.72 / 0.41 | 0.83 / 0.31 |
| principle_train | deberta-v2-xlarge | 0.58 / 0.77 | 0.68 / 0.52 | 0.69 / 0.40 | 0.79 / 0.27 |

For reference, and **not as a contest**: our C2 sits at precision 0.719 / recall
0.430 and C3 at 0.751 / 0.430 on `harness_val`. That lands between their
`conf = 0.5` and `conf = 0.7` points. A 9B general model with a prompt is at the
same operating point as a fine-tuned extractor that has seen these exact
contracts — which is interesting, and is *not* a claim about the two systems'
relative capability, because the two sides earn that point through completely
different errors (§4).

`conf = 0.0` is reported in the JSON but omitted here: it admits the whole
20-deep n-best and gives recall ~0.96 at precision ~0.05. It is not an operating
point, only the curve's endpoint.

---

## 3. Per category

Both operating points are shown because neither alone is honest. `conf = 0.5` is
their committed decision and is the like-for-like point against our
single-answer harness; `conf = 0.1` lets them emit multiple spans and is the
point at which multi-span categories become interpretable. Ours is at whatever
point our prompt produces — it has no threshold to sweep.

### `harness_val` (precision / recall)

| category | gold spans/Q | rb @0.5 | rl @0.5 | db @0.5 | rl @0.1 | C2 | C3 |
|---|---|---|---|---|---|---|---|
| Agreement Date | 1.00 | 0.97/0.92 | 0.95/0.97 | 0.97/0.92 | 0.88/1.00 | 0.96/0.91 | 0.97/0.94 |
| Governing Law | 1.06 | 0.97/0.88 | 1.00/0.94 | 0.97/0.91 | 0.97/1.00 | **0.42/0.38** | **0.44/0.41** |
| Expiration Date | 1.06 | 0.86/0.86 | 0.84/0.89 | 0.89/0.94 | 0.80/0.94 | **0.07/0.01** | **0.31/0.06** |
| Anti-Assignment | 1.50 | 0.76/0.44 | 0.82/0.39 | 0.83/0.42 | 0.76/0.94 | 0.89/0.60 | 0.88/0.59 |
| Cap On Liability | 1.71 | 0.68/0.36 | 0.87/0.36 | 0.72/0.36 | 0.72/0.86 | 0.89/0.43 | 0.91/0.47 |
| License Grant | 3.81 | 0.82/0.15 | 0.75/0.15 | 0.71/0.08 | 0.82/0.44 | 0.95/0.48 | 0.97/0.41 |
| Exclusivity | 1.77 | 0.27/0.17 | 0.36/0.22 | 0.43/0.26 | 0.42/0.96 | 0.56/0.55 | 0.68/0.61 |
| Revenue/Profit Sharing | 1.85 | 0.46/0.25 | 0.50/0.29 | 0.46/0.25 | 0.40/0.67 | 0.53/0.37 | 0.57/0.36 |
| Minimum Commitment | 2.67 | 0.60/0.19 | 0.60/0.19 | 0.31/0.12 | 0.62/0.66 | 0.53/0.13 | 0.56/0.13 |
| Volume Restriction | 1.50 | 0.12/0.33 | 0.23/0.50 | 0.14/0.33 | 0.12/0.67 | 0.14/0.17 | 0.00/0.00 |
| Most Favored Nation | 1.00 | 0.44/1.00 | 0.40/1.00 | 0.44/1.00 | 0.29/1.00 | 0.75/0.30 | 1.00/0.18 |
| Source Code Escrow | 7.00 | 0.00/0.00 | 0.00/0.00 | —/0.00 | 0.00/0.00 | 0.50/0.07 | 0.75/0.14 |

### `principle_train` (precision / recall, no C2/C3 counterpart)

| category | gold spans | rb @0.5 | rl @0.5 | db @0.5 | rl @0.1 |
|---|---|---|---|---|---|
| Agreement Date | 52 | 0.92/0.94 | 0.93/0.98 | 0.88/0.98 | 0.79/1.00 |
| Governing Law | 55 | 1.00/0.93 | 1.00/0.89 | 1.00/0.87 | 1.00/0.98 |
| Expiration Date | 55 | 0.86/0.87 | 0.92/0.82 | 0.90/0.85 | 0.70/1.00 |
| Anti-Assignment | 84 | 0.94/0.36 | 0.91/0.35 | 0.94/0.35 | 0.83/0.83 |
| Cap On Liability | 97 | 0.64/0.16 | 0.82/0.19 | 0.59/0.16 | 0.76/0.68 |
| License Grant | 71 | 0.60/0.21 | 0.62/0.23 | 0.68/0.27 | 0.61/0.69 |
| Exclusivity | 50 | 0.41/0.22 | 0.44/0.22 | 0.33/0.18 | 0.53/0.80 |
| Revenue/Profit Sharing | 52 | 0.35/0.12 | 0.38/0.12 | 0.30/0.06 | 0.60/0.83 |
| Minimum Commitment | 51 | 0.38/0.18 | 0.48/0.20 | 0.27/0.12 | 0.52/0.59 |
| Volume Restriction | 14 | 0.19/0.43 | 0.27/0.57 | 0.24/0.50 | 0.25/0.93 |
| Most Favored Nation | 12 | 0.28/0.58 | 0.37/0.58 | 0.50/0.58 | 0.32/0.92 |
| Source Code Escrow | 18 | 0.40/0.11 | 0.33/0.06 | 0.33/0.11 | 0.50/0.50 |

The `principle_train` picture is the same as `harness_val`'s in every respect
that matters — memorised on the single-span categories, threshold-limited on the
multi-span ones, weakest on Source Code Escrow and Volume Restriction. It is 50%
more contracts and it does not change any conclusion, which is itself useful:
whatever we select on `principle_train` will not be sitting on a split that
behaves differently from the one the diagnosis was run on.

---

## 4. Where the error patterns differ in kind, not degree

Same scorer, same gold, `harness_val`, their `conf = 0.5` against our C2/C3.

| system | gold-present Qs with no prediction | gold-absent Qs with a prediction | FP on gold-absent Qs | FP on gold-present Qs |
|---|---|---|---|---|
| roberta-base | 55/211 (26%) | 59/269 (22%) | 59 | **3** |
| roberta-large | 46/211 (22%) | 47/269 (17%) | 47 | **6** |
| deberta-v2-xlarge | 53/211 (25%) | 51/269 (19%) | 51 | **6** |
| C2 (9B, 3 seeds) | 140/509 (28%) | 38/727 (5%) | 42 | **91** |
| C3 (9B, 3 seeds) | 129/500 (26%) | 31/700 (4%) | 32 | **82** |

**Their false positives are almost entirely over-claiming on absent categories
(89–95%); ours are almost entirely wrong spans on present ones (68–72%).**
The decline rates are nearly identical — 22–26% vs 26–28% — so the two systems
lose roughly the same amount of recall to silence, and then differ completely in
what they do when they speak. A fine-tuned extractor, having memorised the
clause locations, essentially never mis-delimits a span it finds; it errs by
answering a question the contract does not answer. Our harness errs the other
way: it is conservative about absence (4–5% over-claim rate against their
17–22% — this is `w06` and the absence machinery working, and working well) and
imprecise about boundaries.

That asymmetry means **span fidelity and absence discipline are separable
problems for us, and we are already winning one of them.** Any principle that
improves boundaries is not in tension with the absence work.

Category-level qualitative differences, beyond magnitude:

- **Governing Law — different error entirely.** Their precision is 0.97–1.00;
  ours is 0.42 with 44 false positives on 40 contracts. Ours is not missing the
  clause, it is *adding* venue, forum and arbitration clauses. Their models were
  trained on annotations that exclude those, and they exclude them. This is a
  second, independent confirmation of the `w03` convention from exactly the same
  kind of evidence as the Expiration Date result — and `w03` is already the one
  record in the working set with `checker_status: usable`. Worth noting that
  `w03` is *not yet fixing this*: C2 and C3 both carry the same 42–44 FPs.
- **Most Favored Nation — opposite error direction.** They claim it everywhere
  (recall 1.00, precision 0.29–0.44); we claim it rarely and correctly
  (C3 precision 1.00, recall 0.18). A rare category where the memorised models
  are the reckless ones. Do not read our low recall here as the same kind of
  failure as Expiration Date.
- **Source Code Escrow — nobody has it.** One gold-present question on
  `harness_val` with 7 gold spans; their recall is 0.00 at both thresholds, ours
  0.07–0.14. On `principle_train` (5 questions, 18 spans) they reach 0.44–0.50 at
  `conf = 0.1`. n is too small on `harness_val` to support any statement.
- **Volume Restriction — both sides are bad, and the gold is the reason.** They
  reach recall 0.33–1.00 only by holding precision at 0.10–0.27; we score
  0.14/0.17 and 0.00/0.00. The diagnosis's read — a genuine annotation-boundary
  dispute running in both directions — survives contact with a model trained on
  that boundary. **A model that memorised this corpus cannot make Volume
  Restriction precise either.** That is a meaningful negative result and it
  supports the diagnosis's recommendation not to write a principle for it off
  `harness_val`.
- **Anti-Assignment / Cap On Liability / License Grant — our apparent advantage
  is mostly the multi-span artifact.** We beat them on all three at
  `conf = 0.5`. At `conf = 0.1` their recall overtakes ours decisively on
  Anti-Assignment (0.94 vs 0.60) and Cap On Liability (0.86 vs 0.43), at the
  cost of precision (0.76 and 0.72 against our 0.89). **License Grant is the
  exception and is worth a second look**: even at `conf = 0.1` they sit at
  0.82/0.44 against our 0.95/0.48 — a memorised model does not beat our harness
  on the split's most multi-span category at any threshold. Do not report the
  `conf = 0.5` column for these three without the `conf = 0.1` one.

---

## 5. Run record

18 shards: 3 models × 2 splits × 3 category-groups of 4. One `--cache_dir` per
shard, deleted after use (the smoke's cache-key collision — the predict file is
not in `cached_dev_{model}_{seq_len}` — is avoided by construction, not by
`--overwrite_cache`). `make_split_shards.py` and `run_split_shards.sh` both
refuse anything named `test`.

| model | harness_val (3 shards) | principle_train (3 shards) | peak RSS |
|---|---|---|---|
| roberta-base | 238 s | 410 s | 4.1–5.2 GB |
| roberta-large | 532 s | 937 s | 5.2–6.0 GB |
| deberta-v2-xlarge | 1,182 s | 2,066 s | **10.0 GB** |
| **total** | **0.54 h** | **0.95 h** | — |

**1.49 h wall for everything**, against the brief's 0.4–1 GPU-h per split: the
estimate held. Two corrections to the smoke's numbers:

- **DeBERTa's peak RSS is 10.0 GB per shard**, flat across shard sizes. The
  smoke's fitted line (3.61 GB intercept + 93 KB/window) predicts ~4.4 GB for a
  6.5 K-window shard. The intercept is model-dependent and roughly 2.7× larger
  for DeBERTa-v2-xlarge than the RoBERTas; the slope was fitted on RoBERTa runs.
  Sharding was the right call for a different reason than the one recorded —
  even one shard of DeBERTa costs 10 GB of a 23 GB box, so an unsharded
  41-category DeBERTa run would not have been merely tight, it would have
  swapped. Anyone re-using the smoke's RSS line for DeBERTa should replace the
  intercept with a measured 9.9 GB.
- **Time per window matched the smoke closely** — the 4-category throughput
  slice extrapolated to 12 categories predicted 0.24 / 0.46 / 0.94 h for
  `test`'s 102 contracts; we measured 0.18 / 0.41 / 0.90 h for 100 contracts.

One operational note for whoever runs the next long job: the driver survived
its controlling SSH session being killed mid-run, contrary to the
`desktop-gpu-access` skill's warning that WSL tears down on last-session close.
It did not tear down here. Do not rely on that either way — the script is
idempotent (it skips shards whose `nbest_predictions_.json` exists), which is
what actually made the interruption a non-event.

---

## Artifacts

| path | what |
|---|---|
| `scripts/cuad-baseline/make_split_shards.py` | build 12-category SQuAD shards from a named split; refuses `test` |
| `scripts/cuad-baseline/run_split_shards.sh` | the 18-shard driver; per-shard cache dir, idempotent, refuses `test` |
| `scripts/cuad-baseline/expiration_taxonomy.py` | gold Expiration Date span classifier (calendar / duration / event / other) |
| `scripts/cuad-baseline/expiration_taxonomy_overrides.json` | the five hand overrides |
| `scripts/cuad-baseline/score_split_runs.py` | scoring: curve metrics, conf sweep, per-category, Expiration taxonomy |
| `scripts/cuad-baseline/c2c3_absence_profile.py` | recomputes C2/C3 with the same absence profile and the same taxonomy |
| `data/cuad-baseline/baseline_on_train_splits.json` | all of §1–§4 for their models |
| `data/cuad-baseline/c2c3_absence_profile.json` | our side, same scorer, same taxonomy |
| `data/cuad-baseline/expiration_gold_taxonomy.json` | per-span class assignments, both splits |
| `data/cuad-baseline/split-preds/` | 18 shards of raw `nbest_predictions_` (45 MB, **gitignored**) |

Desktop state left at `/home/tlifke/Projects/cuad-baseline`: `shards/`,
`out-splits/`, `run_split_shards.sh`. `cache-splits/` was deleted per shard.
Nothing committed. `HF_TOKEN` was not needed and was not used.

---

## Things I made up that you should review

1. **The gold-span taxonomy is mine, not the diagnosis's.** The diagnosis
   hand-labelled 32 contracts; I wrote a deterministic classifier and five
   overrides. It reproduces the diagnosis's calendar count (7) and duration
   count (18) on `harness_val` exactly, and disagrees on the event/other
   boundary (I get 5/5, the diagnosis 3/4) plus one extra contract the
   diagnosis had no scored trials for. The calendar/duration split — the
   load-bearing one — is agreed; the event/other split is not, and both cells
   are n ≤ 9.
2. **`conf = 0.5` as the headline operating point is my choice**, picked as "the
   model's committed decision" rather than derived from anything. Their P@80%R
   thresholds are 0.02–0.05, far below it. Every table is also computed at 0.1,
   0.3, 0.7 and 0.9 in the JSON; if a different point is wanted, no re-run is
   needed.
3. **The `terminal_date` sub-flag on calendar spans** (does the span print the
   *end* date, or only a start date plus a duration) is my addition, a
   cue-word heuristic. It fires on n = 3 `principle_train` spans. It is
   suggestive — those three behave like durations — and nowhere near enough
   evidence to act on.
4. **"95% of their FPs are over-claims on absent questions."** That is at
   `conf = 0.5`. At `conf = 0.1` the FP mix shifts toward gold-present questions
   as they emit more spans. The qualitative contrast with our error profile
   holds at both, but the 95% figure is threshold-specific.
5. **The claim that our Governing Law FPs are venue/arbitration clauses** is
   carried over from the diagnosis and the `w03` record, not re-verified against
   the spans in this run.
6. **Peak RSS is `/usr/bin/time -v` maximum resident set size** for the whole
   `train.py` process including the feature-conversion worker pool; I did not
   separate model residency from feature residency, so the "intercept is
   model-dependent" reading is an inference from the flatness across shard
   sizes, not a decomposition.
7. **I did not diff our re-run's n-best against the authors' shipped
   predictions.** That check — the one remaining reproduction risk named in
   `cuad-table2-reproduction.md` §4.2 — is a `test`-split operation and stays
   sealed until G4. Nothing in this document speaks to it.
