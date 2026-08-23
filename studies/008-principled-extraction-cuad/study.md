---
id: studies/008-principled-extraction-cuad
title: Principled extraction (CUAD) — does citation improve performance?
status: planned
parents: []
children:
  - studies/008-principled-extraction-cuad/investigations/001-dataset-and-splits
  - studies/008-principled-extraction-cuad/investigations/002-principle-derivation
  - studies/008-principled-extraction-cuad/investigations/003-applicability-ground-truth
  - studies/008-principled-extraction-cuad/investigations/004-schema-leakage-pilot
  - studies/008-principled-extraction-cuad/investigations/005-phase1-condition-grid
  - studies/008-principled-extraction-cuad/investigations/006-empirical-principle-selection
  - studies/008-principled-extraction-cuad/investigations/007-comparison-metrics
  - studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop
related: []
axes:
  llm_capability: medium
  human_capability: high
tags: [cuad, citation, principles, tinker, extraction, rl]
created: 2026-08-15
updated: 2026-08-15
---

# Study 8 — Principled extraction (CUAD)

## Question

Does requiring principle citation in structured agent outputs improve task
performance?

An agent performs a task governed by an explicit set of principles ("business
logic"). Phase 1 compares three inference-time conditions (no principles /
principles / principles + required citation) on CUAD clause extraction. Phase 2
fine-tunes on Tinker with a composite reward over answer correctness and
citation correctness.

## Why this study

_To be populated by the human._

Working framing carried over from the plan: *making process supervision
verifiable by constraining the process vocabulary.*

## Hypotheses

Verbatim from the reference plan (v2, 2026-08-15):

- **H1 (performance)** — providing principles improves task success; requiring
  citation improves it further by forcing deliberation at decision points.
- **H2 (generalizability, Phase 2)** — composite-reward fine-tuning generalizes
  better than answer-only reward, including to held-out/edited principles.
- **H3 (small-model leverage)** — explicit principles + citation lets small
  models match or beat frontier models on business-logic-dominated tasks.
- **H4 (diagnostics)** — citation errors form an interpretable confusion
  structure over principles, enabling maintenance of the principle set itself.
- **H5 (failure characterization)** — system failure modes are measurable and
  attributable, notably small-model degradation with contract length.

## Investigations

- `001-dataset-and-splits` — WS1. CUAD → instance records, category subset,
  harness_val/model_train/test splits. **planned**
- `002-principle-derivation` — WS2. 15–25 candidate `Principle` records with
  checker sketches and provenance. **planned**
- `003-applicability-ground-truth` — WS3. Implement checkers, label the
  manual residual, measure reliability. **planned**
- `004-schema-leakage-pilot` — WS4 / pilot P0. Field-present vs field-absent
  schema × C1/C2. Blocks the main grid. **planned**
- `005-phase1-condition-grid` — the C1/C2/C3 × model × length grid on the
  official test split. **planned**
- `006-empirical-principle-selection` — select principles by measured effect on
  task performance rather than by human judgement of their truth. Opened
  2026-08-16 after the curation pilot showed a non-expert curator cannot
  reliably judge substantive quality. Does **not** change C1/C2/C3; changes how
  the set entering C2 and C3 is built. **planned**
- `007-comparison-metrics` — decides and justifies the scoring methodology for
  comparing three systems with incompatible output contracts (finetuned
  DeBERTa-xlarge, ContractEval-prompted Qwen3.5-9B, principles-based
  Qwen3.5-9B). Opened 2026-08-17. The task is scored as **detection** (2×2
  confusion per (contract, category); **F2 headline**, F1 reported) plus
  **localization** (span quality on the TP cell). DeBERTa's free threshold is
  reported at two operating points — F2-optimal and volume-matched — for two
  distinct reasons that must not be conflated. **This investigation is the
  citable source for every comparison number the study reports, and for the
  Phase-2 reward decomposition.** **in-progress**

The harness (WS5) is **not** an investigation. It is shared study-level code at
`harness/`, specified in `plans/component-contracts.md`, consumed by 004 and
005 and by any later environment (AbstentionBench, Terminal-Bench).

Phase 2 (Tinker SFT + RL) is deliberately unscheduled; it opens only after 005
returns results. Outline in `plans/phase2-outline.md`.

## Repository policy

Deviates from the repo default. Decided 2026-08-15:

**In git**
- The deterministic build script and the resulting **instance manifest**
  (contract_id, title, n_chars, n_tokens, split, per-category gold span
  offsets + `is_impossible` flags). No full contract text.
- The principle set (`principles/*.yaml`), checker implementations, and the
  applicability label files over harness_val + test.
- Per-trial **scored records** as JSONL: one row per
  (instance, condition, model, seed, schema_variant) with parsed decisions,
  scores, compliance results, citation P/R/F1, and outcome status
  (`ok | parse_failure | infeasible_at_length`).
- Prompt templates, config, figures + their source scripts.

**Not in git** (`.gitignore`d under `studies/008-.../data/raw/` and
`.../data/responses/`)
- The cloned Atticus CUAD repo and its raw JSONs (rebuildable from upstream).
- Full contract text.
- Raw model responses (kept locally; the scored records are the audit trail).

**Attribution.** CUAD is licensed CC BY 4.0. Any checked-in derivative (the
instance manifest, category definitions quoted in prompt templates, principle
statements traced to the guidelines) carries an attribution line crediting The
Atticus Project, and the study's one-pager cites the CUAD paper. This is a
license obligation, not a courtesy.

Rationale: H5 claims are length-stratified and must be auditable from the repo
alone, which the scored records give us; contract text and raw responses are
bulk that adds no auditability the manifest doesn't already provide.

## Which repo machinery applies

Assessed 2026-08-15 rather than inherited by default:

| Machinery | Verdict |
|---|---|
| `new-study` / `new-investigation` scaffolds, frontmatter, `lineage.yaml` | **Keep.** Standard. |
| `one-pagers/template` + `scaffold-one-pager` | **Keep**, at the end of 005. Prose is the human's. |
| `morel-branding` for Plotly figures | **Keep.** All figures here. |
| `capability-map` | **Mostly out of scope.** The map plots *our research activities*, not the prompts under study. Candidate entries later: "derive a principle set from annotation guidelines" and "build applicability checkers" — propose only, don't auto-log. |
| Study 007 ticket system, `drain.py`, OpenCode/distributed-agent infra | **Cut.** Built for autonomous-researcher orchestration. This study runs a deterministic trial grid; a plain runner plus a results store is the right shape. |
| `agent-trace-report`, `three-tier-evaluation` skills | **Cut for Phase 1.** They render multi-step agent traces and judge panels; Phase 1 is single-turn structured output scored programmatically (no judge). Revisit if env #3 (Terminal-Bench) happens. |
| LLM-judge scoring patterns from studies 004/005 | **Cut.** Deliberate: every Phase-1 and Phase-2 metric is programmatic. A judge would contaminate the reward story in Phase 2. |
| Desktop-GPU / Ollama path | **Not primary.** Model axis is Tinker + one frontier API. Local models only if a cheap sanity loop is wanted. |

## Running cost

Recorded per session so the study's cost is reportable rather than
reconstructed. Inference spend only (Tinker + labelling), excluding the
researcher's and agents' own time.

| date | spend | what it bought |
|---|---|---|
| 2026-08-16 | **$5.49** | the C2-vs-C3 grid (240 trials, 5.26M tokens, 6.55 model-hours), applicability labelling (4,498 judgements over 100 contracts), and all smoke runs |

For scale: the CUAD baseline reproduction costs **$0** (the checkpoints ship
the authors' own test-split predictions, so `evaluate.py` runs CPU-only), and a
full three-model inference run is ~5.6 GPU-hours on the desktop, also $0.

## Forward-looking

_To be populated._

## Open questions

- inkling-small availability and context window on Tinker (blocks the P0
  model choice).
- Final ~12-category subset — decided after 002 reads the Atticus guidelines.
- Exact 8B / 32B open-model picks (Qwen family likely; confirm the current
  Tinker model list).
- ~~Whether Atticus guideline licensing permits verbatim reuse of definitions
  in prompts.~~ **Resolved 2026-08-15**: CUAD is released under CC BY 4.0 —
  verbatim reuse is permitted with attribution. Remaining narrow question:
  confirm the annotation-guidelines PDF is covered by the same release and not
  licensed separately from the dataset. Attribution obligation is now a
  standing requirement (see Repository policy).
- AbstentionBench programmatic-vs-judge scoring split — deferred to env #2.
