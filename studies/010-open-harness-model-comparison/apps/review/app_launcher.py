"""Live app launcher (SPEC 9 addendum).

Launches an agent-built app from a run's workspace so a human can review it
as a running application, not just static files. One launch per run at a
time.

Safety: this executes agent-written code on the host from a FRESH TEMP COPY
of the workspace (originals never touched). No sandbox — same trust level
as the agent judge.

Modes:
  http     — probe URLs until one responds (injected PORT + README-declared ports)
  desktop  — GUI app (e.g. tkinter); healthy when the process stays alive a
             few seconds; the window opens on the host display
  static   — served via `python -m http.server <port>` (uniform experience)
"""

import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
from pathlib import Path

PORT_RANGE_START = 8450
PORT_RANGE_END = 8499
HEALTH_TIMEOUT_S = 60
DESKTOP_GRACE_S = 4
PROBE_INTERVAL_S = 1.0

_log_lock = threading.Lock()
_launches: dict[str, "LaunchState"] = {}
# set by api.py: fn(run_id, command, port, mode, healthy, log_excerpt) -> None
event_sink = None


class LaunchState:
    def __init__(self, run_id: str, workspace: Path, temp_dir: Path, command: str,
                 mode: str, port: int | None, health_urls: list[str], log_path: Path):
        self.run_id = run_id
        self.workspace = workspace
        self.temp_dir = temp_dir
        self.command = command
        self.mode = mode
        self.port = port
        self.health_urls = health_urls
        self.log_path = log_path
        self.proc: subprocess.Popen | None = None
        self.status = "starting"  # starting | healthy | failed | stopped
        self.healthy_url: str | None = None
        self.started_at = time.time()
        self.log_excerpt = ""


def _free_port() -> int:
    used = {s.port for s in _launches.values() if s.port}
    for port in range(PORT_RANGE_START, PORT_RANGE_END + 1):
        if port in used:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"no free port in {PORT_RANGE_START}-{PORT_RANGE_END}")


def _readme(workspace: Path) -> str:
    for name in ("README.md", "README.txt", "README"):
        p = workspace / name
        if p.exists():
            return p.read_text(errors="replace")
    return ""


def _extract_readme_command(workspace: Path) -> str | None:
    """First line in a fenced code block that looks like a launch command."""
    blocks = re.findall(r"```[a-z]*\n(.*?)```", _readme(workspace), re.DOTALL)
    for block in blocks:
        for line in block.splitlines():
            line = line.strip()
            if re.match(r"^(python3?|uv run|npm (start|run)|node|bash)\b", line):
                return line
    return None


def _readme_ports(workspace: Path) -> list[int]:
    ports = []
    for match in re.findall(r"localhost:(\d{2,5})", _readme(workspace)):
        port = int(match)
        if port not in ports:
            ports.append(port)
    return ports


def detect_components(workspace: Path) -> list[dict]:
    """Spec heuristics: frontend / backend / database presence."""
    files = [p.relative_to(workspace).as_posix() for p in workspace.rglob("*") if p.is_file()]

    def has(pred) -> bool:
        return any(pred(f) for f in files)

    frontend = has(lambda f: f.endswith((".html", ".css", ".js"))
                   and not f.startswith("contract_text/"))
    backend = has(lambda f: re.fullmatch(r"(app|server|main|visualizer)\.py", f)
                  or f in ("requirements.txt", "package.json") or f == "run.sh")
    database = has(lambda f: f.endswith((".db", ".sqlite", ".sql"))
                   or "migration" in f.lower())
    return [
        {"name": "frontend", "present": frontend},
        {"name": "backend", "present": backend},
        {"name": "database", "present": database},
    ]


def _is_desktop(workspace: Path, command: str) -> bool:
    target = command.split()[-1] if command.split() else ""
    script = workspace / target
    if script.exists():
        try:
            content = script.read_text(errors="replace")
            if "tkinter" in content or ".mainloop()" in content:
                return True
        except OSError:
            pass
    return bool(re.search(r"\btkinter\b|\bGUI\b|desktop app", _readme(workspace), re.IGNORECASE))


def resolve_launch_command(workspace: Path, port: int) -> tuple[str, str, list[int]]:
    """Return (command, mode, health_probe_ports)."""
    cmd = _extract_readme_command(workspace)
    if not cmd and (workspace / "run.sh").exists():
        cmd = "bash run.sh"
    if cmd:
        mode = "desktop" if _is_desktop(workspace, cmd) else "http"
        return cmd, mode, _readme_ports(workspace)
    # static fallback — uniform experience even for pure-static runs
    return f"python3 -m http.server {port}", "static", [port]


def _probe(url: str) -> bool:
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            return resp.status < 500
    except Exception:
        return False


class LaunchManager:
    def start(self, run_id: str, workspace: str, command_override: str | None = None) -> LaunchState:
        with _log_lock:
            existing = _launches.get(run_id)
            if existing and existing.status in ("starting", "healthy"):
                raise RuntimeError(f"launch already active for run {run_id} (status {existing.status})")
            ws = Path(workspace)
            if not ws.exists():
                raise RuntimeError(f"workspace missing: {workspace}")
            temp_dir = Path(tempfile.mkdtemp(prefix=f"contractlab-launch-{run_id[:13]}-"))
            shutil.copytree(ws, temp_dir, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__"))
            port = _free_port()
            if command_override and command_override.strip():
                command = command_override.strip()
                mode = "desktop" if _is_desktop(ws, command) else "http"
                probe_ports = _readme_ports(ws) + [port]
            else:
                command, mode, probe_ports = resolve_launch_command(ws, port)
            # static http.server needs the allocated port in the command
            if mode == "static":
                command = re.sub(r"\d{4,5}$", str(port), command)
            health_urls = [f"http://localhost:{p}/" for p in dict.fromkeys(probe_ports)]
            log_path = temp_dir / "launch.log"
            state = LaunchState(run_id, ws, temp_dir, command, mode, port, health_urls, log_path)

            env = dict(os.environ)
            env["PORT"] = str(port)
            env["BROWSER"] = "/usr/bin/true"  # suppress webbrowser.open() in agent apps
            env["PYTHONUNBUFFERED"] = "1"  # suppress webbrowser.open() in agent apps
            log_file = open(log_path, "w")
            state.proc = subprocess.Popen(
                command, shell=True, cwd=temp_dir, env=env,
                stdout=log_file, stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
            )
            log_file.close()
            _launches[run_id] = state
            threading.Thread(target=self._watch, args=(state,), daemon=True).start()
            self._emit(state)
            return state

    def _watch(self, state: LaunchState) -> None:
        deadline = time.time() + HEALTH_TIMEOUT_S
        if state.mode == "desktop":
            time.sleep(DESKTOP_GRACE_S)
            if state.proc and state.proc.poll() is None:
                self._resolve(state, healthy=True, url=None)
            else:
                self._resolve(state, healthy=False, url=None)
            return
        while time.time() < deadline:
            if state.proc and state.proc.poll() is not None:
                self._resolve(state, healthy=False, url=None)
                return
            for url in state.health_urls:
                # require OUR process to still be alive at resolution time —
                # a probe hit on a README-declared port could be an unrelated
                # server squatting on it (observed: stale app.py on 8765).
                if _probe(url) and state.proc and state.proc.poll() is None:
                    state.healthy_url = url
                    self._resolve(state, healthy=True, url=url)
                    return
                if state.proc and state.proc.poll() is not None:
                    self._resolve(state, healthy=False, url=None)
                    return
            time.sleep(PROBE_INTERVAL_S)
        self._resolve(state, healthy=False, url=None)

    def _resolve(self, state: LaunchState, healthy: bool, url: str | None) -> None:
        if state.status in ("healthy", "failed"):
            return
        state.status = "healthy" if healthy else "failed"
        if healthy and url:
            state.healthy_url = url
        state.log_excerpt = self._tail(state)
        self._emit(state)

    def stop(self, run_id: str) -> dict:
        state = _launches.get(run_id)
        if not state:
            return {"stopped": False, "message": "no active launch"}
        if state.proc and state.proc.poll() is None:
            state.proc.terminate()
            try:
                state.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                state.proc.kill()
        was = state.status
        state.status = "stopped"
        state.log_excerpt = self._tail(state)
        if event_sink and was in ("healthy", "starting"):
            try:
                event_sink(run_id, state.command, state.port, state.mode, False, "stopped by user")
            except Exception:
                pass
        shutil.rmtree(state.temp_dir, ignore_errors=True)
        return {"stopped": True}

    def status(self, run_id: str) -> dict:
        state = _launches.get(run_id)
        if not state:
            return {"active": False, "running": False, "status": None, "components": []}
        # a finished process we never marked (e.g. raced) -> failed
        if state.status == "starting" and state.proc and state.proc.poll() is not None:
            self._resolve(state, healthy=False, url=None)
        url = state.healthy_url or (f"http://localhost:{state.port}/" if state.mode == "static" else None)
        return {
            "active": True,
            "running": state.status in ("starting", "healthy") and state.proc and state.proc.poll() is None,
            "status": state.status,
            "mode": state.mode,
            "port": state.port,
            "url": url,
            "command": state.command,
            "log_tail": self._tail(state),
        }

    @staticmethod
    def _tail(state: LaunchState, lines: int = 40) -> str:
        try:
            content = state.log_path.read_text(errors="replace")
            return "\n".join(content.splitlines()[-lines:])
        except OSError:
            return ""

    @staticmethod
    def _emit(state: LaunchState) -> None:
        if event_sink:
            try:
                event_sink(state.run_id, state.command, state.port, state.mode,
                           state.status == "healthy", state.log_excerpt)
            except Exception:
                pass  # launcher must not die on DB hiccups


manager = LaunchManager()
