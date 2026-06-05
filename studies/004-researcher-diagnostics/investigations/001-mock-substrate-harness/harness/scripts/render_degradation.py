import argparse
import glob
import json
import statistics as st
from pathlib import Path

MODELS = [
    ("nemotron-4b · served 4K (default)", "runs/loop_batch"),
    ("nemotron-4b · served 32K", "runs/loop_batch_32k"),
    ("nemotron-4b · served 131K", "runs/loop_batch_131k"),
    ("qwen3.5-4b · served 32K", "runs/loop_batch_qwen35_4b"),
    ("gemini-3.1-flash-lite · cloud (~1M)", "runs/loop_batch_gem31lite"),
]


def compact(train):
    if train >= 1000 and train % 1000 == 0:
        return f"{train//1000}k"
    if train >= 1000:
        return f"{train/1000:.1f}k"
    return str(train)


def halves(rows):
    fh, sh = [], []
    for d in rows:
        t = d["trajectory"]
        mid = len(t) // 2
        if mid:
            fh.append(sum(1 for x in t[:mid] if x["repeat"]) / mid)
            sh.append(sum(1 for x in t[mid:] if x["repeat"]) / (len(t) - mid))
    return (st.mean(fh) if fh else 0), (st.mean(sh) if sh else 0)


def strip(traj):
    mid = len(traj) // 2
    cells = []
    for i, x in enumerate(traj):
        if i == mid and mid:
            cells.append('<span class="mid"></span>')
        cls = "rep" if x["repeat"] else "new"
        cells.append(f'<span class="cell {cls}" title="train {x["train"]}, epochs {x["epochs"]}, pgr {x["pgr"]:.3f}{" — REPEAT" if x["repeat"] else ""}">{compact(x["train"])}<sub>e{x["epochs"]}</sub></span>')
    return "".join(cells)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="../assets/degradation.html")
    args = ap.parse_args()

    blocks = ""
    summary = ""
    for label, d in MODELS:
        files = sorted(glob.glob(f"{d}/run_*/loop_summary.json"))
        if not files:
            continue
        rows = [json.load(open(f)) for f in files]
        fh, sh = halves(rows)
        summary += (
            f'<tr><td>{label}</td><td class=num>{len(rows)}</td>'
            f'<td class=num>{fh*100:.0f}%</td><td class=num><b>{sh*100:.0f}%</b></td>'
            f'<td><span class=barwrap><span class=bar style="width:{min(sh*100,100):.0f}%"></span></span></td></tr>'
        )
        runrows = "".join(f'<div class=run><span class=rlabel>run {i+1}</span><div class=strip>{strip(r["trajectory"])}</div></div>' for i, r in enumerate(rows[:6]))
        blocks += f'<section class=model><h3>{label} <span class=hl>1st-half {fh*100:.0f}% → 2nd-half {sh*100:.0f}% repeats</span></h3>{runrows}</section>'

    doc = f"""<!doctype html><html lang=en><head><meta charset=utf-8>
<meta name=viewport content="width=device-width, initial-scale=1"><title>Coherence degradation — what it looks like</title>
<style>
:root{{--ink:#0f172a;--mut:#64748b;--line:#e2e8f0;--bg:#f8fafc;--new:#16a34a;--rep:#dc2626}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:14.5px/1.5 ui-sans-serif,system-ui,sans-serif}}
.wrap{{max-width:1000px;margin:0 auto;padding:30px 22px 80px}}
h1{{font-size:22px;margin:0 0 3px}} .sub{{color:var(--mut);font-size:13px;margin:0 0 18px}}
h2{{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:26px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}}
.note{{background:#eef2ff;border:1px solid #c7d2fe;border-radius:10px;padding:11px 15px;color:#312e81;font-size:13px;margin-bottom:16px}}
.key{{display:inline-flex;gap:14px;font-size:12px;color:#334155;margin:2px 0 10px}}
.sw{{display:inline-block;width:12px;height:12px;border-radius:3px;vertical-align:-2px;margin-right:4px}}
table{{border-collapse:collapse;width:100%;background:#fff;border:1px solid var(--line);border-radius:10px;overflow:hidden;margin-bottom:6px}}
td,th{{padding:7px 12px;border-bottom:1px solid var(--line);font-size:13px;text-align:left}} td.num{{text-align:right;font-variant-numeric:tabular-nums}}
.barwrap{{display:inline-block;width:160px;height:10px;background:#f1f5f9;border-radius:5px;overflow:hidden}}
.bar{{display:block;height:100%;background:var(--rep)}}
.model{{background:#fff;border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin-bottom:12px}}
.model h3{{font-size:14.5px;margin:0 0 8px;display:flex;justify-content:space-between;align-items:baseline;gap:10px}}
.hl{{font-size:12px;color:var(--mut);font-weight:500}}
.run{{display:flex;align-items:center;gap:10px;margin:4px 0}}
.rlabel{{font-size:11px;color:var(--mut);width:44px;flex:none}}
.strip{{display:flex;align-items:stretch;flex-wrap:nowrap;overflow-x:auto;gap:3px}}
.cell{{flex:none;min-width:34px;text-align:center;font-size:11px;font-weight:600;padding:4px 2px;border-radius:5px;color:#fff}}
.cell sub{{font-size:8.5px;opacity:.85}}
.cell.new{{background:var(--new)}} .cell.rep{{background:var(--rep)}}
.mid{{flex:none;width:0;border-left:2px dashed #94a3b8;margin:0 3px}}
.foot{{color:var(--mut);font-size:12px;margin-top:26px;border-top:1px solid var(--line);padding-top:12px}}
</style></head><body><div class=wrap>
<h1>Coherence degradation — what it actually looks like</h1>
<p class=sub>study 004 · each model runs a 15-iteration hyperparameter search on a scripted landscape; the prompt tells it not to re-run configs it already tried.</p>
<div class=note>Every cell below is <b>one experiment the model ran</b> (a config: train-size + epochs). <span style="color:#16a34a;font-weight:700">Green</span> = a config it had not tried; <span style="color:#dc2626;font-weight:700">red</span> = a <b>re-run of one it already did</b> (a coherence failure — it forgot). The dashed line marks each run's midpoint. <b>Degradation = red cells clustering in the second half.</b></div>
<div class=key><span><span class=sw style="background:#16a34a"></span>new config</span><span><span class=sw style="background:#dc2626"></span>repeat (forgot it already tried this)</span></div>

<h2>Summary — late-run repeat rate by model</h2>
<table><tr><th>model / served window</th><th class=num>runs</th><th class=num>1st-half</th><th class=num>2nd-half</th><th>2nd-half repeats</th></tr>{summary}</table>

<h2>The trajectories</h2>
{blocks}

<div class=foot>Lower 2nd-half = better long-horizon coherence. More context never helps nemotron (4K→131K worsens); a stronger model (gemini-3.1-flash-lite) halves the decay but does not remove it — the wall moves, it doesn't vanish.</div>
</div></body></html>"""
    Path(args.output).write_text(doc)
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()
