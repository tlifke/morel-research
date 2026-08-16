# Workstream plan — study 008

Derived from the reference plan v2 (2026-08-15). This file is the sequencing
and acceptance-criteria index; each workstream's running record lives in its
investigation.md (or, for WS5, in `component-contracts.md`).

## Map: plan workstream → repo unit

| WS | Repo unit | Blocks |
|---|---|---|
| WS1 dataset | `investigations/001-dataset-and-splits` | everything |
| WS2 principles | `investigations/002-principle-derivation` | WS3, WS4, WS5 prompts |
| WS3 applicability GT | `investigations/003-applicability-ground-truth` | WS5 grid scoring |
| WS4 pilot P0 | `investigations/004-schema-leakage-pilot` | main grid |
| WS5 harness | `harness/` + `plans/component-contracts.md` | WS4, main grid |
| main grid | `investigations/005-phase1-condition-grid` | Phase 2 |

## Sequencing

```
WS1 ──┬──► WS2(draft) ──┬──► WS4 (P0) ──► WS5 grid (inv 005) ──► Phase 2
      └──► WS5(build) ──┘        │
                                 └──► WS3 (parallel with WS4)
```

WS2 and WS5 run in parallel once WS1 lands. WS4 needs WS1 + a *draft* principle
set + a working harness — P0 tests schema behavior, not principle quality, so a
non-curated candidate set is acceptable input. WS3 runs alongside WS4 and must
finish before inv 005 can score compliance or citation.

## Gates

Each gate is a stop-and-check with Tyler, not a self-certified pass.

- **G1 (after WS1)** — category subset provisional, split files frozen and
  seeded. Nothing downstream may resample splits.
  **Scope note (2026-08-15):** inv 001 raised open calls that would *change* the
  splits — chiefly whether harness_val should be re-stratified to test's length
  profile rather than its own pool's. Those are decided **at** G1, before the
  freeze, not after it. G1 is the last moment splits are cheap to change; every
  other question inv 001 raised (rare-category redundancy, the Uncapped
  Liability alternate) belongs to the G2 subset decision and does not require
  unfreezing anything, because the manifest carries all 41 categories.
- **G2 (after WS2)** — Tyler curates the principle set. Nothing enters the
  scored set without a feasible checker/labeling plan. Locked before WS3
  implements checkers.
- **G3 (after WS4)** — the schema decision, made from data per the P0 decision
  rule. Written into `plans/decisions.md`.
- **G4 (before inv 005 touches test)** — the official test split (102
  contracts) is untouched until this gate. harness_val-set iteration only before it.

## Where the human is needed

Two kinds of dependency, and they behave differently:

- **Blocking (serial, Tyler is the critical path)** — work stops until he acts.
- **Unblocking-later (batchable)** — Claude proceeds on an assumption, Tyler's
  answer lands before the artifact is used downstream.

| # | Ask | Kind | Blocks | Rough size |
|---|---|---|---|---|
| H1 | Confirm inkling-small on Tinker (availability + context window); name the ~8B / ~32B / frontier picks | blocking for WS4 only | inv 004 | minutes, but needs Tinker access |
| H2 | Sign off on the provisional ~12-category subset (G1) | unblocking-later | freezes at G2 | ~30 min |
| H3 | Read + curate the candidate principle set (G2) | **blocking, the big one** | WS3 entirely, WS5 prompts | hours; 15–25 records with rationales |
| H4 | Adjudicate the manual applicability residual (WS3) | **blocking, the long one** | inv 005 scoring | the study's largest human cost — size it before committing |
| H5 | Ratify the P0 schema decision (G3) | blocking | main grid | ~15 min, rule is pre-written |
| H6 | Open the test (G4) | blocking | inv 005 | a deliberate go/no-go |
| H7 | One-pager prose | blocking by policy | publication | — |

H3 and H4 are the study's real human cost. H4 in particular scales with
(n principles × n instances × decisions per instance), so the first thing inv
003 should produce is a **cost estimate on a 3-contract sample**, before the
full labeling flow is committed to.

## Parallelization

**Track A (data)** — WS1 → the pair-mining half of WS2 → nothing else blocked.
**Track B (code)** — WS5 harness, buildable against the interface spec in
`component-contracts.md` from day one, with a fake environment. It does not
need real CUAD data to exist. Backends are pluggable and **two are tested
separately**: qwen3.5:8b on the desktop RTX 3080 via ollama, and inkling-small
via Tinker. A third (frontier API) comes later; the interface is the
deliverable, the two implementations are the proof it generalizes.
**Track C (principles)** — WS2 reading + drafting, then Tyler's G2 curation,
then WS3 checkers.

A and B are fully independent and should start together. C starts when A
lands the model_train split (pair mining needs it), but the guidelines-reading
half of C is independent of everything and can start immediately.

The join point is WS4/P0: it needs A (harness_val contracts) + B (working runner) + a
*draft* of C. WS3 then runs in parallel with WS4 — P0 doesn't need
applicability labels, only inv 005 does.

**Sequencing risk to watch:** WS5's prompt templates encode the principle set's
shape, and WS3's checkers encode its content. If G2 slips, both stall. Mitigate
by having WS5 take the principle set as data (never hardcoded) and by having
WS2 lock a *small* provisional set early enough to unblock P0, accepting that
the locked set may grow before inv 005.

## Standing constraints

- **Full dataset, no length filtering, no chunking.** A contract that exceeds a
  model's context is recorded as `infeasible_at_length` — a first-class result
  for H5, never a silent truncation or a dropped row.
- **All primary metrics reported by length bucket.** Reference distribution
  (official test set, **measured** by inv 001 with the Qwen3 tokenizer):
  median 25,657 chars / 5,440 tokens; 37 contracts ≤4k tokens, 66 ≤8k, 83 ≤16k,
  max 64,640.
  The earlier planning figures (≈6.4k median tokens; 27 / 63 / 79; max ~75k)
  came from a 4-chars-per-token heuristic and are **retired** — CUAD contract
  text runs at 4.70 chars/token, so the heuristic overstated length by ~18%.
  Character figures were correct. Re-derive any feasibility planning against a
  context window from the measured column.
- **≥30–50 instances per cell where feasible; ≥3 sampled runs per instance at
  temp ~0.7; report CIs.**
- **No LLM judge anywhere in the scoring path.** Programmatic or hand-labeled.
- **Contamination note travels with every result table**: CUAD is public and in
  pretraining corpora. Condition *comparisons* are valid (shared
  contamination); absolute numbers are not leaderboard-comparable.
- **Tinker-first scope guard**: if a subproblem doesn't advance Tinker usage or
  the core question, cut it.

## Per-workstream acceptance

### WS1 — dataset and splits (inv 001)
Deterministic rebuild from the upstream Atticus repo; per-instance gold
loadable through the env interface; length-distribution table reproduced;
harness_val/model_train/test disjoint and seeded; manifest + summary stats emitted.

### WS2 — principle derivation (inv 002)
15–25 candidate `Principle` records including 3–5 deliberately rare ones, each
with provenance and a proposed gold-applicability checker sketch. Sources in
priority order: Atticus annotation guidelines PDF, literature confusions
(Savelka 2023 trio), contrastive data mining on the train split. Nothing
CUAD-specific leaks into the `Principle` model itself.

### WS3 — applicability ground truth (inv 003)
Every scored principle has applicability labels over harness_val + test. Each
checker classified fully-programmatic / heuristic-needs-spot-check / manual.
Spot-check agreement measured on a sample of the programmatic ones and
documented.

### WS4 — pilot P0 (inv 004)
2 schema variants × 2 conditions (C1, C2) × ~12 harness_val contracts spanning the
length range × 3 seeds. Deliverable: leakage rates (including text-field scan
for migrated principle references), answer-score deltas, and the schema
decision with the data behind it.

### WS5 — harness (`harness/`)
Env interface, C1/C2/C3 prompt templates from a single source of truth, trial
runner, structured-output parsing with a bounded repair policy, metrics module,
results store. Contract detail in `component-contracts.md`. Acceptance: P0 runs
end-to-end through it, and a second environment could be added by supplying
only (a)–(g) of the env interface.

### inv 005 — Phase 1 condition grid
C1/C2/C3 × {~8B, ~32B, frontier} × official test split × ≥3 seeds. Reports
answer score, compliance, citation P/R/F1, and the causal chain
principles → compliance → success, all length-stratified.
