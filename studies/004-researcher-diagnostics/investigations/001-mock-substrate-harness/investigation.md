---
id: studies/004-researcher-diagnostics/investigations/001-mock-substrate-harness
title: Mock-substrate researcher harness
status: in-progress
parents:
  - studies/004-researcher-diagnostics
children: []
related:
  - studies/003-automated-w2s-replication/investigations/006-overnight-agent-loop
  - studies/001-tool-calibration
axes:
  llm_capability: medium
  human_capability: high
tags:
  - pi
  - mock-substrate
  - tracing
  - tool-use
created: 2026-06-03
updated: 2026-06-03
---

# Inv 001 — Mock-substrate researcher harness

## Scope

Build a clean "researcher CLI" on Pi (`pi-agent-core` SDK) that drives a
real researcher model (nemotron-3-nano:4b locally; a cheap ceiling model
for contrast) against a **mock substrate** whose results are scripted
fixtures or synthetic. The same CLI, with one switch flipped, runs
against the **real desktop substrate** with a byte-identical researcher
response path. On top of it, instrument the loop with a move-taxonomy
trace (OpenTelemetry → Phoenix) and a suite of capability test cases
(T1–T8) that score **tool-call validity** and **decision correctness**
as two independent axes.

Goal: stop conflating "proposed a bad idea" with "couldn't emit a valid
tool call" with "the harness dropped the result." Localize the failure.

## Design decisions (locked with Tyler)

- **Researcher model:** real nemotron-3-nano:4b (Mac Ollama), plus a
  cheap ceiling model for a model-floor-vs-harness-floor contrast.
  Ceiling is capped to the cheap tier — **Gemini 3.x Flash / Haiku 4.5,
  nothing pricier.** A hard cost ceiling is enforced so the contrast can
  never silently reach an expensive model.
- **Base harness:** Pi via its SDK (`createAgentSession`). Rationale: the
  expensive, bug-prone part of an agent CLI is the loop + multi-provider
  streaming tool-call wire — exactly what shim_v2 was, and exactly what
  pi-ai already solved. The `SUBSTRATE` seam Tyler requires is a
  one-function swap in Pi's tool model.
- **Traces:** emit OpenTelemetry spans (move-taxonomy). Phoenix is the
  daily viewer (pip install, SQLite, no Docker); the same spans can point
  at a local MLflow 3 server. JSONL stays the canonical artifact; the
  trace store is a derived view.
- **Console (sibling investigation):** Pi interactive mode / a thin SDK
  wrapper, terminal-first.

## The SUBSTRATE seam (the hard requirement)

A run in test mode and a run on the desktop must differ by exactly one
injected dependency. Everything the model sees — system prompt, loop,
tool names, tool schemas, result shapes — is identical. Only the tool
`execute()` body changes:

| Tool | `SUBSTRATE=mock` | `SUBSTRATE=desktop` |
|---|---|---|
| `bash` | return fixture stdout/exit/markers | SSH via Tailscale, real stdout |
| `evaluate_predictions` | return fixture PGR ack | POST the real orchestrator |
| `read` / `write` | fixture / scratch handoff dir | real workspace |

If COMPARE works in test (fake handoffs) it must work on the desktop
(real handoffs) — same reasoning code path. Same for EXECUTE, etc.

## The researcher's action space — the move taxonomy

The model emits raw blocks (Thinking / Text / ToolUse / ToolResult). We
tag every trace step with one **research move**, which is the layer of
visibility study 003's HTML reports never had:

| Move | Trace signature | Tool |
|---|---|---|
| ORIENT | reads prior handoff / history | read, glob |
| COMPARE | reasons over prior PGRs, names best-so-far | thinking/text |
| HYPOTHESIZE | proposes an idea | thinking/text |
| DESIGN | idea → concrete command + hyperparams | text |
| EXECUTE | kicks off the experiment | bash |
| OBSERVE | reads raw run output | read |
| MEASURE | gets the metric | evaluate_predictions |
| INTERPRET | makes sense of the metric | thinking/text |
| DECIDE | refine / pivot / stop | thinking/text |
| RECORD | writes learnings/hints for future self | write |
| DIAGNOSE | on error, names cause + correction | thinking/text |
| REPORT | publishes a notable result | share_finding |

Move boundaries are a starting point, not settled (Tyler's note). DESIGN
vs HYPOTHESIZE in particular may merge.

## Capability test cases (T1–T8)

Each test: seed a controlled context → let the real researcher act
against the mock substrate → score **(A) tool-call validity** and
**(B) decision correctness** separately. Fixtures from study 003 inv 006
where possible, synthetic where needed.

| # | Capability | Injected context | Mock returns | Pass = A + B | Fixture |
|---|---|---|---|---|---|
| T1 | Initialize / cold start | system+prompt, no handoff | — | A: valid canonical `bash`; B: command in budget | real `iteration_00` (a failure) |
| T2 | Kick off a run | "propose next config" | — | A: not lowercase/invented bash, params ≤ caps, timeout ≤1800 | `tool_call_shape` in every yaml |
| T3 | Interpret one result | one config just ran | real `server_ack` (PGR 0.43) | B: direction right, no hallucinated number | jsonl_validation session_000 |
| T4 | Compare to prior runs | handoffs w/ PGRs 0.06,0.24,0.43,−0.01 | — | B: names 0.43 best, ignores regression | synthetic from real PGRs |
| T5 | Build off improvement | prior train500 → 0.24→0.43 | — | B: extends winning lever, RECORDs the win | synthetic (RECORD gap is real) |
| T6 | Handle non-improvement | prior epochs=3 → −0.01 | — | B: backs off, no repeat of failing config | real `iteration_08` regression |
| T7 | Diagnose an error | error injected | one of 5 real payloads | B: names cause + corrected command | weak-artifacts-missing, `Qwen15` typo, missing `data/`, 1800s timeout, CUDA OOM |
| T8 | Long-horizon coherence | replay 20+ synthetic handoffs | — | B: redundant-config rate (re-runs known configs?) | synthetic long history |

## Replicate vs remove (vs the study 003 system)

| Current piece | Verdict | Why |
|---|---|---|
| shim_v2 (OpenAI-wire + Anthropic-facade) | REMOVE | pi-ai replaces it; nemotron speaks OpenAI-compat natively |
| AutonomousAgentLoop + run_smoke.py | REMOVE | pi-agent-core is the loop |
| patch_006 heavy prompt | STRIP to minimum | the suspect lifting; measure how much we add back |
| handoff pattern (writer/yaml/bootstrap) | REPLICATE concept, simplify | memory is real; but 256K context may obviate the lossy reset |
| SFT+eval on desktop | REMOVE from harness | the mock-substrate decision; desktop reachable behind the seam |
| tools (bash, read, write, glob, evaluate_predictions) | REPLICATE as Pi tools, MOCK backends | trivial via registerTool |
| run_overnight.sh, SIGTERM/resume, VRAM sampler | REMOVE | no long unattended GPU run in tests |
| render_run.py + JSONL | REPLACE | OTel → Phoenix; keep JSONL canonical |

## De-risk slice (current step)

Smallest vertical slice to validate the Pi bet before committing the full
harness. Build a ~80-line Pi SDK app:

- nemotron-3-nano:4b, minimal system prompt
- one mock `bash` tool returning a real inv-006 fixture
- the T1 cold-start scenario
- the event stream tagged with moves → console + JSONL; one OTel span to
  Phoenix

**Kill criterion (explicit):** if the mock↔desktop tool swap or the
event-based tracing fights Pi, fall back to Python + Textual having spent
~a day. Otherwise, proceed to the full T1–T8 suite + the human console.

## Status / log

- 2026-06-03 — Investigation scaffolded. Pi installed; `ollama-local`
  provider wired (nemotron + qwen3.5); nemotron answers end-to-end
  through Pi. Building the de-risk slice.
- 2026-06-03 — **De-risk slice passed; kill criterion not triggered.**
  `harness/src/slice.ts`: a self-contained `pi-agent-core` app (inline
  nemotron `Model`, mock `bash` + `evaluate_predictions` tools, the
  `SUBSTRATE` seam stubbed for desktop at the single `execute()`
  boundary, move-tagged console + JSONL trace). On the T1 cold-start
  scenario, nemotron: emitted a valid canonical `bash` command (matched
  baseline), chained the `eval_output_path` from the bash result into a
  correct `evaluate_predictions` call, and interpreted the PGR (0.0598)
  and transfer (0.547, 35/64) accurately. The mock substrate, the
  one-function seam, and event-stream move-tagging are all clean in Pi.
  Two findings already: (a) it ran a full clean iteration under a ~5-line
  system prompt vs patch_006's ~60 lines — supports the over-prompted
  hypothesis; (b) it set `timeout: 60` on the training Bash —
  reproduces the unrealistic-short-timeout pathology seen in study 003.
- 2026-06-03 — **Desktop substrate live + Phoenix tracing wired.**
  - `scripts/desktop_run.sh`: synchronous SSH job-runner over Tailscale.
    Base64's the whole remote script to dodge cmd.exe -> WSL -> bash
    quoting; runs **synchronously** with SSH keepalive because WSL kills
    backgrounded jobs when the one-shot channel closes. Emits the
    study-003-style summary (exit, elapsed, synthesized markers, absolute
    eval_output path). `scripts/desktop_eval.sh`: POSTs the eval_output.json
    to the live orchestrator (`POST :8000/api/evaluate-predictions`).
  - `slice.ts` gained a `SUBSTRATE=desktop` branch (shells out to the two
    scripts) + a smoke scenario (train64/test64/e1, weak artifacts cached).
  - **Full end-to-end real-GPU iteration:** nemotron emitted the smoke
    command -> bash SSH'd to the 3080 -> real SFT + vLLM eval (107s, exit 0)
    -> it lifted the absolute eval path into `evaluate_predictions` -> live
    orchestrator -> **real PGR 0.2319** (transfer 0.578, 37/64) -> accurate
    interpretation. Identical response path to the mock; only the substrate
    flipped. Trace + `runs/desktop_report.html`.
  - Simple bugs corrected: nested-quote launch (WSL bg-job death) ->
    synchronous keepalive SSH; relative eval path -> absolutized; raw run
    lacks the old wrapper's markers -> synthesized from log signals.
  - **Phoenix:** `scripts/to_phoenix.py` ingests a trace.jsonl as
    move-spans (OTel -> Phoenix). Server runs with a persistent store at
    `runs/phoenix`; mock + desktop traces are in project
    `researcher-harness` at `http://localhost:6006`.
- 2026-06-03 — **T7 (diagnose an error) — run, mock, n=4. Key finding.**
  Injected the real study-003 `Weak artifacts not found` error on the
  first `bash`, success on retry. Instrumented `slice.ts` with
  `stop_reason` / `saw_error` / `acted_after_error`. Four runs produced
  **four different behaviors**:
  - **1× clean recovery** (`t7_recovery_report.html`): diagnosed the
    error, hypothesized training the weak teacher first (re-ran with
    `--weak-model` only), re-ran the full command, evaluated, reported
    accurately. **The capability is present.**
  - **1× diagnose-but-freeze:** correctly named the cause in its
    reasoning, then emitted no action and no output; loop ended.
  - **1× no-op:** never emitted a `bash` call at all.
  - **1× confabulation** (`t7_hallucination_report.html`): **zero tool
    calls**, fabricated "PGR improved to 0.675 (up from baseline 0.65)".
    Real fixture PGR is 0.0598. From a final-answer log this looks like a
    successful iteration; only the trace exposes it.
  Headline: the diagnosis capability **exists but is highly unreliable**
  (~1/4 clean), and one failure mode — **reporting fabricated results
  with no tool calls** — is invisible without the move-tagged trace. This
  is the sharpest validation yet of the reasoning-vs-actuation split and
  motivates n>=10 repeats + the judge investigation to get rates.

- 2026-06-03 — **T7 real error-variety + the multi-iteration loop.**
  - Added two more *observed* study-003 error fixtures (CUDA OOM,
    timeout) alongside weak-artifacts, selectable via `ERROR_KIND`.
    n=15 each on desktop nemotron. **Recovery rate is dominated by the
    error type, not diagnosis:** OOM 100% recovered, timeout 87%,
    weak-artifacts 55%. The split is fix-availability — OOM/timeout have
    an action the model can take (shrink the config); weak-artifacts
    needs an action outside its toolset (train the weak teacher), so it
    stalls or blind-tweaks. The earlier "55%" was a hard-error number.
  - `src/loop.ts`: the multi-iteration loop (the on-ramp to T4–T8 and the
    memory-design sim). Two memory modes via `MEMORY`: `full` (keep the
    whole history in nemotron's 256K context) vs `handoff` (reset each
    iteration, seed only a one-line summary of the prior one). Scripted
    substrate returns a synthetic PGR landscape (rises with train-size,
    falls with excess epochs) so the researcher has something to climb;
    logs per-iteration config + PGR + whether it re-ran a known config.
    `loop_summary.json` per run; the full-vs-handoff sim aggregates
    repeat-rate / climbed / best-PGR.
  - **Fast-sim result (4 reps each, 8 iters):** full-context **9%**
    redundant-rerun rate vs handoff-reset **62%** — a 7× difference. With
    the whole history in its 256K window the researcher rarely re-runs a
    config; under handoff-reset (only the prior iteration's summary) it
    re-runs configs it already tried most of the time, because it has
    forgotten everything from 2+ iterations back. **Conclusion: for this
    model the study-003 handoff-reset is not just unnecessary — it is
    harmful; keep full context, drop the handoff.** (Directional: small
    scripted sim, n=4; note also an eval-count asymmetry — handoff
    sessions thrash with ~4× more runs per iteration.)

- 2026-06-04 — **Test ladder completed (T2–T6, T8).**
  - **T2 (command shape, n=70 single-iter commands):** canonical bash
    100%, uses run module 98%, model names intact 98%, params in budget
    91% — but **timeout set <300s in 85%** (mostly `timeout: 120`). The
    short-timeout pathology is near-universal and would kill ~85% of real
    iterations.
  - **T3 (interpret a result, n=59):** reports the PGR correctly 94%,
    hallucinates a stray number 3%. Comprehension is reliable.
  - **T4/T5/T6/T8 (full-context loop, 15 iters × 10, gemini-3.5-flash
    audited judge + objective trajectory metrics):**
    - T4 compares_to_history **100%**, T5 builds_on_wins **100%** +
      tracks_learning **100%**, T6 handles_regressions **90%**.
    - T8 stays_coherent **10%**; objective redundant-rerun rate **13%**
      overall but **1% first-half → 23% second-half**.
  - **Capstone:** the model HAS the research instincts (compares, builds
    on wins, handles regressions, tracks learning — all 90–100%) but
    **cannot sustain them past ~4 iterations** (T8 coherence collapses).
    The bottleneck for an overnight researcher is not reasoning,
    interpretation, instincts, or memory capacity (256K) — it is
    **actuation reliability** (the timeout bug, recovery follow-through)
    and **coherence stamina**. nemotron-4b is a competent researcher for
    ~4 iterations, then degrades.

## Confounds & limitations

Surfaced in review 2026-06-04 (Tyler asked "what's missing / what
confounds"). The scorecard (`runs/scorecard.html`) carries the same list.

**Confounds — ranked by threat to the conclusions:**

1. **num_ctx truncation (decisive).** The desktop Ollama has no
   `OLLAMA_CONTEXT_LENGTH` / Modelfile `num_ctx` override, so it very
   likely serves nemotron at the ~4K default, NOT 256K. Loop traces reach
   ~6K tokens by iteration 4 — exactly where the T8 "coherence decay"
   begins. So T8 may be the harness truncating the model's memory, not the
   model losing coherence; it also weakens the full-vs-handoff memory
   result (full was really "~4K-truncated" vs "handoff summary").
   **RESOLVED 2026-06-04 — confound rejected.** Served windows confirmed
   via `ollama ps`: original 4096, re-test model `nemotron-32k` 32768. On
   the verified full window the T8 decay PERSISTED (2nd-half redundant
   ~40%, n=6, vs original ~23%, n=10 — unchanged-to-worse, not reduced),
   and the memory result REPLICATED (full 11% vs handoff 61%, n=3). So
   truncation is not the cause: T8 is a genuine model limit (poor
   long-context utilization — the 4B sees its whole history and still
   repeats), and the handoff-harmful finding stands on a true full window.
   A 131K spot-check (n=3, max trace ~14.5K = 11% of window, zero
   truncation) extends the trend: **2nd-half redundant 23% (4K) → 40%
   (32K) → 54% (131K).** More context never reduces the decay and appears
   to *worsen* it — consistent with long-context degradation ("lost in
   the middle") in the 4B, not truncation. (n small + high per-run
   variance, so the monotonic worsening is suggestive, not established;
   the persistence-of-decay conclusion is solid.)
2. **Mock recovery is free.** In T7 the substrate returns success on ANY
   retry, so recovery rates measure "emitted a second command", not "fixed
   it". A real substrate would punish wrong fixes; recovery is optimistic.
3. **Trivial, noiseless landscape.** The scripted PGR is smooth and
   monotone. T4/T5/T6 are easy here; we never test signal-vs-noise
   judgement (real PGR SE ≈ 19pp) or deceptive optima.
4. **Behaviors are prompted.** The loop prompt explicitly instructs
   "compare to history / don't re-run configs / use what you learned", so
   T4/T5/T6 ≈ 100% may be instruction-following, not emergent instinct.
5. **LLM-graded ground truth.** Reference labels are curated from
   Opus/Claude, not humans — mildly circular on the subtle cases.
6. **Endpoint / sampling uncontrolled.** n=4 on Mac nemotron, n=20 on
   desktop nemotron (different instances); sampling temperature not pinned.

**Not tested by this framework (gaps):**

- **Idea generation** — the biggest gap, out of scope by construction: we
  fix the task and the hyperparameter levers, so we never test whether the
  researcher proposes tractable, novel, correct hypotheses.
- **Signal vs noise** — deterministic substrate removes it.
- **Writing / modifying experiments** — it only tweaks hyperparameters of
  one fixed script.
- **Knowing when to stop** — convergence / diminishing returns / declaring
  a finding.
- **Code & method comprehension, multi-task generalization** — one task,
  one domain.

## Things made up that need review

- The move taxonomy boundaries (12 moves).
- T1–T8 pass/fail rubrics are still qualitative; concrete thresholds TBD.
- T8 reframed as lossy-handoff amnesia (re-running known configs) rather
  than within-iteration context growth — confirm that's the right risk.
