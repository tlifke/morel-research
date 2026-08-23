# Implementation brief — inv 007 comparison metrics

For an agent picking this up cold. Read `investigation.md` first (the six
decisions), then `../../reviews/scoring-methodology-verification.md` (what was
verified against source), then this.

**Everything below that is a decision has already been made by Tyler. Do not
re-litigate it. The open rulings are listed at the end and are his, not yours.**

## What exists

| file | state |
|---|---|
| `harness/comparison_metrics.py` | scorer: schemas, matching, detection/localization, aggregation. **19 tests green** |
| `harness/tests/test_comparison_metrics.py` | the plan's test list plus our decisions |
| `scripts/contracteval_prompt.py` | ContractEval prompt, **byte-verified against upstream by SHA-256** |
| `harness/tests/test_contracteval_prompt.py` | 10 tests, including the hash assertions |
| `scripts/run_contracteval_smoke.py` | Tinker runner, resumable, per-row token accounting |
| `scripts/cuad-baseline/make_split_shards.py` | gained `--all-categories` |

Run tests from the study dir with:
`uv run --with pytest --with pandas --with numpy --with scikit-learn python -m pytest harness/tests/ -q`

The upstream `evaluate.py` import needs `pandas`/`numpy`/`scikit-learn` and
**must run with cwd set to `data/raw`** — `comparison_metrics.upstream()`
handles the chdir; do not bypass it.

## The scoring model, in one paragraph

The task is scored as **two sub-tasks**. **Detection**: is this clause type
present? One 2×2 cell per (contract, category); **F2 is the headline**, F1
reported alongside. **Localization**: given presence, is the text right?
Span-level, on the **TP cell only**, using upstream CUAD's `get_jaccard` at
≥ 0.5 with **many-to-many** matching. Micro and macro both reported.

## Things that will silently corrupt results if you change them

1. **Matching is many-to-many, not one-to-one greedy.** The eval plan said
   greedy; that was overruled (Decision 4). Upstream CUAD, ContractEval, and
   every existing path here are many-to-many, and our Table 2 reproduction
   matches published AUPR to four decimals *because* of it. One-to-one is
   computed as `tp_oto/fp_oto/fn_oto` for sensitivity only — never as headline.
2. **Use upstream `get_jaccard`, never reimplement it.** `harness/metrics.py`
   has `token_f1`, a *different* function (multiset F1 over `[a-z0-9]+`) also
   thresholded at 0.5. The two are not interchangeable. Anything
   CUAD-comparable uses upstream.
3. **The `Parties` substring exception must stay on.** Upstream relaxes to
   `jaccard >= 0.5 OR gold in pred` for Parties, on **raw unnormalized
   strings**, gold-in-pred only. Our two older scoring scripts *drop* it; that
   was harmless at 12 categories (Parties excluded) and is a live bug at 41,
   where Parties is 216 of 951 gold spans on `harness_val` (22.7%).
4. **Localization is TP-cell only, and TP-cell size travels with every
   localization number.** The cell is a different size per system, so the
   scores are not comparable without it.
5. **Never load `test`.** Sealed until G4. The runner and shard builder both
   refuse it; keep those guards.
6. **Do not "fix" prompt-serialized structured output.** Tinker does not
   enforce schemas; conformance comes from the schema being in the prompt.

## DeBERTa's two operating points — say why, correctly

- **F2-optimal** — DeBERTa's best possible showing, chosen because recall is
  the priority. An LLM win against it is *conservative*.
- **Volume-matched** — same prediction count as the LLM arm. This is
  **confound control**, not charity.

**Do not describe volume-matched as "so DeBERTa isn't penalised for emitting
more."** F2-optimal already protects it maximally; volume-matched will score it
at or below that. Getting this backwards invites an obvious objection.

## The ContractEval arm

Faithful reproduction, deliberately. No JSON schema — free text. Prompt is
hash-pinned; if a test fails on those hashes, upstream changed, do not edit the
constants to make it pass.

Their scoring, which we reproduce as a **calibration** metric only
(`contracteval_correct`): TP requires `all(gold_span in raw_response)` — exact
substring, case- and whitespace-sensitive, no partial credit. Declination is
`'no related clause' in output.lower()`, substring-anywhere.

`response_to_spans()` converts their free text into spans for *our* span-level
metric. **This function is invented.** Their metric never splits. It has tests,
but the tests pin the chosen behaviour, they do not validate it. It is the
weakest link in this arm and Tyler has not reviewed it.

## Empirical findings from the smoke run (2026-08-17)

Qwen3.5-9B on Tinker, ContractEval prompt, `separate_reasoning: true`,
temperature 0 (their config is greedy — this **deviates from the study's
temp=1.0/top_p=0.95 default**, deliberately, for fidelity).

- **ContractEval's 5,000-token cap yields empty content on every call.**
  Reasoning consumed 100% of the budget; `content` was `''` 3/3.
- **Removing the cap fixes it only partly.** With ~59.7k tokens of headroom:
  2/3 returned real text; `Document Name` burned the **entire** headroom on
  reasoning (229,583 chars), finished `length`, emitted nothing, and took
  **11.6 minutes**.
- **Cost is high-variance, not fixed.** ~2 min vs 11.6 min per call.
  Reasoning dwarfs output (32k chars reasoning → 1.6k chars content).
- **This is a reportable defect in ContractEval's published numbers.** Any
  thinking model in their 15-model open-source arm would emit empty content
  under their 5,000 cap, scored as FN on gold-positive and FP on gold-empty
  questions — the worst of both. We found it by running their config faithfully.

**Implication for scoring:** empty content must NOT be scored as an absence
claim. See the open ruling below.

## Data locations

- DeBERTa 41-category predictions: **on the desktop only**, at
  `~/Projects/cuad-baseline/out-splits41/{model}/harness_val_g{0..10}/`.
  Deliberately not synced — the Mac is short on storage. 3 models × 11 shards,
  `n_best_size 20` preserved so dedup/truncation stay open downstream.
- Smoke traces: scratchpad only, not yet promoted into `data/traces/`.
- The 5 smoke contracts are length-quintile picks from `harness_val`
  (1,397 → 191,775 chars).

## Open rulings — Tyler's, not yours

1. **Status field for empty/failed generations.** Proposed: an `OutputStatus`
   enum separating `extracted` / `declared_absent` / `parse_failure` /
   `generation_failure`, with detection cells assigned only to the first two.
   Un-ruled. **Until it is ruled, do not let empty content fall through as
   "absent"** — that makes a truncated run look like a cautious one, and it
   biases the LLM arms only, since DeBERTa cannot fail this way.
2. **Dedup threshold and ordering.** 0.8 Jaccard greedy keep-first is
   implemented as the default; the existing analysis scripts disagree on
   whether dedup precedes or follows depth truncation.
3. **Whitespace normalization for the ContractEval arm.** 24 of 951
   `harness_val` gold spans (2.5%) contain a newline or tab — negligible under
   Jaccard, potentially decisive under exact-substring containment.
4. **Whether `response_to_spans()`'s splitting rule is right.**
5. **Whether to bound reasoning** on the ContractEval arm, and whether any such
   bound breaks the fidelity claim.
6. **Pydantic at the persistence boundary** — currently frozen dataclasses.
7. **Generation-schema changes** (`Optional[list[PrincipleId]] = None` instead
   of `default_factory=list`; `PrincipleId` as a closed `Literal`). Blocked on
   G2, since the working set is not locked.

## Working style that this study expects

- Small scale first; case studies before aggregates.
- Deliver comparison artifacts, keep prose light — Tyler reads results himself.
- Return a "things I made up that you should review" list with any draft.
- Re-derive numbers from the artifact, including from prose an earlier agent
  wrote. This repo has a documented history of figures drifting from sources.
