"""inv 006 — render a run's launch dir as a single self-contained HTML report.

Walks the launch dir + associated .agent_handoff/ + (optionally) the
orchestrator's /tmp/w2s_server.log and produces a single HTML file with:

- run summary (start/end times, iteration counts, PGR/transfer_acc headline)
- PGR + transfer_acc trajectory (Plotly)
- VRAM timeline (Plotly)
- iteration table (config, exit, elapsed, predictions_count, transfer_acc, pgr, errors)
- per-iteration drill-down (collapsible <details>):
    - Bash command + cwd + timeout
    - Bash subprocess log preview (head + tail)
    - submission tool_call args
    - server_ack (full)
    - session log preview (tool-use sequence)
- failure summary (counts of common failure modes)

Usage:
    uv run --with plotly --with pyyaml python render_run.py <launch_dir>
    uv run --with plotly --with pyyaml python render_run.py \
        --launch-dir <launch_dir> \
        --handoff-dir <override>  \
        --server-log /tmp/w2s_server.log \
        --output <out.html>

Default output path: <launch_dir>/report.html
"""

from __future__ import annotations

import argparse
import html
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import plotly.graph_objects as go
import yaml


# ---------------------------------------------------------------------------
# Data extraction
# ---------------------------------------------------------------------------


@dataclass
class IterationRow:
    n: int
    yaml_path: Path
    timestamp: Optional[str] = None
    bash_exit: Any = None
    bash_elapsed: Optional[float] = None
    bash_full_log: Optional[str] = None
    predictions_file: Optional[str] = None
    bash_markers: List[str] = field(default_factory=list)
    submitted: bool = False
    predictions_count: Optional[int] = None
    transfer_acc: Optional[float] = None
    pgr: Optional[float] = None
    correct: Optional[int] = None
    total: Optional[int] = None
    fixed_weak_acc: Optional[float] = None
    fixed_strong_acc: Optional[float] = None
    server_ack: Dict[str, Any] = field(default_factory=dict)
    failure_log: List[str] = field(default_factory=list)
    tool_call_shape: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionRecord:
    n: int
    started: Optional[str] = None
    ended: Optional[str] = None
    tool_calls: List[Tuple[str, str, str]] = field(default_factory=list)  # (ts, tool, input_preview)
    text_messages: List[Tuple[str, str]] = field(default_factory=list)    # (ts, text_preview)
    result_line: Optional[str] = None
    raw: str = ""


def load_iterations(handoff_dir: Path) -> List[IterationRow]:
    rows: List[IterationRow] = []
    for f in sorted(handoff_dir.glob("iteration_*.yaml")):
        try:
            with open(f) as fp:
                data = yaml.safe_load(fp) or {}
        except Exception as e:
            print(f"WARN: failed to read {f}: {e}")
            continue
        n_str = f.stem.split("_")[-1]
        try:
            n = int(n_str)
        except ValueError:
            n = -1

        result = (data.get("result") or {})
        ep = (result.get("evaluate_predictions") or {})
        server_ack = ep.get("server_ack") if isinstance(ep.get("server_ack"), dict) else {}
        server_response = server_ack.get("server_response") or {}

        # transfer_acc / pgr can live in server_ack OR server_ack.server_response
        def _pick(key):
            v = server_ack.get(key)
            if v is None:
                v = server_response.get(key)
            return v

        rows.append(IterationRow(
            n=n,
            yaml_path=f,
            timestamp=data.get("timestamp"),
            bash_exit=result.get("exit_code"),
            bash_elapsed=result.get("elapsed_sec"),
            bash_full_log=(data.get("attempted_command") or {}).get("full_log"),
            predictions_file=result.get("predictions_file"),
            bash_markers=data.get("bash_markers") or [],
            submitted=bool(ep.get("submitted")),
            predictions_count=ep.get("predictions_count"),
            transfer_acc=_pick("transfer_acc"),
            pgr=_pick("pgr"),
            correct=_pick("correct"),
            total=_pick("total"),
            fixed_weak_acc=_pick("fixed_weak_acc"),
            fixed_strong_acc=_pick("fixed_strong_acc"),
            server_ack=server_ack,
            failure_log=data.get("failure_log") or [],
            tool_call_shape=data.get("tool_call_shape") or {},
        ))
    return rows


_TS_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})\]\s+(\w+)(?:\s+(.*))?$", re.MULTILINE)
_SESSION_TOOL_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\s+AssistantMessage\s*\n.*?Tool:\s*(\S+)\s*\n\s*Input:\s*(\{.*?\})\s*\n",
    re.DOTALL,
)
_SESSION_RESULT_RE = re.compile(r"# Result:\s*([^\n]+)")
_SESSION_TEXT_RE = re.compile(
    r"\[(\d{2}:\d{2}:\d{2})\]\s+AssistantMessage\s*\n(?!Tool:)(.+?)(?=\n\[\d{2}:\d{2}:\d{2}\]|\Z)",
    re.DOTALL,
)


def load_sessions(launch_dir: Path) -> List[SessionRecord]:
    sessions: List[SessionRecord] = []
    logs_dir = launch_dir / "logs"
    if not logs_dir.exists():
        return sessions
    for f in sorted(logs_dir.glob("session_*.log")):
        try:
            raw = f.read_text()
        except Exception:
            continue
        m_n = re.match(r"session_(\d{3})_", f.stem)
        n = int(m_n.group(1)) if m_n else -1
        m_start = re.search(r"# Started:\s*([^\n]+)", raw)
        m_end = re.search(r"# Ended:\s*([^\n]+)", raw)
        m_result = _SESSION_RESULT_RE.search(raw)

        tool_calls = []
        for m in _SESSION_TOOL_RE.finditer(raw):
            ts, tool, input_blob = m.group(1), m.group(2), m.group(3)
            preview = input_blob[:200].replace("\n", " ")
            tool_calls.append((ts, tool, preview))

        sessions.append(SessionRecord(
            n=n,
            started=m_start.group(1) if m_start else None,
            ended=m_end.group(1) if m_end else None,
            tool_calls=tool_calls,
            result_line=m_result.group(1) if m_result else None,
            raw=raw,
        ))
    return sessions


def load_bash_logs(launch_dir: Path) -> Dict[int, Dict[str, Any]]:
    out: Dict[int, Dict[str, Any]] = {}
    d = launch_dir / "bash_subprocess_logs"
    if not d.exists():
        return out
    for f in sorted(d.glob("bash_*.log")):
        m = re.match(r"bash_(\d{4})", f.stem)
        if not m:
            continue
        n = int(m.group(1))
        try:
            raw = f.read_text()
        except Exception:
            continue
        size = f.stat().st_size
        head = "\n".join(raw.splitlines()[:30])
        tail = "\n".join(raw.splitlines()[-30:]) if size > 4000 else ""
        # parse the header lines we emit
        cmd = ""
        exit_code = ""
        elapsed = ""
        timed_out = "TIMED OUT" in raw[:200]
        cmd_m = re.search(r"# command:\n(.+?)(?=\n# |\n--- |\Z)", raw, re.DOTALL)
        if cmd_m:
            cmd = cmd_m.group(1).strip()
        ex_m = re.search(r"# exit_code:\s*(\S+)", raw)
        if ex_m:
            exit_code = ex_m.group(1)
        el_m = re.search(r"# elapsed:\s*(\S+)", raw)
        if el_m:
            elapsed = el_m.group(1)
        out[n] = {
            "path": f,
            "size": size,
            "command": cmd,
            "exit_code": exit_code,
            "elapsed": elapsed,
            "timed_out": timed_out,
            "head": head,
            "tail": tail,
        }
    return out


def load_vram(launch_dir: Path) -> Tuple[List[float], List[float], List[float]]:
    """Returns (epoch_secs_relative_to_start, used_mib, free_mib)."""
    csv_path = launch_dir / "vram_samples.csv"
    if not csv_path.exists():
        return [], [], []
    times, used, free = [], [], []
    t0 = None
    with open(csv_path) as f:
        next(f, None)  # header
        for line in f:
            try:
                parts = line.strip().split(",")
                t = float(parts[0])
                u = int(parts[1].strip())
                fr = int(parts[2].strip())
            except (ValueError, IndexError):
                continue
            if t0 is None:
                t0 = t
            times.append((t - t0) / 60.0)  # minutes since start
            used.append(u)
            free.append(fr)
    return times, used, free


def load_server_posts(server_log: Optional[Path], day_prefix: str) -> List[Tuple[str, int]]:
    """Returns list of (timestamp, status_code) for POSTs to evaluate-predictions
    on the given day_prefix (e.g. '01/Jun/2026')."""
    if not server_log or not server_log.exists():
        return []
    out = []
    pat = re.compile(
        rf"\[{re.escape(day_prefix)} (\d{{2}}:\d{{2}}:\d{{2}})\] \"POST /api/evaluate-predictions HTTP/1\.1\" (\d+)"
    )
    try:
        for line in server_log.read_text(errors="replace").splitlines():
            m = pat.search(line)
            if m:
                out.append((m.group(1), int(m.group(2))))
    except Exception:
        pass
    return out


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _esc(s: Any) -> str:
    return html.escape(str(s)) if s is not None else ""


def render_trajectory_chart(rows: List[IterationRow]) -> str:
    iters = [r.n for r in rows]
    pgr = [r.pgr for r in rows]
    ta = [r.transfer_acc for r in rows]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=iters, y=pgr, mode="lines+markers", name="PGR",
        line=dict(color="#3b82f6"), marker=dict(size=10),
    ))
    fig.add_trace(go.Scatter(
        x=iters, y=ta, mode="lines+markers", name="transfer_acc",
        line=dict(color="#10b981"), marker=dict(size=8), yaxis="y2",
    ))
    # Reference lines for the orchestrator baselines (use the latest non-None values seen)
    fw = next((r.fixed_weak_acc for r in reversed(rows) if r.fixed_weak_acc is not None), None)
    fs = next((r.fixed_strong_acc for r in reversed(rows) if r.fixed_strong_acc is not None), None)
    if fw is not None:
        fig.add_hline(y=fw, line_dash="dot", line_color="#94a3b8",
                      annotation_text=f"weak_acc={fw:.3f}", annotation_position="bottom right", yref="y2")
    if fs is not None:
        fig.add_hline(y=fs, line_dash="dot", line_color="#94a3b8",
                      annotation_text=f"strong_acc={fs:.3f}", annotation_position="top right", yref="y2")
    fig.update_layout(
        title="PGR + transfer_acc per iteration",
        xaxis_title="iteration",
        yaxis=dict(title="PGR", tickformat=".3f"),
        yaxis2=dict(title="transfer_acc", overlaying="y", side="right", tickformat=".3f"),
        legend=dict(x=0.01, y=0.99),
        height=420,
        margin=dict(l=60, r=60, t=60, b=40),
    )
    return fig.to_html(full_html=False, include_plotlyjs="cdn")


def render_vram_chart(times: List[float], used: List[int], free: List[int]) -> str:
    if not times:
        return "<p><em>no vram samples</em></p>"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=times, y=used, mode="lines", name="used (MiB)", line=dict(color="#ef4444")))
    fig.update_layout(
        title="GPU memory used (MiB) over run",
        xaxis_title="minutes since launch",
        yaxis_title="MiB",
        height=300,
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def render_tool_shape_chart(rows: List[IterationRow]) -> str:
    iters = [r.n for r in rows]
    shape_keys = ["canonical_bash", "lowercase_bash", "invented_bash", "evaluate_predictions"]
    fig = go.Figure()
    for k in shape_keys:
        fig.add_trace(go.Bar(
            x=iters, y=[r.tool_call_shape.get(k, 0) for r in rows], name=k,
        ))
    fig.update_layout(
        title="Tool-use shape per iteration",
        xaxis_title="iteration",
        yaxis_title="count",
        barmode="stack",
        height=300,
        margin=dict(l=60, r=20, t=50, b=40),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def render_iteration_table(rows: List[IterationRow]) -> str:
    headers = ["iter", "ts", "exit", "elapsed(s)", "submitted", "n_pred", "transfer_acc", "PGR", "correct/total", "notes"]
    lines = ["<table class='it-table'>", "<thead><tr>" + "".join(f"<th>{h}</th>" for h in headers) + "</tr></thead><tbody>"]
    for r in rows:
        notes = []
        if r.failure_log:
            notes.append(f"{len(r.failure_log)} failure(s)")
        if r.server_ack.get("success") is False:
            err = r.server_ack.get("error") or (r.server_ack.get("server_response", {}).get("pgr_error"))
            if err:
                notes.append(f"ack: {str(err)[:80]}")
        if r.submitted and r.pgr is None and r.transfer_acc is not None:
            notes.append("submitted, PGR null")
        cells = [
            r.n,
            _esc(r.timestamp or ""),
            _esc(r.bash_exit if r.bash_exit is not None else ""),
            f"{r.bash_elapsed:.1f}" if isinstance(r.bash_elapsed, (int, float)) else "",
            "✓" if r.submitted else "",
            r.predictions_count if r.predictions_count is not None else "",
            f"{r.transfer_acc:.3f}" if isinstance(r.transfer_acc, (int, float)) else "",
            f"{r.pgr:.3f}" if isinstance(r.pgr, (int, float)) else "",
            f"{r.correct}/{r.total}" if r.correct is not None and r.total is not None else "",
            "; ".join(_esc(n) for n in notes),
        ]
        lines.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    lines.append("</tbody></table>")
    return "\n".join(lines)


def render_iteration_drill(
    rows: List[IterationRow],
    sessions_by_n: Dict[int, SessionRecord],
    bash_logs: Dict[int, Dict[str, Any]],
) -> str:
    """For each iteration N, render a collapsible block with:
       - sessions whose number == N (might be 0, 1, or N+1 if numbering offset)
       - all bash calls referenced by attempted_command.full_log
       - submission details + server_ack
    """
    out = []
    for r in rows:
        sess = sessions_by_n.get(r.n)
        bash_num = None
        if r.bash_full_log:
            m = re.search(r"bash_(\d{4})\.log", r.bash_full_log)
            if m:
                bash_num = int(m.group(1))
        bash_info = bash_logs.get(bash_num) if bash_num is not None else None

        title = f"iteration {r.n}"
        if isinstance(r.pgr, (int, float)):
            title += f" — PGR {r.pgr:.3f}"
        elif r.submitted:
            title += " — submitted (no PGR)"
        elif r.bash_exit == 0:
            title += " — Bash succeeded, no submission"
        elif r.bash_exit not in (None, 0):
            title += f" — Bash exit {r.bash_exit}"

        out.append(f"<details><summary>{_esc(title)}</summary>")

        # session
        if sess:
            out.append(f"<h4>session {sess.n}</h4>")
            out.append(f"<p>started: {_esc(sess.started)}  &nbsp;|&nbsp; ended: {_esc(sess.ended)}</p>")
            if sess.result_line:
                out.append(f"<p class='result-line'>result: <code>{_esc(sess.result_line)}</code></p>")
            if sess.tool_calls:
                out.append("<table class='tool-table'><thead><tr><th>ts</th><th>tool</th><th>input (preview)</th></tr></thead><tbody>")
                for ts, tool, prev in sess.tool_calls:
                    out.append(f"<tr><td>{_esc(ts)}</td><td><b>{_esc(tool)}</b></td><td><code>{_esc(prev)}</code></td></tr>")
                out.append("</tbody></table>")

        # bash
        if bash_info:
            out.append(f"<h4>bash call (bash_{bash_num:04d}.log, {bash_info['size']} bytes)</h4>")
            out.append(f"<p>exit: <code>{_esc(bash_info['exit_code'])}</code>  elapsed: <code>{_esc(bash_info['elapsed'])}</code>"
                       + (f"  <b style='color:#ef4444'>TIMED OUT</b>" if bash_info["timed_out"] else "") + "</p>")
            if bash_info["command"]:
                out.append("<pre class='cmd'>" + _esc(bash_info["command"]) + "</pre>")
            out.append("<details class='bash-log'><summary>bash log (head)</summary><pre>" + _esc(bash_info["head"]) + "</pre></details>")
            if bash_info["tail"]:
                out.append("<details class='bash-log'><summary>bash log (tail)</summary><pre>" + _esc(bash_info["tail"]) + "</pre></details>")

        # submission + ack
        if r.submitted:
            out.append("<h4>evaluate_predictions submission</h4>")
            out.append(f"<p>predictions_file: <code>{_esc(r.predictions_file)}</code></p>")
            if r.server_ack:
                pretty = json.dumps(r.server_ack, indent=2, default=str)
                out.append(f"<details class='ack'><summary>server_ack</summary><pre>{_esc(pretty)}</pre></details>")

        # failure log
        if r.failure_log:
            out.append("<h4>failure log</h4><ul>")
            for fl in r.failure_log:
                out.append(f"<li><code>{_esc(fl)}</code></li>")
            out.append("</ul>")

        # bash markers
        if r.bash_markers:
            out.append(f"<p>bash_markers: {' '.join('<code>' + _esc(m) + '</code>' for m in r.bash_markers)}</p>")

        out.append("</details>")
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Summaries
# ---------------------------------------------------------------------------


def render_summary(rows: List[IterationRow], posts: List[Tuple[str, int]]) -> str:
    n_iter = len(rows)
    n_submitted = sum(1 for r in rows if r.submitted)
    n_valid_pgr = sum(1 for r in rows if isinstance(r.pgr, (int, float)))
    n_bash_ok = sum(1 for r in rows if r.bash_exit == 0)
    valid_pgrs = [r.pgr for r in rows if isinstance(r.pgr, (int, float))]
    valid_tas = [r.transfer_acc for r in rows if isinstance(r.transfer_acc, (int, float))]
    best_pgr = max(valid_pgrs) if valid_pgrs else None
    n_post_200 = sum(1 for _, code in posts if code == 200)
    n_post_other = len(posts) - n_post_200

    parts = [
        "<div class='summary'>",
        f"<div class='card'><div class='lbl'>iterations</div><div class='val'>{n_iter}</div></div>",
        f"<div class='card'><div class='lbl'>Bash exit=0</div><div class='val'>{n_bash_ok}</div></div>",
        f"<div class='card'><div class='lbl'>submissions</div><div class='val'>{n_submitted}</div></div>",
        f"<div class='card'><div class='lbl'>valid PGRs</div><div class='val'>{n_valid_pgr}</div></div>",
        f"<div class='card best'><div class='lbl'>best PGR</div><div class='val'>{'-' if best_pgr is None else f'{best_pgr:.3f}'}</div></div>",
        f"<div class='card'><div class='lbl'>POST 200</div><div class='val'>{n_post_200}</div></div>",
        f"<div class='card'><div class='lbl'>POST other</div><div class='val'>{n_post_other}</div></div>",
        "</div>",
    ]
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Top-level
# ---------------------------------------------------------------------------


CSS = """
* { box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
       background: #f8fafc; color: #0f172a; margin: 0; padding: 24px; }
h1 { font-size: 22px; margin: 0 0 4px 0; }
h2 { font-size: 18px; margin: 28px 0 8px 0; border-bottom: 1px solid #e2e8f0; padding-bottom: 4px; }
h3 { font-size: 15px; margin: 16px 0 6px 0; color: #334155; }
h4 { font-size: 13px; margin: 12px 0 4px 0; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; }
p { font-size: 13px; line-height: 1.5; margin: 4px 0; }
code, pre { font-family: 'SF Mono', 'Menlo', monospace; font-size: 12px; }
pre { background: #1e293b; color: #e2e8f0; padding: 12px; border-radius: 6px; overflow-x: auto; max-height: 360px; }
pre.cmd { background: #f1f5f9; color: #0f172a; max-height: 200px; }
.subhead { color: #64748b; font-size: 12px; margin-bottom: 16px; }
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
           gap: 8px; margin: 12px 0 16px 0; }
.card { background: white; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px 12px; }
.card .lbl { color: #64748b; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; }
.card .val { font-size: 22px; font-weight: 600; color: #0f172a; }
.card.best { background: #ecfdf5; border-color: #6ee7b7; }
.card.best .val { color: #047857; }
table { border-collapse: collapse; width: 100%; font-size: 12px; background: white; }
table th { background: #f1f5f9; padding: 6px 8px; text-align: left; border-bottom: 1px solid #cbd5e1; }
table td { padding: 6px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
table.it-table tr:hover { background: #f8fafc; }
table.tool-table { margin: 4px 0; }
details { background: white; border: 1px solid #e2e8f0; border-radius: 6px;
          padding: 8px 12px; margin: 6px 0; }
details summary { cursor: pointer; font-weight: 600; padding: 4px 0; outline: none; }
details details { background: #fafafa; margin: 4px 0; }
.bash-log pre, .ack pre { max-height: 240px; }
.result-line code { background: #f1f5f9; padding: 1px 6px; border-radius: 3px; }
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("launch_dir", nargs="?", help="path to launch dir (e.g. .../launches/20260601_121730)")
    ap.add_argument("--launch-dir", dest="launch_dir_flag")
    ap.add_argument("--handoff-dir", help="override handoff dir (default: <launch_parent>/workspace/.agent_handoff)")
    ap.add_argument("--server-log", default="/tmp/w2s_server.log")
    ap.add_argument("--output", help="output path (default: <launch_dir>/report.html)")
    args = ap.parse_args()

    launch_dir = Path(args.launch_dir or args.launch_dir_flag).resolve()
    if not launch_dir.exists():
        raise SystemExit(f"launch dir not found: {launch_dir}")

    handoff_dir = (
        Path(args.handoff_dir).resolve()
        if args.handoff_dir
        else launch_dir.parent.parent / "workspace" / ".agent_handoff"
    )
    if not handoff_dir.exists():
        # second guess: maybe handoff lives at .../handoff_math_seed42/.agent_handoff/ (sibling)
        alt = launch_dir.parent.parent / ".agent_handoff"
        if alt.exists():
            handoff_dir = alt
    out_path = Path(args.output) if args.output else launch_dir / "report.html"

    rows = load_iterations(handoff_dir)
    sessions = load_sessions(launch_dir)
    sessions_by_n = {s.n: s for s in sessions}
    bash_logs = load_bash_logs(launch_dir)
    times, used, free = load_vram(launch_dir)

    # Day prefix for server log filter — pick the earliest yaml timestamp
    day_prefix = None
    if rows and rows[0].timestamp:
        try:
            dt = datetime.fromisoformat(rows[0].timestamp.rstrip("Z"))
            day_prefix = dt.strftime("%d/%b/%Y")
        except Exception:
            pass
    if day_prefix is None:
        day_prefix = datetime.now().strftime("%d/%b/%Y")
    posts = load_server_posts(Path(args.server_log) if args.server_log else None, day_prefix)

    parts = [
        f"<!doctype html><html><head><meta charset='utf-8'>",
        f"<title>inv 006 run report — {launch_dir.name}</title>",
        f"<style>{CSS}</style></head><body>",
        f"<h1>inv 006 run report — {_esc(launch_dir.name)}</h1>",
        f"<div class='subhead'>launch dir: <code>{_esc(launch_dir)}</code><br>"
        f"handoff dir: <code>{_esc(handoff_dir)}</code></div>",
        render_summary(rows, posts),
        "<h2>PGR trajectory</h2>",
        render_trajectory_chart(rows) if rows else "<p><em>no iterations</em></p>",
        "<h2>Tool-use shape</h2>",
        render_tool_shape_chart(rows) if rows else "<p><em>no iterations</em></p>",
        "<h2>VRAM</h2>",
        render_vram_chart(times, used, free),
        "<h2>Iterations</h2>",
        render_iteration_table(rows) if rows else "<p><em>no iterations</em></p>",
        "<h2>Drill-down</h2>",
        render_iteration_drill(rows, sessions_by_n, bash_logs) if rows else "",
        "</body></html>",
    ]
    out_path.write_text("\n".join(parts))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
