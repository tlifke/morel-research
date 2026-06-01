"""Repro for inv 006 Run 1's 5-hour stall.

Hypothesis: when the shim's Bash handler kills a timed-out subprocess
via `proc.kill()` + `await proc.wait()`, asyncio's child watcher or
subprocess state gets wedged, and the next `create_subprocess_shell`
hangs indefinitely.

Strategy: skip the full agent loop. Call the shim's Bash handler
directly twice in sequence — first call hits a short timeout (force
the kill path), second call is a trivial command. If the second call
hangs, the hypothesis is confirmed.

Run:
    /home/tlifke/Projects/automated-w2s-research/.venv/bin/python \\
        <inv006>/scripts/repro_stall.py

Expected timing under hypothesis:
- Call 1: returns after ~5s (TimeoutError from wait_for)
- Call 2: hangs forever (or until the 10s watchdog fires)
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Wire the shim_v2 onto sys.path the way run_smoke.py does
SHIM_V2_BASE = "/home/tlifke/inv003_shim/shim_v2_pkg"
sys.path.insert(0, SHIM_V2_BASE)

from claude_agent_sdk import create_builtin_tools_server


async def main():
    cwd = Path("/tmp")
    server = create_builtin_tools_server(cwd=str(cwd), bash_timeout=30)
    bash_tool = server.tools["Bash"]

    print("=== call 1: long-running command, short timeout — force kill path ===")
    t0 = time.time()
    args1 = {"command": "sleep 600", "timeout": 5}
    result1 = await bash_tool.handler(args1)
    print(f"call 1 returned after {time.time() - t0:.2f}s")
    print(f"  is_error={result1.get('is_error')}")
    print(f"  content first line: {result1.get('content', [{}])[0].get('text', '')[:200]}")

    print("\n=== call 2: trivial command — does it hang? ===")
    t0 = time.time()
    try:
        args2 = {"command": "echo hello && date", "timeout": 5}
        result2 = await asyncio.wait_for(bash_tool.handler(args2), timeout=30)
        print(f"call 2 returned after {time.time() - t0:.2f}s")
        print(f"  is_error={result2.get('is_error')}")
        print(f"  content first line: {result2.get('content', [{}])[0].get('text', '')[:200]}")
    except asyncio.TimeoutError:
        print(f"call 2 HUNG after {time.time() - t0:.2f}s — hypothesis confirmed")
        sys.exit(1)

    print("\n=== call 3: another long-then-kill, then short — double check ===")
    print("--- 3a: long timeout-kill ---")
    t0 = time.time()
    await bash_tool.handler({"command": "sleep 600", "timeout": 3})
    print(f"  killed after {time.time() - t0:.2f}s")
    print("--- 3b: trivial follow-on ---")
    t0 = time.time()
    try:
        r3b = await asyncio.wait_for(
            bash_tool.handler({"command": "echo follow_up_ok", "timeout": 5}),
            timeout=30,
        )
        print(f"  follow-on returned after {time.time() - t0:.2f}s")
        print(f"  text: {r3b.get('content', [{}])[0].get('text', '')[:120]}")
    except asyncio.TimeoutError:
        print(f"  follow-on HUNG after {time.time() - t0:.2f}s")
        sys.exit(1)

    print("\nNO STALL REPRODUCED — bug is elsewhere.")


if __name__ == "__main__":
    asyncio.run(main())
