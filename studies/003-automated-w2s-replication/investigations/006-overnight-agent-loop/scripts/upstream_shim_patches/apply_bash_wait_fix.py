#!/usr/bin/env python3
"""inv 006: fix the Bash handler deadlock after timeout-kill.

Root cause (reproduced in pure asyncio, no shim involved): in Python
3.12 on systems without `os.pidfd_open` (uv-managed CPython 3.12.13
build doesn't expose it; falls back to ThreadedChildWatcher), the
following sequence deadlocks:

    proc = await asyncio.create_subprocess_shell(cmd, stdout=PIPE, stderr=PIPE)
    try:
        await asyncio.wait_for(proc.communicate(), timeout=N)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()       # <-- never returns

The watcher thread DOES reap the SIGKILL'd subprocess (we confirmed
this — direct `os.waitpid(pid, WNOHANG)` afterwards returns
`ChildProcessError [Errno 10] No child processes`), but the asyncio
`Process._returncode` is never set, so `Process.wait()` awaits an
internal future that's never resolved.

This caused the inv 006 Run 1 5-hour stall (2026-06-01 03:20–08:25):
agent emitted a retry Bash call after the prior one timed out, the
handler entered `proc.wait()` after the second timeout's `proc.kill()`,
and never came out.

Fix: bound `proc.wait()` with a small `wait_for`, fall back to
`os.waitpid(pid, WNOHANG)` (and swallow `ChildProcessError` — the
kernel may have already reaped). Either way the handler returns
promptly with the correct "timed out" tool result.

Applies to both shim_v1 (`/home/tlifke/inv003_shim/shim_pkg/`) and
shim_v2 (`/home/tlifke/inv003_shim/shim_v2_pkg/`).

Idempotent.
"""
from __future__ import annotations
from pathlib import Path

SHIM_V1 = Path("/home/tlifke/inv003_shim/shim_pkg/claude_agent_sdk/builtins.py")
SHIM_V2 = Path("/home/tlifke/inv003_shim/shim_v2_pkg/claude_agent_sdk/builtins.py")


def patch(p: Path) -> bool:
    src = p.read_text()
    if "_safe_kill_and_reap" in src:
        print(f"[{p.parent.parent.name}/{p.name}] already patched")
        return False
    old = (
        "            except asyncio.TimeoutError:\n"
        "                proc.kill()\n"
        "                await proc.wait()\n"
    )
    new = (
        "            except asyncio.TimeoutError:\n"
        "                await _safe_kill_and_reap(proc)\n"
    )
    if old not in src:
        print(f"[{p.parent.parent.name}/{p.name}] anchor not found — skipping")
        return False
    src = src.replace(old, new)

    helper = (
        "\n"
        "async def _safe_kill_and_reap(proc) -> None:\n"
        "    \"\"\"Kill a subprocess and reap it, working around the Python 3.12\n"
        "    asyncio deadlock where Process.wait() never resolves after a\n"
        "    wait_for-cancelled communicate() on systems without pidfd_open.\n"
        "    Inv 006 finding: bound the wait + fall back to direct waitpid.\n"
        "    \"\"\"\n"
        "    proc.kill()\n"
        "    try:\n"
        "        await asyncio.wait_for(proc.wait(), timeout=2.0)\n"
        "        return\n"
        "    except asyncio.TimeoutError:\n"
        "        pass\n"
        "    try:\n"
        "        os.waitpid(proc.pid, os.WNOHANG)\n"
        "    except (ChildProcessError, OSError):\n"
        "        pass\n"
        "    transport = getattr(proc, \"_transport\", None)\n"
        "    if transport is not None:\n"
        "        try:\n"
        "            transport.close()\n"
        "        except Exception:\n"
        "            pass\n"
    )

    # Insert helper right before `def _make_bash_tool`
    anchor = "def _make_bash_tool("
    if anchor not in src:
        print(f"[{p.parent.parent.name}/{p.name}] _make_bash_tool anchor not found")
        return False
    src = src.replace(anchor, helper + "\n" + anchor, 1)

    p.write_text(src)
    print(f"[{p.parent.parent.name}/{p.name}] patched")
    return True


def main():
    for p in (SHIM_V1, SHIM_V2):
        patch(p)


if __name__ == "__main__":
    main()
