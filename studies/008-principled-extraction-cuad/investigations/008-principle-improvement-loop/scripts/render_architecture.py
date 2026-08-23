from __future__ import annotations

from pathlib import Path

INV = Path(__file__).resolve().parents[1]
OUT = INV / "reviews" / "harness-map.html"

HTML = """<title>Harness Map</title>
<style>
:root{--bg:#faf9f7;--fg:#1a1a1a;--mut:#6b6b6b;--line:#ddd9d3;--card:#fff;
--new:#2c4f7c;--newbg:#e9eff7;--borrow:#1a6b3c;--borrowbg:#e8f5ed;
--dead:#9a9a9a;--deadbg:#f0efec;--data:#8a5a00;--databg:#fdf2e0}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:26px 20px 70px}
h1{font-size:23px;margin:0 0 4px}
h2{font-size:16px;margin:34px 0 12px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--mut);font-size:13px;margin-bottom:20px}
.legend{display:flex;gap:15px;flex-wrap:wrap;font-size:12.5px;margin:0 0 22px}
.legend span{display:inline-flex;align-items:center;gap:6px}
.sw{width:11px;height:11px;border-radius:3px;display:inline-block}
.stage{background:var(--card);border:1px solid var(--line);border-radius:10px;
padding:0;margin-bottom:11px;overflow:hidden}
.hd{display:flex;align-items:baseline;gap:10px;padding:11px 15px;background:#f7f6f3;
border-bottom:1px solid var(--line)}
.num{font-size:11px;font-weight:700;color:#fff;background:var(--new);border-radius:50%;
width:19px;height:19px;display:grid;place-items:center;flex:none}
.hd b{font-size:14.5px}
.hd .what{color:var(--mut);font-size:12.5px;margin-left:auto;text-align:right}
.body{padding:12px 15px;display:grid;grid-template-columns:1fr 1fr;gap:14px}
.io{font-size:12.5px}
.io h4{margin:0 0 5px;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut)}
code{font:12px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace;background:#f2f1ee;
padding:1px 5px;border-radius:4px}
.file{display:block;margin-bottom:3px}
.tag{display:inline-block;font-size:9.5px;font-weight:700;letter-spacing:.04em;
padding:1px 5px;border-radius:3px;margin-left:5px;vertical-align:1px}
.t-new{background:var(--newbg);color:var(--new)}
.t-bor{background:var(--borrowbg);color:var(--borrow)}
.t-dat{background:var(--databg);color:var(--data)}
.arrow{text-align:center;color:var(--mut);font-size:17px;margin:-4px 0 7px;line-height:1}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}
tr.off td{color:var(--dead)} tr.off code{background:var(--deadbg);color:var(--dead)}
.note{background:var(--newbg);border-left:3px solid var(--new);padding:11px 14px;
border-radius:0 6px 6px 0;font-size:13px;margin:14px 0}
.num2{text-align:right;font-variant-numeric:tabular-nums}
</style>
<div class="wrap">
<h1>How the loop is wired</h1>
<div class="sub">studies/008-principled-extraction-cuad &middot; investigation 008 &middot; the pipeline from frozen text to a rung verdict</div>

<div class="legend">
<span><i class="sw" style="background:var(--newbg);border:1px solid var(--new)"></i>new in this investigation</span>
<span><i class="sw" style="background:var(--borrowbg);border:1px solid var(--borrow)"></i>borrowed from study harness</span>
<span><i class="sw" style="background:var(--databg);border:1px solid var(--data)"></i>data on disk</span>
</div>

<div class="note"><strong>Start here:</strong> <code>loop/run_slice.py</code> is the spine &mdash; read it top to
bottom and every other file appears in the order it is used. <code>loop/prompt.py</code> is what a principle
actually changes. <code>loop/ladder.py</code> is where a principle lives or dies.</div>

<h2>The pipeline</h2>
STAGES

<h2>What is borrowed from the study harness, and what is not</h2>
<div class="note">The study harness is 3,063 lines. The loop touches about a third of it and deliberately
bypasses the rest &mdash; <code>runner.py</code> and <code>metrics.py</code> alone are 1,598 lines built for the
earlier C1/C2/C3 framing, with their own trial records, repair loop, and Level A/B/C metrics. Reusing them
would have meant inheriting that framing. Greyed rows are not imported by anything in the loop.</div>
<table>
<tr><th>file</th><th class="num2">lines</th><th>used for</th></tr>
BORROW
</table>

<h2>Where the data lands</h2>
<table>
<tr><th>path</th><th>written by</th><th>contains</th></tr>
DATA
</table>
</div>
"""

STAGES = [
    (1, "Freeze the task", "scripts/build_task_definition.py", "new",
     ["ContractEval SYSTEM_PROMPT <span class='tag t-bor'>pinned</span>",
      "data/raw/CUADv1.json questions",
      "data/processed/categories.json"],
     ["task_definition/v1.json <span class='tag t-dat'>sha-pinned</span>"],
     "run once; 7 tests assert it never drifts"),
    (2, "Choose the slice", "scripts/select_mvp_contracts.py", "new",
     ["data/processed/splits/principle_train.txt", "data/processed/instances.jsonl"],
     ["mvp_slice.json <span class='tag t-dat'></span>"],
     "deterministic, no seed"),
    (3, "Assemble the prompt", "loop/prompt.py", "new",
     ["task_definition/v1.json", "the contract text",
      "a PrincipleSet <span class='tag t-bor'>harness.models</span>",
      "schema <span class='tag t-bor'>harness.output_schema</span>"],
     ["system + user messages"],
     "the ONLY thing that differs between arms is the principles block"),
    (4, "Sample", "loop/run_slice.py", "new",
     ["messages", "TinkerBackend <span class='tag t-bor'>harness.backends</span>"],
     ["raw response text", "reasoning text", "a TrialRecord"],
     "temp 1.0 / top_p 0.95, k repeats, resumable by trial_id"),
    (5, "Parse", "loop/models.py", "new",
     ["raw response", "parse_output <span class='tag t-bor'>harness.parsing</span>"],
     ["LoopOutput: 41 decisions", "conformance counts"],
     "strict; defects counted, never repaired"),
    (6, "Record", "loop/ledger.py", "new",
     ["TrialRecord"],
     ["runs/&lt;run_id&gt;/trials.jsonl <span class='tag t-dat'></span>",
      "runs/&lt;run_id&gt;/manifest.json"],
     "append-only, keyed on task-def + principle-set + arm + model + contract + repeat"),
    (7, "Score", "loop/scoring.py &rarr; scripts/score_run.py", "new",
     ["trials.jsonl", "CUAD gold",
      "score/is_match <span class='tag t-bor'>harness.comparison_metrics</span>"],
     ["runs/&lt;run_id&gt;/score.json <span class='tag t-dat'></span>",
      "runs/&lt;run_id&gt;/failures.jsonl <span class='tag t-dat'></span>"],
     "detection 2&times;2 + localization on the TP cell; each cell labelled with a failure class"),
    (8, "Diagnose", "scripts/make_casefile.py", "new",
     ["failures.jsonl"],
     ["casefile-&lt;class&gt;.json <span class='tag t-dat'></span>"],
     "persistent cells only (2-of-3), ranked &mdash; this is the proposer's input"),
    (9, "Judge", "loop/ladder.py", "new",
     ["control run score.json + failures.jsonl", "candidate run, same two"],
     ["RungResult: passed, reasons, F2 delta"],
     "applies pre-registration.md; the score decides, citation only routes"),
]

BORROW = [
    ("harness/backends/tinker_backend.py", 215, "the API client. top_p forwarding added here.", True),
    ("harness/comparison_metrics.py", 346, "CUAD-comparable scoring: jaccard, is_match, detection/localization.", True),
    ("harness/models.py", 152, "<code>Principle</code> / <code>PrincipleSet</code> only. Its <code>TaskOutput</code> is NOT used &mdash; see Decision 7.", True),
    ("harness/output_schema.py", 108, "serialises the output model into the prompt with the category enum.", True),
    ("harness/parsing.py", 71, "pulls the JSON object out of the response.", True),
    ("harness/model_registry.py", 51, "substrate-neutral model ids.", True),
    ("harness/metrics.py", 909, "Level A/B/C, citation metrics, verbatim classes. Earlier framing.", False),
    ("harness/runner.py", 689, "the C1/C2/C3 trial runner, repair loop, condition grid.", False),
    ("harness/prompts.py", 183, "the C1/C2/C3 prompt builder. <code>loop/prompt.py</code> replaces it.", False),
    ("harness/trace_store.py", 199, "tier-1 trace store. The ledger replaces it.", False),
    ("harness/store.py", 135, "trial store for the grid.", False),
    ("harness/env.py", 105, "the env abstraction.", False),
]

DATA = [
    ("task_definition/v1.json", "build_task_definition.py", "frozen instruction + 41 questions + content sha"),
    ("mvp_slice.json", "select_mvp_contracts.py", "the 5 contracts and why each was chosen"),
    ("runs/&lt;id&gt;/manifest.json", "loop/ledger.py", "model, sampling, versions, backend description"),
    ("runs/&lt;id&gt;/trials.jsonl", "loop/ledger.py", "one row per trial: key, outcome, tokens, parsed output"),
    ("runs/&lt;id&gt;/&lt;trial&gt;.txt", "loop/run_slice.py", "the raw response, byte for byte"),
    ("runs/&lt;id&gt;/&lt;trial&gt;.reasoning.txt", "loop/run_slice.py", "the chain of thought (new; absent for baseline-001)"),
    ("runs/&lt;id&gt;/score.json", "scripts/score_run.py", "per-trial detection + localization, conformance totals"),
    ("runs/&lt;id&gt;/failures.jsonl", "scripts/score_run.py", "one row per failing cell, with gold and predicted text"),
    ("runs/&lt;id&gt;/casefile-*.json", "scripts/make_casefile.py", "persistent cells for one failure class"),
]


def main():
    st = []
    for i, (n, name, files, _kind, ins, outs, note) in enumerate(STAGES):
        st.append("<div class='stage'>")
        st.append(f"<div class='hd'><span class='num'>{n}</span><b>{name}</b>"
                  f"<span class='what'>{note}</span></div>")
        st.append("<div class='body'>")
        st.append("<div class='io'><h4>in</h4>" +
                  "".join(f"<span class='file'>{x}</span>" for x in ins) + "</div>")
        st.append("<div class='io'><h4>out</h4>" +
                  "".join(f"<span class='file'>{x}</span>" for x in outs) + "</div>")
        st.append("</div>")
        st.append(f"<div class='body' style='padding-top:0;grid-template-columns:1fr'>"
                  f"<div class='io'><h4>code</h4><code>{files}</code></div></div>")
        st.append("</div>")
        if i < len(STAGES) - 1:
            st.append("<div class='arrow'>&darr;</div>")

    br = []
    for path, lines, why, used in BORROW:
        cls = "" if used else " class='off'"
        br.append(f"<tr{cls}><td><code>{path}</code></td><td class='num2'>{lines}</td><td>{why}</td></tr>")

    dt = [f"<tr><td><code>{p}</code></td><td><code>{w}</code></td><td>{c}</td></tr>"
          for p, w, c in DATA]

    OUT.write_text(
        HTML.replace("STAGES", "\n".join(st))
            .replace("BORROW", "\n".join(br))
            .replace("DATA", "\n".join(dt))
    )
    print(f"wrote {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
