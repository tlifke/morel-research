---
name: three-tier-evaluation
description: Render a per-trace agent-evaluation artifact (self-contained HTML) that LEADS with the three evaluation tiers as a prominent banner — ① End-to-End Metrics, ② Intermediate Metrics, ③ Judgements — with the rubric/trace/judge-grid as supporting detail below. Use whenever presenting how a single agent run was evaluated, comparing multiple LLM judges on one trace, or showing WHY a run succeeded/failed across the objective/computable/qualitative layers. Triggers on "evaluation artifact", "judge comparison", "three-tier evaluation", "how was this run judged", "show the evaluation", "compare the judges on this trace". Built for study-005's StepLaw researcher (judge_compare.py) but the three-tier structure is the reusable pattern.
---

# three-tier-evaluation

Tyler's endorsed way to present a single run's evaluation. The point is that
**the three evaluation tiers are visually dominant at the top**; the rubric,
trace, and per-judge detail are important but supporting.

## The three tiers (this is the reusable structure)

Grounded in `studies/005-harness-rescue/reasoner-not-optimizer.md`. Every
evaluation artifact leads with these three, in this order, as a banner of three
cards:

1. **① End-to-End Metrics** — the *objective outcome*. The ground-truth result
   (e.g. regret as the headline number, reached-optimum, outcome/finish-kind).
   **Lost when there's no objective optimum** (e.g. the real W2S task).
2. **② Intermediate Metrics** — *problem-specific, computable* trajectory facts
   that **survive without an objective outcome** and are the **transfer bridge**
   (e.g. for lr/bs tuning: reached the high-lr/large-bs corner, froze-an-axis,
   coverage/repeats, experiments-used, claim-matched-best). These must be
   **identified at problem-framing outset** — they are *not* generic; each
   substrate defines its own.
3. **③ Judgements** — the *panel's qualitative* process verdict (consensus or
   split, each judge, how external help was handled). No ground truth; the
   judges' best estimate of the *why*. Validate + panel them; never reduce to
   naive string-match metrics.

Below the banner, a **"supporting detail"** section: the rubric (so the reader
sees what the judges were asked), the agent trace, and the **judge-comparison
grid** (verdict per rubric dimension per judge — for eyeballing agreement) plus
each judge's full bifurcation + justification.

Keep this hierarchy. The three tiers up top, dominant; everything else supports.

## How to run (study-005 reference implementation)

```bash
uv run --no-project python scripts/judge_compare.py <run_dir> <out.html>
```
from `studies/005-harness-rescue/investigations/001-steplaw-substrate/harness`.
It reads the run's `trace.jsonl` + `loop_summary.json`, all persisted judge
verdicts for that run (`runs/judgments/<run>__<judge>.json`), computes the
intermediate metrics, and writes the self-contained HTML. New judges (e.g.
nemotron once the desktop is up) appear as extra columns automatically — no
renderer change.

## Recreating it for a different substrate

The three-tier *structure* is fixed; the *contents* are substrate-specific:
- Swap tier ② for that problem's computable signals (identified at its outset).
- Tier ③ reads whatever judge verdicts exist (the shared rubric is in
  `harness/judges/process_judge.md`; judges run retrospective + privileged with
  coarse verdicts — see [[feedback_multi_llm_judge_panel]]).
- Tier ① is the objective outcome if one exists; if not (real-world task), say
  so and lean on tiers ② and ③.

## Related

- `judge_compare.py` (renderer), `judge_casefile.py` (the privileged judge
  input), `run_api_judge.py` / Agent-subagent judges, `persist_judgments.py`
  (tracked dataset) — all in the inv-001 harness.
- The three-tier model + the "report all three components" standing rule live in
  `reasoner-not-optimizer.md` and study-005 `study.md`.
- For the agent's own move-by-move story (a different artifact), use
  `agent-trace-report`.
