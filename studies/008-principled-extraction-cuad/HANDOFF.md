# HANDOFF — study 008, principled extraction (CUAD)

**Read this first, then `plans/workstreams.md`, then `plans/decisions.md`.**
Written 2026-08-16 at the end of the session that built the study.

## Live state — the one thing you can break

**A review app is running on `http://127.0.0.1:8823` and Tyler is working
through a 23-record queue in it.**

- Do **not** kill, restart, or rebind that process. Do not touch its database
  at `apps/principle-review/state/`.
- **The exported YAML is the durable record; SQLite is a cache.** Export before
  any restart. A previous session lost a completed round of decisions because a
  database disappeared and an export ran against the empty queue, overwriting
  the good file. Both failure modes are now guarded, but the ordering rule
  stands.
- Round-2 export target:
  `principles/pilot/round2/candidates_round2.reviewed.yaml`.
- When Tyler finishes, **score the calibration controls** against
  `principles/pilot/round2_key.yaml` (gitignored — see Blinding below).

## What this study is

Does requiring principle citation in structured agent outputs improve task
performance? C1 (task definition only) / C2 (+ principles) / C3 (+ required
citation), on CUAD clause extraction. Phase 2 is Tinker fine-tuning with a
composite answer+citation reward. Full framing in `study.md`; hypotheses H1–H5
there.

## Where things actually stand

**Built and working**

- **Dataset** (inv 001, complete pending G1). Deterministic rebuild, six
  frozen splits — see `plans/splits.md` for each one's PURPOSE, which is the
  part that matters: test 102 / harness_val 40 / principle_train 60 /
  principle_val 40 / model_train 264 / scratch 4. These are the conventional
  names adopted on 2026-08-16; the old ones (`holdout` / `dev` / `selection` /
  `confirmation` / `ft_train` / `excluded`) still appear in records written
  before that date — the mapping is in `plans/splits.md`.
- **Harness** (`harness/`, study-level code, not an investigation). 190 tests.
  Three Tinker backends measured and working; ollama backend built and
  mock-tested, blocked on the desktop being offline. Trace store is tier-1.
- **Review app** (`apps/principle-review/`). 47 tests. Generic over record
  type: `principle` and `gold_audit`. Four sidecars: pairs, footprint,
  cross_source, critiques.
- **Principle pilot** (inv 002). 16 candidates from two independent arms,
  round-1 curation done, round-2 queue live with three evidence passes.

**Not started**

- inv 003 applicability ground truth, inv 004 pilot P0, inv 005 the Phase-1
  grid, inv 006 empirical principle selection (just scoped).

**Blocked**

- ollama / desktop GPU is offline. `harness/scripts/probe_ollama.py` runs the
  moment it returns and **must** be run before trusting any local
  `infeasible_at_length` result.

## Decisions you should not silently reverse

All in `plans/decisions.md` with reasoning. The ones most likely to be
undone by accident:

- **D-2** full contracts, never truncated or chunked; over-context trials are
  recorded as `infeasible_at_length`, never dropped.
- **D-4** no LLM judge anywhere in the scoring path, either phase. This departs
  from the multi-judge pattern used elsewhere in this repo, deliberately: a
  judge would contaminate the Phase-2 reward and concede the paper's claim.
- **D-14** one decision per target, always — 12 per contract. Keeps the
  citation denominator stable across models.
- **D-15** gold is left uncorrected; the noise floor is measured instead.
- **D-16** repair is off (`max_repair_attempts = 0`). The machinery is intact
  and tested so re-enabling is a config change. With repair off, the
  parse-failure rate broken down by stage *is* the clean unassisted conformance
  measurement.
- **D-21** compliance must be separable from correctness. A checker may read
  gold; it must not gate on the answer of the decision being scored.
- **D-22** principles are selected by measured effect, not judged truth
  (inv 006).

## Blinding — active experiment, do not break it

A calibration-control instrument is **live**. Seven of the 23 round-2 records
are deliberately-wrong controls.

- `principles/pilot/controls.yaml`, `controls_key.yaml`, `round2_key.yaml` are
  **untracked and gitignored**. Tyler reads this repo; blinding cannot rest on
  his discipline.
- Do not name, quote, or identify any control to him, and do not summarise
  per-record verdicts from the evidence artifacts. He adjudicates the evidence;
  a pre-digested reading makes the round measure the summariser instead.
- Known limitation, already recorded: he was told the control count and the
  failure-mode taxonomy in conversation before the round ran. Identity is still
  blind. Read catch rate alongside false-alarm rate on real candidates.
- Restore the key files to git **after** scoring — the key is part of the
  methodological record.

## Conventions specific to this study

- **`uv run` for everything.** Agents were told not to edit the root
  `pyproject.toml`; deps were passed with `uv run --with`. Consolidating them is
  outstanding tidy-up (`transformers`, `tokenizers`, `pytest`).
- **Human-facing HTML goes in the repo**, under `reviews/` or the study root —
  never a hosted artifact. Existing: `overview.html`,
  `reviews/sample-contracts.html`, `reviews/derivation-pipeline.html`,
  `reviews/structured-output-evidence.html`.
- **Figures**: Plotly with the `morel-branding` skill, source script and PNG
  both checked in, figure data separate from rendering code.
- **The Atticus Labeling Handbook** (`assets/`) is copyrighted, paywalled and
  non-redistributable. Gitignored. **Paraphrase only — never quote it
  verbatim** into prompts, principles, or the writeup. CUAD itself is CC BY 4.0
  and quotable; cite `hendrycks2021cuad`.
- **Never load the `test` split** outside gate G4. Several agents were given read access
  for contamination checks only.

## Traps that already cost time

- **Seeds are not honoured on Tinker.** A seed is a repetition label, not a
  reproducibility handle. The trace store is the only record of what was
  sampled.
- **Structured output is not enforced on Tinker.** Verified against controls,
  not inferred — see `reviews/structured-output-evidence.html`. Conformance is
  nonetheless good when the schema is serialised into the prompt as
  `prompts.py` already does it. Do not "fix" that serialisation.
- **`separate_reasoning` must be sent explicitly.** Its default flipped in June
  2026; another flip would silently move reasoning into `content` and corrupt
  every parse.
- **Title-based split disjointness is not enough.** Identical contract content
  is filed under different titles; a content-hash and cross-split containment
  assertion runs in `build_dataset.py`. Re-run it after any split change.
- **The `<omitted>` marker does not exist in CUAD v1.** The Handbook describes
  Atticus's internal tool; the public release stores annotations as contiguous
  ranges, so multi-fragment annotations arrive as separate spans.
- **Numbers drift between human-readable intermediates and their sources.**
  Both the 4-chars/token figure and a swapped-direction contamination claim
  survived several documents before being caught. Re-derive from the artifact,
  not from prose — including prose written by an earlier agent.

## Working style that produced good results here

- **Dispatch agents blind and independently when their outputs will be
  compared.** The cross-source, critique, and footprint passes each caught
  things the others missed, and their convergence is reportable corroboration.
  Contaminating them would have destroyed that.
- **Ask for a "things I made up that Tyler should review" list.** Most of the
  session's real catches came from those sections.
- **Commit while agents are mid-write and you will sweep partial state.** It
  happened repeatedly. It was harmless here; it will not always be.
- Tyler wants to read results himself. Deliver comparison artifacts and keep
  prose light and non-load-bearing.

## Open questions for Tyler, not for you to decide

- G1 sign-off freezing the splits; G2 principle-set lock.
- Whether to email The Atticus Project for research-use permission to quote the
  Handbook verbatim (paraphrase may shift disambiguation rules, which is an
  unmeasured confound in the guidelines arm).
- Which gold-defect classes count toward the published noise floor (three are
  unruled; both figures are reported meanwhile).
- The final ~12-category subset and the frontier-model arm.
