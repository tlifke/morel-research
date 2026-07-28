# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import html
from pathlib import Path

import yaml

TICKETS = Path("/Users/tylerlifke/Projects/morel-research/studies/007-autoresearch-infrastructure/investigations/001-better-harnesses-derisk/tickets")
OUT = Path(__file__).parent / "2026-07-27-ticket-review-round-1.html"

STATUS_COLOR = {
    "draft": "#8a8a86", "blocked": "#c77d2e", "ready": "#3572b0",
    "in-progress": "#7d5bb0", "done": "#3d8a4e", "failed": "#b03535",
    "abandoned": "#6b6b67",
}

NOTES = {
    "001-author-replication-plan": "Right assignee, and the acceptance criteria make pre-registration explicit — good. One open question for you: should this instead depend on 002 (the repo audit)? A contract written blind is stronger science, but it can't name concrete metrics if the repo turns out to lack the task pipelines. My proposal: keep 001 first, allow one amendment pass after 002, recorded in the deviation log.",
    "002-audit-migration-repo": "Disagree with the human assignment: cloning and inventorying a repo is exactly the walkthrough's small-agent candidate — cheap to test, and the delegation measurement we want. The dependency on 001 also looks unnecessary; these can run in parallel.",
    "003-setup-software-agent-sdk": "Human is defensible (install quirks, auth), but our working norm is frontier-agent with you watching the run. The $0 ceiling silently assumes the frontier-model smoke run happens under the Claude subscription; if it needs API spend, the ceiling must be nonzero.",
    "004-measure-slm-performance-3080": "Should be agent work: there is a scripted SSH route to the 3080 (the desktop-gpu-access skill). Haiku didn't know that — which is evidence for the constraints doc: assignee hypotheses need the fleet and access routes in the drafting context.",
    "005-run-baseline-budget-approval": "Human again; I'd propose small-agent execution with you watching. The acceptance list is good — summary stats plus at-least-one-success is a real capability-floor probe.",
    "006-harness-optimization-run": "The $3 ceiling is sensible against the $5 phase budget. Human-as-driver is fine for v0 given the watch-the-run convention, but the optimizer itself is frontier-agent work — the assignee taxonomy may need a mixed value. Worth deciding at this review.",
    "007-comparison-artifact": "Right assignee. Note the new rule applies to its output: the comparison must render as a phone-readable HTML card set — if it can't, the analysis is trying to say too much at once.",
}

SUMMARY = [
    ("Delegation skew", "Haiku assigned 5 of 7 tickets to you. My counter-hypothesis: 002, 004, and 005 are agent-drivable. The disagreement itself is the first data for the delegation dataset — we should record both hypotheses and let execution settle it."),
    ("Structure", "The chain is fully linear. 002 can run parallel to 001, and there's a real ordering question between them (see the 001 note). Nothing else structural to complain about."),
    ("One schema bug caught", "Two acceptance items contained unquoted colons and parsed as YAML dicts, not strings. drain.py check now rejects that class of error; the drafting contract for future ticket-writing agents needs a quoting rule — or a self-validation loop where the drafter runs check before finishing."),
    ("Costs", "Proposed ceilings sum to $3.00 against the $5.00 derisk compute budget. Frontier-agent tickets carry $0 on the assumption they run under subscription — that assumption should be blessed or corrected at this gate."),
    ("Gate state", "derisk-approval is unapproved, so no ticket is eligible to run. Approving it (with your rationale + what-would-change-your-mind, stored verbatim in plan.yaml) is the system's first live gate record."),
]

CSS = """
:root {
  --bg:#f7f6f3; --fg:#232220; --muted:#6e6c66; --card:#fffefb;
  --line:#dedcd4; --accent:#a4711f; --accent-soft:#a4711f14; --mono:ui-monospace,'SF Mono',Menlo,monospace;
}
@media (prefers-color-scheme: dark) {
  :root { --bg:#191816; --fg:#e8e6e1; --muted:#98958d; --card:#211f1c;
    --line:#3a3833; --accent:#d9a44a; --accent-soft:#d9a44a1a; }
}
:root[data-theme="dark"] { --bg:#191816; --fg:#e8e6e1; --muted:#98958d;
  --card:#211f1c; --line:#3a3833; --accent:#d9a44a; --accent-soft:#d9a44a1a; }
:root[data-theme="light"] { --bg:#f7f6f3; --fg:#232220; --muted:#6e6c66;
  --card:#fffefb; --line:#dedcd4; --accent:#a4711f; --accent-soft:#a4711f14; }
* { box-sizing:border-box; }
body { margin:0 auto; max-width:44rem; padding:1.4rem 1rem 4rem;
  background:var(--bg); color:var(--fg);
  font:16px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; }
header h1 { font-size:1.5rem; margin:.1rem 0; text-wrap:balance; }
.eyebrow { color:var(--muted); font-size:.78rem; text-transform:uppercase;
  letter-spacing:.08em; margin:0; }
.gatebar { display:flex; align-items:center; gap:.6rem; margin:1rem 0 1.6rem;
  padding:.65rem .9rem; border:1px solid var(--line); border-left:4px solid #c77d2e;
  border-radius:8px; background:var(--card); font-size:.9rem; }
section { display:flex; flex-direction:column; gap:1rem; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:1rem 1.2rem; }
.badge { display:inline-block; color:#fff; border-radius:999px;
  padding:.08rem .65rem; font-size:.75rem; font-weight:600; }
.tid { font-family:var(--mono); font-size:.82rem; color:var(--muted); }
h2 { font-size:1.08rem; margin:.35rem 0 .4rem; text-wrap:balance; }
h3 { font-size:.85rem; margin:1rem 0 0; text-transform:uppercase;
  letter-spacing:.07em; color:var(--muted); }
.meta { color:var(--muted); font-size:.85rem; margin:.15rem 0; }
ul { margin:.35rem 0 0; padding-left:1.25rem; }
li { margin:.2rem 0; }
.note { margin-top:.9rem; padding:.7rem .9rem; background:var(--accent-soft);
  border:1px dashed var(--accent); border-radius:8px; font-size:.92rem; }
.note b { color:var(--accent); font-size:.78rem; text-transform:uppercase;
  letter-spacing:.07em; display:block; margin-bottom:.25rem; }
.sumitem b { display:block; }
footer { margin-top:2.2rem; color:var(--muted); font-size:.8rem; }
"""


def esc(s):
    return html.escape(str(s))


def ticket_card(t):
    color = STATUS_COLOR.get(t["status"], "#888")
    deps = ", ".join(t["depends_on"]) or "none"
    acc = "".join(f"<li>{esc(a)}</li>" for a in t["acceptance"])
    note = NOTES.get(t["id"], "")
    notehtml = f"<div class='note'><b>Review note — Fable</b>{esc(note)}</div>" if note else ""
    return f"""
<div class='card'>
  <span class='badge' style='background:{color}'>{esc(t['status'])}</span>
  <span class='tid'>{esc(t['id'])}</span>
  <h2>{esc(t['title'])}</h2>
  <p class='meta'>assignee: <b>{esc(t['assignee_class'])}</b> · ceiling: ${esc(t['cost_ceiling_usd'])} · depends on: {esc(deps)}</p>
  <p class='meta'>serves: {esc(t['claim'])}</p>
  <p>{esc(t['description']).strip()}</p>
  <h3>Acceptance</h3>
  <ul>{acc}</ul>
  {notehtml}
</div>"""


def main():
    plan = yaml.safe_load((TICKETS / "plan.yaml").read_text())
    tickets = [yaml.safe_load(p.read_text()) for p in sorted(TICKETS.glob("0*.yaml"))]
    human = sum(1 for t in tickets if t["assignee_class"] == "human")
    summary = "".join(
        f"<div class='card sumitem'><b>{esc(k)}</b>{esc(v)}</div>" for k, v in SUMMARY
    )
    cards = "".join(ticket_card(t) for t in tickets)
    OUT.write_text(f"""<title>Derisk tickets — review round 1</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>{CSS}</style>
<header>
  <p class='eyebrow'>Study 007 · investigation 001 · Better Harnesses derisk</p>
  <h1>PoC ticket review — round 1</h1>
  <p class='meta'>{len(tickets)} tickets drafted by claude-haiku-4-5 against the pinned v0 schema · {human}/{len(tickets)} assigned to human · phase budget ${plan['phase_budget_usd']}</p>
</header>
<div class='gatebar'>Gate <b>derisk-approval</b> is unapproved — nothing below can run until you approve it (your rationale is stored verbatim in plan.yaml).</div>
<section>
  {summary}
  {cards}
</section>
<footer>Generated from tickets/*.yaml · cards are Haiku's verbatim; dashed annotations are Fable's review · 2026-07-27</footer>
""")
    print(OUT)


main()
