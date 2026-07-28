# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml"]
# ///
import argparse
import datetime
import html
import subprocess
import sys
from pathlib import Path

import yaml

REQUIRED = [
    "id", "title", "summary", "why", "claim", "description", "acceptance",
    "assignee_class", "depends_on", "produces", "consumes",
    "human_needed", "gate", "cost_ceiling_usd", "status", "provenance",
    "related", "created",
]
STATUSES = {"draft", "blocked", "ready", "in-progress", "done", "failed", "abandoned"}
CLASSES = {"human", "frontier-agent", "small-agent"}
OPEN = {"draft", "blocked", "ready", "in-progress"}

STATUS_COLOR = {
    "draft": "#8a8a8a", "blocked": "#c77d2e", "ready": "#3572b0",
    "in-progress": "#7d5bb0", "done": "#3d8a4e", "failed": "#b03535",
    "abandoned": "#666666",
}


def load(tickets_dir):
    plan_path = next(
        (d / "plan.yaml" for d in [tickets_dir, *tickets_dir.parents[:2]] if (d / "plan.yaml").exists()),
        None,
    )
    if plan_path is None:
        sys.exit(f"no plan.yaml found in or above {tickets_dir}")
    plan = yaml.safe_load(plan_path.read_text())
    tickets = {}
    for p in sorted(tickets_dir.glob("[0-9][0-9][0-9]-*.yaml")):
        t = yaml.safe_load(p.read_text())
        t["_path"] = p
        if "human_needed" not in t and "human_touchpoints" in t:
            t["human_needed"] = t["human_touchpoints"]
            t["_legacy_touchpoints"] = True
        tickets[t.get("id", p.stem)] = t
    return plan, tickets


def gate_approved(plan, name):
    g = plan.get("gates", {}).get(name)
    return bool(g and g.get("approved_by"))


def eligible(t, plan, tickets):
    if t["status"] not in OPEN:
        return False
    if t.get("gate") and not gate_approved(plan, t["gate"]):
        return False
    return all(tickets.get(d, {}).get("status") == "done" for d in t["depends_on"])


def check(plan, tickets):
    errors, warnings = [], []
    for tid, t in tickets.items():
        for f in REQUIRED:
            if f not in t:
                errors.append(f"{tid}: missing field '{f}'")
        if t.get("status") not in STATUSES:
            errors.append(f"{tid}: invalid status '{t.get('status')}'")
        if t.get("assignee_class") not in CLASSES:
            errors.append(f"{tid}: invalid assignee_class '{t.get('assignee_class')}'")
        for d in t.get("depends_on", []):
            if d not in tickets:
                errors.append(f"{tid}: unknown dependency '{d}'")
        g = t.get("gate")
        if g and g not in plan.get("gates", {}):
            errors.append(f"{tid}: unknown gate '{g}'")
        if t.get("status") in {"ready", "in-progress"} and t.get("cost_ceiling_usd") is None:
            errors.append(f"{tid}: status '{t['status']}' with no cost ceiling")
        if not t.get("acceptance"):
            errors.append(f"{tid}: empty acceptance criteria")
        if t.get("_legacy_touchpoints"):
            warnings.append(f"{tid}: uses legacy field 'human_touchpoints' (schema v1.1 name is 'human_needed')")
        for a in t.get("acceptance") or []:
            if not isinstance(a, str):
                errors.append(f"{tid}: acceptance item is not a string (unquoted colon?): {a}")
        for d in t.get("depends_on", []):
            dep = tickets.get(d)
            if dep is not None:
                produced = set(dep.get("produces") or [])
                consumed = set(t.get("consumes") or [])
                if produced and consumed and not (produced & consumed):
                    warnings.append(f"{tid}: edge to '{d}' not justified by a handoff (consumes ∩ produces is empty)")
        for c in t.get("consumes") or []:
            providers = [
                d for d in t.get("depends_on", [])
                if c in (tickets.get(d, {}).get("produces") or [])
            ]
            if not providers:
                warnings.append(f"{tid}: consumes '{c}' but no dependency produces it")
    state = {tid: 0 for tid in tickets}

    def visit(tid, stack):
        if state.get(tid) == 1:
            errors.append(f"dependency cycle: {' -> '.join(stack + [tid])}")
            return
        if state.get(tid) != 0:
            return
        state[tid] = 1
        for d in tickets[tid].get("depends_on", []):
            if d in tickets:
                visit(d, stack + [tid])
        state[tid] = 2

    for tid in tickets:
        visit(tid, [])
    ceilings = sum(t.get("cost_ceiling_usd") or 0 for t in tickets.values())
    budget = plan.get("phase_budget_usd")
    if budget is not None and ceilings > budget:
        warnings.append(f"sum of ceilings ${ceilings:.2f} exceeds phase budget ${budget:.2f}")
    return errors, warnings


def cmd_check(args, plan, tickets):
    errors, warnings = check(plan, tickets)
    for w in warnings:
        print(f"WARN  {w}")
    for e in errors:
        print(f"ERROR {e}")
    if not errors:
        print(f"ok: {len(tickets)} tickets valid")
    return 1 if errors else 0


def cmd_status(args, plan, tickets):
    g = ", ".join(
        f"{name}={'approved by ' + gate['approved_by'] if gate.get('approved_by') else 'UNAPPROVED'}"
        for name, gate in plan.get("gates", {}).items()
    )
    print(f"phase: {plan.get('phase')}  budget: ${plan.get('phase_budget_usd')}  gates: {g}")
    spent = 0.0
    for tid, t in tickets.items():
        spent += t["provenance"].get("cost_spent_usd") or 0
        deps = ",".join(t["depends_on"]) or "-"
        mark = "*" if eligible(t, plan, tickets) else " "
        print(f"{mark} {t['status']:<12} {t['assignee_class']:<15} ${t.get('cost_ceiling_usd') or 0:<6} {tid:<40} deps: {deps}")
    print(f"spent: ${spent:.2f}  (* = eligible to run)")
    return 0


def cmd_next(args, plan, tickets):
    found = False
    for cls in sorted(CLASSES):
        ids = [tid for tid, t in tickets.items() if t["assignee_class"] == cls and eligible(t, plan, tickets)]
        if ids:
            found = True
            print(f"{cls}:")
            for tid in ids:
                print(f"  {tid} — {tickets[tid]['title']}")
    if not found:
        print("no eligible tickets (check gates and dependencies)")
    return 0


def contract(t):
    acc = "\n".join(f"  - {a}" for a in t["acceptance"])
    return (
        f"TICKET {t['id']}: {t['title']}\n"
        f"claim: {t['claim']}\n"
        f"cost ceiling: ${t.get('cost_ceiling_usd')}\n"
        f"description:\n{t['description']}\n"
        f"acceptance criteria (all artifacts go next to the tickets dir):\n{acc}\n"
    )


def cmd_run(args, plan, tickets):
    t = tickets.get(args.ticket)
    if not t:
        print(f"no ticket '{args.ticket}'")
        return 1
    if not eligible(t, plan, tickets):
        print(f"{t['id']} is not eligible (status={t['status']}, gate/deps unsatisfied)")
        return 1
    print(contract(t))
    if t["assignee_class"] == "human":
        print("human ticket: do the work, then record with: drain.py done <id> --by <name>")
        return 0
    if args.dry_run:
        print("dry run: not dispatching")
        return 0
    if t["assignee_class"] == "frontier-agent":
        set_field(t, "status", "in-progress")
        prov = dict(t["provenance"], started=today())
        set_field(t, "provenance", prov)
        r = subprocess.run(["claude", "-p", contract(t)], capture_output=True, text=True)
        print(r.stdout[-4000:])
        verdict = "pass" if r.returncode == 0 else f"fail (exit {r.returncode})"
        prov = dict(prov, executed_by="claude (headless)", finished=today(), verdict=verdict)
        set_field(t, "provenance", prov)
        set_field(t, "status", "done" if r.returncode == 0 else "failed")
        return r.returncode
    print("small-agent dispatch not implemented in v0; run manually via the desktop route and record with done/fail")
    return 1


def today():
    return datetime.date.today().isoformat()


def set_field(t, field, value):
    doc = yaml.safe_load(t["_path"].read_text())
    doc[field] = value
    t["_path"].write_text(yaml.safe_dump(doc, sort_keys=False, allow_unicode=True))
    t[field] = value


def cmd_done(args, plan, tickets):
    t = tickets.get(args.ticket)
    if not t:
        print(f"no ticket '{args.ticket}'")
        return 1
    prov = dict(
        t["provenance"], executed_by=args.by, finished=today(),
        cost_spent_usd=args.cost, verdict=args.verdict,
    )
    if args.artifacts:
        prov["artifacts"] = args.artifacts.split(",")
    set_field(t, "provenance", prov)
    set_field(t, "status", "failed" if args.verdict == "fail" else "done")
    print(f"{t['id']} -> {t['status']} (by {args.by})")
    return 0


CSS = """
:root { --bg:#ffffff; --fg:#1a1a1a; --muted:#666; --card:#f6f6f4; --line:#ddd; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#181818; --fg:#e8e8e8; --muted:#9a9a9a; --card:#222; --line:#3a3a3a; }
}
* { box-sizing:border-box; }
body { margin:0 auto; max-width:46rem; padding:1.5rem 1rem; background:var(--bg);
  color:var(--fg); font:16px/1.55 -apple-system,'Segoe UI',sans-serif; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
  padding:1.1rem 1.3rem; margin:1rem 0; }
.badge { display:inline-block; color:#fff; border-radius:999px; padding:.1rem .7rem;
  font-size:.8rem; font-weight:600; }
h1 { font-size:1.35rem; margin:.2rem 0 .6rem; }
h2 { font-size:1.05rem; margin:1rem 0 .3rem; }
.meta { color:var(--muted); font-size:.85rem; margin:.15rem 0; }
ul { margin:.3rem 0; padding-left:1.3rem; }
a { color:inherit; }
.gate-warn { border-left:4px solid #c77d2e; padding:.5rem .9rem; background:var(--card);
  border-radius:6px; font-size:.9rem; }
"""


def ticket_html(t):
    e = html.escape
    color = STATUS_COLOR.get(t["status"], "#888")
    deps = ", ".join(t["depends_on"]) or "none"
    acc = "".join(f"<li>{e(a)}</li>" for a in t["acceptance"])
    prov = ""
    if t["provenance"].get("executed_by"):
        p = t["provenance"]
        arts = ", ".join(p.get("artifacts") or []) or "none"
        prov = (
            f"<h2>Provenance</h2><p class='meta'>executed by {e(str(p['executed_by']))} · "
            f"finished {e(str(p.get('finished')))} · spent ${p.get('cost_spent_usd') or 0} · "
            f"verdict {e(str(p.get('verdict')))} · artifacts: {e(arts)}</p>"
        )
    produces = ", ".join(t.get("produces") or []) or "none"
    consumes = ", ".join(t.get("consumes") or []) or "none"
    needed = ", ".join(t.get("human_needed") or []) or "none"
    return (
        f"<div class='card'><span class='badge' style='background:{color}'>{e(t['status'])}</span>"
        f"<h1>{e(t['id'])} — {e(t['title'])}</h1>"
        f"<p><b>{e(str(t.get('summary', ''))).strip()}</b></p>"
        f"<p class='meta'>assignee: {e(t['assignee_class'])} · ceiling: ${t.get('cost_ceiling_usd')} · "
        f"human needed: {e(needed)}</p>"
        f"<details><summary>details</summary>"
        f"<p class='meta'>gate: {e(str(t.get('gate')))} · depends on: {e(deps)} · serves: {e(t['claim'])}</p>"
        f"<p class='meta'>why: {e(str(t.get('why', ''))).strip()}</p>"
        f"<p class='meta'>produces: {e(produces)} · consumes: {e(consumes)}</p>"
        f"<p>{e(t['description']).strip()}</p>"
        f"<h2>Acceptance</h2><ul>{acc}</ul>{prov}</details></div>"
    )


def page(title, body):
    return (
        f"<meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{html.escape(title)}</title><style>{CSS}</style>{body}"
    )


def cmd_render(args, plan, tickets):
    out = args.dir / "html"
    out.mkdir(exist_ok=True)
    gates = plan.get("gates", {})
    banner = ""
    for name, g in gates.items():
        if g.get("approved_by"):
            banner += f"<p class='gate-warn'>gate <b>{name}</b> approved by {html.escape(g['approved_by'])} ({g.get('date')}): {html.escape(str(g.get('rationale')))}</p>"
        else:
            banner += f"<p class='gate-warn'>gate <b>{name}</b> is UNAPPROVED — no ticket below it can run</p>"
    items = ""
    for tid, t in tickets.items():
        (out / f"{tid}.html").write_text(page(tid, ticket_html(t)))
        color = STATUS_COLOR.get(t["status"], "#888")
        items += (
            f"<p><span class='badge' style='background:{color}'>{t['status']}</span> "
            f"<a href='{tid}.html'>{tid}</a> — <b>{html.escape(t['title'])}</b> "
            f"<span class='meta'>({t['assignee_class']})</span><br>"
            f"<span class='meta'>{html.escape(t.get('summary', ''))}</span></p>"
        )
    idx = f"<h1>{plan.get('phase')} tickets</h1>{banner}{items}"
    (out / "index.html").write_text(page("tickets", idx))
    print(f"rendered {len(tickets)} cards -> {out}")
    return 0


def main():
    ap = argparse.ArgumentParser(prog="drain.py")
    ap.add_argument("--dir", type=Path, default=Path(__file__).resolve().parents[1] / "investigations/001-better-harnesses-derisk/tickets")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    sub.add_parser("status")
    sub.add_parser("next")
    sub.add_parser("render")
    p = sub.add_parser("run")
    p.add_argument("ticket")
    p.add_argument("--dry-run", action="store_true")
    p = sub.add_parser("done")
    p.add_argument("ticket")
    p.add_argument("--by", required=True)
    p.add_argument("--cost", type=float, default=0.0)
    p.add_argument("--verdict", default="pass")
    p.add_argument("--artifacts", default="")
    args = ap.parse_args()
    plan, tickets = load(args.dir)
    fn = {"check": cmd_check, "status": cmd_status, "next": cmd_next,
          "render": cmd_render, "run": cmd_run, "done": cmd_done}[args.cmd]
    sys.exit(fn(args, plan, tickets))


if __name__ == "__main__":
    main()
