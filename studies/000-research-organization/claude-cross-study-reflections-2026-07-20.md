# Cross-study reflections — what the body of work shows

_Assembled 2026-07-20 by Claude (Opus 4.8, 1M context) via Claude Code, during
the pin-and-publish session, at Tyler's request. **These are Claude's thoughts,
not Tyler's.** They are a synthesis offered as input to Tyler's writeups, and
are subordinate to his judgment. Per this repo's role boundaries, Claude does
not write the one-pagers; this is notes and argument for him to accept, reject,
or overwrite._

_Basis: a read across studies 003, 004, and 005 — the investigation docs plus
the raw `society_*/loop_summary.json` (37 runs), `phase1_runs.csv` (120 rows),
and `judgments.jsonl`. Numbers were independently recomputed from the raw data
where possible rather than taken from the prose. Where a claim rests on n=1–3 or
a single environment, that is stated inline. This document supersedes nothing;
it sits alongside `framework-drift-evidence.md` as a second kind of note — that
one is about the framework's bookkeeping, this one is about the research
findings._

_Two of the framings below are Tyler's, added in conversation on 2026-07-20 and
marked **(Tyler)**. They corrected or sharpened what Claude first proposed, and
the corrected versions are the ones recorded here._

---

## 0. The one honesty note up front

In conversation Claude called the "a 4B can do the research job" result the
"best result" of the program. **That was an overclaim and is retracted here.**
The evidence for that claim is a single promising signal (§4, item 8) with a
failing seed hidden inside its median and an unverified leak assumption. The
sturdy findings are the two Tyler named — decomposition enables diagnosis, and
cheap-fast iteration design enables the whole program. The rest of this document
is written at the confidence level the data actually supports, not higher.

---

## 1. The two through-lines

### Through-line A — the harness is opinionated, and the failures came from
### implicit opinions assumed correct rather than made explicit and tested

Claude's first framing was "every intervention that worked removed a constraint;
every one that added capacity backfired." That is wrong as stated, because the
harness is not optional: remove context-passing and the Executor has nothing to
execute and the Hypothesizer does not know what has been tried. The accurate
statement is Tyler's:

> **(Tyler)** The harness is by its nature opinionated. Being explicit about
> those opinionated choices — rather than assuming they are right — is what
> matters. Removing is not the universal fix.

Every intervention in this program encodes a belief about what the model needs.
C4 encodes "the model needs a nudge to finish." Critic v1 encodes "revise until
the critique is satisfied." Patch 2 encodes "enumerate every forbidden tool."
Each belief was wrong, and each was only exposed *because it was ablated against
a control*. The generalizable lesson is not *less harness*. It is: **no
load-bearing harness opinion should go unmeasured.** The value the framework
delivered was not scaffolding — it was the discipline of turning implicit
opinions into tested arms.

The reason "adding capacity backfires" looked true so often at 4B is the
mechanism in Through-line B, not a law about harnesses in general.

### Through-line B — at small scale, context and option-count are consumables;
### the winning move is minimum necessary context and a clear frame

> **(Tyler)** We want the minimum necessary context utilization when using
> smaller models. Too much context, they get confused; too many options, they
> cannot narrow it down. Given a properly scoped problem and a clear frame to
> work in, they do okay and sometimes well.

This is a design principle the data repeatedly confirms:

- **Patch 2** (study 003, inv 004): ~700 tokens of correct anti-hallucination
  instruction drove 26 sessions to *zero* native tool calls. The 4096-token
  window left no headroom to reason once the prompt filled it. Patch 1 at ~350
  tokens fired tools. More correct instruction, strictly worse behavior.
- **Axis-freezing** (study 005): given a 47–120-config grid, the 4B freezes one
  axis and sweeps the other rather than reasoning about the interaction. Too
  many options, cannot narrow.
- **C1-self reflection** (study 005): added deliberation made the agent *more
  methodical inside the region it had already wrongly anchored* — "changes
  flavor, not the freeze."
- **Critic v1** (study 005): added review made regret *worse* (0.027 vs 0.0016
  without it) at ~3× the calls.

The converse is the encouraging half: **properly scoped, the 4B does okay.** The
same nemotron that collapses over 15 iterations scores 90–100% on the
single-step research instincts (study 004, T4/T5/T6). The same model that
freezes on a 120-config grid moves both axes correctly when the frame is
tightened (the VibeThinker executor, §4 item 9). The floor is not "the model
cannot reason." It is "the model cannot hold the frame while also carrying the
context and the option space."

---

## 2. The finding inventory, ranked by evidentiary weight

Recorded because Tyler noted the iteration rate was high enough that the
learnings are hard to enumerate. Sorted by how much weight each can bear.

### Well-supported (double-digit n, or a clean isolated mechanism)

1. **Judges fracture on hard cases; a sharp rubric is the universal lever.**
   T1 (clean corpus): 100% four-way agreement including the 4B. T7 (injected
   error): pairwise agreement falls to 40–90%. Sharpening the rubric moved
   flash-lite 95%→100% and nemotron-4b 45%→90%. Conclusion from the doc:
   flash-lite + a sharp rubric ≈ Opus. (study 004 inv 002; n=20.)

2. **Finish-actuation fixes finishing, not thinking.** C4 drove the stall rate
   from 45–60% to 0% across all reflection levels, with *zero* effect on the
   median regret of runs that already finished. A clean dissociation between the
   actuation half and the search half of the problem. (study 005 inv 002 Phase
   1; 120 runs, 20 seeds/arm.)

3. **The T8 coherence collapse is a real stamina limit, not a context-window
   artifact.** The confound was tested: second-half redundant-rerun rate went
   23% at 4K → 40% at 32K → 54% at 131K. A bigger window made it worse, which
   rules out truncation. (study 004 inv 001; replicated n=3–6, self-flagged as
   suggestive not established.)

4. **Adding deliberation, instruction, or review to a 4B reliably backfires.**
   Patch 2 (overflow), Critic v1 (worse + 3× cost), audited reasoning applied to
   flash-lite (100%→95%, re-missed the case it had caught), C1-self (no
   unfreeze). Four independent instances. This is the empirical spine under
   Through-line B.

### Suggestive (n=1–3, Env A only)

5. **Decomposition localizes the failure causally — this is the sturdiest thing
   the program produced.** The monolith reports "it froze." The society shows
   the freeze is *born in the Orienter* and inherited, and that even when the
   agent is primed with only the correct hypothesis ("optimum at HIGH lr AND
   HIGH bs"), the high-corner region gets zero experiments across three runs —
   the Designer cannot translate a joint two-variable claim into a joint action.
   Diagnosis you cannot get from a monolith. **(This is Tyler's #1 headline, and
   Claude agrees it is the correct one.)**

6. **Axis-freezing is a reasoning/coverage failure, not a hardware failure.**
   It reproduces on the study-005 substrate, which is a zero-compute CSV lookup
   over StepLaw's precomputed grid — no GPU contention exists there at all. It
   survives a budget increase (budget-10 run pinned bs≈256 for all ten
   experiments) and survives correct priming. This is what cleanly separates the
   hardware wall (study 003) from the reasoning wall (study 005), and it is the
   evidence that licenses continuing to believe a 4B could do this with the right
   harness.

7. **The Hypothesizer is the bottleneck role.** Swapping it 4B→gemini gets 3/3
   corners; swapping the Analyst instead does not (0/3). The deficit is
   localized to hypothesis generation/prioritization, not analysis.

8. **The single "a 4B can do it" signal — held at low confidence.** A 4B in the
   Hypothesizer role, given a general-principles context frame *instead of* a
   model swap, reached median regret 0.00015 (corner 2/3) vs the all-4B base at
   0.022 (1/3). Caveats that keep this a signal and not a result: n=3 with seeds
   0.0 / 0.02688 / 0.00015 — **one seed failed badly and the median hides it**;
   single environment; and the load-bearing assumption that the "general
   principles" injection did not smuggle in the answer was never independently
   verified. **Verifying the leak question is the highest-value cheap experiment
   available.**

9. **A reasoning-trained small model can self-format; hard grammar starves it.**
   VibeThinker-3B under the society's strict JSON grammar degenerated to
   placeholder values in ~27 tokens. Unconstrained, it produced genuine
   orientation, and self-formatting it *beat* nemotron on grid fidelity (45% vs
   33% on-grid) with the best regret of three extractors, reaching the corner
   nemotron freezes on. The unrescuable part is real but general: gemini hit
   100% on-grid because it *snaps* to the nearest valid point; both 4B-class
   models strand ~half their configs. Grid fidelity is a small-model limit, not
   a VibeThinker-specific one. (study 005 inv 004; extractor matrix n=1/seed.)

### Method and measurement — Tyler flagged these as the useful ones; agreed

10. **Substrate and measurement confounds repeatedly masqueraded as capability
    findings.** The 003 agent's command was correct and the *environment* was
    broken. The confabulation rate "dropping" 25%→5% was partly an endpoint
    confound (Mac vs desktop Ollama). Study 004's pathologies turned out to be
    substantially harness artifacts. And most sharply: Ollama renders Qwen3.5
    tool prompts with the Qwen3 Hermes JSON renderer instead of the Qwen3-Coder
    XML renderer the family was trained on — meaning study 003/004's qwen3.5
    "Bash fires" were likely string matches on `Bash` inside markdown fences,
    not structured tool calls. **The framework's real value was catching these.**

11. **Cheap, fast iteration is a first-class enabler, not a convenience.** The
    study-005 substrate is a zero-compute lookup precisely so that a full run is
    seconds, not GPU-hours. That is what made the axis-freezing localization
    possible at all. **(Tyler's #2 headline: problem design such that iterations
    are quick and cheap is key to enabling work on a researcher and its
    harness.)** The corollary is a caution — the cheapness comes from a noiseless
    deterministic landscape, which tests the coherence/exploration half of the
    problem and *not* the actuation half. The two substrates (003 real-GPU, 005
    CSV) are complementary, and neither alone is the whole picture.

12. **Visual comparison artifacts changed comprehension.**
    > **(Tyler)** Claude Code's ability to make visual artifacts for me to
    > better understand things is a key finding that should shape next steps.

    When the iteration rate outruns a human's ability to read raw logs,
    on-demand small-multiple comparison figures (heatmap grids, region 2×2s)
    were what made a batch legible. This is a finding about the *research
    harness for the human*, parallel to the findings about the harness for the
    model, and it should inform how the next framework is built.

---

## 3. Corrections to the working recollection (2026-07-20)

Tyler's recollection of the body of work was directionally right. Three points
did not survive contact with the artifacts and are recorded so they do not
propagate into a writeup:

- **"Haiku ≈ Opus" is not stable across studies.** In study 005 (n=8) Opus and
  Haiku agree 100% on the core verdict and *gemini* is the outlier (75%). In
  study 004 (n=20) it inverts: Haiku is 65% vs the reference where Opus is 100%,
  and on the discriminating confabulation case Opus caught it while **Haiku
  missed it** (labeled `other`, distracted by formatting). Honest statement:
  cheap judges are Opus-equivalent on *unambiguous* traces; their ranking on
  hard traces is unstable across corpora and both corpora are underpowered.

- **The judge finding is about the rubric more than the model.** flash-lite went
  95%→100% and nemotron 45%→90% from rubric-sharpening alone. Nemotron's 90%
  agreement with the objective heuristic is explicitly a *trap* — both are
  shallow, and agreement between two weak instruments is not validation.

- **"qwen3.5:4b was the best ≤4B researcher" does not survive the artifacts.**
  No controlled head-to-head exists — it was scoped as inv 005 Q4 and deferred.
  Where the two were compared, nemotron was equal or better (patch 4's hint
  transferred cleanly, it produced the only real end-to-end Bash cycle, every
  study after 003 uses it), and the qwen3.5 evidence carries the renderer bug in
  item 10. The defensible claim is narrower: qwen3.5:4b + a tool-name-pinning
  patch was the *first* config to fire canonical Bash in study 003's gate-5.

- **"Decomposition helped performance" — it helped *diagnosis*.** The society
  base (all 4B) was *worse* than the monolith: median 0.022, corner 1/3, vs the
  A0 monolith at 0.0016. What moved the number was a model swap in one role or a
  context-frame injection — not the decomposition itself. Decomposition's payoff
  is observability (items 5–8), and that is enough to make it the headline.

---

## 4. Implications for the next framework (Claude's suggestions)

Offered as directions, not decisions:

- **Make every harness opinion an explicit, ablatable arm.** The program's
  wins all came from ablation against a control. A v2 framework should make
  "add a control" the path of least resistance, not an act of discipline.
- **Budget context and options as scarce resources at small scale.** A frame
  that scopes the problem and caps the option space is worth more than a frame
  that adds capability. "Minimum necessary context" should be a design default
  when the model is small.
- **Keep at least one cheap, fast, deterministic substrate in the loop** for
  localization, paired with at least one real substrate for actuation. Neither
  alone is sufficient; the study-003/005 split showed both halves matter.
- **Treat human-facing visual artifacts as part of the harness.** The
  comprehension bottleneck is real once iteration is cheap.
- **Verify the leak question in §2 item 8 first.** It is the cheapest
  experiment that could turn the strongest "4B can do it" signal into a result
  or kill it.

---

## Confidence and things to review

- Items 1–4 are the only findings backed by double-digit n. Everything in the
  "suggestive" tier is n=1–3 on a single environment (Env A) and should be
  written as promising rather than established.
- Item 8's median (0.00015) is not a robust central tendency at n=3 with one
  failing seed. Do not quote the median without the seed spread.
- The society/decomposition results (items 5–8) currently exist in raw JSON and
  one auto-memory note, not in any investigation `.md`. Numbers here were
  recomputed from `loop_summary.json`, but they have not been through the normal
  write-up-and-review path. Treat as preliminary until they are.
- Claude's judgment on research *direction* is explicitly unreliable (per the
  repo's own memory). The rankings here should be checked against Tyler's North
  Star, not adopted because they read as clean.
- The two through-lines are interpretations. The findings in §2 are the
  falsifiable content; §1 is Claude's attempt to name the pattern and could be
  wrong about the pattern while the findings stay true.
