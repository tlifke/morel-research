# morel-research

Public research repo. Studies probe what LLMs can and can't do, how that shifts
with harness and model changes, and adjacent questions.

Most of the work runs a small local model (4B-class, on a single consumer GPU)
as the *researcher* rather than the subject — asking what a weak agent can
actually drive, and how much of its failure is the model versus the scaffolding
around it.

> **Status: paused.** This line of work is on hold as of 2026-07-20 while it gets
> written up. The `framework-v1` tag pins the repo as it stood at that point.

## Layout

```
studies/               # one directory per study; see below
writeups/              # one-pagers and long-form prose (publishing artifacts)
one-pagers/template/   # LaTeX template for one-page writeups
capability-map/        # running figure of research tasks vs. LLM/human axes
scripts/               # repo-wide tooling (lineage generator, hooks)
drafts/                # unfinished prose
future-directions.md   # ideas not attached to any study
lineage.yaml           # derived index — never edit by hand
CLAUDE.md              # conventions and Claude's role boundaries
```

## The six studies

Each study has a canonical `study.md`; each investigation an `investigation.md`.

Legend: ✅ complete · 🔄 in progress · 💡 **suggested — named in a study's plan
but never scaffolded or started.** The 💡 items are listed so the gap between
what was planned and what was actually done is visible rather than buried.

### 000 — Research organization
The meta-study about how this repo organizes research.

- ✅ `001-initial-scaffold`, `002-plotly-migration`
- 💡 Suggested, not started: frontmatter CI validation; rendered lineage graph
  from `lineage.yaml`; cross-study tag search; multi-agent lineage conventions.

The validator was named on day one and never built. See
`studies/000-research-organization/framework-drift-evidence.md` — an evidence
pack on where this framework held and where it became ceremonial. It is the
main input to the forthcoming writeups.

### 001 — Tool calibration (matched-pair)
When does a model call a tool it should, and skip one it shouldn't? Built on
matched pairs where one half needs the tool and the other doesn't.

- ✅ `001-foundations`, `002-difficulty-axes`, `003-bulk-generation`,
  `004-calibration-pilot`, `006-temperature-prompt`, `007-axes-performativity`
- 🔄 `005-tool-spec-optimization` — 4 A/B experiments run; style-guide synthesis
  unfinished.
- 💡 Suggested, not started: `cross-model-eval` — sweep across model families
  and harness variations.

Locked `temperature=1.0, top_p=0.95` as the production-typical baseline, and
found the hand-designed difficulty axes **do not** predict tool-call
calibration — a negative result that redirected the work into study 002.

### 002 — Principle-bootstrapped difficulty
Can difficulty principles be bootstrapped from model behavior instead of
hand-designed?

- ✅ `001-self-prediction-baseline` — full 366-record corpus, 4,392 calls.
  Self-prediction of calculator behavior is **at chance** (0.432); overall
  0.664 [0.616, 0.711].
- 💡 Suggested, not started: `002-single-principle-ablations`,
  `003-principle-combination-search`, `004-cross-model-transfer`,
  `005-researcher-substitution`, `006-difficulty-targeted-generation`.

Note the shape here: the baseline ran, and **five of six planned investigations
never started**. The study's central claim — that principles can be bootstrapped
and then used to generate calibrated difficulty — was never tested.

### 003 — Automated weak-to-strong researcher replication
Can a local 4B model drive a real weak-to-strong generalization experiment?

- ✅ `001-hardware-derisk`, `002-vanilla-w2s-replication`,
  `003-claude-sdk-shim-and-researcher-swap`, `004-qwen-researcher-floor`
- 🔄 `005-split-host-researcher`, `006-overnight-agent-loop`

The substrate replicates faithfully (+0.013–0.014 above upstream across three
datasets). The researcher does not: inv 004 hit its pre-registered 5-patch
budget without crossing the stopping criterion and closed as a negative result
— prompt induction at 4B is solvable, substrate contention is the wall. The
overnight loop later produced real PGR (best 0.435 at iteration 3).

### 004 — Researcher diagnostics
If a weak researcher fails, *which* capability failed? A T1–T8 test ladder over
a mock substrate.

- ✅ `001-mock-substrate-harness`, `002-judge-comparison`
- 💡 Suggested, not started: human-as-researcher console (same I/O contract,
  human drives, logged for side-by-side comparison) — explicitly parked as
  half-baked.

Capstone: the model **has** the research instincts (T4/T5/T6 at 90–100%) but
coherence collapses after ~4 iterations (T8 at 10%). The bottleneck is stamina
and actuation, not capability. Judges agree on easy traces and fracture on hard
ones.

### 005 — Harness rescue (context engineering vs. training)
Does rich scaffolding rescue a weak researcher — and does it *hurt* a strong
one?

- ✅ `001-steplaw-substrate`
- 🔄 `002-rich-harness` (120-run 6-arm factorial), `003-process-judges`
  (4-model judge panel), `004-alternative-models` (VibeThinker-3B)
- 💡 Suggested, not started: real-W2S desktop transfer — port the winning
  harness to the real weak-to-strong task, 24h+, against the ~0.23 PGR human
  baseline.

Study 004's pathologies turned out to be **substantially harness artifacts**.
The residual failure is an actuation gap and axis-freezing, not confabulation.
Note the unstarted item: it was the study's payoff experiment.

**The live edge** is `005/investigations/004-alternative-models`. VibeThinker-3B
can self-format its own reasoning (dropping a whole extraction hop), and grid
fidelity is a small-model limit rather than a model-specific one. All of it is
n=1 and wants seeds.

## Where to start

- **New here?** `CLAUDE.md` defines the taxonomy and conventions.
- **Want the punchline about the framework itself?**
  `studies/000-research-organization/framework-drift-evidence.md`.
- **Want the research?** Each `study.md`, then descend into investigations.
- **Want to see the asymmetries?** `capability-map/capability-map.png`.

## Conventions in one paragraph

Studies live at `studies/NNN-slug/study.md`. Investigations inside them live at
`studies/NNN-.../investigations/NNN-slug/investigation.md`. Both carry YAML
frontmatter declaring `parents`, `children`, `status`, and axis position;
`lineage.yaml` is derived from that frontmatter and should never be edited by
hand. One-pagers are LaTeX, single page, fixed structure, and are written by
humans — Claude scaffolds but does not write prose.

A caveat this repo earned the hard way: **that frontmatter drifted.** As of
2026-07-20 all statuses were reconciled against document contents, but for
roughly seven weeks the derived index was confidently wrong. Read status fields
with that in mind, and see the drift evidence pack for the full accounting.

## Regenerating derived artifacts

```bash
python3 scripts/update_lineage.py        # rebuild lineage.yaml from frontmatter
python3 capability-map/plot.py           # rebuild capability-map.png from tasks.yaml
```

Experiments generally expect `DESKTOP_OLLAMA_URL` / `MAC_OLLAMA_URL` to point at
an Ollama endpoint; they default to `http://127.0.0.1:11434`.

## License

Code — harnesses, shims, figure scripts, and repo tooling — is licensed under
the **Apache License 2.0** (see `LICENSE`). This includes the explicit patent
grant in section 3.

Written research content — `studies/**/*.md`, one-pagers, and figures — is
licensed **CC BY 4.0**. If you build on the findings, please cite the study or
investigation by its path ID.
