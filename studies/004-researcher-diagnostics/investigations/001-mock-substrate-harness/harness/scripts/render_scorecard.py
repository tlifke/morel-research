import argparse
from pathlib import Path

G, A, R = "#16a34a", "#d97706", "#dc2626"

TESTS = [
    ("T1", "Cold start", "single iteration", "100% clean (n=20)", G, "Runs → evaluates → reports. The happy path is solid."),
    ("T2", "Command well-formedness", "tool-call shape", "structure 98–100% · 85% set a fatal <300s timeout", A, "Canonical bash, right module, model names intact, params in budget — but it sets timeout≈120s for a ~20-min job almost every time. On a real substrate this alone kills ~85% of iterations."),
    ("T3", "Interpret a result", "comprehension", "94% correct · 3% hallucinated (n=59)", G, "When it gets a PGR it reads it correctly. Comprehension is not the weak link."),
    ("T4", "Compare to history", "multi-iteration", "100% (n=10)", A, "It references and compares prior iterations' results — but on a trivial monotone landscape, and the prompt explicitly tells it to. Likely inflated."),
    ("T5", "Build on a win + track", "multi-iteration", "100%", A, "Extends the winning lever and keeps a table of what it tried — same caveats as T4 (easy landscape, prompted)."),
    ("T6", "Handle a regression", "multi-iteration", "90%", A, "Backs off after a PGR drop. Easy on a noiseless landscape; untested against noise where a 'drop' may be sampling variance."),
    ("T7", "Diagnose an error", "single iteration", "diagnosis good · recovery 55–100% by error type · ~3% confab", A, "Diagnoses correctly; recovery is gated by fix-availability (OOM 100% / timeout 87% / weak-artifacts 55%). But the mock returns success on ANY retry, so 'recovery' is partly free — a wrong fix would fail again on a real substrate."),
    ("T8", "Long-horizon coherence", "multi-iteration", "redundant ~1–4% → ~23–40% by 2nd half — CONFIRMED (not truncation)", R, "The num_ctx confound was checked and REJECTED. Served windows were verified via `ollama ps`: original 4096 (truncates the ~6K+ trace), re-test 32768 (holds it whole). On the true full window the late-run decay PERSISTED (2nd-half redundant unchanged-to-worse). So it is a genuine model limit, not Ollama dropping history: the 4B can see its entire history and still re-runs configs it already tried — poor long-context utilization."),
]

CONFOUNDS = [
    "<b>num_ctx truncation — CHECKED &amp; REJECTED:</b> the original model did serve at 4096 (confirmed via `ollama ps`) and the trace exceeds it by iter 4, so the confound was real and worth checking. But re-running on a verified 32768 window did NOT remove the T8 decay, and the handoff-vs-full memory result REPLICATED (full 11% vs handoff 61%). So truncation is not the explanation for either; both findings stand.",
    "<b>Mock recovery is free:</b> in T7 the substrate returns success on any retry, so recovery rates measure 'emitted a second command', not 'fixed the problem'. A real substrate would punish wrong fixes.",
    "<b>Trivial landscape:</b> the scripted PGR is a smooth monotone function with no noise. T4/T5/T6 (compare/build/back-off) are easy here; real research has noise, deceptive optima, and signal-vs-noise judgement we never test.",
    "<b>Behaviors are prompted:</b> the loop prompt explicitly says 'compare to history', 'don't re-run configs', 'use what you learned'. T4/T5/T6 may be instruction-following, not emergent instinct — the same over-prompting we set out to question.",
    "<b>LLM-graded ground truth:</b> the reference labels are curated from Opus + Claude, not humans. Accuracy-vs-reference is accuracy-vs-a-strong-LLM; the subtle cases are mildly circular and want human spot-checks.",
    "<b>Endpoint / sampling:</b> n=4 ran on Mac nemotron, n=20 on desktop nemotron (different instances); sampling temperature was not pinned. Both affect the behavior rates.",
]

MISSING = [
    "<b>Idea generation</b> — the core of an 'automated researcher'. We test execution of a fixed task with fixed hyperparameter levers; we never test whether it proposes tractable, novel, correct hypotheses. (Tyler's point — outside this framework by construction.)",
    "<b>Writing / modifying experiments</b> — it only tweaks hyperparameters of one script. Real automated research implements new ideas in code; we test the narrowest slice.",
    "<b>Signal vs noise</b> — distinguishing a real gain from sampling variance (real PGR SE ≈ 19pp). Our deterministic substrate removes this entirely.",
    "<b>Knowing when to stop</b> — recognizing convergence / diminishing returns / declaring a finding. Never tested.",
    "<b>Code & method comprehension, multi-task generalization</b> — one task, one domain, no reading of the codebase or adapting to a new problem.",
]


def li(items):
    return "".join(f"<li>{x}</li>" for x in items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="../assets/scorecard.html")
    args = ap.parse_args()

    rows = ""
    for tid, name, kind, result, color, note in TESTS:
        rows += (
            f"<div class='card' style='border-left-color:{color}'>"
            f"<div class='ch'><span class='tid' style='background:{color}'>{tid}</span>"
            f"<span class='tn'>{name}</span><span class='tk'>{kind}</span></div>"
            f"<div class='res'>{result}</div><div class='note'>{note}</div></div>"
        )

    doc = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1"><title>Study 004 — researcher test ladder T1–T8</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f8fafc}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 ui-sans-serif,system-ui,sans-serif}}
.wrap{{max-width:880px;margin:0 auto;padding:32px 22px 80px}}
h1{{font-size:23px;margin:0 0 3px}} .sub{{color:var(--mut);font-size:13px;margin:0 0 20px}}
h2{{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:28px 0 12px;border-bottom:1px solid var(--line);padding-bottom:6px}}
.card{{background:#fff;border:1px solid var(--line);border-left:5px solid;border-radius:10px;padding:12px 16px;margin-bottom:10px}}
.ch{{display:flex;align-items:center;gap:10px}}
.tid{{color:#fff;font-weight:700;font-size:12px;padding:2px 9px;border-radius:5px;font-family:ui-monospace,Menlo,monospace}}
.tn{{font-weight:700;font-size:15px}} .tk{{color:var(--mut);font-size:11.5px;background:#f1f5f9;padding:1px 7px;border-radius:5px}}
.res{{font-size:14px;margin:6px 0 4px;font-weight:600;color:#1e293b}}
.note{{font-size:13px;color:#475569}}
.punch{{background:#eef2ff;border:1px solid #c7d2fe;border-radius:12px;padding:16px 18px;color:#312e81;font-size:14px;margin:6px 0}}
.box{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:8px 20px}}
.box li{{margin:8px 0;font-size:13.5px;color:#334155}}
.warn{{background:#fffbeb;border-color:#fde68a}}
.foot{{color:var(--mut);font-size:12px;margin-top:28px;border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class=wrap>
<h1>Researcher test ladder — T1 → T8</h1>
<p class=sub>study 004 · diagnosing nemotron-3-nano:4b as an autonomous researcher · Pi harness, mock + real-GPU substrate</p>

<h2>Scorecard</h2>
{rows}

<h2>Punchline</h2>
<div class=punch><b>The model has the research instincts but not the stamina.</b> It reads results (T3), compares across its history (T4), extends winning levers and tracks what it tried (T5), and backs off after regressions (T6) — all 90–100%. The bottlenecks are not reasoning, interpretation, instinct, or memory <i>capacity</i>: they are <b>actuation reliability</b> (the near-universal short-timeout bug; recovery gated by fix-availability) and <b>long-horizon endurance</b> — though the endurance result is confounded (see below) and may be a serving artifact rather than a model limit. The sharper framing: this is a <b>harness-design question</b> (can we make a small model run a long task?) and an <b>LLM-capability question</b> (does it have the stamina?) — both now <b>testable</b> against this framework.</div>

<h2>Confounds (what could undermine these numbers)</h2>
<div class="box warn"><ul>{li(CONFOUNDS)}</ul></div>

<h2>What this framework does NOT test</h2>
<div class=box><ul>{li(MISSING)}</ul></div>

<div class=foot>Generated by render_scorecard.py. Status colours: green = robust, amber = holds with caveats, red = confounded / needs re-test. The framework validates the researcher's <i>execution and trajectory behaviors</i>; it does not test idea <i>generation</i> — the quality of the hypotheses themselves is out of scope by construction.</div>
</div></body></html>"""
    Path(args.output).write_text(doc)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
