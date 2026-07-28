# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import html
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parents[1] / "tickets" / "rounds"
OUT = Path(__file__).parent / "2026-07-27-ticket-review-round-2.html"

STATUS_COLOR = {"draft": "#8a8a86", "ready": "#3572b0", "done": "#3d8a4e", "failed": "#b03535"}
CHIP = {"agree": ("#3d8a4e", "agree"), "flag": ("#c77d2e", "flag")}

NOTES = {
    "001-write-replication-plan": ("flag", "Right assignee, but real content drift: it restates the paper as 3 invented claims that don't match the paper card's 7. The blind contract summarized the paper instead of including the claims verbatim — contract v3 should ship the paper card itself. The plan-vs-audit ordering question from round 1 is now resolved by parallelism, but an amendment pass after the audit may still be wanted."),
    "002-audit-repo": ("agree", "Now small-agent and dependency-free — matches the round-1 review recommendation exactly. Acceptance list is stronger than round 1's."),
    "003-sdk-setup": ("agree", "Reasonable, but zero human_touchpoints declared feels optimistic — SSH keys, installs, or sudo on the desktop are exactly the touchpoint class we predicted. Expect this ticket to generate the first real touchpoint data."),
    "004-frontier-baseline": ("flag", "Conflation: it wants the 'frontier' baseline run on the strongest local ollama model and suggests llama2-70b — which neither fits a 12GB card nor is frontier. The paper's baseline is a frontier API model. Either run the LLM baseline under the Claude subscription or rename this ticket an environment smoke test."),
    "005-slm-measurement": ("flag", "Right shape, wrong fleet: candidate list (llama2-7b, neural-chat) is dated and generic; our actual local fleet (nemotron-4b, qwen3.5:4b, ministral-class) is absent. Same root cause as 001 — the constraints doc wasn't in the drafting context."),
    "006-slm-baseline": ("agree", "Good ticket. Clean handoffs, per-instance raw logs, aggregate stats. Nothing to change."),
    "007-optimization-run": ("flag", "Assignee disagreement: a small agent can babysit the run, but the optimizer's meta-agent must be frontier-class — the paper's own lesson is that a cheaper meta-agent produced worse harnesses. Suggest frontier-agent, or split driver vs meta-model explicitly."),
    "008-comparison-artifact": ("agree", "Right assignee, and it self-applies the HTML rule — self-contained, human-readable without external context. The acceptance table mirrors the fidelity contract correctly."),
}

SUMMARY = [
    ("Shape: graph achieved", "Chain depth 7 → 4, parallel width 1 → 4. Four tickets (001, 002, 003, 005) can start the moment the gate opens; every edge is justified by a named artifact handoff."),
    ("Delegation swing", "Round 1: 5/7 human. Round 2: 0/8 human, 6/8 small-agent. The AI-first rule worked, possibly too well — see the 007 flag. Both rounds are recorded hypotheses; execution settles them."),
    ("Self-validation worked", "Round 1 shipped 2 YAML parse errors. Round 2 ran drain.py check itself and shipped clean on the same model. Cheap fix, real effect."),
    ("Content drift where context was summarized", "The three flags (001's invented claims, 004's llama2-70b, 005's dated fleet) share one root cause: the blind contract paraphrased the paper and hardware instead of shipping the paper card + constraints doc. That's the strongest evidence yet that constraints.md belongs in every drafting context."),
    ("No human touchpoints declared anywhere", "Suspicious given SSH/sudo realities on the desktop. Worth watching which tickets actually generate touchpoints at execution."),
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
body { margin:0 auto; max-width:44rem; padding:1.4rem 1rem 4rem;
  background:var(--bg); color:var(--fg);
  font:16px/1.5 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
header h1 { font-size:1.45rem; margin:.1rem 0; text-wrap:balance; }
.eyebrow { color:var(--muted); font-size:.78rem; text-transform:uppercase;
  letter-spacing:.08em; margin:0; }
.gatebar { margin:1rem 0 1.4rem; padding:.65rem .9rem; border:1px solid var(--line);
  border-left:4px solid #c77d2e; border-radius:8px; background:var(--card);
  font-size:.9rem; }
section { display:flex; flex-direction:column; gap:.8rem; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:.85rem 1.1rem; }
.badge, .chip { display:inline-block; color:#fff; border-radius:999px;
  padding:.06rem .6rem; font-size:.72rem; font-weight:600; vertical-align:1px; }
.tid { font-family:var(--mono); font-size:.8rem; color:var(--muted); }
h2 { font-size:1rem; margin:0; display:inline; }
h3 { font-size:.8rem; margin:.9rem 0 .2rem; text-transform:uppercase;
  letter-spacing:.07em; color:var(--muted); }
.oneliner { margin:.35rem 0 0; }
.meta { color:var(--muted); font-size:.85rem; margin:.15rem 0; }
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
.waves { font-family:var(--mono); font-size:.82rem; overflow-x:auto;
  white-space:nowrap; padding:.2rem 0; }
footer { margin-top:2rem; color:var(--muted); font-size:.8rem; }
"""


def esc(s):
    return html.escape(str(s or ""))


def load_round(n):
    return [yaml.safe_load(p.read_text()) for p in sorted((BASE / f"round-{n}").glob("0*.yaml"))]


def waves(tickets):
    ids = {t["id"] for t in tickets}
    depth = {}

    def d(t):
        if t["id"] not in depth:
            deps = [x for x in tickets if x["id"] in t["depends_on"]]
            depth[t["id"]] = 1 + max((d(x) for x in deps), default=0)
        return depth[t["id"]]

    for t in tickets:
        d(t)
    levels = {}
    for t in tickets:
        levels.setdefault(depth[t["id"]], []).append(t["id"].split("-")[0])
    return [sorted(v) for _, v in sorted(levels.items())], max(depth.values())


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
    touch = ", ".join(t.get("human_touchpoints") or []) or "none"
    notehtml = f"<div class='note'><b>Review note — Fable</b>{esc(note)}</div>" if note else ""
    return f"""
<div class='card'>
  <span class='tid'>{esc(t['id'].split('-')[0])}</span>
  <h2>{esc(t['title'])}</h2>
  <span class='meta'>· {esc(t['assignee_class'])} · ${esc(t['cost_ceiling_usd'])}</span> {chiph}
  <p class='oneliner'>{esc(t.get('summary')).strip()}</p>
  <details>
    <summary>details — why, acceptance, handoffs{', review note' if note else ''}</summary>
    <h3>Why</h3><p>{esc(t.get('why')).strip()}</p>
    <h3>What</h3><p>{esc(t['description']).strip()}</p>
    <h3>Acceptance</h3><ul>{acc}</ul>
    <h3>Handoffs</h3>
    <p class='meta'>depends on: {esc(deps)}<br>produces: {esc(produces)}<br>consumes: {esc(consumes)}<br>human touchpoints: {esc(touch)}</p>
    <p class='meta'>serves: {esc(t['claim'])}</p>
    {notehtml}
  </details>
</div>"""


def main():
    r1, r2 = load_round(1), load_round(2)
    w2, depth2 = waves(r2)
    _, depth1 = waves(r1)
    wavestr = "  →  ".join("[" + " ".join(w) + "]" for w in w2)
    comparison = f"""
<div class='card'>
<h2>Round 1 → round 2</h2>
<p class='oneliner meta'>Same model (haiku), same task, blind rounds; only the drafting contract changed.</p>
<table>
<tr><th></th><th>round 1</th><th>round 2</th></tr>
<tr><td>tickets</td><td>7</td><td>{len(r2)}</td></tr>
<tr><td>assigned to human</td><td>5</td><td>{sum(1 for t in r2 if t['assignee_class'] == 'human')}</td></tr>
<tr><td>chain depth</td><td>{depth1}</td><td>{depth2}</td></tr>
<tr><td>parallel width</td><td>1</td><td>{max(len(w) for w in w2)}</td></tr>
<tr><td>schema errors shipped</td><td>2</td><td>0 (self-validated)</td></tr>
<tr><td>summary / why / handoffs</td><td>absent</td><td>all present</td></tr>
</table>
<h3>Execution waves</h3>
<div class='waves'>{esc(wavestr)}</div>
</div>"""
    summary = "".join(
        f"<div class='card'><h2>{esc(k)}</h2><p class='oneliner'>{esc(v)}</p></div>"
        for k, v in SUMMARY
    )
    cards = "".join(ticket_card(t) for t in r2)
    OUT.write_text(f"""<meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>Derisk tickets — review round 2</title>
<style>{CSS}</style>
<header>
  <p class='eyebrow'>Study 007 · investigation 001 · Better Harnesses derisk</p>
  <h1>PoC ticket review — round 2</h1>
  <p class='meta'>{len(r2)} tickets · drafted blind by claude-haiku-4-5 against schema v1 · titles + one-liners first, tap for detail</p>
</header>
<div class='gatebar'>Gate <b>derisk-approval</b> is still unapproved. Approving this round (with rationale) promotes these tickets and opens wave 1.</div>
<section>
{comparison}
{summary}
{cards}
</section>
<footer>Generated from tickets/rounds/round-2/*.yaml by build_review_round2.py · tickets are Haiku's verbatim; chips and dashed notes are Fable's review · 2026-07-27</footer>
""")
    print(OUT)


main()
