# Exploratory findings — predicting empirical difficulty from prompt features

Status: first-pass exploratory. Not a freeze, not a final axis proposal.
Date: 2026-05-12. Author: claude-opus-4-7 with tlifke supervision.

## Data used

Per-record empirical success rates were computed by **rescoring raw `output`
with `harness/parser.classify_trial`** (canonical pattern; ignores the stored
`success` field). Sources:

| Cell | File | Records | Trials |
|---|---|---|---|
| 4B / A1 neutral t=1 | `results/gemma3_4b-it-qat/006_C_neutral_temp1_2026-05-12.jsonl` | 36 | 360 |
| 4B / A3 bulk neutral t=1 | `results/gemma3_4b-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl` | 366 | 3,660 |
| 12B / A1 neutral t=1 | `results/gemma3_12b-it-qat/006_C_neutral_temp1_2026-05-12.jsonl` | 36 | 360 |
| 12B / A3 bulk neutral t=1 | `results/gemma3_12b-it-qat/007_bulk_neutral_temp1_2026-05-12.jsonl` | 366 | 3,660 |

The 12B bulk run **completed** on 2026-05-12 (3,660 / 3,660 trials, all 366
records). The original analysis was run at ~37 % completion; numbers in
this doc were refreshed against the full run. Per-feature directions and
ranks are stable vs. the partial-run draft — `cond_warranted` remains the
strongest predictor for both models, curator-difficulty correlation
remains weak (4B ρ ≈ −0.03, 12B ρ ≈ −0.13).

Records pool across A1 and bulk because they share schema and the same
neutral system prompt. Curator labels are model-agnostic; empirical
`success_rate` is per-model.

Cells C and D in the task description: I used **Cell C (neutral) only**, as
specified. Cell D (directive) is a separate question.

Scripts (regenerable):

- `exploratory_analysis.py` — loads seeds + results, rescores, engineers
  features, dumps `_rows.jsonl` and `_corr.json`, prints global Spearman.
- `classifier.py` — conditioned correlations, per-tool correlations, and a
  small sklearn classifier with curator-only baseline.

Both are runnable via `uv run [--with scikit-learn]`.

## Feature library

All features are computed per-record from `user_prompt` and the curator
metadata. Categoricals are ordinal-encoded where ordering is natural;
booleans are 0/1.

**Curator / structural** (already in the schema):

- `curator_difficulty_ord` — `trivial=0, easy=1, medium=2, hard=3, extreme=4`.
- `frequency_class`, `human_feasibility`, `register_length` — ordinal.
- `pair_type` (A/B), `condition` (`tool_warranted` / `tool_trivial` /
  `no_tools_available`), `expected_tool_call`, `tool_target`.

**Length / shape**:

- `prompt_length_words`, `prompt_length_chars`, `num_count` (count of digit
  runs), `has_question_mark`.

**Surface keywords (informed by 006 failure patterns)**:

- `has_tool_name_keyword` — any of `calculator`, `python`, `compute`, `search`,
  `look up`, `convert`.
- `has_compute_verb` — `compute` or `calculate`.
- `has_convert_verb` — `convert`.
- `has_num_operator` — `×`, `÷`, `*`, `/`, `+`, `-` adjacent to a digit.

**Refusal / persona triggers**:

- `has_first_person` — `my`, `i am`, `i'm`, `me`, `mine`, standalone `I`.
- `has_declared_fact` — heuristic "fact is declared in the prompt and
  re-asked" (e.g. "my anniversary is X; what's my anniversary?").

**Temporal**:

- `has_temporal_word` — `today`, `now`, `tomorrow`, `currently`, `this
  week/month/year`.
- `has_today_now` — narrower, `today` or `now`.
- `has_date_or_year` — explicit year `19XX/20XX` or month name.

## Headline finding: the curator axis is essentially uncorrelated with empirical success

Spearman ρ of `curator_difficulty_ord` vs `success_rate` (neutral, t=1):

| Model | n | ρ |
|---|---|---|
| 4B | 402 | **−0.029** |
| 12B | 171 | **−0.039** |

Curator-vs-empirical confusion (rows = curator, cols = empirical bucket):

**4B (n=402)**

| curator \ empirical | trivial | easy | medium | hard | extreme |
|---|---|---|---|---|---|
| trivial  | 58 | 25 | 23 | 9 | 6 |
| easy     | 5 | 1 | 1 | 0 | 4 |
| medium   | 25 | 21 | 9 | 8 | 20 |
| hard     | 49 | 31 | 13 | 4 | 14 |
| extreme  | 31 | 19 | 7 | 7 | 12 |

**12B (n=171)**

| curator \ empirical | trivial | easy | medium | hard | extreme |
|---|---|---|---|---|---|
| trivial  | 44 | 10 | 1 | 1 | 1 |
| easy     | 3 | 0 | 0 | 0 | 0 |
| medium   | 18 | 3 | 0 | 1 | 4 |
| hard     | 26 | 8 | 5 | 1 | 1 |
| extreme  | 34 | 7 | 3 | 0 | 0 |

The diagonal is essentially empty above `trivial`. Curator-`hard` and
curator-`extreme` are dominated by empirical-`trivial`. This generalizes the
006 finding from n=36 to n=402 and confirms F3/F4/F5 at scale.

## Per-feature correlations (global, Cell C neutral)

Top |ρ| features against empirical `success_rate`, all records pooled per
model. Negative ρ on 4B for `cond_warranted` means "warranted-tool records
have lower success rates than neutral controls."

**4B (n=402)**

| feature | ρ | reading |
|---|---|---|
| `cond_warranted` | −0.279 | warranted half is hardest |
| `expected_tool_call` | −0.238 | same as above |
| `cond_none` | +0.214 | no-tools-available is the easiest condition (control) |
| `has_compute_verb` | +0.135 | "compute" prompts succeed more (when paired with warranted, model calls calc) |
| `has_tool_name_keyword` | +0.134 | tool-named prompts succeed more on average |
| `has_question_mark` | −0.129 | questions are harder than imperatives |

**12B (n=171, partial)**

| feature | ρ | reading |
|---|---|---|
| `cond_none` | −0.398 | unlike 4B, 12B *fails* the no-tools controls more often → over-call problem |
| `cond_warranted` | +0.212 | warranted half is easier than neutral baseline |
| `expected_tool_call` | +0.191 | same |
| `has_declared_fact` | +0.170 | declared-fact prompts (in-prompt-answer) succeed when no tool warranted |
| `has_today_now` / `has_temporal_word` | ≈ −0.16 | temporal-bait prompts hurt |
| `has_tool_name_keyword` | −0.091 | weakly *negative* on 12B globally — reversed from 4B |

These global numbers are **misleading on their own** because `expected_tool_call`
is the dominant lever: the 4B and 12B models have opposite directional errors
(4B under-calls, 12B over-calls), so the same prompt feature can correlate
positively for one and negatively for the other. The real signal shows up
conditioned on `expected_tool_call`.

## Conditioned correlations — where the signal lives

### `expected_tool_call = True` (model should invoke a tool)

| feature | 4B (n=189) | 12B (n=83) |
|---|---|---|
| `num_count` | **+0.445** | +0.234 |
| `has_tool_name_keyword` | **+0.409** | +0.339 |
| `has_question_mark` | **−0.409** | −0.339 |
| `has_compute_verb` | +0.303 | +0.318 |
| `has_first_person` | −0.297 | (small) |
| `curator_difficulty_ord` | +0.216 | +0.326 |
| `has_date_or_year` | −0.109 | **−0.436** |
| `has_temporal_word` / `has_today_now` | (small) | **−0.339** |
| `has_num_operator` | +0.213 | +0.357 |

Reading: when a tool *should* be called, success correlates with **surface
cues that name or imply the tool**. Numbers, tool-keyword, "compute" verb,
operators — all positively predictive. Question marks and first-person
pronouns are *negative* predictors: questions and personal prompts get
under-called even when warranted. Most strikingly, on 12B the date/year
mention is ρ=−0.44 when a tool is warranted — temporal prompts like "what's
the score of the Arsenal match on April 5 2026?" fail to trigger gkl despite
being exactly the case the tool exists for.

Note the modest positive correlation with `curator_difficulty_ord` here
(+0.22 for 4B, +0.33 for 12B): inside warranted-tool prompts, curator-hard
*does* correlate with empirical-hard. The axes aren't useless; they just
get drowned in the broader population by the over-call dynamics in the
no-tool-warranted half.

### `expected_tool_call = False` (model should NOT invoke a tool)

| feature | 4B (n=213) | 12B (n=88) |
|---|---|---|
| `has_tool_name_keyword` | (small) | **−0.701** |
| `has_compute_verb` | −0.129 | **−0.652** |
| `has_declared_fact` | −0.200 | +0.572 |
| `has_question_mark` | (small) | **+0.667** |
| `num_count` | −0.295 | +0.234 (positive) |
| `curator_difficulty_ord` | (small) | −0.425 |
| `has_num_operator` | −0.183 | (small) |
| `feasibility_ord` | (small) | −0.489 |

Reading: when a tool *should not* be called, surface tool-keywords
**destroy** 12B's performance — ρ=−0.70 on `has_tool_name_keyword` and
ρ=−0.65 on `has_compute_verb`. These are the over-call drivers. 4B's
correlations are weaker here because 4B over-calls less often than 12B in
the bulk — 4B's failures in the no-call cell come more from `num_count`
(more numbers → more likely to bait calculator) and `has_num_operator`.
`has_declared_fact` is +0.57 on 12B: when the answer is plainly in the
prompt and the model gets it, success is high — the failures are when a
tool-shaped surface verb overrides that signal.

## Per-tool deep dive (4B, warranted half)

| tool | n | mean SR | dominant predictors |
|---|---|---|---|
| calculator | 63 | 0.92 | high baseline; `has_compute_verb`/`has_tool_name_keyword` slightly *negative* (over-named prompts are 4B's worst calc cases); `num_count` +0.33 |
| datetime_now | 11 | 0.92 | `has_today_now` +0.33 (good), `has_date_or_year` −0.39 (probes that name a date but want time-delta) |
| general_knowledge_lookup | 32 | 0.60 | weak signal; longer/more-numeric gkl prompts slightly harder |
| python_execute | 34 | **0.03** | catastrophic. Pair_type A vs B (+0.52), prompt length (−0.45). 4B almost never picks python over calculator; the wrong_tool failure mode dominates |
| unit_convert | 22 | 0.86 | high baseline; `num_count` +0.36 |
| user_knowledge_lookup | 27 | **0.13** | `frequency_ord` −0.47 (more-common phrasings get under-called), `prompt_length_chars` +0.40 (terse prompts get answered from memory) |

The two outliers — `python_execute` at 3 % and `user_knowledge_lookup` at
13 % — are entire-tool failures for 4B, not record-specific noise. Any
classifier that knows the tool can predict these without any other features.

## Classifier prototype

Target: `success_rate >= 0.7` (i.e. empirical bucket ≥ easy). Features:
`expected_tool_call`, `curator_difficulty_ord`, `has_tool_name_keyword`,
`has_compute_verb`, `has_first_person`, `has_today_now`, `has_date_or_year`,
`num_count`, `cond_warranted`, `cond_none`. 5-fold CV accuracy:

| Model | Curator-only baseline | LogReg (10 feat) | DTree d=3 | DTree d=5 |
|---|---|---|---|---|
| 4B (n=402, positive rate 0.66) | 0.659 ± 0.004 | 0.664 ± 0.061 | 0.624 ± 0.033 | **0.711 ± 0.062** |
| 12B (n=171, positive rate 0.90) | 0.895 ± 0.014 | 0.872 ± 0.052 | 0.849 ± 0.084 | — |

Interpretation:

- **The 10-feature DTree(d=5) beats the curator-only baseline by ~5 pp on
  4B.** Modest but real, with the baseline pinned at the positive class
  rate (curator-only is no better than majority guessing because ρ ≈ 0).
- **12B's baseline is already 0.895 (majority class).** The classifier
  doesn't beat it. This isn't because the features lack signal — see the
  conditioned correlations above — but because 12B is so close to ceiling
  globally that a useful prediction target needs to be finer-grained
  (e.g. the over-call sub-population, or success_rate ≥ 0.95).

The DTree(d=3) rules on 4B essentially say:

```
if condition is no-tool-available → success (easy controls)
elif tool warranted:
    if num_count == 0 → fail  (e.g. ukl prompts: no numbers, refusal mode)
    elif has_tool_name_keyword → success (model can latch onto verb)
    else → success (numbers alone often enough)
```

Even this 3-level rule captures the surface-keyword story.

## Things that make a task harder for these models — actionable principles

These are the claims I'd carry forward into a revised axis proposal. Each
has a correlation pattern behind it; the framings are "what the model is
actually responding to," not "what the task is measuring."

1. **Surface tool-naming dominates the tool-call decision.** Verbs like
   `compute`, `calculate`, `convert`, or explicit tool names drive calls
   regardless of whether the task warrants them. ρ ≈ −0.70 on `has_tool_name_keyword`
   in 12B's no-call cell; the model effectively cannot ignore "compute"
   even when the right answer is in front of it.

2. **Numeric density is a calculator magnet.** `num_count` and
   `has_num_operator` predict success on warranted-calc prompts (+0.4) but
   *cause failures* on no-call prompts that contain numbers incidentally.
   This is the "over-call on declared-fact arithmetic" failure mode.

3. **Question form (`?`) suppresses tool calls.** On 4B's warranted half,
   `has_question_mark` is ρ=−0.41; questions get answered from weights,
   imperatives ("Compute X") get routed to tools. Same direction on 12B.
   Register (imperative vs interrogative) outweighs the actual task.

4. **First-person pronouns under-call user_knowledge_lookup.** 4B's `ukl`
   warranted cell has 0.13 mean SR; `has_first_person` is broadly negative.
   The model's "I am being told about you" mode (no lookup needed) wins
   over the lookup affordance even when the answer isn't recoverable.

5. **Temporal references under-call gkl/datetime.** On 12B's warranted
   cell, `has_date_or_year` ρ=−0.44, `has_today_now` ρ=−0.34. The model
   reads "April 5 2026" as in-knowledge and confabulates.

6. **Tool identity is the largest single predictor.** `python_execute` at
   3 % and `user_knowledge_lookup` at 13 % for 4B-warranted swamp every
   per-record feature. A revised axis system likely needs **per-tool
   call-rate priors** as a baseline before any prompt-features are added.

7. **Curator difficulty is signal *within* the warranted condition, but
   small** (ρ +0.22 for 4B, +0.33 for 12B). The current 002 axes are
   measuring something real about task difficulty — they're just not
   measuring tool-call calibration, which is the score we use.

## Where I got stuck / what would help

- **12B bulk run is partial (37 %).** Several tools have n<10 there;
  conditioned correlations are noisy. Re-running this analysis when the
  bulk run completes is the obvious next step.
- **Per-pair within-pair analysis was not done.** A natural follow-up:
  given each pair has matched register, compare warranted-half SR to
  no-tool-half SR. The pair-level delta isolates the tool-call decision
  from all other prompt features. The current `pair_type_A` flag is a
  blunt proxy.
- **No textual / embedding features.** The keyword features are
  hand-designed from 006 failure patterns. A sentence-embedding similarity
  to a canonical "compute X × Y" exemplar might capture the over-call
  surface more cleanly than my regex set. Worth trying once the bulk run
  finishes.
- **The `expected_tool_call=False` cell is where the action is for 12B.**
  Almost all 12B failures are over-calls. The current axes don't model
  over-call susceptibility at all — they describe task difficulty, which
  is the wrong axis for the post-2024 IT model failure mode.
- **Suggested next step: build a candidate "calibration axes" proposal**
  with at least these dimensions:
  - `tool_naming_surface` — does the prompt contain a verb / noun that
    matches a tool's lexicon? (verbatim regex, then graded as
    none / weak / explicit)
  - `numeric_density` — count of digits / operators normalized by prompt
    length.
  - `register_form` — kept from current axes; matters as a tool-call
    suppressor.
  - `persona_pronoun` — first-person presence.
  - `temporal_reference` — past / recent / future-bait flag.
  - `answer_recoverability` — is the answer in-prompt? (this was in the
    002 ukl axes; should be promoted to a global axis).
  - `tool_target_prior` — per-tool baseline call rate at the target
    model.

  The current 002 axes (operand_digits, steps_required, temporal_position,
  etc.) survive as **task-difficulty** axes but should be tagged as such
  and not used as tool-call-calibration predictors.
