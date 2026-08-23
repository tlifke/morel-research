---
id: studies/008-principled-extraction-cuad/investigations/008-principle-improvement-loop
title: Principle improvement loop
status: in-progress
parents:
  - studies/008-principled-extraction-cuad
children: []
related:
  - studies/008-principled-extraction-cuad/investigations/002-principle-derivation
  - studies/008-principled-extraction-cuad/investigations/006-empirical-principle-selection
  - studies/008-principled-extraction-cuad/investigations/007-comparison-metrics
axes:
  llm_capability: medium
  human_capability: high
tags: [principles, loop, task-definition, escalation-ladder, mvp]
created: 2026-08-17
updated: 2026-08-17
---

# Investigation 8 — Principle improvement loop

## Scope

Build and test a system that improves performance on a fixed task by modular,
principle-level changes: a frozen task definition, a principle store, a proposer
that derives candidate principles from observed failures, and an escalation
ladder that promotes a candidate only as far as measured effect justifies.

**MVP acceptance: one proposed principle that improves detection F2 on five
`principle_train` contracts, produced by the loop end to end.** That is rungs 1
and 2 of the ladder, with every component present but nothing above rung 2 built.

This investigation is the rethink inv 006 was deferred pending — see
`../006-empirical-principle-selection/investigation.md`, "Deferred: the
derivation approach itself needs a rethink". Inv 006 assumed the candidate pool
was roughly right and only selection was missing; this one makes proposal and
selection a single loop and takes failure diagnosis as the primary derivation
route.

## The components

_Each is documented below at the level needed to build it; implementation notes
land in `Methods` as they are written._

1. **Task definition** — frozen, external, versioned. See Decision 1.
2. **Principle store** — versioned set; a principle is `statement` +
   `trigger_guidance` + scope + provenance.
3. **Prompt assembly** — task definition + principle set + contract.
4. **Runner** — produces `TaskOutput` (extractions, absence claims, cited
   principles, explanations) per contract.
5. **Scorer** — inv 007's detection/localization decomposition, unchanged.
6. **Proposer** — reads gold and model output on a failing contract, names the
   error, drafts a candidate principle.
7. **Ladder controller** — runs the rung, applies the acceptance rule, chooses
   the next action from the action set.
8. **Trial ledger** — every trial keyed on (task-definition version, principle
   set version, model, contract, repeat index).

## The action set

`add` / `modify` / `remove` / **`split`**. Split is fourth because the observed
failure mode is not always a bad principle — `w01`'s minimal-expression
exception is right for Agreement Date and wrong for Expiration Date, and the
correct repair is two narrower principles, not an edit or a deletion.

Trials are keyed on a principle **set**, never a singleton, even while the MVP
tests one principle at a time.

## Decisions

> **Decision 1 — the task definition is frozen, external, and citable.**
> (2026-08-17)
>
> The task definition is ContractEval's published prompt plus CUAD's own
> per-category descriptions (`data/processed/categories.json`). It is versioned
> and the loop may not modify it.
>
> Alternatives considered: starting from zero and letting principles supply the
> task (the improvement curve is then dominated by principles that are task
> description, which measures prompt-writing rather than principle selection);
> having the system devise its own task definition first (doubles the search
> space and makes definition failure indistinguishable from principle failure —
> retained as a future direction, not a rung); ContractEval's prompt without
> CUAD's category descriptions (leaves category semantics to the principle
> layer, guaranteeing the first accepted principles are definitional).
>
> This wins because the text is published and not ours, so principle gain is a
> **delta over a citable baseline** rather than a delta over a prompt we wrote,
> and the comparability apparatus of inv 007 applies directly.

> **Decision 2 — task/principle overlap is measured, not policed.**
> (2026-08-17)
>
> Effective principles will partly be descriptions of the task. Because the task
> definition is frozen text, anything a principle adds is by construction not in
> it; the study reports the accepted set's composition by `type` (definitional
> vs. procedural / disambiguation / constraint) as a result.
>
> Judgement-based gating is explicitly rejected: inv 002 measured that the
> curator discriminates over structural properties and near-zero over
> substantive ones (§4a, `../../methods-scaffold.md`), so a "is this really a
> principle or just the task?" gate would not function.

> **Decision 3 — citation routes the next edit; it never decides acceptance.**
> (2026-08-17)
>
> `principles_cited` and `explanation` are behavioural proxies for whether the
> mechanism fired, and are used as triage: not cited → try the trigger; cited
> but score fell → try the statement or remove. The accept/reject rule at every
> rung is the **score**.
>
> This is constrained by prior measurement: citation frequency does not track
> principle quality (D-28) and declared `scope` does not constrain the model —
> `w06` is scoped to Agreement Date and is named in 43 of 63 false-absents on
> Expiration Date (D-29). Treating citation as evidence of value has already
> produced a wrong conclusion in this study once.

> **Decision 4 — the ladder ends on a split never used for selection.**
> (2026-08-17)
>
> Rungs run on `principle_train`; the final rung is a **confirmation pass on
> `principle_val`**, which the loop never reads during selection or iteration.
> Without it the entire ladder is selection artifact and inv 006's acceptance
> criterion ("selection then confirmation, never selection alone") is unmet.
>
> Not built for the MVP, but the ledger and split discipline are laid down now
> so the top rung is a run rather than a rebuild.

> **Decision 5 — the MVP scores 41 categories.** (2026-08-17)
>
> Chosen over the frozen 12-category subset. Absolute numbers are then not
> flattered by the subset choice (D-34), and the runs are directly comparable to
> the 41-category baseline work.
>
> Two consequences that must be handled before the first scored run:
> - The **`substr_ok` exception must be on.** Upstream relaxes matching to
>   `jaccard >= 0.5 OR gold in pred` for Parties, on raw unnormalised strings.
>   `harness/comparison_metrics.py` already implements it; the two older C2/C3
>   scoring scripts (`scripts/score_c2c3_with_cuad_evaluator.py` and
>   `scripts/bootstrap_c2c3_cuad_contrast.py`) do not. Harmless at 12 categories
>   where Parties is excluded, live at 41 where Parties is 216 of 951
>   `harness_val` gold spans. This loop scores through `comparison_metrics.py`,
>   so the defect is out of its path — but any comparison against older C2/C3
>   numbers crosses it.
> - **Macro is reported alongside micro** (inv 007, D-5). `Parties` is 216 of
>   951 gold spans on `harness_val`; a micro-pooled 41-category number is
>   substantially a Parties measurement.

> **Decision 6 — sampling follows Qwen's thinking-mode recommendation as far
> as the Tinker shim reaches, and the gap is documented rather than faked.**
> (2026-08-17)
>
> `temperature = 1.0`, `top_p = 0.95`. Qwen3.5-9B's card recommends
> `temperature=1.0, top_p=0.95, top_k=20, min_p=0.0, presence_penalty=1.5` for
> thinking-mode general tasks, and this study runs the model in thinking mode
> (`emits_reasoning_content=True`, `separate_reasoning` set explicitly).
>
> **`top_k`, `min_p` and `presence_penalty` are unreachable.** The Tinker OAI
> shim documents only `model`, `messages`, `prompt`, `max_tokens`,
> `temperature`, `top_p`, `separate_reasoning`, `reasoning_effort`, and
> silently drops everything else — proven, not inferred
> (`reviews/structured-output-evidence.html`: 14 request shapes returned 200
> including deliberately invalid controls). Sending them would look set and not
> be. Recorded as a deviation; revisit if the native-SDK path from the
> comparability work gets built.
>
> **`presence_penalty=1.5` would be wrong for this task even if reachable.**
> It penalises re-emitting tokens already in context, and the task is verbatim
> copying of long spans out of that context, with verbatim exact-rate a
> measured quantity of the study. If the native path arrives, use 0.0 and say
> why.
>
> This changes the study's previous setting. The C2/C3 runs used
> `temperature=0.7` with `top_p` unset — the *non*-thinking-mode general
> temperature paired with thinking mode and a default nucleus, which matches no
> published recommendation. Nothing numeric carries over: those runs were 12
> categories on `harness_val` under our own task definition, and this
> investigation opens a fresh baseline at 41 categories on `principle_train`
> under the frozen definition, so the change costs no comparability.

> **Decision 7 — the loop's output contract is one flat list of decisions, not
> two lists plus a discriminator.** (2026-08-17)
>
> `LoopOutput.decisions` holds exactly one `LoopDecision` per question, each
> carrying `category`, `kind`, `spans`, `explanation`, `principles_cited`.
> Replaces the study-level `TaskOutput`, which splits `extractions` from
> `absent` while *also* carrying a `kind` discriminator on each record.
>
> **Measured, not preferred.** The first live trial at 41 categories under the
> two-list shape misfiled **41 of 41** decisions — every record landed in
> `extractions` with `kind: "absence"` — and the trial was a total parse
> failure despite the model having answered all 41 questions correctly in
> substance. Re-running the identical contract under the flat list produced
> 41 of 41 conforming decisions: no duplicates, none missing, no kind/span
> disagreement. The two-list shape asks the model to keep two invariants in
> sync and it does not, at this width.
>
> Conformance defects that survive parsing are **counted, not repaired**
> (`LoopOutput.conformance`): missing categories, duplicates, unknown
> categories, and kind/span disagreement. `predicted_present` is derived as
> `kind == "extraction" AND spans is non-empty`, so a self-contradicting record
> still scores rather than voiding the trial. This keeps D-16's measurement —
> the unassisted conformance rate — without discarding usable data.

## Methods

_To be populated as components are built._

### Running and scoring

`loop/` holds the system; `scripts/` holds the one-shot builders; `tests/`
covers both. Nothing here imports the study's legacy decision records.

- `loop/prompt.py` — assembles frozen instruction + 41 questions + principles
  block + output contract. A test asserts the two arms differ **only** in the
  principles block.
- `loop/models.py` — `LoopOutput` / `LoopDecision` (Decision 7), with
  `conformance()` counting defects rather than repairing them.
- `loop/ledger.py` — append-only JSONL keyed on
  (task-definition version + sha, principle-set version, arm, model, contract,
  repeat). Resumable: a re-run skips trial ids already present.
- `loop/run_slice.py` — the one-shot arm. Contract text is read from CUADv1 and
  its sha256 checked against `instances.jsonl` before it enters a prompt.
- `loop/run_contracteval.py` — the ContractEval-native arm, one call per
  (contract, question).
- `loop/scoring.py`, `scripts/score_run.py` — scoring and the failure taxonomy.

**Invocation carries two extra deps.** Upstream `evaluate.py` imports pandas and
scikit-learn at module scope, so anything touching the scorer runs as
`uv run --with pandas --with scikit-learn`. `harness/comparison_metrics.py`
already handles the cwd trap.

### The MVP slice — five contracts

Selected by `scripts/select_mvp_contracts.py` (deterministic, no seed);
recorded at `mvp_slice.json`. From `principle_train` only.

Rule: token cap 25,000; one contract from each of the four length buckets in
fixed order; then greedy maximum marginal positive-category coverage over the 41
categories, ties broken by `contract_id`; a fifth drawn by the same coverage
rule from any bucket.

| bucket | tokens | positive cats | title |
|---|---|---|---|
| `<=4k` | 3,332 | 13 | GAINSCOINC_01_21_2010-EX-10.41-SPONSORSHIP AGREEMENT |
| `4k-8k` | 7,673 | 19 | AlliedEsportsEntertainmentInc_20190815_8-K_EX-10.19_11788293_EX-10.19_ |
| `8k-16k` | 9,402 | 24 | AURASYSTEMSINC_06_16_2010-EX-10.25-STRATEGIC ALLIANCE AGREEMENT |
| `>16k` | 19,828 | 8 | OLDAPIWIND-DOWNLTD_01_08_2016-EX-1.3-AGENCY AGREEMENT1 |
| `8k-16k` | 14,611 | 19 | INKTOMICORP_06_08_1998-EX-10.14-SOFTWARE HOSTING AGREEMENT |

The five jointly cover **34 of 41 categories** with at least one positive. The
seven uncovered are the rarest in the split (Affiliate License-Licensee /
-Licensor, No-Solicit Of Customers, No-Solicit Of Employees, Price Restrictions,
Rofr/Rofo/Rofn, Unlimited/All-You-Can-Eat-License — 1 to 9 positives across all
60 contracts). Those seven contribute only true negatives here; a principle
targeting one of them cannot be tested on this slice.

Why these criteria:

- **Token cap 25,000** — D-2 forbids truncating or chunking, so the whole
  contract enters the prompt. The split's maximum is 59,063 tokens and
  truncation has already been observed condition-dependently (4 of 240 trials).
  The cap keeps the `>16k` bucket represented at its low end rather than
  dropping the bucket.
- **One per length bucket** — length is the axis H5 rests on, and a slice drawn
  purely by coverage would skew long, since long contracts have more positives.
- **Coverage, not random draw** — at n=5 a random draw over 41 categories leaves
  large parts of the confusion matrix empty and makes the detection F2 a
  measurement of the top few categories.
- **No twin risk** — only cluster singletons were eligible for `principle_train`
  by construction (`scripts/config/dataset.yaml`), so no near-duplicate pair can
  be drawn.
- **No derivation overlap** — the MVP starts from an empty principle set under
  the frozen task definition, so inv 006's derivation-overlap rule (standing
  rule 5, `../../plans/splits.md`) has nothing to exclude. It becomes live again
  the moment any inv 002 principle enters this loop.

**Ordering note.** These five are the working *slice*, not "five contracts
exhibiting failure X" — the failure cannot be named before the frozen task
definition has been run. Rung 1's target is assigned from the baseline pass over
this slice: run the no-principles arm at k=3, score it, take the most frequent
scoreable failure class, and let its worst single contract be rung 1. Rung 2 is
then the remaining contracts in the slice that exhibit the same class, which may
be fewer than four. If the dominant failure appears on only one or two, the
slice is extended from `principle_train` by the same rule rather than a
different failure being chosen to fit the slice.

### Rungs

_Rungs 1–2 are the MVP; 3–5 are specified so the ledger and controller do not
need rebuilding, and are not implemented yet._

1. **One contract.** A specific observed failure; does the candidate fix it?
2. **Up to five contracts** exhibiting the same failure. Refine until it holds
   on all five, bounded at 3 attempts.
3. **Regression, 10–20 contracts** that may or may not exhibit the failure.
   Two-sided rule: targeted improvement ≥ threshold **and** non-targeted delta
   ≥ −epsilon. Both pre-registered.
4. **Random sizeable subset of `principle_train`**, combined with other
   candidates that reached this rung; best combination retained.
5. **Full `principle_train`**, then confirmation on `principle_val` (Decision 4).

### Statistical discipline at rungs 1–2

At n=1 and n=5, with temp 1.0 and seeds not honoured on Tinker, an apparent fix
is frequently sampling noise. Required and to be written down before the first
run:

- **k repeats per contract per arm** (3 for the MVP),
- **paired** with/without the candidate on the same contracts,
- an acceptance threshold fixed in advance, not read off the result.

## Results

### Baseline on the slice (`runs/baseline-001`, 2026-08-17)

15 trials, 5 contracts x 3 repeats, no principles, frozen task definition v1,
41 categories, Qwen3.5-9B, temperature 1.0 / top_p 0.95.

**Conformance is not the problem.** 14 of 15 parsed. Across all 14: zero missing
categories, zero duplicates, zero unknown categories, zero kind/span
disagreement, zero truncations. The single failure was a JSON serialisation
defect, not a wrong answer (see below).

**Detection is close to ceiling; localization is not.**

| | precision | recall | F1 | F2 |
|---|---|---|---|---|
| detection (mean over trials) | ~0.79 | ~0.90 | ~0.83 | ~0.87 |
| localization (micro, mean) | 0.765 | 0.622 | 0.679 | 0.643 |

Mean detection F2 per contract ranged 0.810 to 0.910. **Within-contract spread
across the three repeats reached 0.167** (OLDAPIWIND: 1.000 / 0.833 / 0.897) and
was 0.066-0.086 on three of the other four. This is sampling noise on identical
inputs, and it is the empirical justification for the 2-of-3 majority rule.

**The failure profile inverts the 12-category expectation.** Per parsed trial:
boundary_miss 7.36, false_present 4.14, false_absent 1.71. The model finds the
right clause and gets the span wrong; it rarely misses a clause outright. Only
false_present and false_absent move detection F2 at all - a boundary miss sits
inside an already-correct TP cell and moves only localization.

**Persistent failure cells (2-of-3 rule), ranked by contracts affected:**

| class | category | contracts |
|---|---|---|
| boundary_miss | Document Name | **5 of 5** |
| boundary_miss | Agreement Date | 4 |
| boundary_miss | Effective Date | 4 |
| false_present | Third Party Beneficiary | 3 |
| false_absent | Uncapped Liability | 2 (the maximum for this class) |

37 of 46 boundary-miss cells, 19 of 31 false-present cells, and 10 of 12
false-absent cells were persistent rather than one-off.

**Document Name fails the same way on every contract in the slice.** Gold is the
title alone; the model returns the title wrapped in the exhibit header and the
opening sentence:

| gold | predicted |
|---|---|
| `AGENCY AGREEMENT` | `Exhibit 1.3 AGENCY AGREEMENT May 21, 2015 Tribute Pharmaceuticals Canada Inc.` |
| `SPONSORSHIP AGREEMENT` | `Exhibit 10.41\n\nSPONSORSHIP AGREEMENT` |
| `STRATEGIC ALLIANCE AGREEMENT` | `This STRATEGIC ALLIANCE AGREEMENT (the "Agreement") is entered into as of March 18, 2010...` |

Agreement Date fails the same way on four: gold `February 1, 2018`, predicted
the entire preamble sentence containing it.

**No single category supports a rung-2 set for the classes that move detection
F2.** The largest false-present category covers 3 contracts and the largest
false-absent covers 2. Recorded here because it constrains what the MVP can
target - see "Things to flag".

### The parse failure is a serialisation defect, not a task failure

1 of 15 (AURASYSTEMS r2). The model emitted a verbatim span containing an
unescaped `"` - `a Delaware Corporation ("Aura")` - and the JSON died on it.
`finish_reason` was `stop`. Legal text is dense with defined terms in quotation
marks, so this recurs by construction. Handled in `pre-registration.md` under
"Lost repeats"; whether to adopt lenient parsing is flagged for Tyler.

## Forward-looking

_To be populated._

Standing candidates, recorded so they are not rediscovered:

- **Task definition as a rung-below-zero** — the system deriving its own task
  definition, tested against the frozen ContractEval definition as control.
- **Split as routing, and principles as composable modules.** `split` is scoped
  in this investigation as "one principle becomes two narrower ones". A stronger
  reading: if contracts fall into recognisable types, the system identifies the
  type and loads the principle set already proven for that type. Splitting then
  produces *routed modules* rather than narrower statements, and the unit of
  improvement becomes a composition of principle sets rather than a flat set.
  Deliberately out of scope for the MVP — it adds a document-type classifier,
  per-type ledgers, and a composition rule on top of a loop that is not yet
  debugged — but the ledger keying on principle **set** rather than singleton is
  the piece that keeps it reachable.

## Things to flag

Assumptions and choices made by Claude that need human review:

- **Provenance needs a fifth value, `failure_diagnosis`.** The existing enum in
  `harness/models.py` is `atticus_guidelines | data_mined | authored | other`.
  This loop's primary proposer is failure diagnosis, which is the route that
  produced `w11`, the strongest candidate the study has — and it is not
  nameable in the current schema.
- **The new system defines its own records rather than importing
  `harness/models.py` wholesale.** Load-bearing pieces reused: `Principle`,
  `Decision`/`Extraction`/`AbsenceClaim`/`TaskOutput`, `Instance`/`Gold*`,
  `harness/comparison_metrics.py`, `harness/prompts.py`, the frozen splits.
  `DecisionRecord`, `AnswerScore`, and the Level A/B/C machinery in
  `harness/metrics.py` belong to the earlier framing and are not carried in.
  Reconciliation happens when this graduates to study level, per Tyler's
  instruction to keep it clean and local first.
- **The MVP is one sequential stream.** Parallel proposers with consolidation at
  rung 4 is the intended end state; sequential is chosen for debuggability, not
  because parallel was rejected.
- **The rung-3 threshold and epsilon are not yet chosen**, and choosing them
  after seeing rung-3 data would void the pre-registration.
- **The five MVP contracts are not yet selected**, and the derivation-overlap
  rule (standing rule 5, `../../plans/splits.md`) applies: exclude a
  principle's derivation contracts from its own A/B and report the count.

## Limitations

- **Effect sizes may not clear any honest threshold.** Inherited from inv 006:
  if nothing does, that is itself a reportable result about how much a principle
  can be expected to move extraction performance.
- **The MVP proves the machinery runs, not that the method works.** One
  principle improving F2 on five contracts is a plumbing result; the method
  claim needs rung 5 and the `principle_val` confirmation.
- **Selection is on one model.** Whether a set selected for one model transfers
  up the size axis is a separate measurement (inv 006, "Model axis").
