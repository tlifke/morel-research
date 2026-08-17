# HANDOFF — study 008, principled extraction (CUAD)

**Read this first, then `plans/splits.md`, `plans/workstreams.md`,
`plans/comparability-plan.md`, then `plans/decisions.md`.** Updated 2026-08-17.

**Before relying on any data that is not in git, read
`plans/data-inventory.md`** — it records what lives outside the repo, why, and
the exact command to rebuild each piece. The two that matter most: their models'
raw n-best over our splits (45 MB, gitignored, ~1.49 GPU-h to regenerate — the
raw material for exploring alternative scoring methods, logits included), and
their shipped `test`-split predictions, which exist **only on the desktop** and
are re-downloadable from Zenodo record 4599830. Our own trial traces **cannot**
be regenerated at all: Tinker does not honour seeds, so a re-run yields
different data, not the same data.

## What this study is

Does requiring principle citation in structured agent outputs improve task
performance? On CUAD clause extraction, 12-category subset, one decision per
category per contract. Phase 2 is Tinker fine-tuning with a composite
answer+citation reward. Framing and hypotheses in `study.md`.

**C1 is no longer a condition.** It is iteration 0 of the escalation ladder in
inv 006 (D-22, `plans/workstreams.md`). Any hand-written baseline embeds
implicit choices about answer granularity — we measured ourselves accidentally
instructing the model to answer yes/no on nine of twelve targets — so a tuned
C1 would do by hand what this study claims to do by derivation.

## Where things stand

**Done and reported**

- **Dataset** (inv 001). Deterministic rebuild, six frozen splits. See
  `plans/splits.md` for each split's PURPOSE — that is the part that matters.
- **Harness** (`harness/`, study-level code). 213 tests. CUAD environment built;
  three Tinker backends measured; trace store tier-1.
- **Review app** (`apps/principle-review/`). 47 tests. Two record types, four
  sidecars. Nothing is currently serving; check before binding 8823.
- **Principle pilot** (inv 002). Two derivation arms, two curation rounds with
  calibration controls, nine-principle working set at
  `principles/working_set.yaml`.
- **Applicability** (`principles/applicability/`). 4,498 labels, frozen,
  `gold_visibility: none`. Citation metrics are now measurable.
- **C2 vs C3 on answer metrics** — the study's first experiment. **A clean null.**
- **CUAD baseline** — Table 2 reproduced exactly; their models run on our
  non-`test` splits as a diagnostic.

**Not started**

- inv 003 (largely superseded by D-27/D-31), inv 004 (pilot P0), inv 005 (the
  grid), inv 006 (the ladder — **deliberately deferred, see below**).

**Blocked / gated**

- Everything on `test` waits for gate G4.
- G1 (freeze splits) and G2 (lock the principle set) need Tyler's sign-off.

## The results so far, in one place

1. **Requiring citation does not change what the model extracts** (D-28, D-32).
   240 trials, Qwen3.5-9B, paired over a 38-contract intersection. Every
   accuracy CI contains zero; the headline micro-F1 contrast is +0.0230
   [−0.0102, +0.0578]. The manipulation demonstrably took — C2 cited on 0 of
   1,260 decisions, C3 on 1,077 of 1,200. **A null effect, not a null
   treatment.**
2. **Two things did move**: verbatim exact rate −2.5 pts, and +627 completion
   tokens for a +48-token prompt delta.
3. **Truncation is condition-dependent and counter-intuitive** — 4 of 240, all
   C3, three on the *shortest* contracts.
4. **Declared `scope` does not constrain citation** (D-29). `w06` is scoped to
   Agreement Date and is named in 43 of 63 false-absents on *Expiration Date*.
5. **Citation frequency does not track principle quality** (D-28). The
   most-cited records include one firing on 1 of 480 decisions and one with no
   measured footprint at all.
6. **The Expiration Date convention is real and learnable** (D-33). Their three
   models score 0.89–1.00 duration recall where we score 0.00–0.02.
7. **Our 12-category subset is the easy end of CUAD** (D-34). DeBERTa averages
   AUPR 0.608 on our subset against 0.393 on the excluded 29. **Every absolute
   number this study has produced is flattered by the subset choice.** Tyler's
   position: a caveat on absolute figures, not a blocker, since expanding is
   planned anyway.
8. **CUAD's published AUPR is slightly depressed by their own windowing**
   (`reviews/logprobs-and-nbest-depth.md`). Deduplicating their n-best gains
   ~+1 pp. An architectural artifact reaching a published number.

**Two unexplained items — do not build on them until resolved.** Our recomputed
per-category AUPR ordering diverges from the paper's (Spearman ρ = 0.861) while
pooled Table 2 reproduces to four decimals. And D-33's claim that our Governing
Law false positives are venue/arbitration clauses is **not established** — all
of them fall on gold-*present* questions, so it is a boundary failure, not
over-claiming.

## Decisions not to silently reverse

All in `plans/decisions.md` with reasoning. Most likely to be undone by
accident:

- **D-2** full contracts, never truncated or chunked.
- **D-4** no LLM judge in the scoring path. Departs from this repo's usual
  pattern deliberately.
- **D-14** one decision per target, always.
- **D-16** repair off, so the parse-failure rate by stage *is* the unassisted
  conformance measurement.
- **D-21** compliance must be separable from correctness. A checker may read
  gold; it must not gate on the answer of the decision being scored.
- **D-22** principles selected by measured effect, not judged truth.
- **D-24 / D-27** applicability may be LLM-labelled — a labelling tool, not a
  judge. Our pipeline goes further and reads no gold at all.
- **D-30 / D-32** CUAD's own scorer is the headline metric; the aggregate is
  **micro-F1 at our operating point** — because that is what our *current*
  output supports, **not** because nothing else is possible. An earlier version
  of this line said AUPR and P@80%R were "unavailable by construction". That was
  **wrong**: AUPR needs a scored ranking, and our lack of one is a design choice
  in the output contract. Both are obtainable — see the comparability section
  below.
- **D-31** applicability has measurable *reliability* and unestablishable
  *validity*. Citation numbers are relative, never absolute.

## The comparability work — resolved, and ready to build

`plans/comparability-plan.md` is the document; it now carries answers, not open
questions, for its two hardest parts.

- **Teacher-forced candidate scoring works**, verified live:
  `SamplingClient.compute_logprobs(prompt)` in the **native** Tinker SDK scores
  arbitrary supplied tokens. **Not reachable through our OAI shim** — all four
  routes measured closed — so this needs a second backend path, and the two
  surfaces are disjoint (`separate_reasoning` does not exist natively). Prefix
  caching makes it cheap.
- **k = 10 deduplicated spans**, not 20. Rank 1 satisfies 88% of recoverable
  *questions*, but their recall denominator is gold **spans**, so depth 1 caps
  span recall at 47% and costs 38% of AUPR. ~60% of their candidates are
  near-duplicates — ~40% of their depth is the 512-token encoder.
- **Length normalisation must be settled before any AUPR is computed.** Sum and
  mean logprob ranked a correct span and a longer superset in *opposite* orders.
- **Sequence-logprob-of-the-span is unimplementable** on the shim: under
  `separate_reasoning` the returned logprobs cover reasoning tokens, not
  content.
- **A ruling is needed against D-14.** k=1 is indefensible on their axes, so the
  committed decision and the ranked shortlist should be **two fields**, not one
  field doing both. D-14 fixes exactly one decision per target; a shortlist is
  not that. Settle it deliberately rather than letting the schema drift.

Tyler's framing, which organises the whole plan: **their windowing is an
architectural artifact of a 512-token encoder; their ranking is a genuine
design choice.** Copy the second, not the first.

## What the next session should probably do

**Tyler deferred the ladder deliberately** — inv 006 needs a rethink of how
principles are derived and validated, not a selection loop bolted onto the
existing pool. Note is in
`investigations/006-empirical-principle-selection/investigation.md`. The
evidence:

- 9 of 10 working-set principles have unusable checkers.
- Scope-based reasoning about candidates was unsound (D-29).
- Citation frequency does not track quality (D-28).
- Principles conflict in pairs: `w11` vs `w06`, `w11` vs `w01` (D-33).
- **The strongest candidate in the study, `w11`, came from diagnosing a
  failure — not from either derivation arm.** That is a fourth derivation route
  neither arm covers, and it is the open question for that session.

Ready when the rethink lands: `w11` is drafted in
`reviews/expiration-date-diagnosis.md` (**not** added to the working set),
`w01`'s date exception needs narrowing to Agreement Date, and `w03` is in the
prompt and demonstrably not being applied.

## Conventions specific to this study

- **`uv run` for everything.** Agents were told not to edit the root
  `pyproject.toml`; deps go via `uv run --with`. Consolidating them is
  outstanding tidy-up.
- **Human-facing HTML lives in the repo**, under `reviews/` or the study root —
  never a hosted artifact.
- **Figures**: Plotly with `morel-branding`, source script and PNG both checked
  in, figure data separate from rendering code.
- **The Atticus Labeling Handbook** (`assets/`) is copyrighted, paywalled,
  non-redistributable, gitignored. **Paraphrase only.** CUAD itself is CC BY 4.0;
  cite `hendrycks2021cuad`.
- **Never load `test`** outside G4.
- **Cost is tracked** per session in `study.md`. 2026-08-16 was $5.49.

## Traps that already cost time

- **Seeds are not honoured on Tinker.** A seed is a repetition label. The trace
  store is the only record of what was sampled.
- **Structured output is not enforced on Tinker** — verified against controls.
  Conformance is nonetheless good because the schema is serialised into the
  prompt. Do not "fix" that.
- **`separate_reasoning` must be sent explicitly**; its default flipped in June
  2026.
- **Title-based split disjointness is insufficient** — identical content is
  filed under different titles. A content-hash and cross-split containment
  assertion runs in `build_dataset.py`. Re-run after any split change.
- **The `<omitted>` marker does not exist in CUAD v1.**
- **`evaluate.py` must run with cwd set to `data/raw`** — it reads
  `category_descriptions.csv` at module scope.
- **Cache-key collision in their pipeline**: `cached_dev_{model}_{seq_len}`
  omits the predict file, so a per-category loop sharing one `--cache_dir`
  silently scores every shard against shard one's features.
- **Numbers drift between prose and their sources.** The 4-chars/token figure,
  a swapped-direction contamination claim, an "identical recall" that was
  coincidence, and two different quantities both called "macro" all survived
  several documents before being caught. **Re-derive from the artifact,
  including from prose written by an earlier agent.**

## Working style that produced good results

- **Dispatch agents blind and independently when their outputs will be
  compared.** The cross-source, critique, and footprint passes converged on the
  same disqualifications, and that convergence is reportable corroboration.
- **Ask for a "things I made up that Tyler should review" list.** Most of the
  session's real catches came from those sections.
- **Chase the near-significant result.** The one apparent effect in the study —
  a precision gain — died on a stability check showing the conclusion flipped
  with the RNG seed.
- **Committing while agents are mid-write sweeps partial state.** It happened
  repeatedly and was harmless; it will not always be.
- Tyler reads results himself. Deliver comparison artifacts; keep prose light.

## Open for Tyler, not for an agent

- G1 (freeze splits) and G2 (lock the principle set).
- Whether to email The Atticus Project for permission to quote the Handbook
  verbatim — paraphrase may shift disambiguation rules, an unmeasured confound.
- Which gold-defect classes count toward the published noise floor (three
  unruled; both figures reported meanwhile).
- The final ~12-category subset. Dropping Source Code Escrow would resolve both
  its untestability (n=5 in `principle_train`) and its Phase-2 coverage problem
  (2 positives in `model_train`).
- The frontier-model arm.
