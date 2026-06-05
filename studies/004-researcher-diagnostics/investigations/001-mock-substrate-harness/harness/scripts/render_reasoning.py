import argparse
import html
import json
import re
from pathlib import Path

RUNS = [
    ("gemini-3.1-flash-lite", "success", "18 iterations, 0 repeats — sustained", "runs/loop_batch_gem31lite/run_03/trace.jsonl"),
    ("gemini-3.1-flash-lite", "failure", "20 iterations, 80% repeats late — declares 'done' early then spins", "runs/loop_batch_gem31lite/run_05/trace.jsonl"),
    ("gemini-3.5-flash", "success", "13 iterations, 1 repeat", "runs/loop_batch_gem35/run_06/trace.jsonl"),
    ("gemini-3.5-flash", "failure", "30 iterations, 2nd-half 100% repeats — heavy premature-convergence spin", "runs/loop_batch_gem35/run_02/trace.jsonl"),
    ("nemotron-4b", "success", "9 iterations, 0 repeats — clean", "runs/loop_batch_32k/run_04/trace.jsonl"),
    ("nemotron-4b", "failure", "21 iterations, 73% repeats late — loses track / forgets", "runs/loop_batch_32k/run_05/trace.jsonl"),
    ("qwen3.5-4b", "partial", "9 iterations before stalling — ~20 experiments/iter, deliberately re-tests configs it remembers (thorough, not incoherent; too slow to finish)", "runs/loop_batch_qwen35_4b/run_01/trace.jsonl"),
]


def esc(s):
    return html.escape(str(s))


def cfg(cmd):
    t = re.search(r"--train-size\s+(\d+)", cmd)
    e = re.search(r"--epochs\s+(\d+)", cmd)
    return (int(t.group(1)) if t else None, int(e.group(1)) if e else None)


def iterations(trace_path):
    recs = [json.loads(l) for l in Path(trace_path).read_text().splitlines() if l.strip()]
    its, cur, seen = [], None, set()
    for r in recs:
        k = r["kind"]
        if k == "input":
            if cur:
                its.append(cur)
            cur = {"think": [], "configs": [], "pgr": None}
        elif cur is None:
            continue
        elif k == "thinking" and r.get("text", "").strip():
            cur["think"].append(r["text"].strip())
        elif k == "tool_use" and r.get("name") == "bash":
            c = cfg(str(r.get("arguments", {}).get("command", "")))
            if c[0]:
                key = f"{c[0]}/{c[1]}"
                cur["configs"].append((key, key in seen))
                seen.add(key)
        elif k == "tool_result":
            m = re.search(r'"pgr":\s*([0-9.]+)', r.get("text", ""))
            if m:
                cur["pgr"] = float(m.group(1))
        elif k == "assistant_text" and r.get("text", "").strip():
            cur["think"].append("[answer] " + r["text"].strip())
    if cur:
        its.append(cur)
    return its


def render_run(model, status, note, trace_path):
    its = iterations(trace_path)
    n = len(its)
    rows = ""
    for i, it in enumerate(its):
        late = i >= n / 2
        cfgs = "".join(
            f'<span class="cfg {"rep" if rep else "new"}">{esc(k)}{" ↺" if rep else ""}</span>'
            for k, rep in it["configs"]
        ) or '<span class="cfg none">— no experiment run —</span>'
        pgr = f'<span class="pgr">PGR {it["pgr"]:.3f}</span>' if it["pgr"] is not None else ""
        think = esc("\n\n".join(it["think"])) or "<i>(no reasoning logged)</i>"
        rows += (
            f'<div class="it{" late" if late else ""}">'
            f'<div class="ith"><span class="itn">iter {i+1}</span>{cfgs}{pgr}</div>'
            f'<div class="think">{think}</div></div>'
        )
    cls = "ok" if status == "success" else "bad" if status == "failure" else "neutral"
    return (
        f'<section class="run {cls}"><h3>{esc(model)} '
        f'<span class="badge {cls}">{status.upper()}</span> '
        f'<span class="rnote">{esc(note)}</span></h3>{rows}</section>'
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="../assets/reasoning.html")
    args = ap.parse_args()
    blocks = "".join(render_run(*r) for r in RUNS)
    doc = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1"><title>Reasoning — success vs failure runs</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f8fafc}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.55 ui-sans-serif,system-ui,sans-serif}}
.wrap{{max-width:920px;margin:0 auto;padding:30px 22px 80px}}
h1{{font-size:22px;margin:0 0 3px}} .sub{{color:var(--mut);font-size:13px;margin:0 0 16px}}
.note{{background:#eef2ff;border:1px solid #c7d2fe;border-radius:10px;padding:11px 15px;color:#312e81;font-size:13px;margin-bottom:16px}}
.run{{background:#fff;border:1px solid var(--line);border-left:5px solid;border-radius:12px;padding:14px 16px;margin-bottom:14px}}
.run.ok{{border-left-color:#16a34a}} .run.bad{{border-left-color:#dc2626}} .run.neutral{{border-left-color:#d97706}}
.run h3{{font-size:15px;margin:0 0 10px;display:flex;align-items:center;gap:10px;flex-wrap:wrap}}
.badge{{color:#fff;font-size:11px;font-weight:700;padding:2px 9px;border-radius:5px}}
.badge.ok{{background:#16a34a}} .badge.bad{{background:#dc2626}} .badge.neutral{{background:#d97706}}
.rnote{{color:var(--mut);font-size:12.5px;font-weight:400}}
.it{{border-top:1px solid var(--line);padding:8px 0}}
.it.late{{background:#fef9f9}}
.ith{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px}}
.itn{{font-size:11px;color:var(--mut);font-weight:700;min-width:48px}}
.cfg{{font-family:ui-monospace,Menlo,monospace;font-size:11px;font-weight:600;padding:1px 7px;border-radius:5px;color:#fff}}
.cfg.new{{background:#16a34a}} .cfg.rep{{background:#dc2626}} .cfg.none{{background:#94a3b8}}
.pgr{{font-size:11px;color:#475569;margin-left:auto}}
.think{{font-size:12.5px;color:#334155;white-space:pre-wrap;background:#f8fafc;border-radius:6px;padding:7px 10px;max-height:320px;overflow-y:auto}}
.foot{{color:var(--mut);font-size:12px;margin-top:24px;border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class=wrap>
<h1>What the reasoning looks like — success vs failure</h1>
<p class=sub>study 004 · two models, one clean run and one collapse run each. Each block is the per-iteration reasoning. <b>Green</b> config = new, <b>red ↺</b> = a re-run it already did. Late-half iterations are tinted.</p>
<div class=note>The two models fail <b>differently</b>, even though both show up as repeats (red ↺). <b>gemini</b> doesn't forget — in its failure run it declares victory early ("I conclude the iteration process", "fully optimized", "verified its robustness") and then <b>spins</b>, re-running known configs while narrating that it's done (premature convergence / context anxiety). <b>nemotron</b> instead <b>loses track</b> — later iterations get vaguer and stop referencing what was already tried. The <b>success</b> runs of both keep citing concrete prior results (gemini literally maintains a PGR table) the whole way. <b>qwen3.5-4b</b> is a third profile entirely: it remembers well and re-runs configs <i>on purpose</i> to confirm them — its repeats are deliberate, which is exactly why a raw repeat count mislabels a thorough model as "incoherent." (It's also why it never finished — ~20 experiments per iteration.)</div>
{blocks}
<div class=foot>Selected runs: gemini-3.1-flash-lite run_03 / run_05; nemotron-4b (32K) run_04 / run_05. Full per-iteration reasoning, untruncated.</div>
</div></body></html>"""
    Path(args.output).write_text(doc)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
