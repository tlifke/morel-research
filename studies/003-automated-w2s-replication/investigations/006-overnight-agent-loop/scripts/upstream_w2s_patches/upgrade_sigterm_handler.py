#!/usr/bin/env python3
"""inv 006: upgrade the SIGTERM handler to be print-failure-tolerant.

Run 1 sanity check (2026-06-01) found: when the bash launcher's
SIGTERM-trap killed `tee` first (a separate launcher bug; see
run_overnight.sh fix), the python's stdout pipe was broken. Then on
the second SIGTERM, the agent's signal handler tried
`print(\"...\", flush=True)` FIRST and raised BrokenPipeError, which
killed the process before `_should_stop_after_session` was set. The
loop never saw the flag; \"clean stop at session boundary\" never
fired.

Fixes both root causes in the handler body:

1. Set the flag FIRST; output is best-effort.
2. Write to stderr (not stdout) so a broken stdout pipe doesn't
   affect the signal path.
3. Wrap the write in try/except so any failure is swallowed.

Run on desktop after apply_agent_resume.py has already executed:

    /home/tlifke/Projects/automated-w2s-research/.venv/bin/python \\
        <inv006>/scripts/upstream_w2s_patches/upgrade_sigterm_handler.py
"""
from __future__ import annotations
from pathlib import Path

AGENT_PY = Path(
    "/home/tlifke/Projects/automated-w2s-research/"
    "w2s_research/research_loop/agent.py"
)


def patch() -> bool:
    src = AGENT_PY.read_text()
    old = (
        "        try:\n"
        "            import signal as _signal\n"
        "            def _on_sigterm(_signum, _frame):\n"
        "                print(\"\\n[Loop] SIGTERM — will stop after current session boundary\", flush=True)\n"
        "                self._should_stop_after_session = True\n"
        "            _signal.signal(_signal.SIGTERM, _on_sigterm)\n"
    )
    new = (
        "        try:\n"
        "            import signal as _signal\n"
        "            def _on_sigterm(_signum, _frame):\n"
        "                # Flag-set FIRST so we never lose the signal even if\n"
        "                # later side-effects raise (inv 006: prior handler put\n"
        "                # `print(flush=True)` first; a broken stdout pipe made\n"
        "                # the whole handler raise BrokenPipeError, killing the\n"
        "                # process before the flag was set).\n"
        "                self._should_stop_after_session = True\n"
        "                try:\n"
        "                    import sys as _sys\n"
        "                    _sys.stderr.write(\"\\n[Loop] SIGTERM — will stop after current session boundary\\n\")\n"
        "                    _sys.stderr.flush()\n"
        "                except Exception:\n"
        "                    pass\n"
        "            _signal.signal(_signal.SIGTERM, _on_sigterm)\n"
    )
    if new in src:
        print("[agent.py] already has robust handler")
        return False
    if old not in src:
        print("[agent.py] old handler block not found — already a different version?")
        return False
    AGENT_PY.write_text(src.replace(old, new))
    print("[agent.py] SIGTERM handler upgraded: flag-set-first, stderr, try/except")
    return True


if __name__ == "__main__":
    patch()
