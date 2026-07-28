# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import html
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1] / "tickets" / "rounds"
OUT = Path(__file__).parent / "2026-07-27-ticket-review-round-3.html"

CLASS_COLOR = {"frontier-agent": "#7d5bb0", "small-agent": "#3572b0", "human": "#c77d2e"}
CHIP = {"agree": ("#3d8a4e", "agree"), "flag": ("#c77d2e", "flag")}

NOTES = {
    "001-author-replication-plan": ("agree", "Right assignee, claim fields now reference the real paper claims. Still open from round 1: should the plan get an amendment pass once the repo audit lands? Currently nothing consumes the audit — see 002."),
    "002-audit-migration-analysis-repo": ("flag", "Good ticket, but its output is orphaned: repo-audit.md is produced and no ticket consumes it, so the audit findings never flow into the plan or the environment setup. Wire it into 001 (amendment) or 004, or it is dead work. Suggests a rule: every produced artifact needs a consumer or an explicit terminal note."),
    "003-measure-slm-vram-feasibility": ("agree", "Grounding worked: names our actual fleet (nemotron-4b, qwen3.5:4b) and carries resources.md's measure-don't-assume language verbatim. Round 2 listed llama2-7b and neural-chat here."),
    "004-setup-software-agent-sdk-and-test-env": ("agree", "Correctly frontier-agent now, and self-scopes as a smoke test. Minor: its description references repo-audit.md findings without declaring the handoff in consumes."),
    "005-run-baseline-with-generic-harness": ("agree", "Solid — reduced instances, raw trajectories, cost-proxy note per resources.md. Minor gap: it doesn't consume env-setup.md from 004, so the baseline could run in a subtly different environment than the one the smoke test validated."),
    "006-one-harness-optimization-run": ("flag", "Flagged as a choice to review, not an error (per Tyler, 2026-07-27): picking flash-lite as meta-agent to protect the budget is defensible cost logic — but the shipped Lesson 1 says meta-agent quality is the binding factor, and the Claude subscription offers frontier-class at $0 marginal, so we judge the choice misaligned with the replication. The ticket is otherwise well-grounded (raw JSON per Lesson 1, failure-mode list from claim 4). This is exactly the judgment class a reviewer layer should surface rather than the drafting contract over-constrain."),
    "007-measure-optimized-harness-on-same-instances": ("agree", "New versus both prior rounds, and good experimental hygiene: the optimized harness is measured on the same instances as the baseline, cleanly separated from the optimization loop itself."),
    "008-compare-and-produce-artifact": ("agree", "Right assignee; comparison keyed to the pre-registered fidelity contract."),
}

SUMMARY = [
    ("Grounding worked", "The three round-2 drift flags are gone: real fleet named in 003, the paper's raw-JSON lesson cited inside 006, the optimization run assigned frontier-class, claim fields reference actual paper claims. Shipping primary sources instead of paraphrases did exactly what it was supposed to."),
    ("A choice to review, not a failure", "006's flash-lite meta-agent is defensible budget logic that we judge misaligned with the replication (Lesson 1 + the $0 subscription option). Per Tyler: don't overtune the drafting prompt to force such choices — surface them for review. Accumulating approve/reject rationales become a principles corpus for a future reviewer (classifier or prompted LLM), and a documented record of why we chose what we chose."),
    ("Missing handoffs", "repo-audit.md is produced but never consumed; env-setup.md isn't consumed by the baseline. Candidate rule for v1.2: every produced artifact has a consumer or an explicit terminal declaration."),
    ("human_needed: 8/8 empty", "Now an explicit assertion rather than an omission, rendered on every card. Watch which tickets actually generate human moments at execution — that delta is delegation data."),
    ("Depth 5 vs round 2's 4 — and that's fine", "The extra depth is a genuinely new stage: 007 re-measures on the same instances. Better science, slightly longer critical path. Depth is a cost, not a score."),
]

CSS = """
:root { --bg:#f7f6f3; --fg:#232220; --muted:#6e6c66; --card:#fffefb;
  --line:#dedcd4; --accent:#a4711f; --accent-soft:#a4711f14;
  --mono:ui-monospace,'SF Mono',Menlo,monospace; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#191816; --fg:#e8e6e1; --muted:#98958d; --card:#211f1c;
    --line:#3a3833; --accent:#d9a44a; --accent-soft:#d9a44a1a; } }
:root[data-theme="dark"] { --bg:#191816; --fg:#e8e6e1; --muted:#98958d;
  --card:#211f1c; --line:#3a3833; --accent:#d9a44a; --accent-soft:#d9a44a1a; }
:root[data-theme="light"] { --bg:#f7f6f3; --fg:#232220; --muted:#6e6c66;
  --card:#fffefb; --line:#dedcd4; --accent:#a4711f; --accent-soft:#a4711f14; }
* { box-sizing:border-box; }
html { scroll-behavior:smooth; }
@media (prefers-reduced-motion: reduce) { html { scroll-behavior:auto; } }
.card { scroll-margin-top:.8rem; }
.graphwrap a { cursor:pointer; }
.card:target { border-color:var(--accent); background:var(--accent-soft); }
body { margin:0 auto; max-width:44rem; padding:1.4rem 1rem 4rem;
  background:var(--bg); color:var(--fg);
  font:16px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
header h1 { font-size:1.45rem; margin:.1rem 0; text-wrap:balance; }
.eyebrow { color:var(--muted); font-size:.78rem; text-transform:uppercase;
  letter-spacing:.08em; margin:0; }
.gatebar { margin:1rem 0; padding:.65rem .9rem; border:1px solid var(--line);
  border-left:4px solid #c77d2e; border-radius:8px; background:var(--card);
  font-size:.9rem; }
#revbtn { margin:.2rem 0 1rem; padding:.4rem .9rem; border:1px solid var(--line);
  border-radius:999px; background:var(--card); color:var(--muted);
  font:inherit; font-size:.85rem; cursor:pointer; }
.show-rev #revbtn { border-color:var(--accent); color:var(--accent); }
section { display:flex; flex-direction:column; gap:.8rem; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:.85rem 1.1rem; }
.chip { display:none; color:#fff; border-radius:999px; padding:.06rem .6rem;
  font-size:.72rem; font-weight:600; vertical-align:1px; }
.show-rev span.chip { display:inline-block; }
.rev { display:none; }
.show-rev div.rev { display:block; }
.tid { font-family:var(--mono); font-size:.8rem; color:var(--muted); }
h2 { font-size:1rem; margin:0; display:inline; }
h3 { font-size:.8rem; margin:.9rem 0 .2rem; text-transform:uppercase;
  letter-spacing:.07em; color:var(--muted); }
.oneliner { margin:.35rem 0 0; }
.meta { color:var(--muted); font-size:.85rem; margin:.15rem 0; }
.hn { font-size:.85rem; margin:.25rem 0 0; }
.hn b { color:var(--accent); }
ul { margin:.3rem 0 0; padding-left:1.25rem; }
li { margin:.15rem 0; }
details { margin-top:.4rem; }
summary { cursor:pointer; color:var(--muted); font-size:.85rem; }
.note { margin-top:.7rem; padding:.6rem .85rem; background:var(--accent-soft);
  border:1px dashed var(--accent); border-radius:8px; font-size:.9rem; }
.note b { color:var(--accent); font-size:.75rem; text-transform:uppercase;
  letter-spacing:.07em; display:block; margin-bottom:.2rem; }
table { border-collapse:collapse; width:100%; font-size:.88rem;
  font-variant-numeric:tabular-nums; }
td, th { border-bottom:1px solid var(--line); padding:.35rem .5rem; text-align:left; }
.graphwrap { overflow-x:auto; }
.graphwrap path { stroke:var(--muted); stroke-opacity:.45; fill:none; }
.graphwrap text { fill:var(--fg); font-family:var(--mono); }
.graphwrap rect.box { fill:var(--card); stroke:var(--line); }
.legend { font-size:.78rem; color:var(--muted); }
.legend i { display:inline-block; width:.7rem; height:.7rem; border-radius:3px;
  vertical-align:-1px; margin:0 .25rem 0 .8rem; }
footer { margin-top:2rem; color:var(--muted); font-size:.8rem; }
"""

JS = """
document.getElementById('revbtn').addEventListener('click', function () {
  var on = document.body.classList.toggle('show-rev');
  this.textContent = on ? 'Reviewer layer: on' : 'Reviewer layer: off';
});
"""


def esc(s):
    return html.escape(str(s) if s is not None else "")


def load_round(n):
    return [yaml.safe_load(p.read_text()) for p in sorted((BASE / f"round-{n}").glob("0*.yaml"))]


def depths(tickets):
    memo = {}

    def d(t):
        if t["id"] not in memo:
            deps = [x for x in tickets if x["id"] in t["depends_on"]]
            memo[t["id"]] = 1 + max((d(x) for x in deps), default=0)
        return memo[t["id"]]

    for t in tickets:
        d(t)
    return memo


def graph_svg(tickets):
    memo = depths(tickets)
    waves = {}
    pos = {}
    for t in tickets:
        w = memo[t["id"]] - 1
        pos[t["id"]] = (w, len(waves.setdefault(w, [])))
        waves[w].append(t["id"])
    nw, nh = 64, 30
    gx, gy = 120, 48
    top = 34
    width = 24 + (max(w for w, _ in pos.values()) + 1) * gx
    height = top + 12 + (max(len(v) for v in waves.values())) * gy
    edges, nodes = "", ""
    for t in tickets:
        x, y = pos[t["id"]]
        px, py = 12 + x * gx, top + y * gy
        for dep in t["depends_on"]:
            dx, dy = pos[dep]
            x1, y1 = 12 + dx * gx + nw, top + dy * gy + nh / 2
            x2, y2 = px, py + nh / 2
            mx = (x1 + x2) / 2
            span = x - dx
            if y1 == y2 and span > 1:
                bump = y1 - (12 + 7 * span)
                edges += f"<path d='M{x1} {y1} C {mx} {bump}, {mx} {bump}, {x2} {y2}'/>"
            else:
                edges += f"<path d='M{x1} {y1} C {mx} {y1}, {mx} {y2}, {x2} {y2}'/>"
        color = CLASS_COLOR.get(t["assignee_class"], "#888")
        num = t["id"].split("-")[0]
        nodes += (
            f"<a href='#t-{num}'><g><rect class='box' x='{px}' y='{py}' width='{nw}' height='{nh}' rx='7'/>"
            f"<rect x='{px}' y='{py + nh - 4}' width='{nw}' height='4' rx='2' fill='{color}'/>"
            f"<text x='{px + nw / 2}' y='{py + 19}' text-anchor='middle' font-size='13'>{num}</text>"
            f"<title>{esc(t['title'])} ({esc(t['assignee_class'])})</title></g></a>"
        )
    legend = "".join(
        f"<i style='background:{c}'></i>{k}" for k, c in CLASS_COLOR.items()
    )
    return (
        f"<div class='card'><h2>Execution graph</h2>"
        f"<p class='oneliner meta'>left to right = dependency waves; everything in a column can run in parallel</p>"
        f"<div class='graphwrap'><svg viewBox='0 0 {width} {height}' width='{width}' "
        f"height='{height}' role='img' aria-label='ticket dependency graph'>{edges}{nodes}</svg></div>"
        f"<p class='legend'>{legend}</p></div>"
    )


def ticket_card(t):
    chip_kind, note = NOTES.get(t["id"], (None, ""))
    chiph = ""
    if chip_kind:
        color, label = CHIP[chip_kind]
        chiph = f"<span class='chip' style='background:{color}'>{label}</span>"
    acc = "".join(f"<li>{esc(a)}</li>" for a in t["acceptance"])
    deps = ", ".join(t["depends_on"]) or "none"
    produces = ", ".join(t.get("produces") or []) or "none"
    consumes = ", ".join(t.get("consumes") or []) or "none"
    needed = ", ".join(t.get("human_needed") or []) or "none"
    notehtml = f"<div class='note rev'><b>Review note — Fable</b>{esc(note)}</div>" if note else ""
    ceiling = t.get("cost_ceiling_usd") or 0
    cost = f" · ${ceiling} cap" if ceiling else ""
    return f"""
<div class='card' id='t-{esc(t['id'].split('-')[0])}'>
  <span class='tid'>{esc(t['id'].split('-')[0])}</span>
  <h2>{esc(t['title'])}</h2>
  <span class='meta'>· {esc(t['assignee_class'])}{cost}</span> {chiph}
  <p class='oneliner'>{esc(str(t.get('summary'))).strip()}</p>
  <p class='hn'><b>Human needed:</b> {esc(needed)}</p>
  <details>
    <summary>details · {len(t['acceptance'])} acceptance criteria · handoffs</summary>
    <h3>Why</h3><p>{esc(str(t.get('why'))).strip()}</p>
    <h3>What</h3><p>{esc(t['description']).strip()}</p>
    <h3>Acceptance</h3><ul>{acc}</ul>
    <h3>Handoffs</h3>
    <p class='meta'>depends on: {esc(deps)}<br>produces: {esc(produces)}<br>consumes: {esc(consumes)}</p>
    <p class='meta'>serves: {esc(t['claim'])}</p>
  </details>
  {notehtml}
</div>"""


def main():
    rounds = {n: load_round(n) for n in (1, 2, 3)}
    r3 = rounds[3]
    stats = {}
    for n, ts in rounds.items():
        memo = depths(ts)
        wavecount = {}
        for tid, d in memo.items():
            wavecount[d] = wavecount.get(d, 0) + 1
        stats[n] = {
            "tickets": len(ts),
            "human": sum(1 for t in ts if t["assignee_class"] == "human"),
            "depth": max(memo.values()),
            "width": max(wavecount.values()),
        }
    row = lambda label, f: (
        f"<tr><td>{label}</td>" + "".join(f"<td>{f(stats[n])}</td>" for n in (1, 2, 3)) + "</tr>"
    )
    comparison = f"""
<div class='card rev'>
<h2>Rounds compared</h2>
<p class='oneliner meta'>Same model (haiku), blind rounds; only the drafting contract changed. Round 2 added rules; round 3 added primary sources (paper card + resources.md).</p>
<table>
<tr><th></th><th>r1</th><th>r2</th><th>r3</th></tr>
{row("tickets", lambda s: s["tickets"])}
{row("assigned to human", lambda s: s["human"])}
{row("chain depth", lambda s: s["depth"])}
{row("parallel width", lambda s: s["width"])}
<tr><td>schema errors shipped</td><td>2</td><td>0</td><td>0</td></tr>
<tr><td>grounded in our fleet</td><td>—</td><td>no</td><td>yes</td></tr>
<tr><td>meta-agent class correct</td><td>—</td><td>no (small)</td><td>yes (wrong model)</td></tr>
</table>
</div>"""
    summary = "".join(
        f"<div class='card rev'><h2>{esc(k)}</h2><p class='oneliner'>{esc(v)}</p></div>"
        for k, v in SUMMARY
    )
    cards = "".join(ticket_card(t) for t in r3)
    OUT.write_text(f"""<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Derisk tickets — round 3</title>
<style>{CSS}</style>
<header>
  <p class='eyebrow'>Study 007 · investigation 001 · Better Harnesses derisk</p>
  <h1>PoC decomposition — round 3</h1>
  <p class='meta'>{len(r3)} tickets · drafted blind by claude-haiku-4-5 against schema v1.1 with primary sources (paper card + resources.md) in the contract</p>
</header>
<button id='revbtn'>Reviewer layer: off</button>
<div class='gatebar'>Gate <b>derisk-approval</b> is unapproved. Approving this round promotes these tickets and opens wave 1 (four tickets in parallel).</div>
<section>
{graph_svg(r3)}
{comparison}
{summary}
{cards}
</section>
<footer>Generated from tickets/rounds/round-3/*.yaml by build_review_round3.py · tickets are Haiku's verbatim · reviewer layer (chips, notes, comparison) is Fable's and hidden by default · 2026-07-27</footer>
<script>{JS}</script>
""")
    print(OUT)


main()
